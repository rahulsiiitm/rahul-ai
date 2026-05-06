"""
jarvis/agent/tools.py
Central tool registry — maps tool names to callables and executes them.
All tools return JSON-serializable dicts or lists.
"""
from __future__ import annotations
import json
from rich.console import Console

console = Console()


# ── Tool implementations ────────────────────────────────────────────────────


def _read_emails(args: dict) -> str:
    from jarvis.tools.email_reader import read_emails
    count  = int(args.get("count", 15))
    filter_ = args.get("filter", "jobs")
    result = read_emails(count=count, filter=filter_)
    return json.dumps(result, indent=2, default=str)


def _scrape_jobs(args: dict) -> str:
    from jarvis.tools.job_scraper import scrape_jobs
    query = args.get("query", "software engineer internship")
    site  = args.get("site", "internshala")
    count = int(args.get("count", 8))
    result = scrape_jobs(query=query, site=site, count=count)
    return json.dumps(result, indent=2, default=str)


def _draft_email(args: dict) -> str:
    from jarvis.modules.emailer import generate_email
    from jarvis.tools.email_sender import queue_draft

    to_name  = args.get("to_name", "Hiring Manager")
    to_email = args.get("to_email", "")
    role     = args.get("role", "Software Engineer")
    company  = args.get("company", "the company")
    tone     = args.get("tone", "semi-formal")

    # Build a brief JD from args for the emailer
    jd = f"Role: {role} at {company}. Application email to {to_name}."
    console.print(f"[dim]  Generating email draft via Mistral...[/dim]")
    body = generate_email(
        job_title=role,
        company=company,
        job_description=jd,
        tone=tone,
    )

    # Parse subject line if present
    subject = f"Application for {role} — {company}"
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body = "\n".join(lines[i + 1:]).strip()
            break

    result = queue_draft(to=to_email, subject=subject, body=body)
    result["full_body"] = body
    return json.dumps(result, indent=2)


def _send_email(args: dict) -> str:
    """Queue the email — actual send triggered by user confirmation in chat.py."""
    from jarvis.tools.email_sender import queue_draft
    to      = args.get("to", "")
    subject = args.get("subject", "")
    body    = args.get("body", "")
    result  = queue_draft(to=to, subject=subject, body=body)
    return json.dumps(result, indent=2)


def _score_job(args: dict) -> str:
    from jarvis.modules.scorer import score_job
    result = score_job(
        job_title=args.get("title", ""),
        company=args.get("company", ""),
        job_description=args.get("description", ""),
    )
    return json.dumps(result, indent=2)


def _find_contact(args: dict) -> str:
    from jarvis.tools.contact_finder import find_contact
    result = find_contact(
        company=args.get("company", ""),
        role=args.get("role", "CEO"),
    )
    return json.dumps(result, indent=2)


def _customize_resume(args: dict) -> str:
    from jarvis.modules.resume import customize_resume
    # This streams, so we capture it
    result = customize_resume(
        job_title=args.get("title", ""),
        company=args.get("company", ""),
        job_description=args.get("description", ""),
    )
    return result  # already a string


# ── Registry ────────────────────────────────────────────────────────────────

TOOLS: dict[str, callable] = {
    "read_emails":      _read_emails,
    "scrape_jobs":      _scrape_jobs,
    "draft_email":      _draft_email,
    "send_email":       _send_email,
    "score_job":        _score_job,
    "find_contact":     _find_contact,
    "customize_resume": _customize_resume,
}


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name. Returns result as a string."""
    fn = TOOLS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: '{name}'. Available: {list(TOOLS.keys())}"})
    try:
        return fn(args)
    except Exception as e:
        return json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})
