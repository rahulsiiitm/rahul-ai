import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, cast

from openai import AsyncOpenAI

from models.schemas import Message
from services.knowledge import get_system_prompt
from services.tools import OPENAI_TOOLS, execute_tool

MAX_TOOL_ROUNDS = 4


async def _openai_compatible_generator(
    messages_data: List[Message],
    *,
    base_url: str,
    api_key_env: str,
    model: str,
    session_id: Optional[str],
) -> AsyncGenerator[str, None]:
    client = AsyncOpenAI(base_url=base_url, api_key=os.environ.get(api_key_env, ""), max_retries=0)
    formatted_messages: List[Dict[str, Any]] = [{"role": "system", "content": get_system_prompt()}]
    for msg in messages_data:
        content = msg.content
        if not content and msg.parts:
            content = "".join([str(p.get("text", "")) for p in msg.parts if isinstance(p, dict)])
        content = content or ""
        if len(content) > 4000:
            content = content[:4000] + "..."
        formatted_messages.append({"role": msg.role, "content": content})

    yielded_any = False
    for _ in range(MAX_TOOL_ROUNDS):
        response = cast(
            Any,
            await client.chat.completions.create(
                model=model,
                messages=formatted_messages,  # type: ignore[arg-type]
                stream=True,
                max_tokens=2048,
                tools=OPENAI_TOOLS,  # type: ignore[arg-type]
            ),
        )
        tool_calls_accumulator: Dict[int, Dict[str, Any]] = {}

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls_accumulator:
                        tool_calls_accumulator[tc.index] = {
                            "id": tc.id or f"tool-call-{tc.index}",
                            "type": "function",
                            "function": {
                                "name": tc.function.name if tc.function and tc.function.name else "",
                                "arguments": "",
                            },
                        }
                    if tc.function and tc.function.arguments:
                        tool_calls_accumulator[tc.index]["function"]["arguments"] += tc.function.arguments
            elif delta.content:
                yielded_any = True
                await asyncio.sleep(0)
                yield delta.content

        if not tool_calls_accumulator:
            if not yielded_any:
                yield "I'm having a little trouble processing that. Can you rephrase?"
            break

        assistant_message: Dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": [],
        }

        for idx in sorted(tool_calls_accumulator.keys()):
            tc = tool_calls_accumulator[idx]
            assistant_message["tool_calls"].append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                },
            })
        formatted_messages.append(assistant_message)

        for idx in sorted(tool_calls_accumulator.keys()):
            tc = tool_calls_accumulator[idx]
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            result = await execute_tool(func_name, args, session_id=session_id)
            formatted_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": func_name,
                "content": result,
            })
    else:
        yield "I stopped a repeated tool loop before it could waste more time. Try a narrower request."


async def openrouter_generator(
    messages_data: List[Message],
    session_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    async for chunk in _openai_compatible_generator(
        messages_data,
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model="openrouter/auto",
        session_id=session_id,
    ):
        yield chunk


async def groq_generator(
    messages_data: List[Message],
    session_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    async for chunk in _openai_compatible_generator(
        messages_data,
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        model="openai/gpt-oss-120b",
        session_id=session_id,
    ):
        yield chunk


ProviderFactory = Callable[[List[Message], Optional[str]], AsyncGenerator[str, None]]


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str
    api_key_env: str
    factory: ProviderFactory
    first_token_timeout: float


PROVIDER_SPECS = (
    ProviderSpec("Groq", "openai/gpt-oss-120b", "GROQ_API_KEY", groq_generator, 12.0),
    ProviderSpec("OpenRouter", "openrouter/auto", "OPENROUTER_API_KEY", openrouter_generator, 12.0),
)
