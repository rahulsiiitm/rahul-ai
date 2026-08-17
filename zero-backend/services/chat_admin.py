import asyncio
import os
from typing import Sequence

import httpx

from core.redis import delete_all_chat_histories, delete_chat_histories


class ChatDeletionConfigurationError(RuntimeError):
    pass


def _supabase_config() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
    if not url or not service_key:
        raise ChatDeletionConfigurationError("Supabase deletion credentials are not configured.")
    return url, service_key


def _headers(service_key: str) -> dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
        "Prefer": "return=minimal",
    }


async def _delete_table(
    client: httpx.AsyncClient,
    base_url: str,
    service_key: str,
    table: str,
    params: dict[str, str],
) -> None:
    response = await client.delete(
        f"{base_url}/rest/v1/{table}",
        headers=_headers(service_key),
        params=params,
    )
    response.raise_for_status()


async def _delete_supabase_sessions(session_ids: Sequence[str] | None) -> None:
    base_url, service_key = _supabase_config()
    if session_ids is None:
        session_filter = {"session_id": "not.is.null"}
        row_filter = {"id": "not.is.null"}
    else:
        value = f"in.({','.join(session_ids)})"
        session_filter = {"session_id": value}
        row_filter = session_filter

    async with httpx.AsyncClient(timeout=15.0) as client:
        await asyncio.gather(
            _delete_table(client, base_url, service_key, "zero_messages", row_filter),
            _delete_table(client, base_url, service_key, "zero_events", row_filter),
            _delete_table(client, base_url, service_key, "zero_leads", row_filter),
        )
        await _delete_table(client, base_url, service_key, "zero_sessions", session_filter)


async def delete_selected_chats(session_ids: Sequence[str]) -> dict[str, int | str]:
    await _delete_supabase_sessions(session_ids)
    redis_deleted = await delete_chat_histories(session_ids)
    return {
        "scope": "selected",
        "sessions_requested": len(session_ids),
        "redis_histories_deleted": redis_deleted,
    }


async def delete_all_chats() -> dict[str, int | str]:
    await _delete_supabase_sessions(None)
    redis_deleted = await delete_all_chat_histories()
    return {
        "scope": "all",
        "sessions_requested": -1,
        "redis_histories_deleted": redis_deleted,
    }
