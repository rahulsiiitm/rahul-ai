import asyncio
import os
from typing import AsyncGenerator, Callable, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.config import TRUST_PROXY_HEADERS
from core.redis import delete_chat_history, get_chat_history, save_message_to_redis
from core.security import is_rate_limited
from models.schemas import ChatRequest, Message
from services.ai import gemini_generator, groq_generator, openrouter_generator

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


async def _create_provider_stream(
    provider_name: str,
    factory: ProviderFactory,
    messages: list[Message],
    timeout_seconds: float,
    session_id: Optional[str],
) -> Optional[StreamingResponse]:
    try:
        generator = factory(messages)
        first_chunk = await asyncio.wait_for(generator.__anext__(), timeout=timeout_seconds)
    except StopAsyncIteration:
        print(f"[{provider_name}] Empty response")
        return None
    except Exception as exc:
        print(f"[{provider_name}] Failed before streaming: {exc}")
        return None

    async def stream() -> AsyncGenerator[str, None]:
        full_response = ""
        if first_chunk:
            full_response += first_chunk
            yield first_chunk

        try:
            async for chunk in generator:
                full_response += chunk
                yield chunk
        except Exception as exc:
            print(f"[{provider_name}] Streaming interrupted: {exc}")
            safe_error = "\n\nZero lost the upstream connection. Try that again."
            full_response += safe_error
            yield safe_error

        if session_id and full_response.strip():
            await save_message_to_redis(
                session_id,
                {"role": "model", "content": full_response},
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
    return {"status": "cleared"}


@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest) -> StreamingResponse:
    if await is_rate_limited(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")

    messages = body.messages[-10:]
    session_id = body.session_id

    if session_id and messages:
        latest_user_msg = messages[-1]
        if latest_user_msg.role == "user":
            await save_message_to_redis(session_id, latest_user_msg.model_dump())

    providers: list[Tuple[str, Optional[str], ProviderFactory, float]] = [
        ("Groq", os.environ.get("GROQ_API_KEY"), groq_generator, 30.0),
        ("OpenRouter", os.environ.get("OPENROUTER_API_KEY"), openrouter_generator, 30.0),
        ("Gemini", os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"), gemini_generator, 5.0),
    ]

    for provider_name, api_key, factory, timeout_seconds in providers:
        if not api_key:
            continue
        response = await _create_provider_stream(
            provider_name,
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

    return StreamingResponse(
        fallback_stream(),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
