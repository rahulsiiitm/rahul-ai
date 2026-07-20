from fastapi import APIRouter

router = APIRouter()

@router.get("/keep-alive")
async def keep_alive_endpoint():
    return {"status": "alive"}
