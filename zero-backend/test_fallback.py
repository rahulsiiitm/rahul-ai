import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
import httpx
import threading
import time

app = FastAPI()

def gemini_generator():
    raise Exception("Gemini fails immediately")
    yield "never reached"

def xai_generator():
    yield "xAI works"

@app.get("/")
def endpoint():
    try:
        return StreamingResponse(gemini_generator(), media_type="text/plain")
    except Exception as e:
        print("Caught exception:", e)
        return StreamingResponse(xai_generator(), media_type="text/plain")

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

threading.Thread(target=run_server, daemon=True).start()
time.sleep(2)

r = httpx.get("http://127.0.0.1:8001/")
print("Status:", r.status_code)
print("Response:", r.text)
