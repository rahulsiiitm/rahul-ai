"""
ui/app.py — FastAPI web server for Jarvis UI
Serves the chat UI and streams agent responses via SSE.
"""
from __future__ import annotations
import json
import sys
import threading
from pathlib import Path
from queue import Queue, Empty

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from jarvis.agent.server_agent import run_agent
from jarvis.tools.email_sender import get_pending_draft, send_pending_draft, discard_draft
from jarvis.tools.email_reader import read_emails
from jarvis.llm import ping
from jarvis.config import EMAIL_CONFIGURED, OLLAMA_MODEL
from jarvis.db import init_db

BASE = Path(__file__).parent

app = FastAPI(title="Jarvis — AI Job Assistant")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

# Single-user in-memory conversation history
conversation_history: list[dict] = []


# ── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def status():
    return {
        "ollama": ping(),
        "model": OLLAMA_MODEL,
        "email": EMAIL_CONFIGURED,
    }


@app.post("/api/chat")
async def chat(body: ChatRequest):
    user_msg = body.message.strip()
    if not user_msg:
        async def empty():
            yield f"data: {json.dumps({'type':'done','final':''})}\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    q: Queue = Queue()

    def _run():
        run_agent(user_msg, conversation_history, q)

    threading.Thread(target=_run, daemon=True).start()

    async def event_stream():
        final = ""
        while True:
            try:
                event = q.get(timeout=180)
            except Empty:
                yield f"data: {json.dumps({'type':'done','final':''})}\n\n"
                break

            data = json.dumps(event, ensure_ascii=False, default=str)
            yield f"data: {data}\n\n"

            if event["type"] == "done":
                final = event.get("final", "")
                # Update history
                conversation_history.append({"role": "user", "content": user_msg})
                if final:
                    conversation_history.append({"role": "assistant", "content": final})
                if len(conversation_history) > 40:
                    conversation_history[:] = conversation_history[-40:]
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/clear")
async def clear_history():
    conversation_history.clear()
    return {"status": "cleared"}


@app.get("/api/emails")
async def get_emails():
    if not EMAIL_CONFIGURED:
        return {"configured": False, "emails": []}
    try:
        emails = read_emails(count=15, filter="jobs")
        return {"configured": True, "emails": emails}
    except Exception as e:
        return {"configured": True, "emails": [], "error": str(e)}


@app.get("/api/draft")
async def get_draft():
    return {"draft": get_pending_draft()}


@app.post("/api/send-confirm")
async def confirm_send():
    return send_pending_draft()


@app.post("/api/send-discard")
async def confirm_discard():
    return discard_draft()


@app.on_event("startup")
async def startup():
    init_db()
