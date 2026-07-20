import os
from google import genai
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = genai.Client(api_key=os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"))
    response = await client.aio.models.generate_content_stream(
        model='gemini-3.5-flash',
        contents="Hi"
    )
    async for chunk in response:
        print(chunk.text)

asyncio.run(main())
