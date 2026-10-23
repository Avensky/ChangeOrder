from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from schemas.changes import ChangeOut, Severity
from services import store
from pathlib import Path
from uuid import uuid4
    

router = APIRouter(prefix="/api/v1", tags=["changes"])

@router.post("/changes", response_model=ChangeOut, status_code=201)
async def submit_change(
    description: str = Form(...),
    severity: Severity = Form(Severity.normal),
    photo: UploadFile = File(...),
):
    if photo.content_type == "image/jpeg":
        extension = ".jpg"
    elif photo.content_type == "image/png":
        extension = ".png"
    else:
        raise HTTPException(status_code=400, detail="Upload a JPEG or PNG image")

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The photo is empty")

    uploads_dir = Path(__file__).resolve().parents[2] / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    (uploads_dir / filename).write_bytes(image_bytes)

    photo_key = f"uploads/{filename}"
    return store.create_change(description, severity, photo_key)

@router.get("/changes", response_model=list[ChangeOut])
def list_changes(status: str | None = None):
    items = list(store.CHANGES.values())
    return [c for c in items if status is None or c["status"] == status]

@router.post("/changes/{change_id}/admin-approve")
def admin_approve(change_id: str):
    c = store.CHANGES.get(change_id)
    if not c:
        raise HTTPException(404, "Not found")
    if c["severity"] == "high":
        c["status"] = "approved"
        store.NOTIFICATIONS.append(dict(to="contractor", change_id=change_id, msg="Approved"))
        return {"status": "approved"}
    c["status"] = "awaiting_client"
    token = store.issue_client_token(change_id)
    link = f"http://localhost:8081/approve?token={token}"
    print("CLIENT LINK:", link)
    store.NOTIFICATIONS.append(dict(to="client", change_id=change_id, msg=link))
    return {"status": "awaiting_client"}

@router.get("/approval-session", response_model=ChangeOut)
def approval_session(token: str):
    c = store.change_for_token(token)
    if not c:
        raise HTTPException(404, "Invalid or expired link")
    return c

def _decide(token: str, new_status: str):
    c = store.change_for_token(token)
    if not c:
        raise HTTPException(404, "Invalid or expired link")
    if c["status"] != "awaiting_client":
        raise HTTPException(409, "Already decided")
    c["status"] = new_status
    store.NOTIFICATIONS.append(dict(to="contractor", change_id=c["id"], msg=new_status))
    return {"status": new_status}

@router.post("/approval-session/approve")
def client_approve(token: str): return _decide(token, "approved")

@router.post("/approval-session/decline")
def client_decline(token: str): return _decide(token, "rejected")

@router.get("/notifications")
def notifications(to: str):
    return [n for n in store.NOTIFICATIONS if n["to"] == to]
