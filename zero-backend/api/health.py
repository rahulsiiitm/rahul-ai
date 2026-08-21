import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.ai import PROVIDER_SPECS
from services.provider_health import provider_status

router = APIRouter()


@router.get("/keep-alive")  # type: ignore[untyped-decorator]
async def keep_alive_endpoint() -> Dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")  # type: ignore[untyped-decorator]
async def readiness_endpoint() -> Dict[str, str]:
    session_secret = os.environ.get("CHAT_SESSION_SECRET") or os.environ.get("TELEMETRY_HASH_SALT", "")
    if len(session_secret.strip().strip('"').strip("'")) < 32:
        raise HTTPException(status_code=503, detail="Chat backend is not ready.")
    return {"status": "ready", "mode": "hosted_or_local"}


@router.get("/health/providers")  # type: ignore[untyped-decorator]
async def provider_health_endpoint() -> Dict[str, Any]:
    providers = {
        spec.name: {
            "configured": bool(os.environ.get(spec.api_key_env)),
            **provider_status(spec.name),
        }
        for spec in PROVIDER_SPECS
    }
    configured = [item for item in providers.values() if item["configured"]]
    if any(item["available"] is True for item in configured):
        state = "available"
    elif configured and all(item["available"] is None for item in configured):
        state = "unknown"
    else:
        state = "degraded"
    return {"status": state, "local_fallback": True, "providers": providers}
