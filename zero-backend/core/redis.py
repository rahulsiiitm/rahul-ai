import json
import os
from typing import Any, List, Sequence

import httpx

from models.schemas import Message


def _redis_config() -> tuple[str, str] | None:
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    return url.strip('"').strip("'").rstrip("/"), token.strip('"').strip("'")


async def _command(*arguments: Any) -> Any:
    config = _redis_config()
    if not config:
        return None

    url, token = config
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, headers=headers, json=list(arguments))
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        return payload.get("result")


async def _pipeline(commands: Sequence[Sequence[Any]]) -> list[dict[str, Any]]:
    config = _redis_config()
    if not config or not commands:
        return []

    url, token = config
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{url}/pipeline", headers=headers, json=commands)
        response.raise_for_status()
        results = response.json()
        if not isinstance(results, list):
            raise RuntimeError("Unexpected Redis pipeline response.")
        errors = [str(item["error"]) for item in results if isinstance(item, dict) and item.get("error")]
        if errors:
            raise RuntimeError("; ".join(errors))
        return results


async def save_message_to_redis(session_id: str, message: dict[str, Any]) -> None:
    if not _redis_config():
        return

    key = f"chat:{session_id}"
    try:
        await _pipeline(
            [
                ["RPUSH", key, json.dumps(message)],
                ["EXPIRE", key, 86_400],
            ]
        )
    except Exception as exc:
        print(f"[REDIS] Failed to save message: {type(exc).__name__}")


async def get_chat_history(session_id: str) -> List[Message]:
    if not _redis_config():
        return []

    try:
        items = await _command("LRANGE", f"chat:{session_id}", 0, -1)
        history: List[Message] = []
        for item in items or []:
            try:
                payload = json.loads(item)
                if payload.get("role") == "model":
                    payload["role"] = "assistant"
                history.append(Message(**payload))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return history
    except Exception as exc:
        print(f"[REDIS] Failed to fetch history: {type(exc).__name__}")
        return []


async def delete_chat_history(session_id: str) -> bool:
    try:
        await delete_chat_histories([session_id])
        return True
    except Exception as exc:
        print(f"[REDIS] Failed to delete history: {type(exc).__name__}")
        return False


async def delete_chat_histories(session_ids: Sequence[str]) -> int:
    if not _redis_config() or not session_ids:
        return 0
    results = await _pipeline([["DEL", f"chat:{session_id}"] for session_id in session_ids])
    return sum(int(item.get("result") or 0) for item in results)


async def delete_all_chat_histories() -> int:
    if not _redis_config():
        return 0

    cursor = "0"
    deleted = 0
    while True:
        result = await _command("SCAN", cursor, "MATCH", "chat:*", "COUNT", 100)
        if not isinstance(result, list) or len(result) != 2:
            raise RuntimeError("Unexpected Redis SCAN response.")
        cursor, keys = str(result[0]), result[1] or []
        if keys:
            pipeline_results = await _pipeline([["DEL", key] for key in keys])
            deleted += sum(int(item.get("result") or 0) for item in pipeline_results)
        if cursor == "0":
            return deleted
