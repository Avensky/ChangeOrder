import os
from typing import Annotated, Literal
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from schemas.changes import (
    Description,
    ReviewTerms,
    Severity,
    Status,
    Suggestion,
    SuggestionRequest,
    WorkspaceChangeOut,
)
from services import store
from services.photos import save_photo
from core.config import UPLOAD_DIR

router = APIRouter(prefix="/api/v1", tags=["changes"])
ProjectId = Literal["north-park", "harbor", "cedar"]


@router.post("/changes", response_model=WorkspaceChangeOut, status_code=201)
async def submit_change(
    description: Annotated[Description, Form()],
    severity: Severity = Form(Severity.normal),
    photos: list[UploadFile] = File(...),
    title: Annotated[str, Form(max_length=120)] = "",
    project_id: ProjectId = Form("north-park"),
    submitted_by: Literal["contractor", "subcontractor"] = Form("contractor"),
):
    if not 1 <= len(photos) <= 10:
        raise HTTPException(422, "Attach between 1 and 10 photos.")
    keys = []
    try:
        for photo in photos:
            keys.append(await save_photo(photo))
        with store.atomic():
            return store.create_change(
                description, severity, keys, title.strip(), project_id, submitted_by
            )
    except BaseException:
        for key in keys:
            (UPLOAD_DIR / key).unlink(missing_ok=True)
        raise
    finally:
        for photo in photos:
            await photo.close()


@router.get("/changes", response_model=list[WorkspaceChangeOut])
def list_changes(status: Status | None = None):
    with store.atomic():
        return [
            c for c in store.CHANGES.values() if status is None or c["status"] == status
        ]


@router.post("/changes/{change_id}/admin-approve")
def admin_approve(change_id: str, terms: ReviewTerms = Body(...)):
    with store.atomic():
        c = store.CHANGES.get(change_id)
        if not c:
            raise HTTPException(404, "Not found")
        if c["status"] != "submitted":
            raise HTTPException(409, "This change has already been reviewed")
        c.update(
            amount=terms.amount,
            impact_days=terms.impact_days,
            approved_scope=terms.scope or c["description"],
        )
        # Preserve the existing prototype urgent approval policy.
        if c["severity"] == "high":
            c["status"] = "approved"
            store.add_event(
                c,
                "approved",
                "Urgent change approved; work order updated",
                "Office Manager",
            )
            store.notify(
                "contractor", change_id, "Approved; project work order updated"
            )
        else:
            c.update(status="awaiting_client", sent_for_approval=True)
            token = store.issue_client_token(change_id)
            link = (
                os.getenv("APP_URL", "http://localhost:8081").rstrip("/")
                + f"/approve?token={token}"
            )
            store.notify("client", change_id, link)
            store.add_event(c, "awaiting_client", "Sent to approver", "Office Manager")
        return {"status": c["status"]}


@router.get("/approval-session", response_model=WorkspaceChangeOut)
def approval_session(token: str):
    with store.atomic():
        c = store.change_for_token(token)
        if not c:
            raise HTTPException(404, "Invalid link")
        return c


def _decide(token, new_status):
    with store.atomic():
        c = store.change_for_token(token)
        if not c:
            raise HTTPException(404, "Invalid link")
        if c["status"] != "awaiting_client":
            raise HTTPException(409, "Already decided")
        c["status"] = new_status
        title = (
            "Change approved; work order updated"
            if new_status == "approved"
            else "Change declined"
        )
        store.add_event(c, new_status, title, "Approver")
        store.notify("contractor", c["id"], title)
        return {"status": new_status}


@router.post("/approval-session/approve")
def client_approve(token: str):
    return _decide(token, "approved")


@router.post("/approval-session/decline")
def client_decline(token: str):
    return _decide(token, "rejected")


@router.get("/notifications")
def notifications(to: str):
    with store.atomic():
        return [n for n in store.NOTIFICATIONS if n["to"] == to]


@router.get("/projects/{project_id}/work-order")
def project_work_order(project_id: ProjectId):
    # Derived from committed approvals: retries/reloads cannot double-count a change.
    with store.atomic():
        return store.work_order(project_id)


@router.post("/changes/{change_id}/suggestion", response_model=Suggestion)
def suggest(change_id: str, request: SuggestionRequest):
    from services.suggestions import suggest_terms

    with store.atomic():
        c = store.CHANGES.get(change_id)
        if not c:
            raise HTTPException(404, "Not found")
        if c["status"] != "submitted":
            raise HTTPException(409, "This change has already been reviewed")
        record = dict(c)
    result = suggest_terms(record, request.original_scope)
    with store.atomic():
        c = store.CHANGES[change_id]
        if c["status"] != "submitted":
            raise HTTPException(409, "This change has already been reviewed")
        c["suggestion"] = result.model_dump()
        c["original_scope"] = request.original_scope
    return result
