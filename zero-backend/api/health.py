from fastapi import APIRouter

router = APIRouter()

from typing import Dict


@router.get("/keep-alive")
async def keep_alive_endpoint() -> Dict[str, str]:
    return {"status": "alive"}
