"""Application configuration."""

import os
from pathlib import Path

# CHANGED: Keep the web origin list in one place instead of repeating it in
# routes. Existing backend/.env values override these local defaults.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081"
    ).split(",")
    if origin.strip()
]
# CHANGED: Resolve uploads relative to this backend, regardless of the folder
# from which npm/uvicorn was started. The upload service shares this size limit.
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
MAX_PHOTO_BYTES = 10 * 1024 * 1024
