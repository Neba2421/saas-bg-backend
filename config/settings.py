"""
config/settings.py
Centralized environment configuration.
All runtime tuning happens here — never hardcoded in business logic.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Upload limits ──────────────────────────────────────────────────────────────
MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 5_242_880))   # 5 MB
MAX_WIDTH: int     = int(os.getenv("MAX_WIDTH",     6_000))
MAX_HEIGHT: int    = int(os.getenv("MAX_HEIGHT",    6_000))

# ── ONNX / threading ───────────────────────────────────────────────────────────
ORT_NUM_THREADS: int = int(os.getenv("ORT_NUM_THREADS", 1))
OMP_NUM_THREADS: int = int(os.getenv("OMP_NUM_THREADS", 1))

# Apply thread limits immediately on import so rembg picks them up.
os.environ["ORT_NUM_THREADS"] = str(ORT_NUM_THREADS)
os.environ["OMP_NUM_THREADS"] = str(OMP_NUM_THREADS)

# ── Gunicorn / Uvicorn ─────────────────────────────────────────────────────────
WEB_CONCURRENCY: int = int(os.getenv("WEB_CONCURRENCY", 4))

# ── CORS ───────────────────────────────────────────────────────────────────────
# Populate via environment; fall back to localhost for development.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
)
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]
