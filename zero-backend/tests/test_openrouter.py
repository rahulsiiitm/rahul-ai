import os

import pytest
from openai import AsyncOpenAI


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openrouter_live():
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY is not configured")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", "")
    )
    
    response = await client.chat.completions.create(
        model="openrouter/auto",
        messages=[{"role": "user", "content": "Hi! Answer with a single word."}]
    )
    print("Success:", response.choices[0].message.content)
