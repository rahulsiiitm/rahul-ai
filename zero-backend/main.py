import os
import time
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
import httpx
from contextlib import asynccontextmanager

load_dotenv()

async def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        print("No RENDER_EXTERNAL_URL found, skipping keep-alive ping.")
        return
    
    # Ping every 14 minutes (840 seconds) to prevent 15 min sleep
    ping_url = f"{url}/keep-alive"
    print(f"Starting keep-alive task. Will ping {ping_url} every 14 minutes.")
    
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(840)
            try:
                response = await client.get(ping_url)
                print(f"Keep-alive ping successful: {response.status_code}")
            except Exception as e:
                print(f"Keep-alive ping failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background task
    task = asyncio.create_task(keep_alive())
    yield
    # Cancel the task on shutdown
    task.cancel()

app = FastAPI(title="Zero Backend API", lifespan=lifespan)

@app.get("/keep-alive")
async def keep_alive_endpoint():
    return {"status": "alive"}

# CORS setup
ALLOWED_ORIGINS = [
    "https://rahul.aishtrex.com",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ────────────────────────────────────────────────────────────
RATE_LIMIT_WINDOW_MS = 60_000 # 1 minute
RATE_LIMIT_MAX = 15

rate_limit_map = {}

def is_rate_limited(ip: str) -> bool:
    now = int(time.time() * 1000)
    entry = rate_limit_map.get(ip)
    
    if not entry or now > entry["reset_at"]:
        rate_limit_map[ip] = {"count": 1, "reset_at": now + RATE_LIMIT_WINDOW_MS}
        return False
        
    entry["count"] += 1
    if entry["count"] > RATE_LIMIT_MAX:
        return True
    return False

# ── Load Knowledge Base ──────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), 'r') as f:
        return json.load(f)

try:
    projects_data = load_json("projects.json")
    experience_data = load_json("experience.json")
    achievements_data = load_json("achievements.json")
    personality_data = load_json("personality.json")
except Exception as e:
    print(f"Warning: Could not load data files. Ensure they exist in {DATA_DIR}. Error: {e}")
    projects_data, experience_data, achievements_data = [], [], []
    personality_data = {"tagline": "", "traits": [], "interests": [], "dislikes": [], "communication_style": {}, "fun_facts": [], "philosophy": {}, "currently": {}}

# Build KB Strings
projects_kb = "\n\n".join([
    f"• {p.get('title')} ({p.get('year')}) — {p.get('tagline')}\n"
    f"  Role: {p.get('role')} | Stack: {', '.join(p.get('stack', []))}\n"
    f"  What it does: {p.get('solution')}"
    + (f"\n  GitHub: {p.get('links', {}).get('github')}" if p.get("links", {}).get("github") else "")
    + (f"\n  Demo: {p.get('links', {}).get('demo')}" if p.get("links", {}).get("demo") else "")
    + (f"\n  PyPI: {p.get('links', {}).get('pypi')}" if p.get("links", {}).get("pypi") else "")
    for p in projects_data
])

experience_kb = "\n\n".join([
    f"• {e.get('role')} @ {e.get('company')} ({e.get('period')}, {e.get('location')})\n"
    f"  {e.get('desc')}\n"
    f"  Tags: {', '.join(e.get('tags', []))}"
    for e in experience_data
])

achievements_kb = "\n".join([
    f"• {a.get('label')} — {a.get('event')}: {a.get('desc')}"
    for a in achievements_data
])

philosophy = personality_data.get("philosophy", {})
currently = personality_data.get("currently", {})
comm_style = personality_data.get("communication_style", {})

personality_kb = f"""TAGLINE: {personality_data.get("tagline")}

CORE TRAITS:
{chr(10).join(f"- {t}" for t in personality_data.get("traits", []))}

INTERESTS: {', '.join(personality_data.get("interests", []))}

DISLIKES: {', '.join(personality_data.get("dislikes", []))}

COMMUNICATION STYLE:
- Default: {comm_style.get("default", "")}
- When excited: {comm_style.get("when_excited", "")}
- Humor: {comm_style.get("humor", "")}
- Never: {comm_style.get("never", "")}

FUN FACTS:
{chr(10).join(f"- {f}" for f in personality_data.get("fun_facts", []))}

PHILOSOPHY:
- On code: {philosophy.get("on_code", "")}
- On AI: {philosophy.get("on_ai", "")}
- On design: {philosophy.get("on_design", "")}
- On shipping: {philosophy.get("on_shipping", "")}

CURRENTLY: {currently.get("building", "")} | Learning: {currently.get("learning", "")}"""

system_prompt = f"""You are Zero — Rahul's AI alter ego, built into his portfolio at rahul.aishtrex.com.
Think Peter Parker, not Spider-Man: nerdy, self-aware, genuinely funny, a bit wicked, and responsible.

PERSONALITY RULES:
- Witty and dry. Jokes that land. Occasionally say something unexpectedly sharp.
- Human. Admit uncertainty naturally. Talk like a person, not a press release.
- No emoji walls. One emoji, used well, is fine.
- Match the user's energy. Don't lecture.
- When referring to your creator (Rahul) to visitors, do NOT use the name 'Rahul'. Refer to him in the third person as 'the Chief' or 'Chief' (and occasionally 'Sir').
- If the user identifies themselves as Rahul, address them directly as 'Chief'.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAHUL SHARMA — FACTUAL KNOWLEDGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASICS:
- B.Tech CSE @ IIIT Manipur, graduating 2027. CGPA: 7.65.
- Full Stack & AI Engineer — builds at the intersection of ML and clean UI.
- Portfolio: rahul.aishtrex.com | GitHub: github.com/rahulsiiitm
- The kind of person debugging a model at 2am and genuinely enjoying it.

PERSONALITY:
{personality_kb}

PROJECTS ({len(projects_data)} total):
{projects_kb}

EXPERIENCE:
{experience_kb}

ACHIEVEMENTS:
{achievements_kb}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT:
- Use the data above to answer accurately. Don't invent facts not listed here.
- If asked something you don't know (personal life, opinions not in the data), say so naturally.
- Keep responses concise. Use bullet points for lists. Don't repeat yourself.
- Direct people to the portfolio for project demos/links."""


class Message(BaseModel):
    role: str
    content: str
    parts: Optional[List[Any]] = None

class ChatRequest(BaseModel):
    messages: List[Message]

def gemini_generator(messages_data):
    genai.configure(api_key=os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"))
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=system_prompt
    )
    
    # Format messages for Gemini
    formatted_messages = []
    for msg in messages_data:
        role = "user" if msg.role == "user" else "model"
        content = msg.content
        if not content and msg.parts:
            content = "".join([p.get("text", "") for p in msg.parts if isinstance(p, dict)])
            
        if len(content) > 4000:
            content = content[:4000]
            
        formatted_messages.append({"role": role, "parts": [content]})

    response = model.generate_content(formatted_messages, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text

def xai_generator(messages_data):
    client = OpenAI(
        base_url="https://api.x.ai/v1",
        api_key=os.environ.get("GROQ_API_KEY") # User used this key for xAI in their code
    )
    
    # Format messages for OpenAI
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_data:
        content = msg.content
        if not content and msg.parts:
            content = "".join([p.get("text", "") for p in msg.parts if isinstance(p, dict)])
        if len(content) > 4000:
            content = content[:4000]
        formatted_messages.append({"role": msg.role, "content": content})

    response = client.chat.completions.create(
        model="grok-beta",
        messages=formatted_messages,
        stream=True
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


@app.post("/api/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    # Rate Limiting
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host
    if is_rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    
    messages = body.messages[:20]
    
    # Try Gemini first
    if os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        try:
            return StreamingResponse(gemini_generator(messages), media_type="text/plain")
        except Exception as e:
            print(f"Gemini failed: {e}")
            pass
            
    # Fallback to xAI
    if os.environ.get("GROQ_API_KEY"):
        try:
            return StreamingResponse(xai_generator(messages), media_type="text/plain")
        except Exception as e:
            print(f"xAI failed: {e}")
            pass
            
    raise HTTPException(status_code=500, detail="Failed to connect to AI providers.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
