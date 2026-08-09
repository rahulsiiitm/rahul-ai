import os

RATE_LIMIT_WINDOW_MS = 60_000  # 1 minute
RATE_LIMIT_MAX = 7

# Only trust proxy-provided client IP headers when the deployment explicitly opts in.
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "false").lower() == "true"

ALLOWED_ORIGINS = [
    "https://rahul.aishtrex.com",
    "http://localhost:3000",
]
