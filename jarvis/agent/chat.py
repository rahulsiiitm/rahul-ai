"""
jarvis/agent/chat.py
Main agentic chat REPL.
- Rich terminal UI with distinct colors per role
- ReAct agent loop (THOUGHT → ACTION → tool result → repeat → FINAL)
- Email send confirmation gate
- Auto email check on startup (if configured)
"""
from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from jarvis.config import OLLAMA_MODEL, OLLAMA_HOST, EMAIL_CONFIGURED
from jarvis.agent.planner import AGENT_SYSTEM, parse_response
from jarvis.agent.tools import execute_tool
from jarvis.tools.email_sender import get_pending_draft, send_pending_draft, discard_draft

console = Console()
MAX_ITERATIONS = 8  # max tool calls per user turn

BANNER = """
[bold cyan]      _  ___  _____  __  __  ___  ____
     | |/ _ \|  __ \|  \/  |/ __|/ ___|
  _  | | |_| | |__) | |\/| |\__ \ (___
 | |_| |  _  |  _  /| |  | |___) \___ |
  \___/|_| |_|_| \_\|_|  |_|____/____/[/bold cyan]
[dim]  v2.0 · Agentic AI Job Assistant · 100% Local[/dim]
"""


def _llm_client():
    return ollama.Client(host=OLLAMA_HOST)


def _stream_final(messages: list[dict]) -> str:
    """Stream the LLM response token by token, return full text."""
    client = _llm_client()
    full = ""
    console.print("[bold cyan]Jarvis:[/bold cyan] ", end="")
    try:
        for chunk in client.chat(model=OLLAMA_MODEL, messages=messages, stream=True):
            token = chunk.message.content or ""
            print(token, end="", flush=True)
            full += token
        print()
    except Exception as e:
        console.print(f"\n[red]LLM error: {e}[/red]")
    return full


def _call_llm_json(messages: list[dict]) -> str:
    """Non-streaming call for ReAct action parsing."""
    client = _llm_client()
    try:
        resp = client.chat(model=OLLAMA_MODEL, messages=messages)
        return resp.message.content or ""
    except Exception as e:
        return f"FINAL: Error calling LLM — {e}"


def _show_tool_call(tool: str, args: dict):
    console.print(
        f"\n[bold yellow]  [Tool: {tool}][/bold yellow] "
        f"[dim]{json.dumps(args, ensure_ascii=False)[:80]}[/dim]"
    )


def _show_tool_result(result_str: str):
    try:
        data = json.loads(result_str)
        # Pretty print a truncated summary
        preview = json.dumps(data, indent=2)[:600]
        console.print(Panel(f"[dim]{preview}[/dim]", title="[dim]Tool Result[/dim]", border_style="dim"))
    except Exception:
        console.print(Panel(f"[dim]{result_str[:400]}[/dim]", title="[dim]Tool Result[/dim]", border_style="dim"))


def _confirm_send() -> bool:
    """Show draft and ask user to confirm sending."""
    draft = get_pending_draft()
    if not draft:
        return False
    console.print()
    console.print(Panel(
        f"[bold]To:[/bold] {draft['to']}\n"
        f"[bold]Subject:[/bold] {draft['subject']}\n\n"
        f"{draft['body']}",
        title="[bold yellow]Draft Email — Ready to Send[/bold yellow]",
        border_style="yellow",
    ))
    console.print("[bold yellow]Send this email? (yes/no):[/bold yellow] ", end="")
    answer = input().strip().lower()
    if answer in ("yes", "y", "send", "ok"):
        result = send_pending_draft()
        if result.get("status") == "sent":
            console.print(f"[bold green]Email sent to {result['to']}[/bold green]\n")
        else:
            console.print(f"[bold red]Send failed: {result.get('error')}[/bold red]\n")
        return True
    else:
        discard_draft()
        console.print("[dim]Draft discarded.[/dim]\n")
        return True


def _agent_turn(user_msg: str, history: list[dict]) -> str:
    """
    Run the ReAct agent loop for one user message.
    Returns the final response string.
    """
    # Build messages for this turn
    messages = (
        [{"role": "system", "content": AGENT_SYSTEM}]
        + history
        + [{"role": "user", "content": user_msg}]
    )

    final_response = ""

    for i in range(MAX_ITERATIONS):
        raw = _call_llm_json(messages)
        parsed = parse_response(raw)

        if parsed["thought"]:
            console.print(f"[dim]  Thinking: {parsed['thought'][:120]}[/dim]")

        if parsed["type"] == "action":
            tool  = parsed["tool"]
            args  = parsed["args"]
            _show_tool_call(tool, args)

            with console.status(f"[cyan]Running {tool}...[/cyan]"):
                result_str = execute_tool(tool, args)

            _show_tool_result(result_str)

            # If a draft was queued, offer to send
            if tool in ("draft_email", "send_email") and get_pending_draft():
                _confirm_send()

            # Feed tool result back into messages
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"[Tool result for {tool}]:\n{result_str}\n\nContinue."
            })

        elif parsed["type"] == "final":
            final_response = parsed["response"]
            break

        else:
            # Unexpected format — treat full response as final
            final_response = raw
            break

    if not final_response:
        final_response = "I've completed the requested actions. What would you like to do next?"

    return final_response


def _handle_special_commands(msg: str) -> bool:
    """Handle built-in slash commands. Returns True if handled."""
    cmd = msg.strip().lower()
    if cmd in ("exit", "quit", "bye"):
        console.print("\n[bold cyan]Jarvis:[/bold cyan] Goodbye! Good luck with your applications.\n")
        raise SystemExit(0)
    if cmd == "help":
        console.print(Panel(
            "[bold]What I can do:[/bold]\n\n"
            "  • [cyan]check my emails[/cyan] — read inbox, find job emails\n"
            "  • [cyan]scrape ML jobs on internshala[/cyan] — scrape job listings\n"
            "  • [cyan]scrape AI internships on ycombinator[/cyan]\n"
            "  • [cyan]find CEO of [company][/cyan] — search contact info\n"
            "  • [cyan]draft email to [name] at [company] for [role][/cyan]\n"
            "  • [cyan]score this job: [paste JD][/cyan]\n"
            "  • [cyan]customize my resume for [role] at [company][/cyan]\n\n"
            "[dim]Type 'exit' to quit.[/dim]",
            title="[bold]Jarvis Help[/bold]",
            border_style="cyan",
        ))
        return True
    return False


def start_chat():
    """Entry point — start the Jarvis agentic chat loop."""
    console.print(BANNER)

    # Startup checks
    from jarvis.llm import ping
    from jarvis.db import init_db
    init_db()

    if not ping():
        console.print(
            "[bold red]Ollama not reachable.[/bold red] "
            f"Make sure [bold]ollama serve[/bold] is running "
            f"and model [bold]{OLLAMA_MODEL}[/bold] is pulled.\n"
        )
        raise SystemExit(1)

    console.print(Panel(
        f"[bold green]Ollama OK[/bold green] — Model: [cyan]{OLLAMA_MODEL}[/cyan]\n"
        + ("[bold green]Email configured[/bold green]" if EMAIL_CONFIGURED
           else "[bold yellow]Email not configured[/yellow] (copy .env.example to .env)"),
        title="[bold]System Status[/bold]",
        border_style="dim",
    ))

    # Welcome message
    console.print("\n[bold cyan]Jarvis:[/bold cyan] Hey Rahul! I'm ready. I can read your emails, scrape job listings, draft cold emails to founders, and more. Just tell me what you need. Type [bold]help[/bold] for ideas.\n")

    # Auto check emails on startup
    if EMAIL_CONFIGURED:
        console.print("[dim]  Auto-checking inbox for job emails...[/dim]")
        with console.status("[cyan]Reading inbox...[/cyan]"):
            from jarvis.tools.email_reader import read_emails
            emails = read_emails(count=20, filter="jobs")

        job_emails = [e for e in emails if not e.get("error") and e.get("is_job")]
        if job_emails:
            console.print(f"[bold cyan]Jarvis:[/bold cyan] Found [bold]{len(job_emails)}[/bold] job-related email(s) in your inbox. Want me to summarize them?\n")
        else:
            console.print("[bold cyan]Jarvis:[/bold cyan] No new job-related emails found in inbox.\n")

    # Conversation history
    history: list[dict] = []

    # Main REPL loop
    while True:
        try:
            console.print("[bold white]You:[/bold white] ", end="")
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold cyan]Jarvis:[/bold cyan] Goodbye!\n")
            break

        if not user_input:
            continue

        if _handle_special_commands(user_input):
            continue

        console.print()

        # Run agent
        response = _agent_turn(user_input, history)

        # Show final response
        console.print(Rule(style="dim"))
        console.print(f"[bold cyan]Jarvis:[/bold cyan] ", end="")
        # Render markdown if it looks like markdown
        if any(c in response for c in ["##", "**", "- ", "```"]):
            console.print()
            console.print(Markdown(response))
        else:
            console.print(response)
        console.print()

        # Update history
        history.append({"role": "user",      "content": user_input})
        history.append({"role": "assistant", "content": response})

        # Keep history bounded (last 20 turns)
        if len(history) > 40:
            history = history[-40:]
