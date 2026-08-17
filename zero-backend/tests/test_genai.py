import os

import pytest
from google import genai


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_live():
    if not os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"):
        pytest.skip("GOOGLE_GENERATIVE_AI_API_KEY is not configured")
    client = genai.Client(http_options={"api_version": "v1alpha", "timeout": 2000})
    try:
        response = await client.aio.models.generate_content(
            model='gemini-1.5-flash',
            contents='Hi'
        )
        print(response.text)
    except Exception as e:
        pytest.fail(f"Gemini request failed: {type(e).__name__}")
