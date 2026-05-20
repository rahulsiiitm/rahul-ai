import os

# ── Base ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Ollama / Brain ─────────────────────────────────────────────────────────────
OLLAMA_MODEL = "zero"

# ── Piper TTS ──────────────────────────────────────────────────────────────────
PIPER_MODEL_PATH = os.path.join(BASE_DIR, "voices", "en_US-ryan-high.onnx")

# ── Whisper STT ────────────────────────────────────────────────────────────────
# Sizes: tiny | base | small | medium  (base = good balance for Indian English)
WHISPER_MODEL_SIZE = "base"

# ── Wake Word ──────────────────────────────────────────────────────────────────
# openWakeWord model — "hey_jarvis" is the closest built-in to "hey zero"
WAKE_WORD_MODEL    = "hey_jarvis"
WAKE_WORD_THRESHOLD = 0.5          # confidence score to trigger (0.0 – 1.0)

# ── Audio ──────────────────────────────────────────────────────────────────────
SAMPLE_RATE        = 16000         # Hz — required by openWakeWord & Whisper
CHUNK_SIZE         = 1280          # 80 ms at 16 kHz — required by openWakeWord
SILENCE_THRESHOLD  = 500           # RMS energy below this = silence
MAX_SILENCE_SECS   = 1.8           # Stop recording after N seconds of silence
MIN_SPEECH_SECS    = 0.4           # Ignore utterances shorter than this

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "db", "zero.db")

# ── Gmail OAuth2 ───────────────────────────────────────────────────────────────
GMAIL_CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials", "gmail_credentials.json")
GMAIL_TOKEN_PATH       = os.path.join(BASE_DIR, "credentials", "gmail_token.json")
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

