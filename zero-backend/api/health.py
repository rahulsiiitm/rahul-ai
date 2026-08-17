import os
from typing import Dict

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/keep-alive")
async def keep_alive_endpoint() -> Dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_endpoint() -> Dict[str, str]:
    provider_ready = any(
        os.environ.get(name)
        for name in ("GROQ_API_KEY", "OPENROUTER_API_KEY")
    )
    session_secret = os.environ.get("CHAT_SESSION_SECRET") or os.environ.get("TELEMETRY_HASH_SALT", "")
    if not provider_ready or len(session_secret.strip().strip('"').strip("'")) < 32:
        raise HTTPException(status_code=503, detail="Chat backend is not ready.")
    return {"status": "ready"}
