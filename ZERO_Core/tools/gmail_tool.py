"""
GmailTool — Gmail API integration for ZERO (OAuth2 Desktop App flow).

Setup:
  1. Go to console.cloud.google.com → Create project → Enable Gmail API
  2. Create OAuth 2.0 Client ID (Desktop App) → Download as gmail_credentials.json
  3. Place it at  ZERO_Core/credentials/gmail_credentials.json
  4. First run will open a browser for consent → saves gmail_token.json automatically
"""

import os
import base64
from email.mime.text import MIMEText

from config import (
    GMAIL_CREDENTIALS_PATH,
    GMAIL_TOKEN_PATH,
    GMAIL_SCOPES,
)

# ── Graceful degradation if google libs not installed yet ──────────────────────
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _LIBS_OK = True
except ImportError:
    _LIBS_OK = False


class GmailTool:

    def __init__(self):
        self.service = None
        if not _LIBS_OK:
            return
        if os.path.exists(GMAIL_CREDENTIALS_PATH):
            self._authenticate()

    # ── Auth ───────────────────────────────────────────────────────────────────

    def _authenticate(self):
        creds = None
        if os.path.exists(GMAIL_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_PATH, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)

            os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH), exist_ok=True)
            with open(GMAIL_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)

    def _not_ready(self) -> str:
        if not _LIBS_OK:
            return "[Gmail] google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib"
        return "[Gmail] credentials not found. Add gmail_credentials.json to ZERO_Core/credentials/"

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_inbox(self, max_results: int = 10) -> str:
        if not self.service:
            return self._not_ready()
        try:
            result   = self.service.users().messages().list(
                userId="me", maxResults=max_results, labelIds=["INBOX"]
            ).execute()
            messages = result.get("messages", [])
            if not messages:
                return "Inbox is empty."

            lines = []
            for msg in messages:
                m = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                h       = {h["name"]: h["value"] for h in m["payload"]["headers"]}
                snippet = m.get("snippet", "")[:80]
                lines.append(
                    f"ID:{msg['id']} | From: {h.get('From','?')} | "
                    f"Subject: {h.get('Subject','?')} | {snippet}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"[Gmail Error] {e}"

    def read_email(self, email_id: str) -> str:
        if not self.service:
            return self._not_ready()
        try:
            m = self.service.users().messages().get(
                userId="me", id=email_id.strip(), format="full"
            ).execute()
            h    = {h["name"]: h["value"] for h in m["payload"]["headers"]}
            body = self._extract_body(m["payload"])
            return (
                f"From: {h.get('From','?')}\n"
                f"Subject: {h.get('Subject','?')}\n"
                f"Date: {h.get('Date','?')}\n\n"
                f"{body[:2000]}"
            )
        except Exception as e:
            return f"[Gmail Error] {e}"

    def send_email(self, to: str, subject: str, body: str) -> str:
        if not self.service:
            return self._not_ready()
        try:
            msg             = MIMEText(body)
            msg["to"]       = to
            msg["subject"]  = subject
            raw             = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self.service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            return f"Email sent to {to} — Subject: {subject}"
        except Exception as e:
            return f"[Gmail Send Error] {e}"

    def search_emails(self, query: str) -> str:
        if not self.service:
            return self._not_ready()
        try:
            result   = self.service.users().messages().list(
                userId="me", q=query, maxResults=10
            ).execute()
            messages = result.get("messages", [])
            if not messages:
                return f"No emails matching: {query}"

            lines = []
            for msg in messages:
                m = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                h = {h["name"]: h["value"] for h in m["payload"]["headers"]}
                lines.append(
                    f"ID:{msg['id']} | From: {h.get('From','?')} | "
                    f"Subject: {h.get('Subject','?')}"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"[Gmail Search Error] {e}"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _extract_body(self, payload) -> str:
        """Recursively extract plain-text body from email payload."""
        if payload.get("body", {}).get("data"):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                return self._extract_body(part)

        for part in payload.get("parts", []):
            result = self._extract_body(part)
            if result:
                return result

        return ""
