import os
from contextlib import contextmanager
from decimal import Decimal
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
from services import email, prototype_workflow
from services.photos import save_photo
from core.config import UPLOAD_DIR, email_settings
from db.repository import Conflict, NotFound
from db.store_selector import store

# One set of workflow functions for both backends. The selected store is the
# repository on postgres; on the default sqlite it is the services/store.py
# module, which lacks the query and decision functions, so those come from
# services/prototype_workflow.py. Both raise the repository's NotFound/Conflict.
workflow = store if hasattr(store, "send_to_gc") else prototype_workflow

router = APIRouter(prefix="/api/v1", tags=["changes"])
ProjectId = Literal["north-park", "harbor", "cedar"]


@contextmanager
def _workflow_errors():
    """Map workflow errors to HTTP. Put outside atomic() so it rolls back first."""
    try:
        yield
    except NotFound as error:
        raise HTTPException(404, str(error) or "Not found") from None
    except Conflict as error:
        raise HTTPException(409, str(error)) from None


def _approval_link(token: str) -> str:
    base = os.getenv("APP_URL", "http://localhost:8081").rstrip("/")
    return f"{base}/approve?token={token}"


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
        with _workflow_errors(), workflow.atomic():
            return workflow.create_change(
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
    with _workflow_errors(), workflow.atomic():
        return workflow.list_changes(status)


# LEGACY: the float-money route the merged frontend still calls. Remove it
# when U3 moves the app onto /review and /authorize.
@router.post("/changes/{change_id}/admin-approve")
def admin_approve(change_id: str, terms: ReviewTerms = Body(...)):
    with _workflow_errors(), workflow.atomic():
        if workflow is prototype_workflow:
            return workflow.legacy_admin_approve(
                change_id, terms.amount, terms.impact_days, terms.scope
            )
        # On postgres the legacy route can only send to the GC. It never
        # approves a high-priority change without the GC (AGENTS.md).
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
        if c["status"] != "submitted":
            raise HTTPException(409, "This change has already been reviewed")
        if c["severity"] == "high":
            raise HTTPException(
                409, "Fast-track changes use /authorize, then /review; the GC decides"
            )
        sent = workflow.send_to_gc(
            change_id,
            terms.scope,
            Decimal(str(terms.amount)),
            terms.impact_days,
            actor_name="Office Manager",
        )
        return {"status": sent["status"]}


@router.post("/changes/{change_id}/review", response_model=WorkspaceChangeOut)
def estimator_review(change_id: str, terms: EstimatorReview = Body(...)):
    """The estimator saves scope, proposed cost and timeline, and sends it on.

    Reviewable from `submitted`, `in_review` and `authorized_to_proceed`: a
    fast-tracked change is authorized before the estimate exists, so it still
    needs its terms added afterwards.
    """
    with _workflow_errors(), workflow.atomic():
        if workflow.get_change(change_id) is None:
            raise HTTPException(404, "Not found")
        sent = workflow.send_to_gc(
            change_id,
            terms.scope,
            # Money is integer cents on the API and dollars inside the workflow;
            # Decimal keeps the division exact.
            Decimal(terms.proposed_cost_cents) / 100,
            terms.requested_timeline_days,
            actor_name="Estimator",
        )
        link = _approval_link(sent["token"])
        c = workflow.get_change(change_id)
        subject, body = email.approval_request(c, link)
        sent_by_email = email.send(email_settings()["gc_address"], subject, body)
        # The console link is the fallback and stays printed either way, so the
        # demo works with no email key and when the provider is down.
        print("GC LINK:", link, "(emailed)" if sent_by_email else "(not emailed)")
        return c


@router.post("/changes/{change_id}/authorize", response_model=WorkspaceChangeOut)
def manager_authorize(change_id: str):
    """Fast track: the manager lets work start before the estimate exists.

    This authorizes work only. The GC still decides, so no timeout and no
    authorization here ever approves a change.
    """
    with _workflow_errors(), workflow.atomic():
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
        if c["severity"] != "high":
            raise HTTPException(409, "Only a high-priority change can be fast tracked")
        if c["status"] not in ("submitted", "in_review"):
            raise HTTPException(409, "This change is past the point of authorizing work")
        workflow.authorize_to_proceed(change_id, actor_name="Manager")
        c = workflow.get_change(change_id)
        # A heads-up only. It carries no link, because there is nothing to
        # decide until the estimator adds the cost.
        subject, body = email.fast_track_notice(c)
        email.send(email_settings()["gc_address"], subject, body)
        return c


@router.get("/approval-session", response_model=WorkspaceChangeOut)
def approval_session(token: str):
    with workflow.atomic():
        c = workflow.change_for_token(token)
        if not c:
            raise HTTPException(404, "Invalid link")
        return c


def _decide(token, decision):
    with _workflow_errors(), workflow.atomic():
        return workflow.decide(token, decision)


@router.post("/approval-session/approve")
def client_approve(token: str):
    return _decide(token, "approved")


@router.post("/approval-session/decline")
def client_decline(token: str):
    return _decide(token, "declined")


@router.get("/notifications")
def notifications(to: str):
    with workflow.atomic():
        return workflow.list_notifications(to)


@router.get("/projects/{project_id}/work-order")
def project_work_order(project_id: ProjectId):
    # Derived from committed approvals: retries/reloads cannot double-count a change.
    with workflow.atomic():
        return workflow.work_order(project_id)


@router.post("/changes/{change_id}/suggestion", response_model=Suggestion)
def suggest(change_id: str, request: SuggestionRequest):
    from services.suggestions import suggest_terms

    with _workflow_errors(), workflow.atomic():
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
        if c["status"] != "submitted":
            raise HTTPException(409, "This change has already been reviewed")
        record = dict(c)
    result = suggest_terms(record, request.original_scope)
    with _workflow_errors(), workflow.atomic():
        workflow.save_suggestion(change_id, result.model_dump(), request.original_scope)
    return result
