import time
from typing import Any, Dict

from core.config import RATE_LIMIT_MAX, RATE_LIMIT_WINDOW_MS

rate_limit_map: Dict[str, Dict[str, Any]] = {}

def is_rate_limited(ip: str) -> bool:
    now = int(time.time() * 1000)
    
    # Cleanup old entries to prevent memory leak
    expired = [k for k, v in rate_limit_map.items() if now > v["reset_at"]]
    for k in expired:
        del rate_limit_map[k]
        
    entry = rate_limit_map.get(ip)
    
    if not entry:
        rate_limit_map[ip] = {"count": 1, "reset_at": now + RATE_LIMIT_WINDOW_MS}
        return False
        
    entry["count"] += 1
    if entry["count"] > RATE_LIMIT_MAX:
        return True
    return False
