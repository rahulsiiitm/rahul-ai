import asyncio
import os
import time
from typing import AsyncGenerator, Callable, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.config import TRUST_PROXY_HEADERS
from core.redis import delete_chat_history, get_chat_history, save_message_to_redis
from core.security import is_rate_limited
from models.schemas import ChatRequest, Message
from services.ai import gemini_generator, groq_generator, openrouter_generator
from services.telemetry import hash_visitor, log_event, log_message, schedule, touch_session

router = APIRouter()

STREAM_HEADERS = {
    "X-Accel-Buffering": "no",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}

ProviderFactory = Callable[[list[Message]], AsyncGenerator[str, None]]


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


async def _create_provider_stream(
    provider_name: str,
    model_name: str,
    factory: ProviderFactory,
    messages: list[Message],
    timeout_seconds: float,
    session_id: Optional[str],
) -> Optional[StreamingResponse]:
    started_at = time.perf_counter()
    schedule(
        log_event(
            "provider_attempt",
            session_id=session_id,
            provider=provider_name,
            model=model_name,
        )
    )

    try:
        generator = factory(messages)
        first_chunk = await asyncio.wait_for(generator.__anext__(), timeout=timeout_seconds)
    except StopAsyncIteration:
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
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        print(f"[{provider_name}] Failed before streaming: {exc}")
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

    async def stream() -> AsyncGenerator[str, None]:
        full_response = ""
        status = "ok"
        if first_chunk:
            full_response += first_chunk
            yield first_chunk

        try:
            async for chunk in generator:
                full_response += chunk
                yield chunk
        except Exception as exc:
            status = "interrupted"
            print(f"[{provider_name}] Streaming interrupted: {exc}")
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

        total_latency_ms = int((time.perf_counter() - started_at) * 1000)
        if session_id and full_response.strip():
            await save_message_to_redis(
                session_id,
                {"role": "model", "content": full_response},
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

    return StreamingResponse(stream(), media_type="text/event-stream", headers=STREAM_HEADERS)


@router.get("/chat/history/{session_id}")
async def get_history(session_id: str):
    history = await get_chat_history(session_id)
    return {"messages": history}


@router.delete("/chat/history/{session_id}")
async def clear_history(session_id: str):
    deleted = await delete_chat_history(session_id)
    if not deleted:
        raise HTTPException(status_code=503, detail="Could not clear conversation history.")
    schedule(log_event("history_cleared", session_id=session_id))
    return {"status": "cleared"}


@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest) -> StreamingResponse:
    session_id = body.session_id
    client_ip = _client_ip(request)

    if await is_rate_limited(client_ip):
        schedule(log_event("rate_limited", session_id=session_id))
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    messages = body.messages[-10:]

    if session_id and messages:
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

    providers: list[Tuple[str, str, Optional[str], ProviderFactory, float]] = [
        ("Groq", "llama-3.3-70b-versatile", os.environ.get("GROQ_API_KEY"), groq_generator, 30.0),
        ("OpenRouter", "openrouter/auto", os.environ.get("OPENROUTER_API_KEY"), openrouter_generator, 30.0),
        ("Gemini", "gemini-2.0-flash", os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"), gemini_generator, 5.0),
    ]

    for provider_name, model_name, api_key, factory, timeout_seconds in providers:
        if not api_key:
            continue
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
        fallback_msg = (
            '🏎️ "Zero left the pit..."\n\n'
            "My upstream providers are unavailable right now. Try again in a bit."
        )
        yield fallback_msg
        if session_id:
            await save_message_to_redis(
                session_id,
                {"role": "model", "content": fallback_msg},
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
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
