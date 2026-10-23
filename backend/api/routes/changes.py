from typing import Annotated

from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from schemas.changes import ChangeOut, Description, Severity, Status
from services import store
from services.photos import save_photo

router = APIRouter(prefix="/api/v1", tags=["changes"])

@router.post("/changes", response_model=ChangeOut, status_code=201)
async def submit_change(
    # CHANGED: Put Form() inside Annotated so FastAPI retains the shared
    # description constraints while validating the incoming multipart fields.
    description: Annotated[Description, Form()],
    severity: Severity = Form(Severity.normal),
    photo: UploadFile = File(...),
):
    # CHANGED: Previously photo.read() discarded the upload. Save the bytes
    # first, then attach the generated storage key to the change record.
    # Validation failures create neither a change nor an office notification.
    photo_key = await save_photo(photo)
    return store.create_change(description, severity, photo_key)

@router.get("/changes", response_model=list[ChangeOut])
def list_changes(status: Status | None = None):
    # CHANGED: Status uses the existing enum, so invalid filters return 422
    # instead of silently returning an empty inbox for a misspelled status.
    items = list(store.CHANGES.values())
    return [c for c in items if status is None or c["status"] == status]

@router.post("/changes/{change_id}/admin-approve")
def admin_approve(change_id: str):
    c = store.CHANGES.get(change_id)
    if not c:
        raise HTTPException(404, "Not found")
    # CHANGED: Do not let another office approval reopen a completed change
    # or issue a second client link for a change that is already under review.
    if c["status"] != "submitted":
        raise HTTPException(409, "This change has already been reviewed")
    if c["severity"] == "high":
        # Existing policy preserved: high priority can be approved by admin;
        # normal priority moves to client review. This is not a new rule.
        c["status"] = "approved"
        # CHANGED: All notifications use the same helper in services/store.py.
        store.notify("contractor", change_id, "Approved")
        return {"status": "approved"}
    c["status"] = "awaiting_client"
    token = store.issue_client_token(change_id)
    link = f"http://localhost:8081/approve?token={token}"
    print("CLIENT LINK:", link)
    store.notify("client", change_id, link)
    return {"status": "awaiting_client"}

@router.get("/approval-session", response_model=ChangeOut)
def approval_session(token: str):
    c = store.change_for_token(token)
    if not c:
        # CHANGED: Tokens have no expiration check yet, so report "Invalid
        # link" rather than claiming an expired link was detected.
        raise HTTPException(404, "Invalid link")
    return c

def _decide(token: str, new_status: str):
    # Both client decision routes already share this function; retain it.
    c = store.change_for_token(token)
    if not c:
        raise HTTPException(404, "Invalid link")
    if c["status"] != "awaiting_client":
        raise HTTPException(409, "Already decided")
    c["status"] = new_status
    # CHANGED: Reuse the same notification shape used by submission/review.
    store.notify("contractor", c["id"], new_status)
    return {"status": new_status}

@router.post("/approval-session/approve")
def client_approve(token: str): return _decide(token, "approved")

@router.post("/approval-session/decline")
def client_decline(token: str): return _decide(token, "rejected")

@router.get("/notifications")
def notifications(to: str):
    return [n for n in store.NOTIFICATIONS if n["to"] == to]
