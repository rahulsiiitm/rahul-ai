"""
jarvis/llm.py
Ollama local LLM wrapper. Single entry-point for all AI calls.
Model: Mistral (quantized, fits RTX 3050 4GB VRAM).
"""

from __future__ import annotations
import json
import ollama
from rich.console import Console
from jarvis.config import OLLAMA_MODEL, OLLAMA_HOST

console = Console()


def _client() -> ollama.Client:
    """Return a configured Ollama client."""
    return ollama.Client(host=OLLAMA_HOST)


def generate(
    prompt: str,
    system: str = "You are Jarvis, a private AI job assistant. Be concise and professional.",
    stream: bool = True,
) -> str:
    """
    Send a prompt to Mistral via Ollama and return the full response string.
    Streams tokens to the terminal in real-time if stream=True.
    """
    client = _client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    full_response = ""
    try:
        if stream:
            stream_response = client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in stream_response:
                # SDK v0.6+ returns Pydantic objects
                token = chunk.message.content or ""
                print(token, end="", flush=True)
                full_response += token
            print()  # newline after stream ends
        else:
            response = client.chat(model=OLLAMA_MODEL, messages=messages)
            full_response = response.message.content
    except Exception as e:
        console.print(f"\n[bold red]❌ Ollama error:[/bold red] {e}")
        console.print(
            "[dim]Make sure Ollama is running: [bold]ollama serve[/bold][/dim]"
        )
        raise SystemExit(1)

    return full_response


def generate_json(prompt: str, system: str) -> dict:
    """
    Generate a response and parse it as JSON.
    Retries once if the first parse fails.
    """
    raw = generate(prompt, system=system, stream=False)

    # Strip markdown code fences if model wraps output
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Second attempt: find JSON block inside free text
        import re
        match = re.search(r"\{[\s\S]+\}", clean)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        console.print("[bold yellow]⚠ Could not parse JSON from LLM response. Returning raw.[/bold yellow]")
        return {"raw": raw}


def ping() -> bool:
    """Check if Ollama is reachable and the model is available."""
    try:
        client = _client()
        list_response = client.list()
        # SDK v0.6+ returns a ListResponse Pydantic object
        for m in list_response.models:
            if OLLAMA_MODEL in m.model:
                return True
        return False
    except Exception:
        return False
