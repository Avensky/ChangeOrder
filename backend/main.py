from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import changes, health
from core.config import CORS_ORIGINS, UPLOAD_DIR, photos_in_bucket

app = FastAPI(title="Change Order API")
# CHANGED: Restore browser access for the Expo web frontend. Native phone
# requests do not use browser CORS, but localhost:8081 web requests do.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(changes.router)
# CHANGED: Reuse the existing health router and its HealthResponse schema.
# Defining /health here as well would duplicate the same endpoint.
app.include_router(health.router)

# Workspace state is stored atomically in local SQLite by services/store.py.
# The planned Supabase schema in db/models.py remains separate.

# Photos (J9). With the private bucket configured, nothing is served from a
# public folder: the API hands out short-lived signed links instead. Without
# it (a laptop with no SUPABASE_SECRET_KEY), photos stay in the local folder
# and are served from /uploads/<key> as before.
if not photos_in_bucket():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
