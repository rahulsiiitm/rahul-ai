import json
import asyncio
import os
from typing import Any, AsyncGenerator, Dict, List, cast

from google import genai
from google.genai import types
from openai import AsyncOpenAI

from models.schemas import Message
from services.knowledge import get_system_prompt
from services.tools import GEMINI_TOOLS, OPENAI_TOOLS, TOOL_FUNCTIONS


async def gemini_generator(messages_data: List[Message]) -> AsyncGenerator[str, None]:
    client = genai.Client(api_key=os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY", ""))
    
    formatted_messages: List[types.Content] = []
    for msg in messages_data:
        role = "user" if msg.role == "user" else "model"
        content = msg.content
        if not content and msg.parts:
            content = "".join([str(p.get("text", "")) for p in msg.parts if isinstance(p, dict)])
            
        content = content or ""
        if len(content) > 1000:
            content = content[:1000]
            
        formatted_messages.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))

    while True:
        response = await client.aio.models.generate_content_stream(
            model='gemini-3.5-flash',
            contents=formatted_messages,
            config=types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                max_output_tokens=2048,
                tools=cast(List[Any], GEMINI_TOOLS)
            )
        )
        
        function_calls = []
        async for chunk in response:
            if chunk.function_calls:
                function_calls.extend(chunk.function_calls)
            elif chunk.text:
                yield chunk.text
                
        if not function_calls:
            break
            
        # Execute tools and append to history
        for fc in function_calls:
            func_name = fc.name
            args = fc.args if hasattr(fc, 'args') and fc.args else {}
            args_dict = dict(args) if isinstance(args, dict) else {}
            
            result = f"Function {func_name} not found."
            if func_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[func_name](**args_dict)
                except Exception as e:
                    result = f"Error: {str(e)}"
                    
            formatted_messages.append(types.Content(role="model", parts=[types.Part.from_function_call(name=func_name or "", args=args_dict)]))
            formatted_messages.append(types.Content(role="user", parts=[types.Part.from_function_response(name=func_name or "", response={"result": result})]))

async def openrouter_generator(messages_data: List[Message]) -> AsyncGenerator[str, None]:
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        max_retries=0
    )
    
    formatted_messages: List[Dict[str, Any]] = [{"role": "system", "content": get_system_prompt()}]
    for msg in messages_data:
        content = msg.content
        if not content and msg.parts:
            content = "".join([str(p.get("text", "")) for p in msg.parts if isinstance(p, dict)])
        content = content or ""
        if len(content) > 1000:
            content = content[:1000]
        formatted_messages.append({"role": msg.role, "content": content})

    while True:
        response = cast(Any, await client.chat.completions.create(
            model="openrouter/auto",
            messages=formatted_messages, # type: ignore
            stream=True,
            max_tokens=2048,
            tools=OPENAI_TOOLS # type: ignore
        ))
        
        tool_calls_accumulator: Dict[int, Dict[str, Any]] = {}
        
        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls_accumulator:
                        tool_calls_accumulator[tc.index] = {
                            "id": tc.id, 
                            "type": "function", 
                            "function": {"name": tc.function.name if tc.function and tc.function.name else "", "arguments": ""}
                        }
                    if tc.function and tc.function.arguments:
                        tool_calls_accumulator[tc.index]["function"]["arguments"] += tc.function.arguments
            elif delta.content:
                await asyncio.sleep(0.02)
                yield delta.content
                
        if not tool_calls_accumulator:
            break
            
        # Append the assistant's tool call message
        assistant_message: Dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": []
        }
        
        for idx in sorted(tool_calls_accumulator.keys()):
            tc = tool_calls_accumulator[idx]
            assistant_message["tool_calls"].append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"]
                }
            })
            
        formatted_messages.append(assistant_message)
        
        for idx in sorted(tool_calls_accumulator.keys()):
            tc = tool_calls_accumulator[idx]
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
                
            result = f"Function {func_name} not found."
            if func_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[func_name](**args)
                except Exception as e:
                    result = f"Error: {str(e)}"
            
            formatted_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": func_name,
                "content": str(result)
            })
