import asyncio
import os
import time
from typing import AsyncGenerator

BOOT_TIME = time.time()
WAKEUP_GREETING_SENT = False

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.security import is_rate_limited
from core.redis import save_message_to_redis, get_chat_history
from models.schemas import ChatRequest
from services.ai import gemini_generator, openrouter_generator

router = APIRouter()

@router.get("/chat/history/{session_id}")
async def get_history(session_id: str):
    history = await get_chat_history(session_id)
    return {"messages": history}

@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest) -> StreamingResponse:
    global WAKEUP_GREETING_SENT
    
    is_cold_start = False
    if not WAKEUP_GREETING_SENT and (time.time() - BOOT_TIME < 120):
        is_cold_start = True
        WAKEUP_GREETING_SENT = True
        
    # Rate Limiting
    client_ip = request.client.host if request.client is not None else "127.0.0.1"
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or client_ip
    if is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    
    messages = body.messages[-10:]
    session_id = body.session_id
    
    if session_id and messages:
        # Save the latest user message to Redis (assuming the last message is the user's prompt)
        latest_user_msg = messages[-1]
        if latest_user_msg.role == "user":
            await save_message_to_redis(session_id, latest_user_msg.dict())

    # Try Groq first
    if os.environ.get("GROQ_API_KEY"):
        try:
            from services.ai import groq_generator
            generator = groq_generator(messages)
            try:
                first_chunk = await asyncio.wait_for(generator.__anext__(), timeout=30.0)
            except StopAsyncIteration:
                raise Exception("Empty response from provider")
                
            async def stream() -> AsyncGenerator[str, None]:
                full_response = ""
                if is_cold_start:
                    cold_start_msg = "*(Stretches my circuits)* Okay, I'm awake! Ready to talk. 🏎️\n\n"
                    full_response += cold_start_msg
                    yield cold_start_msg
                if first_chunk: 
                    full_response += first_chunk
                    yield first_chunk
                
                try:
                    async for chunk in generator:
                        full_response += chunk
                        yield chunk
                except Exception as e:
                    error_msg = f"\n\n[System: Connection interrupted. {e}]"
                    full_response += error_msg
                    yield error_msg
                
                if session_id and full_response.strip():
                    await save_message_to_redis(session_id, {"role": "model", "content": full_response})
                
            headers = {
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
        except Exception as e:
            print(f"Groq failed: {e}")
            pass

    # Try OpenRouter next
    if os.environ.get("OPENROUTER_API_KEY"):
        try:
            generator = openrouter_generator(messages)
            try:
                first_chunk = await asyncio.wait_for(generator.__anext__(), timeout=30.0)
            except StopAsyncIteration:
                raise Exception("Empty response from provider")
                
            async def stream() -> AsyncGenerator[str, None]:
                full_response = ""
                if is_cold_start:
                    cold_start_msg = "*(Stretches my circuits)* Okay, I'm awake! Ready to talk. 🏎️\n\n"
                    full_response += cold_start_msg
                    yield cold_start_msg
                if first_chunk: 
                    full_response += first_chunk
                    yield first_chunk
                
                try:
                    async for chunk in generator:
                        full_response += chunk
                        yield chunk
                except Exception as e:
                    error_msg = f"\n\n[System: Connection interrupted. {e}]"
                    full_response += error_msg
                    yield error_msg
                
                if session_id and full_response.strip():
                    await save_message_to_redis(session_id, {"role": "model", "content": full_response})
                
            headers = {
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
        except Exception as e:
            print(f"OpenRouter failed: {e}")
            pass

    # Fallback to Gemini
    if os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        try:
            generator = gemini_generator(messages)
            try:
                first_chunk = await asyncio.wait_for(generator.__anext__(), timeout=3.0)
            except StopAsyncIteration:
                raise Exception("Empty response from provider")
            
            async def stream() -> AsyncGenerator[str, None]:
                full_response = ""
                if is_cold_start:
                    cold_start_msg = "*(Stretches my circuits)* Okay, I'm awake! Ready to talk. 🏎️\n\n"
                    full_response += cold_start_msg
                    yield cold_start_msg
                if first_chunk: 
                    full_response += first_chunk
                    yield first_chunk
                
                try:
                    async for chunk in generator:
                        full_response += chunk
                        yield chunk
                except Exception as e:
                    error_msg = f"\n\n[System: Connection interrupted. {e}]"
                    full_response += error_msg
                    yield error_msg
                    
                if session_id and full_response.strip():
                    await save_message_to_redis(session_id, {"role": "model", "content": full_response})
                
            headers = {
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
        except Exception as e:
            print(f"Gemini failed: {e}")
            pass

    async def fallback_stream() -> AsyncGenerator[str, None]:
        full_response = ""
        if is_cold_start:
            cold_start_msg = "*(Stretches my circuits)* Okay, I'm awake! Ready to talk. 🏎️\n\n"
            full_response += cold_start_msg
            yield cold_start_msg
            
        fallback_msg = '🏎️ "Zero left the pit..."\n\nIf you are seeing this msg then probably my free api credits are gone please try again later hehehe'
        full_response += fallback_msg
        yield fallback_msg
        
        if session_id:
            await save_message_to_redis(session_id, {"role": "model", "content": full_response})
        
    return StreamingResponse(
        fallback_stream(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
