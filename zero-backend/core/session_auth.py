import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from uuid import UUID, uuid4

from core.config import SESSION_TOKEN_TTL_SECONDS


class SessionConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SessionCredentials:
    session_id: str
    token: str
    expires_at: int


def _secret() -> bytes:
    value = (
        os.environ.get("CHAT_SESSION_SECRET")
        or os.environ.get("TELEMETRY_HASH_SALT", "")
    ).strip().strip('"').strip("'")
    if len(value) < 32:
        raise SessionConfigurationError("CHAT_SESSION_SECRET must contain at least 32 characters.")
    return value.encode("utf-8")


def _signature(payload: str) -> str:
    digest = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def create_session_credentials(now: int | None = None) -> SessionCredentials:
    issued_at = int(time.time() if now is None else now)
    session_id = str(uuid4())
    payload = f"v1.{session_id}.{issued_at}"
    return SessionCredentials(
        session_id=session_id,
        token=f"{payload}.{_signature(payload)}",
        expires_at=issued_at + SESSION_TOKEN_TTL_SECONDS,
    )


def verify_session_token(session_id: str, token: str, now: int | None = None) -> bool:
    try:
        UUID(session_id)
        version, token_session_id, issued_at_raw, supplied_signature = token.split(".", 3)
        issued_at = int(issued_at_raw)
    except (TypeError, ValueError):
        return False

    current_time = int(time.time() if now is None else now)
    if version != "v1" or token_session_id != session_id:
        return False
    if issued_at > current_time + 60 or current_time - issued_at > SESSION_TOKEN_TTL_SECONDS:
        return False

    payload = f"{version}.{token_session_id}.{issued_at}"
    return hmac.compare_digest(supplied_signature, _signature(payload))
