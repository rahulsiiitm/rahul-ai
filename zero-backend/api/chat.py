import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest
from core.security import is_rate_limited
from services.ai import gemini_generator, xai_generator

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    # Rate Limiting
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
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
            
            async def stream():
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
                
            async def stream():
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
            
    raise HTTPException(status_code=500, detail="Failed to connect to AI providers.")
