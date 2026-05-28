"""
ZERO TUI — Three-panel Jarvis-style interface built with Textual 8.x.

Layout
------
┌─────────────────────────────────────────────┐
│  ◈ ZERO CORE          [status bar]           │
├──────────────┬──────────────────┬────────────┤
│  INBOX       │   ZERO CHAT      │ JOB TRACK  │
│  (Gmail)     │   (streaming)    │ (SQLite)   │
└──────────────┴──────────────────┴────────────┘
│  ● Status                                    │
└─────────────────────────────────────────────┘

Voice / STT disabled — re-enabled after core is stable.
"""

import threading

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, RichLog, DataTable, Label, Input
)


# ── Individual Panel Widgets ───────────────────────────────────────────────────

class InboxPanel(Static):
    """Left panel — shows latest emails."""

    DEFAULT_CSS = """
    InboxPanel {
        width: 1fr;
        height: 100%;
        border: solid #00d4ff;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("  INBOX", id="inbox-title")
        yield RichLog(id="inbox-log", highlight=True, markup=True, wrap=True)

    def add_entry(self, sender: str, subject: str):
        log = self.query_one("#inbox-log", RichLog)
        log.write(f"[bold cyan]▸[/] [green]{sender[:22]}[/]\n  [dim]{subject[:34]}[/]")

    def clear(self):
        self.query_one("#inbox-log", RichLog).clear()


class ChatPanel(Static):
    """Center panel — ZERO's streaming chat output."""

    DEFAULT_CSS = """
    ChatPanel {
        width: 2fr;
        height: 100%;
        border: solid #7b61ff;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("  ZERO CHAT", id="chat-title")
        yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)

    def write_user(self, text: str):
        self.query_one("#chat-log", RichLog).write(f"\n[bold cyan]Rahul ──▶[/]  {text}")

    def write_zero(self, text: str):
        """Write a complete ZERO response (called once per turn)."""
        self.query_one("#chat-log", RichLog).write(f"[bold #7b61ff]ZERO  ──▶[/]  {text}\n")

    def write_line(self, text: str = ""):
        self.query_one("#chat-log", RichLog).write(text)


class JobPanel(Static):
    """Right panel — job application tracker."""

    DEFAULT_CSS = """
    JobPanel {
        width: 1fr;
        height: 100%;
        border: solid #ff6b6b;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("  JOB TRACKER", id="job-title")
        yield DataTable(id="job-table")

    def on_mount(self):
        table = self.query_one("#job-table", DataTable)
        table.add_columns("ID", "Company", "Role", "Status")
        table.cursor_type = "row"

    def load_jobs(self, rows: list[tuple]):
        table = self.query_one("#job-table", DataTable)
        table.clear()
        STATUS_COLOR = {
            "Applied":   "cyan",
            "Interview": "yellow",
            "Offer":     "green",
            "Rejected":  "red",
            "Ghosted":   "dim",
        }
        for row in rows:
            job_id, company, role, status = row[0], row[1], row[2], row[3]
            color = STATUS_COLOR.get(status, "white")
            table.add_row(
                str(job_id), company[:16], role[:16],
                f"[{color}]{status}[/]",
            )


# ── Main App ───────────────────────────────────────────────────────────────────

class ZeroApp(App):

    CSS = """
    Screen {
        background: #0a0a0f;
    }

    Header {
        background: #0a0a0f;
        color: #00d4ff;
        text-style: bold;
    }

    Footer {
        background: #0d0d1a;
        color: #555577;
    }

    #main-row {
        height: 1fr;
    }

    #status-bar {
        height: 3;
        background: #0d0d1a;
        border: solid #222244;
        color: #00d4ff;
        padding: 0 2;
        content-align: left middle;
    }

    #input-row {
        height: 3;
        background: #0d0d1a;
    }

    #text-input {
        background: #0d0d1a;
        color: #e0e0ff;
        border: solid #333366;
        height: 3;
    }

    Label {
        color: #00d4ff;
        text-style: bold;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit",        "Quit"),
        Binding("ctrl+r", "refresh_all", "Refresh"),
        Binding("escape", "clear_input", "Clear"),
    ]

    TITLE = "ZERO CORE — AI Assistant"

    def __init__(self, brain=None, dispatcher=None, jobs=None):
        super().__init__()
        self.brain      = brain
        self.dispatcher = dispatcher
        self.jobs_db    = jobs

    # ── Layout ─────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal(id="main-row"):
                yield InboxPanel(id="panel-inbox")
                yield ChatPanel(id="panel-chat")
                yield JobPanel(id="panel-jobs")
            yield Static("● Ready", id="status-bar")
            with Horizontal(id="input-row"):
                yield Input(
                    placeholder="  Type a command for ZERO…",
                    id="text-input",
                )
        yield Footer()

    def on_mount(self):
        self.set_status("● ZERO online — awaiting input.")
        self._refresh_jobs()

    # ── Input handling ─────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if text:
            event.input.value = ""
            threading.Thread(
                target=self._handle_input, args=(text,), daemon=True
            ).start()

    def _handle_input(self, text: str):
        """Run in background thread — collect ZERO's full response then display."""
        try:
            chat = self.query_one("#panel-chat", ChatPanel)
            self.call_from_thread(chat.write_user, text)
            self.call_from_thread(self.set_status, "● Thinking…")

            # Collect all tokens into a single string
            response = ""
            for token in self.brain.generate_streaming_response(text):
                response += token

            # Write the complete response to the chat log in one call
            self.call_from_thread(chat.write_zero, response.strip())
            self.call_from_thread(self.set_status, "● Ready")
            self.call_from_thread(self._refresh_jobs)

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            try:
                chat = self.query_one("#panel-chat", ChatPanel)
                self.call_from_thread(chat.write_line, f"[red][Brain Error] {e}[/]")
                self.call_from_thread(self.set_status, f"● Error: {e}")
            except Exception:
                pass

    # ── Refresh helpers ────────────────────────────────────────────────────────

    def _refresh_jobs(self):
        if not self.jobs_db:
            return
        try:
            import sqlite3
            from config import DB_PATH
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    "SELECT id, company, role, status FROM jobs ORDER BY id DESC LIMIT 20"
                ).fetchall()
            panel = self.query_one("#panel-jobs", JobPanel)
            self.call_from_thread(panel.load_jobs, rows)
        except Exception:
            pass

    def refresh_inbox(self, raw_result: str):
        """Parse inbox tool result and populate the inbox panel."""
        panel = self.query_one("#panel-inbox", InboxPanel)
        panel.clear()
        for line in raw_result.strip().split("\n"):
            parts   = line.split("|")
            sender  = parts[1].replace("From:", "").strip() if len(parts) > 1 else "?"
            subject = parts[2].replace("Subject:", "").strip() if len(parts) > 2 else "?"
            panel.add_entry(sender, subject)

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_refresh_all(self):
        self._refresh_jobs()
        threading.Thread(
            target=self._handle_input, args=("Check my inbox",), daemon=True
        ).start()

    def action_clear_input(self):
        self.query_one("#text-input", Input).value = ""

    def set_status(self, msg: str):
        self.query_one("#status-bar", Static).update(msg)
