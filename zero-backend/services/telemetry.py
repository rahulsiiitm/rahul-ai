import asyncio
import hashlib
import hmac
import os
from typing import Any, Coroutine, Dict, Optional

import httpx


def _config() -> Optional[tuple[str, str]]:
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        return None
    return url.rstrip("/"), service_key.strip('"').strip("'")


def telemetry_enabled() -> bool:
    return _config() is not None


def hash_visitor(value: str) -> Optional[str]:
    salt = os.environ.get("TELEMETRY_HASH_SALT")
    if not value or not salt:
        return None
    return hmac.new(
        salt.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _headers(service_key: str) -> Dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


async def _post(table: str, payload: Dict[str, Any]) -> None:
    config = _config()
    if not config:
        return

    base_url, service_key = config
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{base_url}/rest/v1/{table}",
                headers=_headers(service_key),
                json=payload,
            )
            if response.status_code >= 400:
                print(f"[TELEMETRY] {table} write failed: {response.status_code} {response.text[:200]}")
    except Exception as exc:
        print(f"[TELEMETRY] {table} write failed: {exc}")


async def _rpc(function_name: str, payload: Dict[str, Any]) -> None:
    config = _config()
    if not config:
        return

    base_url, service_key = config
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{base_url}/rest/v1/rpc/{function_name}",
                headers=_headers(service_key),
                json=payload,
            )
            if response.status_code >= 400:
                print(f"[TELEMETRY] RPC {function_name} failed: {response.status_code} {response.text[:200]}")
    except Exception as exc:
        print(f"[TELEMETRY] RPC {function_name} failed: {exc}")


def schedule(coro: Coroutine[Any, Any, Any]) -> None:
    async def safe_run() -> None:
        try:
            await coro
        except Exception as exc:
            print(f"[TELEMETRY] background task failed: {exc}")

    try:
        asyncio.create_task(safe_run())
    except RuntimeError:
        coro.close()


async def touch_session(
    session_id: str,
    *,
    visitor_hash: Optional[str] = None,
    user_agent: Optional[str] = None,
    referrer: Optional[str] = None,
) -> None:
    await _rpc(
        "touch_zero_session",
        {
            "p_session_id": session_id,
            "p_visitor_hash": visitor_hash,
            "p_user_agent": user_agent,
            "p_referrer": referrer,
        },
    )


async def log_message(
    session_id: str,
    role: str,
    content: str,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    latency_ms: Optional[int] = None,
    status: str = "ok",
) -> None:
    await _post(
        "zero_messages",
        {
            "session_id": session_id,
            "role": role,
            "content": content,
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "status": status,
        },
    )


async def log_event(
    event_type: str,
    *,
    session_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    latency_ms: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    await _post(
        "zero_events",
        {
            "session_id": session_id,
            "event_type": event_type,
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
        },
    )


async def log_lead(session_id: Optional[str], email: str, message: str) -> None:
    await _post(
        "zero_leads",
        {
            "session_id": session_id,
            "email": email,
            "message": message,
            "status": "new",
        },
    )
