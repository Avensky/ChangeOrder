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


# Email settings for the GC approval link. These are read at call time, not at
# import, so adding a key to the environment does not need a code change and a
# test can set one without reloading the module. The key itself lives in each
# person's local .env and in the host's secret settings, never in the repository.
def email_settings() -> dict:
    return dict(
        api_key=os.getenv("EMAIL_API_KEY", "").strip(),
        # Defaults to Resend; Bona sets the real provider. Any provider taking
        # a bearer key and {from,to,subject,text} JSON works unchanged.
        api_url=os.getenv("EMAIL_API_URL", "https://api.resend.com/emails").strip(),
        sender=os.getenv("EMAIL_FROM", "ChangeOrder <onboarding@resend.dev>").strip(),
        # Prototype recipient. B2's user table replaces this with the GC on the
        # change's company, so a per-change address is a later rename.
        gc_address=os.getenv("GC_EMAIL", "").strip(),
    )


# Photo storage (J9, decision in docs/photo-storage.md). Read at call time.
# With SUPABASE_SECRET_KEY set, photos go to the private bucket and are served
# with short-lived signed links. Without it (a laptop with no secret key, and
# the tests) they stay in the local uploads folder as before. The secret key
# is backend-only: never EXPO_PUBLIC_, never in the repository.
DEFAULT_PHOTO_BUCKET = "change-photos"
DEFAULT_PHOTO_URL_TTL_SECONDS = 300


def photo_settings() -> dict:
    try:
        ttl = int(os.getenv("PHOTO_URL_TTL_SECONDS", DEFAULT_PHOTO_URL_TTL_SECONDS))
    except ValueError:
        ttl = DEFAULT_PHOTO_URL_TTL_SECONDS
    return dict(
        supabase_url=os.getenv("SUPABASE_URL", "").strip().rstrip("/"),
        secret_key=os.getenv("SUPABASE_SECRET_KEY", "").strip(),
        bucket=os.getenv("PHOTO_BUCKET", "").strip() or DEFAULT_PHOTO_BUCKET,
        ttl_seconds=max(30, min(ttl, 3600)),
    )


def photos_in_bucket() -> bool:
    """True when photos live in the private bucket, False for the local folder."""
    settings = photo_settings()
    return bool(settings["supabase_url"] and settings["secret_key"])
