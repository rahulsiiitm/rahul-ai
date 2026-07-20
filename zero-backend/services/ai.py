import os
from google import genai
from google.genai import types
from openai import AsyncOpenAI
from services.knowledge import system_prompt

async def gemini_generator(messages_data):
    client = genai.Client(api_key=os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"))
    
    # Format messages for Gemini
    formatted_messages = []
    for msg in messages_data:
        role = "user" if msg.role == "user" else "model"
        content = msg.content
        if not content and msg.parts:
            content = "".join([p.get("text", "") for p in msg.parts if isinstance(p, dict)])
            
        if len(content) > 1000:
            content = content[:1000]
            
        formatted_messages.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))

    response = await client.aio.models.generate_content_stream(
        model='gemini-3.5-flash',
        contents=formatted_messages,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2048,
        )
    )
    async for chunk in response:
        try:
            if chunk.text:
                yield chunk.text
        except ValueError:
            # Handle potential ValueError if safety ratings block the response
            pass

async def xai_generator(messages_data):
    client = AsyncOpenAI(
        base_url="https://api.x.ai/v1",
        api_key=os.environ.get("GROQ_API_KEY") # User used this key for xAI in their code
    )
    
    # Format messages for OpenAI
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_data:
        content = msg.content
        if not content and msg.parts:
            content = "".join([p.get("text", "") for p in msg.parts if isinstance(p, dict)])
        if len(content) > 1000:
            content = content[:1000]
        formatted_messages.append({"role": msg.role, "content": content})

    response = await client.chat.completions.create(
        model="grok-beta",
        messages=formatted_messages,
        stream=True,
        max_tokens=2048
    )
    async for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
