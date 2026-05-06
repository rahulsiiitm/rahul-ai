"""
jarvis/config.py
Central configuration — paths, model settings, constants.
"""

import os
from pathlib import Path

# ── Root Paths ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs"

DB_PATH = DATA_DIR / "jarvis.db"
RESUME_PATH = DATA_DIR / "resume.json"
PROFILE_PATH = DATA_DIR / "user_profile.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ── Ollama / LLM Settings ─────────────────────────────────────────────────────
OLLAMA_MODEL = os.getenv("JARVIS_MODEL", "mistral")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Context window & generation limits
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.7

# ── Scoring ───────────────────────────────────────────────────────────────────
SCORE_THRESHOLD_HIGH = 70    # ≥ 70 → Strong Match
SCORE_THRESHOLD_MED = 45     # ≥ 45 → Moderate Match
                             # < 45 → Weak Match

# ── Tone Options ──────────────────────────────────────────────────────────────
EMAIL_TONES = ["formal", "semi-formal", "friendly"]
DEFAULT_TONE = "semi-formal"

# ── Email Config (loaded from .env) ──────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

EMAIL_ADDRESS      = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
IMAP_SERVER        = os.getenv("IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER        = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT          = int(os.getenv("SMTP_PORT", "587"))

EMAIL_CONFIGURED = bool(EMAIL_ADDRESS and EMAIL_APP_PASSWORD)
