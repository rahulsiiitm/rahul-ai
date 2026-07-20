import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
import httpx
import threading
import time

app = FastAPI()

def gemini_generator():
    # simulate an error occurring DURING streaming (which is what happens since API calls are evaluated lazily or error out during the first next())
    raise Exception("API Quota Exceeded or Invalid Key")
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
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error")

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2)
    try:
        r = httpx.get("http://127.0.0.1:8002/")
        print("Status:", r.status_code)
        print("Response text:", repr(r.text))
    except Exception as e:
        print("HTTPX Error:", e)
