import asyncio
import os
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from core.config import (
    MAX_ASSISTANT_MESSAGE_CHARS,
    PROVIDER_SELECTION_TIMEOUT_SECONDS,
    PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS,
    TRUST_PROXY_HEADERS,
)
from core.redis import get_chat_history, save_message_to_redis
from core.security import is_rate_limited
from core.session_auth import (
    SessionConfigurationError,
    create_session_credentials,
    verify_session_token,
)
from models.schemas import ChatRequest, Message
from services.ai import PROVIDER_SPECS, ProviderFactory
from services.local_fallback import build_local_fallback
from services.provider_health import record_provider_result
from services.telemetry import hash_visitor, log_event, log_message, schedule, touch_session

router = APIRouter()

STREAM_HEADERS = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache",
}


def _client_ip(request: Request) -> str:
    fallback = request.client.host if request.client is not None else "127.0.0.1"
    if not TRUST_PROXY_HEADERS:
        return fallback
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or fallback


def _message_text(message: Message) -> str:
    if message.content:
        return message.content
    if message.parts:
        return "".join(
            str(part.get("text", ""))
            for part in message.parts
            if isinstance(part, dict)
        )
    return ""


def _require_session_access(request: Request, session_id: str) -> None:
    token = request.headers.get("x-session-token", "")
    try:
        valid = verify_session_token(session_id, token)
    except SessionConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Chat sessions are not configured.") from exc
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or expired chat session.")


async def _close_generator(generator: AsyncGenerator[str, None] | None) -> None:
    if generator is None:
        return
    try:
        await generator.aclose()
    except Exception:
        pass


async def _create_provider_stream(
    provider_name: str,
    model_name: str,
    factory: ProviderFactory,
    messages: list[Message],
    timeout_seconds: float,
    session_id: Optional[str],
) -> Optional[StreamingResponse]:
    started_at = time.perf_counter()
    generator: AsyncGenerator[str, None] | None = None
    schedule(
        log_event(
            "provider_attempt",
            session_id=session_id,
            provider=provider_name,
            model=model_name,
        )
    )

    try:
        generator = factory(messages, session_id)
        first_chunk = await asyncio.wait_for(generator.__anext__(), timeout=timeout_seconds)
    except StopAsyncIteration:
        record_provider_result(provider_name, available=False, reason="empty_response")
        await _close_generator(generator)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[{provider_name}] Empty response")
        schedule(
            log_event(
                "provider_failure",
                session_id=session_id,
                provider=provider_name,
                model=model_name,
                latency_ms=elapsed_ms,
                metadata={"reason": "empty_response"},
            )
        )
        return None
    except asyncio.TimeoutError:
        record_provider_result(provider_name, available=False, reason="first_token_timeout")
        await _close_generator(generator)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[{provider_name}] First token timed out after {elapsed_ms}ms")
        schedule(
            log_event(
                "provider_failure",
                session_id=session_id,
                provider=provider_name,
                model=model_name,
                latency_ms=elapsed_ms,
                metadata={
                    "reason": "first_token_timeout",
                    "timeout_ms": int(timeout_seconds * 1000),
                },
            )
        )
        return None
    except Exception as exc:
        record_provider_result(provider_name, available=False, reason=type(exc).__name__)
        await _close_generator(generator)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[{provider_name}] Failed before streaming: {type(exc).__name__}")
        schedule(
            log_event(
                "provider_failure",
                session_id=session_id,
                provider=provider_name,
                model=model_name,
                latency_ms=elapsed_ms,
                metadata={"reason": type(exc).__name__},
            )
        )
        return None

    first_token_ms = int((time.perf_counter() - started_at) * 1000)
    record_provider_result(provider_name, available=True)
    schedule(
        log_event(
            "provider_selected",
            session_id=session_id,
            provider=provider_name,
            model=model_name,
            latency_ms=first_token_ms,
            metadata={"metric": "first_token_ms"},
        )
    )
    initial_chunk = first_chunk

    async def stream() -> AsyncGenerator[str, None]:
        full_response = ""
        status = "ok"
        if initial_chunk:
            safe_initial_chunk = initial_chunk[:MAX_ASSISTANT_MESSAGE_CHARS]
            full_response = safe_initial_chunk
            yield safe_initial_chunk

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        generator.__anext__(),
                        timeout=PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS,
                    )
                except StopAsyncIteration:
                    break
                remaining = MAX_ASSISTANT_MESSAGE_CHARS - len(full_response)
                if remaining <= 0:
                    status = "truncated"
                    break
                safe_chunk = chunk[:remaining]
                full_response += safe_chunk
                yield safe_chunk
                if len(safe_chunk) < len(chunk):
                    status = "truncated"
                    break
        except asyncio.TimeoutError:
            status = "interrupted"
            print(f"[{provider_name}] Stream stalled")
            safe_error = "\n\nZero's upstream connection stalled. Try that again."
            full_response += safe_error
            yield safe_error
            schedule(
                log_event(
                    "stream_interrupted",
                    session_id=session_id,
                    provider=provider_name,
                    model=model_name,
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                    metadata={
                        "reason": "stream_idle_timeout",
                        "timeout_ms": int(PROVIDER_STREAM_IDLE_TIMEOUT_SECONDS * 1000),
                    },
                )
            )
        except Exception as exc:
            status = "interrupted"
            print(f"[{provider_name}] Streaming interrupted: {type(exc).__name__}")
            safe_error = "\n\nZero lost the upstream connection. Try that again."
            full_response += safe_error
            yield safe_error
            schedule(
                log_event(
                    "stream_interrupted",
                    session_id=session_id,
                    provider=provider_name,
                    model=model_name,
                    latency_ms=int((time.perf_counter() - started_at) * 1000),
                    metadata={"reason": type(exc).__name__},
                )
            )
        finally:
            await _close_generator(generator)

        total_latency_ms = int((time.perf_counter() - started_at) * 1000)
        if session_id and full_response.strip():
            await save_message_to_redis(
                session_id,
                {"role": "assistant", "content": full_response},
            )
            schedule(touch_session(session_id))
            schedule(
                log_message(
                    session_id,
                    "assistant",
                    full_response,
                    provider=provider_name,
                    model=model_name,
                    latency_ms=total_latency_ms,
                    status=status,
                )
            )
            schedule(
                log_event(
                    "response_complete",
                    session_id=session_id,
                    provider=provider_name,
                    model=model_name,
                    latency_ms=total_latency_ms,
                    metadata={"status": status},
                )
            )

    return StreamingResponse(stream(), media_type="text/plain", headers=STREAM_HEADERS)


@router.post("/chat/session")  # type: ignore[untyped-decorator]
async def create_chat_session(response: Response) -> dict[str, str | int]:
    try:
        credentials = create_session_credentials()
    except SessionConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Chat sessions are not configured.") from exc
    response.headers["Cache-Control"] = "no-store"
    return {
        "session_id": credentials.session_id,
        "session_token": credentials.token,
        "expires_at": credentials.expires_at,
    }


@router.get("/chat/history/{session_id}")  # type: ignore[untyped-decorator]
async def get_history(
    request: Request,
    response: Response,
    session_id: str,
) -> dict[str, list[Message]]:
    _require_session_access(request, session_id)
    history = await get_chat_history(session_id)
    response.headers["Cache-Control"] = "no-store"
    return {"messages": history}


@router.post("/chat")  # type: ignore[untyped-decorator]
async def chat_endpoint(request: Request, body: ChatRequest) -> StreamingResponse:
    session_id = body.session_id
    client_ip = _client_ip(request)

    _require_session_access(request, session_id)

    if await is_rate_limited(client_ip):
        schedule(log_event("rate_limited", session_id=session_id))
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    messages = body.messages[-10:]

    if messages:
        latest_user_msg = messages[-1]
        if latest_user_msg.role == "user":
            user_text = _message_text(latest_user_msg)
            await save_message_to_redis(session_id, latest_user_msg.model_dump())
            schedule(
                touch_session(
                    session_id,
                    visitor_hash=hash_visitor(client_ip),
                    user_agent=request.headers.get("user-agent"),
                    referrer=request.headers.get("referer"),
                )
            )
            if user_text:
                schedule(log_message(session_id, "user", user_text))

    selection_started_at = time.perf_counter()
    for provider in PROVIDER_SPECS:
        provider_name = provider.name
        model_name = provider.model
        factory = provider.factory
        api_key = os.environ.get(provider.api_key_env)
        if not api_key:
            continue

        elapsed_seconds = time.perf_counter() - selection_started_at
        remaining_seconds = PROVIDER_SELECTION_TIMEOUT_SECONDS - elapsed_seconds
        if remaining_seconds <= 0:
            break
        timeout_seconds = min(provider.first_token_timeout, remaining_seconds)

        response = await _create_provider_stream(
            provider_name,
            model_name,
            factory,
            messages,
            timeout_seconds,
            session_id,
        )
        if response is not None:
            return response

    async def fallback_stream() -> AsyncGenerator[str, None]:
        fallback_msg = build_local_fallback(messages)
        yield fallback_msg
        if session_id:
            await save_message_to_redis(
                session_id,
                {"role": "assistant", "content": fallback_msg},
            )
            schedule(touch_session(session_id))
            schedule(
                log_message(
                    session_id,
                    "assistant",
                    fallback_msg,
                    status="providers_unavailable",
                )
            )
            schedule(log_event("all_providers_unavailable", session_id=session_id))

    return StreamingResponse(
        fallback_stream(),
        media_type="text/plain",
        headers=STREAM_HEADERS,
    )
