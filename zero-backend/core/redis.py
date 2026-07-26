import os
import json
import httpx
from typing import List, Dict, Any
from models.schemas import Message

async def save_message_to_redis(session_id: str, message: dict):
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    
    if not url or not token:
        print("[REDIS] Missing credentials, skipping save.")
        return
        
    url = url.strip('"').strip("'")
    token = token.strip('"').strip("'")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    key = f"chat:{session_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            # RPUSH to list
            msg_str = json.dumps(message)
            r = await client.post(f"{url}/rpush/{key}", headers=headers, json=msg_str, timeout=5.0)
            
            # Set TTL to 24 hours (86400 seconds)
            await client.post(f"{url}/expire/{key}/86400", headers=headers, timeout=5.0)
    except Exception as e:
        print(f"[REDIS Error] Failed to save message: {e}")

async def get_chat_history(session_id: str) -> List[Message]:
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    
    if not url or not token:
        return []
        
    url = url.strip('"').strip("'")
    token = token.strip('"').strip("'")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    key = f"chat:{session_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            # LRANGE key 0 -1 to get all elements
            r = await client.get(f"{url}/lrange/{key}/0/-1", headers=headers, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("result"):
                    history = []
                    for item_str in data["result"]:
                        try:
                            item = json.loads(item_str)
                            history.append(Message(**item))
                        except Exception:
                            continue
                    return history
    except Exception as e:
        print(f"[REDIS Error] Failed to fetch history: {e}")
        
    return []
