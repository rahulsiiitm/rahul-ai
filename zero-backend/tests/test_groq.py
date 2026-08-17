import asyncio

import pytest
from dotenv import load_dotenv

load_dotenv(override=True)

from models.schemas import Message
from services.ai import groq_generator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_groq():
    print("Testing groq_generator with a real question...\n")
    messages = [
        Message(role="user", content="Hey Zero, who is the Chief and what is VidChain?")
    ]
    generator = groq_generator(messages)
    
    print("Response stream:\n-----------------")
    try:
        async for chunk in generator:
            print(chunk, end="", flush=True)
    except Exception as e:
        print(f"\nError: {e}")
    print("\n-----------------\nTest complete.")

if __name__ == "__main__":
    asyncio.run(test_groq())
