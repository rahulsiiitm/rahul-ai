import os

from dotenv import load_dotenv

load_dotenv()

RATE_LIMIT_WINDOW_MS = 60_000  # 1 minute
RATE_LIMIT_MAX = 7

MAX_MESSAGE_CHARS = 4_000
MAX_ASSISTANT_MESSAGE_CHARS = 12_000
MAX_MESSAGES_PER_REQUEST = 50
MAX_SESSION_IDS_PER_DELETE = 100
SESSION_TOKEN_TTL_SECONDS = 24 * 60 * 60

# Only trust proxy-provided client IP headers when the deployment explicitly opts in.
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true"

ALLOWED_ORIGINS = [
    "https://rahul.aishtrex.com",
    "http://localhost:3000",
]
