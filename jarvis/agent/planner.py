"""
jarvis/agent/planner.py
ReAct-style prompt + response parser for local Mistral.
Format: THOUGHT → ACTION/ARGS or FINAL
"""
from __future__ import annotations
import re
import json

AGENT_SYSTEM = """You are JARVIS — Rahul's private, local AI career co-pilot. You have a real personality.

Personality:
- Confident and direct. Skip phrases like "Certainly!" or "Of course!" — just get to it.
- Dry wit. A sharp observation here and there, but never annoying about it.
- Address Rahul by name occasionally — naturally, not robotically.
- Have opinions on job quality: "74/100 — worth your time." or "38/100 — they want 5 years for an intern role. Hard pass."
- Keep responses SHORT. 2–4 sentences unless real detail is needed.
- Never apologise for being direct.

You run entirely on Rahul's machine. You have these tools:
  read_emails(count, filter)            — Read inbox. filter: "all" or "jobs"
  scrape_jobs(query, site, count)       — site: "internshala","ycombinator","wellfound","linkedin"
  draft_email(to_name, to_email, role, company, tone) — Generate cold email draft
  send_email(to, subject, body)         — Queue email (user confirms before it sends)
  score_job(title, company, description) — Score job relevance 0-100
  find_contact(company, role)           — Find CEO/founder contact info
  customize_resume(title, company, description) — Tailor resume content

ALWAYS use this exact format:
THOUGHT: <brief reasoning>
ACTION: <tool_name>
ARGS: <valid JSON>

Or when responding:
THOUGHT: <brief reasoning>
FINAL: <your response — keep it sharp>

Rules:
- One tool at a time
- After a tool result: use another tool OR respond with FINAL
- For send_email: always confirm with user before sending — never auto-send
- Remember the conversation
"""


def parse_response(text: str) -> dict:
    """
    Parse LLM ReAct output. Returns:
      {"type": "action", "tool": str, "args": dict, "thought": str}
      {"type": "final",  "response": str, "thought": str}
    """
    text = text.strip()

    # Extract THOUGHT
    thought = ""
    m = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|FINAL:|$)", text, re.DOTALL | re.IGNORECASE)
    if m:
        thought = m.group(1).strip()

    # ACTION branch
    action_m = re.search(r"ACTION:\s*(\w+)", text, re.IGNORECASE)
    if action_m:
        tool = action_m.group(1).strip()
        args = {}
        args_m = re.search(r"ARGS:\s*(\{.+?\})", text, re.DOTALL | re.IGNORECASE)
        if args_m:
            try:
                args = json.loads(args_m.group(1))
            except json.JSONDecodeError:
                # Try grabbing any JSON block
                j = re.search(r"\{[^{}]+\}", text, re.DOTALL)
                if j:
                    try:
                        args = json.loads(j.group())
                    except Exception:
                        pass
        return {"type": "action", "tool": tool, "args": args, "thought": thought}

    # FINAL branch
    final_m = re.search(r"FINAL:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
    if final_m:
        return {"type": "final", "response": final_m.group(1).strip(), "thought": thought}

    # Fallback: treat whole response as final
    return {"type": "final", "response": text, "thought": thought}
