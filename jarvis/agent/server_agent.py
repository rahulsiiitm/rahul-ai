"""
jarvis/agent/server_agent.py
Agent loop that writes events to a Queue instead of printing to console.
Used by the FastAPI web server for SSE streaming.
"""
from __future__ import annotations
import json
from queue import Queue

import ollama

from jarvis.config import OLLAMA_MODEL, OLLAMA_HOST
from jarvis.agent.planner import AGENT_SYSTEM, parse_response
from jarvis.agent.tools import execute_tool
from jarvis.tools.email_sender import get_pending_draft

MAX_ITERATIONS = 8


def _llm(messages: list) -> str:
    client = ollama.Client(host=OLLAMA_HOST)
    resp = client.chat(model=OLLAMA_MODEL, messages=messages)
    return resp.message.content or ""


def run_agent(user_msg: str, history: list, q: Queue) -> None:
    """
    Run the ReAct agent loop. Push events to q:
      {type: thought | tool_start | tool_result | draft_ready | message | error | done}
    """
    messages = (
        [{"role": "system", "content": AGENT_SYSTEM}]
        + history
        + [{"role": "user", "content": user_msg}]
    )

    final_response = ""

    try:
        for _ in range(MAX_ITERATIONS):
            raw = _llm(messages)
            parsed = parse_response(raw)

            if parsed["thought"]:
                q.put({"type": "thought", "content": parsed["thought"][:160]})

            if parsed["type"] == "action":
                tool = parsed["tool"]
                args = parsed["args"]
                q.put({"type": "tool_start", "tool": tool, "args": args})

                result_str = execute_tool(tool, args)

                # Try to give structured data to frontend
                try:
                    result_data = json.loads(result_str)
                except Exception:
                    result_data = result_str

                q.put({"type": "tool_result", "tool": tool, "result": result_data})

                # If a draft was queued, surface it and stop
                draft = get_pending_draft()
                if draft and tool in ("draft_email", "send_email"):
                    q.put({"type": "draft_ready", "draft": draft})
                    q.put({"type": "done", "final": ""})
                    return

                # Feed result back and loop
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": f"[Tool {tool} result]:\n{result_str[:1200]}\nContinue."
                })

            elif parsed["type"] == "final":
                final_response = parsed["response"]
                q.put({"type": "message", "content": final_response})
                break
            else:
                # Raw fallback
                final_response = raw
                q.put({"type": "message", "content": raw})
                break

    except Exception as e:
        q.put({"type": "error", "content": str(e)})

    q.put({"type": "done", "final": final_response})
