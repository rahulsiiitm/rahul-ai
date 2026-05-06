"""
jarvis/tools/email_sender.py
SMTP email sender — drafts go to a queue, user must confirm before sending.
"""
from __future__ import annotations
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jarvis.config import (
    EMAIL_ADDRESS, EMAIL_APP_PASSWORD,
    SMTP_SERVER, SMTP_PORT, EMAIL_CONFIGURED,
)

# In-memory draft queue (one draft at a time is fine for MVP)
_pending_draft: dict | None = None


def queue_draft(to: str, subject: str, body: str) -> dict:
    """Store a draft for user review. Does NOT send."""
    global _pending_draft
    _pending_draft = {"to": to, "subject": subject, "body": body}
    return {
        "status": "draft_ready",
        "to": to,
        "subject": subject,
        "preview": body[:400],
        "message": "Draft ready. User must confirm before sending.",
    }


def get_pending_draft() -> dict | None:
    return _pending_draft


def send_pending_draft() -> dict:
    """Actually send the pending draft via SMTP."""
    global _pending_draft
    if not _pending_draft:
        return {"error": "No pending draft to send."}
    if not EMAIL_CONFIGURED:
        return {"error": "Email not configured. Fill in .env file."}

    d = _pending_draft
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = d["to"]
        msg["Subject"] = d["subject"]
        msg.attach(MIMEText(d["body"], "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, d["to"], msg.as_string())

        _pending_draft = None
        return {"status": "sent", "to": d["to"], "subject": d["subject"]}

    except smtplib.SMTPAuthenticationError:
        return {"error": "SMTP auth failed. Check EMAIL_APP_PASSWORD in .env"}
    except Exception as e:
        return {"error": str(e)}


def discard_draft() -> dict:
    global _pending_draft
    _pending_draft = None
    return {"status": "discarded"}
