import time
from typing import Any

_provider_state: dict[str, dict[str, Any]] = {}


def record_provider_result(provider: str, *, available: bool, reason: str = "") -> None:
    _provider_state[provider] = {
        "available": available,
        "reason": reason,
        "checked_at": int(time.time()),
    }


def provider_status(provider: str) -> dict[str, Any]:
    return _provider_state.get(provider, {"available": None, "reason": "not_checked", "checked_at": None})
