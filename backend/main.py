from datetime import UTC, datetime

from fastapi import FastAPI
from api.routes import changes 

app = FastAPI(title="Change Order API")

app.include_router(changes.router)

@app.get("/health")
def health():
    return {"status": "ok"}