"""
jarvis/tools/email_reader.py
IMAP email reader — reads inbox, identifies job-related emails.
Uses stdlib imaplib only.
"""
from __future__ import annotations
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime
from jarvis.config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD, IMAP_SERVER, EMAIL_CONFIGURED

JOB_KEYWORDS = [
    "hiring", "internship", "opportunity", "position", "role", "job",
    "application", "interview", "recruit", "we're looking", "join us",
    "opening", "vacancy", "offer", "shortlisted", "selected",
]


def _decode_str(s) -> str:
    if s is None:
        return ""
    parts = decode_header(s)
    out = []
    for b, enc in parts:
        if isinstance(b, bytes):
            out.append(b.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(b))
    return " ".join(out)


def _is_job_related(subject: str, snippet: str) -> bool:
    text = (subject + " " + snippet).lower()
    return any(kw in text for kw in JOB_KEYWORDS)


def read_emails(count: int = 15, filter: str = "jobs") -> list[dict]:
    """
    Connect to IMAP, read last `count` emails.
    If filter='jobs', return only job-related ones.
    Returns list of dicts: {id, from, subject, date, snippet, is_job}
    """
    if not EMAIL_CONFIGURED:
        return [{"error": "Email not configured. Copy .env.example to .env and fill credentials."}]

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("INBOX")

        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        # Take last `count` emails (most recent)
        ids = ids[-count:][::-1]

        results = []
        for uid in ids:
            _, msg_data = mail.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            subject = _decode_str(msg.get("Subject", ""))
            sender  = _decode_str(msg.get("From", ""))
            date_str = msg.get("Date", "")

            # Get plain text snippet
            snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain":
                        try:
                            snippet = part.get_payload(decode=True).decode("utf-8", errors="replace")[:300]
                        except Exception:
                            pass
                        break
            else:
                try:
                    snippet = msg.get_payload(decode=True).decode("utf-8", errors="replace")[:300]
                except Exception:
                    pass

            is_job = _is_job_related(subject, snippet)
            entry = {
                "id": uid.decode(),
                "from": sender,
                "subject": subject,
                "date": date_str[:25],
                "snippet": snippet[:200].strip(),
                "is_job": is_job,
            }
            if filter == "jobs" and not is_job:
                continue
            results.append(entry)

        mail.logout()
        return results

    except imaplib.IMAP4.error as e:
        return [{"error": f"IMAP error: {e}. Check credentials in .env"}]
    except Exception as e:
        return [{"error": str(e)}]
