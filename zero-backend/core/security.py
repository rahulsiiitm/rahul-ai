import os
import time
from typing import Any, Dict

import httpx

from core.config import RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS

rate_limit_map: Dict[str, Dict[str, Any]] = {}


def _memory_rate_limited(ip: str) -> bool:
    now = int(time.time() * 1000)
    expired = [k for k, v in rate_limit_map.items() if now > v["reset_at"]]
    for key in expired:
        del rate_limit_map[key]

    entry = rate_limit_map.get(ip)
    if not entry:
        rate_limit_map[ip] = {"count": 1, "reset_at": now + RATE_LIMIT_WINDOW_MS}
        return False

    entry["count"] += 1
    return int(entry["count"]) > RATE_LIMIT_MAX


async def is_rate_limited(ip: str) -> bool:
    """Use Upstash for distributed rate limiting, with an in-memory dev fallback."""
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return _memory_rate_limited(ip)

    url = url.strip('"').strip("'").rstrip("/")
    token = token.strip('"').strip("'")
    headers = {"Authorization": f"Bearer {token}"}
    key = f"rate-limit:{ip}"
    script = (
        "local current = redis.call('INCR', KEYS[1]); "
        "if current == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]); end; "
        "return current"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=["EVAL", script, 1, key, RATE_LIMIT_WINDOW_MS],
                timeout=3.0,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            count = int(payload.get("result", 0))
            return count > RATE_LIMIT_MAX
    except Exception as exc:
        print(f"[RATE LIMIT] Redis unavailable, using local fallback: {type(exc).__name__}")
        return _memory_rate_limited(ip)
