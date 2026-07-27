import asyncio
from models.schemas import Message
from services.ai import openrouter_generator, gemini_generator
import dotenv
dotenv.load_dotenv(override=True)

async def test_tool(query):
    print(f"\n[{query}]")
    print("Zero: ", end="")
    messages = [Message(role="user", content=query)]
    try:
        async for chunk in openrouter_generator(messages):
            print(chunk, end="", flush=True)
    except Exception as e:
        print(f"\n[CRASH] {e}")
    print("\n" + "-"*50)

async def main():
    queries = [
        "who are u? heheheh",
        "fetch the github profile for rahulsiiitm",
        "tell me about the architecture of sutra"
    ]
    for q in queries:
        await test_tool(q)

if __name__ == "__main__":
    asyncio.run(main())
