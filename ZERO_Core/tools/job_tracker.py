"""
JobTracker — SQLite-backed job application tracker for ZERO.

Schema
------
jobs(id, company, role, status, applied_date, last_update, notes, link)

Statuses: Applied | Interview | Offer | Rejected | Ghosted
"""

import sqlite3
import os
from datetime import date, datetime

from config import DB_PATH

_VALID_STATUSES = {"Applied", "Interview", "Offer", "Rejected", "Ghosted"}


class JobTracker:

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    company      TEXT    NOT NULL,
                    role         TEXT    NOT NULL,
                    status       TEXT    DEFAULT 'Applied',
                    applied_date TEXT,
                    last_update  TEXT,
                    notes        TEXT    DEFAULT '',
                    link         TEXT    DEFAULT ''
                )
            """)

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def _today(self) -> str:
        return date.today().isoformat()

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_job(self, company: str, role: str, link: str = "", notes: str = "") -> str:
        if not company or not role:
            return "[Job Tracker] company and role are required."
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO jobs (company, role, status, applied_date, last_update, link, notes) "
                "VALUES (?, ?, 'Applied', ?, ?, ?, ?)",
                (company, role, self._today(), self._now(), link, notes),
            )
            job_id = cur.lastrowid
        return f"Job #{job_id} logged — {company} | {role} | Status: Applied"

    def update_status(self, job_id: int, status: str) -> str:
        status = status.strip().title()
        if status not in _VALID_STATUSES:
            return f"[Job Tracker] Invalid status '{status}'. Use: {', '.join(_VALID_STATUSES)}"
        with self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET status=?, last_update=? WHERE id=?",
                (status, self._now(), job_id),
            )
        return f"Job #{job_id} → {status}"

    def add_notes(self, job_id: int, notes: str) -> str:
        with self._conn() as conn:
            conn.execute(
                "UPDATE jobs SET notes=?, last_update=? WHERE id=?",
                (notes, self._now(), job_id),
            )
        return f"Notes updated for job #{job_id}"

    def get_all_jobs(self, status_filter: str = None) -> str:
        with self._conn() as conn:
            if status_filter:
                status_filter = status_filter.strip().title()
                rows = conn.execute(
                    "SELECT id, company, role, status, applied_date FROM jobs WHERE status=? ORDER BY id",
                    (status_filter,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, company, role, status, applied_date FROM jobs ORDER BY id"
                ).fetchall()

        if not rows:
            label = f"with status '{status_filter}'" if status_filter else ""
            return f"No job applications found {label}.".strip()

        lines = [
            f"#{r[0]} {r[1]} | {r[2]} | {r[3]} | Applied: {r[4]}"
            for r in rows
        ]
        return "\n".join(lines)

    def get_stats(self) -> str:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM jobs GROUP BY status"
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        if total == 0:
            return "No job applications logged yet."

        counts = {r[0]: r[1] for r in rows}
        parts  = [f"{s}: {counts.get(s, 0)}" for s in _VALID_STATUSES]
        return f"Total: {total}  |  " + "  |  ".join(parts)

    def delete_job(self, job_id: int) -> str:
        with self._conn() as conn:
            conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        return f"Job #{job_id} removed."
