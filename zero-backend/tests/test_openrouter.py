import asyncio
from openai import AsyncOpenAI

import os

async def main():
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", "")
    )
    
    response = await client.chat.completions.create(
        model="openrouter/auto",
        messages=[{"role": "user", "content": "Hi! Answer with a single word."}]
    )
    print("Success:", response.choices[0].message.content)

asyncio.run(main())
