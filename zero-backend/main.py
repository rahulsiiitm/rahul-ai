import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import admin, chat, health
from core.config import ALLOWED_ORIGINS
from core.tasks import keep_alive
from services.telemetry import drain_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Start the background task
    task = asyncio.create_task(keep_alive())
    yield
    # Cancel the task on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await drain_telemetry()

app = FastAPI(title="Zero Backend API", lifespan=lifespan)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Token"],
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
