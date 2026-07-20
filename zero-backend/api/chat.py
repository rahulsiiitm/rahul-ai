import os
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.security import is_rate_limited
from models.schemas import ChatRequest
from services.ai import gemini_generator, xai_generator

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest) -> StreamingResponse:
    # Rate Limiting
    client_ip = request.client.host if request.client is not None else "127.0.0.1"
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or client_ip
    if is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    
    messages = body.messages[:10]
    
    # Try Gemini first
    if os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        try:
            generator = gemini_generator(messages)
            try:
                first_chunk = await generator.__anext__()
            except StopAsyncIteration:
                first_chunk = ""
            
            async def stream() -> AsyncGenerator[str, None]:
                if first_chunk: yield first_chunk
                async for chunk in generator:
                    yield chunk
                
            headers = {
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            return StreamingResponse(stream(), media_type="text/plain", headers=headers)
        except Exception as e:
            print(f"Gemini failed: {e}")
            pass
            
    # Fallback to xAI
    if os.environ.get("GROQ_API_KEY"):
        try:
            generator = xai_generator(messages)
            try:
                first_chunk = await generator.__anext__()
            except StopAsyncIteration:
                first_chunk = ""
                
            async def stream() -> AsyncGenerator[str, None]:
                if first_chunk: yield first_chunk
                async for chunk in generator:
                    yield chunk
                
            headers = {
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
            return StreamingResponse(stream(), media_type="text/plain", headers=headers)
        except Exception as e:
            print(f"xAI failed: {e}")
            pass
            
    async def fallback_stream() -> AsyncGenerator[str, None]:
        yield '🏎️ "Zero left the pit..."\n\nIf you are seeing this msg then probably my free api credits are gone please try again later hehehe'
        
    return StreamingResponse(
        fallback_stream(),
        media_type="text/plain",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
