import os
from typing import Annotated, Literal
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from schemas.changes import (
    Description,
    EstimatorReview,
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


@router.post("/changes/{change_id}/review", response_model=WorkspaceChangeOut)
def estimator_review(change_id: str, terms: EstimatorReview = Body(...)):
    """The estimator saves scope, proposed cost and timeline, and sends it on.

    Reviewable from `submitted`, from `in_review`, and from
    `authorized_to_proceed`: a fast-tracked change is authorized before the
    estimate exists, so it still needs its terms added afterwards.
    """
    with store.atomic():
        c = store.CHANGES.get(change_id)
        if not c:
            raise HTTPException(404, "Not found")
        if c["status"] not in ("submitted", "in_review", "authorized_to_proceed"):
            raise HTTPException(409, "This change is no longer open for review")
        link = store.record_review(
            c,
            terms.scope,
            terms.proposed_cost_cents,
            terms.requested_timeline_days,
            terms.currency,
        )
        # The console link stays the fallback until J3 sends real email.
        print("GC LINK:", link)
        return c


@router.post("/changes/{change_id}/authorize", response_model=WorkspaceChangeOut)
def manager_authorize(change_id: str):
    """Fast track: the manager lets work start before the estimate exists.

    This authorizes work only. The GC still decides, so no timeout and no
    authorization here ever approves a change.
    """
    with store.atomic():
        c = store.CHANGES.get(change_id)
        if not c:
            raise HTTPException(404, "Not found")
        if c["severity"] != "high":
            raise HTTPException(409, "Only a high-priority change can be fast tracked")
        if c["status"] not in ("submitted", "in_review"):
            raise HTTPException(409, "This change is past the point of authorizing work")
        store.authorize_fast_track(c)
        return c


@router.get("/approval-session", response_model=WorkspaceChangeOut)
def approval_session(token: str):
    with store.atomic():
        c = store.change_for_token(token)
        if not c:
            raise HTTPException(404, "Invalid link")
        return c


def _decide(token, approving):
    with store.atomic():
        c = store.change_for_token(token)
        if not c:
            raise HTTPException(404, "Invalid link")
        # A change sent by /review waits in awaiting_gc; one sent by the legacy
        # /admin-approve waits in awaiting_client. Both are a pending decision.
        if c["status"] not in ("awaiting_gc", "awaiting_client"):
            raise HTTPException(409, "Already decided")
        # Answer a legacy request in legacy words so the merged frontend, which
        # tests for "rejected", keeps working until U3 lands.
        legacy = c["status"] == "awaiting_client"
        if approving:
            new_status = "approved"
        else:
            new_status = "rejected" if legacy else "declined"
        c["status"] = new_status
        title = (
            "Change approved; work order updated" if approving else "Change declined"
        )
        store.add_event(c, new_status, title, "GC")
        store.notify("contractor" if legacy else "office", c["id"], title)
        return {"status": new_status}


@router.post("/approval-session/approve")
def client_approve(token: str):
    return _decide(token, True)


@router.post("/approval-session/decline")
def client_decline(token: str):
    return _decide(token, False)


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
