"""
ZeroDispatcher — Routes [TOOL:name:args] tags from ZERO's output to real tools.
"""

import re

# Lazy imports — tools are loaded only when dispatcher is constructed
from tools.gmail_tool   import GmailTool
from tools.job_tracker  import JobTracker
from tools.system_tool  import SystemTool

# Pattern:  [TOOL:tool_name]  or  [TOOL:tool_name:args]
_TOOL_RE = re.compile(r'\[TOOL:([^\]]+)\]')


class ZeroDispatcher:

    def __init__(self):
        self.gmail  = GmailTool()
        self.jobs   = JobTracker()
        self.system = SystemTool()

    # ── Public API ─────────────────────────────────────────────────────────────

    def extract(self, text: str) -> str | None:
        """Return the first tool tag found in text, or None."""
        m = _TOOL_RE.search(text)
        return m.group(0) if m else None

    def dispatch(self, tool_tag: str) -> str:
        """
        Accept a full tag string like '[TOOL:job_add:Google|SWE|https://...]'
        and route to the correct tool handler.
        Returns a plain-text result string.
        """
        # Strip surrounding brackets if present
        inner = tool_tag.strip("[]")          # e.g.  TOOL:gmail_inbox
        inner = inner[5:]                      # strip leading 'TOOL:'
        name, _, args = inner.partition(":")   # split on first colon only

        try:
            return self._route(name.lower().strip(), args.strip())
        except Exception as e:
            return f"[Tool Error — {name}] {e}"

    # ── Routing table ──────────────────────────────────────────────────────────

    def _route(self, name: str, args: str) -> str:
        # ── Gmail ──────────────────────────────────────────────────────────────
        if name == "gmail_inbox":
            return self.gmail.get_inbox()

        if name == "gmail_read":
            return self.gmail.read_email(args)

        if name == "gmail_send":
            to, subject, body = (args.split("|") + ["", "", ""])[:3]
            return self.gmail.send_email(to.strip(), subject.strip(), body.strip())

        if name == "gmail_search":
            return self.gmail.search_emails(args)

        # ── Job Tracker ────────────────────────────────────────────────────────
        if name == "job_add":
            parts = (args.split("|") + ["", "", ""])[:3]
            company, role, link = [p.strip() for p in parts]
            return self.jobs.add_job(company, role, link)

        if name == "job_list":
            status_filter = args if args else None
            return self.jobs.get_all_jobs(status_filter)

        if name == "job_update":
            parts  = (args.split("|") + [""])[:2]
            job_id = int(parts[0].strip())
            status = parts[1].strip()
            return self.jobs.update_status(job_id, status)

        if name == "job_stats":
            return self.jobs.get_stats()

        # ── System ─────────────────────────────────────────────────────────────
        if name == "sys_stats":
            return self.system.get_stats()

        if name == "sys_cmd":
            return self.system.run_command(args)

        return f"[Dispatcher] Unknown tool: '{name}'"
