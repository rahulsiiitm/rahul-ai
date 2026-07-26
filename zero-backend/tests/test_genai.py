import asyncio
import os
from google import genai
from google.genai import types

async def main():
    client = genai.Client(http_options={"api_version": "v1alpha", "timeout": 2000})
    try:
        response = await client.aio.models.generate_content(
            model='gemini-1.5-flash',
            contents='Hi'
        )
        print(response.text)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
