import json
import os
from typing import List

import httpx

from models.schemas import Message


def _redis_config():
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    return url.strip('"').strip("'"), token.strip('"').strip("'")


async def save_message_to_redis(session_id: str, message: dict) -> None:
    config = _redis_config()
    if not config:
        print("[REDIS] Missing credentials, skipping save.")
        return

    url, token = config
    headers = {"Authorization": f"Bearer {token}"}
    key = f"chat:{session_id}"

    try:
        async with httpx.AsyncClient() as client:
            msg_str = json.dumps(message)
            await client.post(f"{url}/rpush/{key}", headers=headers, json=msg_str, timeout=5.0)
            await client.post(f"{url}/expire/{key}/86400", headers=headers, timeout=5.0)
    except Exception as exc:
        print(f"[REDIS Error] Failed to save message: {exc}")


async def get_chat_history(session_id: str) -> List[Message]:
    config = _redis_config()
    if not config:
        return []

    url, token = config
    headers = {"Authorization": f"Bearer {token}"}
    key = f"chat:{session_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/lrange/{key}/0/-1", headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                history: List[Message] = []
                for item_str in data.get("result") or []:
                    try:
                        history.append(Message(**json.loads(item_str)))
                    except Exception:
                        continue
                return history
    except Exception as exc:
        print(f"[REDIS Error] Failed to fetch history: {exc}")

    return []


async def delete_chat_history(session_id: str) -> bool:
    config = _redis_config()
    if not config:
        return True

    url, token = config
    headers = {"Authorization": f"Bearer {token}"}
    key = f"chat:{session_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{url}/del/{key}", headers=headers, timeout=5.0)
            return response.status_code == 200
    except Exception as exc:
        print(f"[REDIS Error] Failed to delete history: {exc}")
        return False
