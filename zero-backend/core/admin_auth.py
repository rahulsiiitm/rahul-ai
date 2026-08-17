import hmac
import os

from fastapi import Header, HTTPException


def require_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("ZERO_ADMIN_API_KEY", "").strip().strip('"').strip("'")
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="Admin deletion API is not configured.")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
