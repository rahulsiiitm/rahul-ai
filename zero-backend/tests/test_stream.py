import time

import httpx
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_stream():
    start = time.time()
    async with httpx.AsyncClient(timeout=15.0) as client:
        async with client.stream("POST", "http://localhost:8000/api/chat", json={"messages": [{"role": "user", "content": "Write a long story."}]}) as response:
            print(f"Time to first byte: {time.time() - start:.2f}s")
            async for chunk in response.aiter_text():
                print(f"Chunk at {time.time() - start:.2f}s: {len(chunk)} bytes")
    print(f"Total time: {time.time() - start:.2f}s")
