from fastapi import FastAPI

app = FastAPI(title="Change Order API")


@app.get("/health")
def health():
    return {"status": "ok"}