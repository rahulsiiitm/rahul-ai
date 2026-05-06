"""
jarvis/db.py
SQLite persistence layer.
Tables: jobs, outputs
"""

from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from jarvis.config import DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # dict-like access
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                company     TEXT    NOT NULL,
                description TEXT    NOT NULL,
                score       INTEGER,
                verdict     TEXT,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outputs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      INTEGER NOT NULL,
                type        TEXT    NOT NULL,   -- 'email' | 'resume' | 'score'
                content     TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            );
            """
        )


def save_job(title: str, company: str, description: str) -> int:
    """Insert a new job and return its ID."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (title, company, description, created_at) VALUES (?, ?, ?, ?)",
            (title, company, description, _now()),
        )
        return cur.lastrowid


def update_job_score(job_id: int, score: int, verdict: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE jobs SET score = ?, verdict = ? WHERE id = ?",
            (score, verdict, job_id),
        )


def save_output(job_id: int, output_type: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO outputs (job_id, type, content, created_at) VALUES (?, ?, ?, ?)",
            (job_id, output_type, content, _now()),
        )


def get_all_jobs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, company, score, verdict, created_at FROM jobs ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_job_outputs(job_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT type, content, created_at FROM outputs WHERE job_id = ? ORDER BY id",
            (job_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
