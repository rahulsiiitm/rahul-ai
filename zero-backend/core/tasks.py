import os
import asyncio
import httpx

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
