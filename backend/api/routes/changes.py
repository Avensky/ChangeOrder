import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from api.routes import session
from core.auth import Caller, require_roles
from schemas.changes import (
    Description,
    ChangeWithPhotos,
    EstimatorReview,
    PhotoLink,
    ReviewTerms,
    Severity,
    Status,
    Suggestion,
    SuggestionRequest,
)
from services import email, prototype_workflow
from services.photos import delete_photo, key_company, photo_links, save_photo
from core.config import email_settings
from db.repository import Conflict, NotFound, default_company_id
from db.store_selector import store

# One set of workflow functions for both backends. The selected store is the
# repository on postgres; on the default sqlite it is the services/store.py
# module, which lacks the query and decision functions, so those come from
# services/prototype_workflow.py. Both raise the repository's NotFound/Conflict.
workflow = store if hasattr(store, "send_to_gc") else prototype_workflow

router = APIRouter(prefix="/api/v1", tags=["changes"])
router.include_router(session.router)
ProjectId = Literal["north-park", "harbor", "cedar"]

FIELD = require_roles("field")
ESTIMATOR = require_roles("estimator")
MANAGER = require_roles("manager")
STAFF = require_roles("field", "estimator", "manager")


@contextmanager
def _workflow_errors():
    """Map workflow errors to HTTP. Put outside atomic() so it rolls back first."""
    try:
        yield
    except NotFound as error:
        raise HTTPException(404, str(error) or "Not found") from None
    except Conflict as error:
        raise HTTPException(409, str(error)) from None


def _transaction(caller: Caller | None):
    """Open the workflow transaction for the caller's company (postgres).

    The prototype has one workspace and takes no company.
    """
    if caller is None:
        return workflow.atomic()
    return workflow.atomic(caller.company_id)


def _company_id(caller: Caller | None) -> int:
    return caller.company_id if caller else default_company_id()


def _with_photos(changes: list[dict], company_id: int | None) -> list[dict]:
    """Add each change's photo links (J9), signed in one batch for the list.

    Only photos of company_id are signed; the API checked the caller (staff:
    the verified token; GC: the link token) before this runs.
    """
    keys = [key for c in changes for key in (c.get("photo_keys") or [])]
    links = {link["key"]: link for link in photo_links(keys, company_id)}
    return [
        dict(c, photos=[links[k] for k in (c.get("photo_keys") or []) if k in links])
        for c in changes
    ]


def _with_photos_for_gc(change: dict) -> dict:
    """The GC has no company of their own: the change's keys name it."""
    keys = change.get("photo_keys") or []
    company = next((key_company(k) for k in keys if key_company(k) is not None), None)
    return _with_photos([change], company)[0]


def _actor_id(caller: Caller | None):
    return None if caller is None else caller.id


def _approval_link(token: str) -> str:
    base = os.getenv("APP_URL", "http://localhost:8081").rstrip("/")
    return f"{base}/approve?token={token}"


@router.post("/changes", response_model=ChangeWithPhotos, status_code=201)
async def submit_change(
    description: Annotated[Description, Form()],
    severity: Severity = Form(Severity.normal),
    photos: list[UploadFile] = File(...),
    title: Annotated[str, Form(max_length=120)] = "",
    project_id: ProjectId = Form("north-park"),
    submitted_by: Literal["contractor", "subcontractor"] = Form("contractor"),
    caller: Caller | None = Depends(FIELD),
):
    if not 1 <= len(photos) <= 10:
        raise HTTPException(422, "Attach between 1 and 10 photos.")
    keys = []
    company_id = _company_id(caller)
    try:
        # Upload first, then write the rows; if the write fails, the uploads
        # are removed again so no orphan photo is left in storage.
        for photo in photos:
            keys.append(await save_photo(photo, company_id))
        with _workflow_errors(), _transaction(caller):
            change = workflow.create_change(
                description,
                severity,
                keys,
                title.strip(),
                project_id,
                submitted_by,
                submitted_by_user_id=_actor_id(caller),
            )
    except BaseException:
        for key in keys:
            await delete_photo(key)
        raise
    finally:
        for photo in photos:
            await photo.close()
    return _with_photos([change], company_id)[0]


@router.get("/changes", response_model=list[ChangeWithPhotos])
def list_changes(status: Status | None = None, caller: Caller | None = Depends(STAFF)):
    with _workflow_errors(), _transaction(caller):
        changes = workflow.list_changes(status)
    return _with_photos(changes, _company_id(caller))


@router.get("/changes/{change_id}/photos", response_model=list[PhotoLink])
def change_photos(change_id: str, caller: Caller | None = Depends(STAFF)):
    """Fresh links for one change's photos, when the ones the app has expired.

    404 for an unknown change or one of another company (the lookup is
    company-filtered), so the answer never reveals that a change exists.
    """
    with _workflow_errors(), _transaction(caller):
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
    return _with_photos([c], _company_id(caller))[0]["photos"]


# LEGACY: the float-money route the merged frontend still calls. Remove it
# when U3 moves the app onto /review and /authorize.
@router.post("/changes/{change_id}/admin-approve")
def admin_approve(
    change_id: str,
    terms: ReviewTerms = Body(...),
    caller: Caller | None = Depends(ESTIMATOR),
):
    with _workflow_errors(), _transaction(caller):
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
            actor_name=caller.name if caller else "Office Manager",
            actor_user_id=_actor_id(caller),
        )
        return {"status": sent["status"]}


@router.post("/changes/{change_id}/review", response_model=ChangeWithPhotos)
def estimator_review(
    change_id: str,
    terms: EstimatorReview = Body(...),
    caller: Caller | None = Depends(ESTIMATOR),
):
    """The estimator saves scope, proposed cost and timeline, and sends it on.

    Reviewable from `submitted`, `in_review` and `authorized_to_proceed`: a
    fast-tracked change is authorized before the estimate exists, so it still
    needs its terms added afterwards.
    """
    with _workflow_errors(), _transaction(caller):
        if workflow.get_change(change_id) is None:
            raise HTTPException(404, "Not found")
        # Integer cents and the currency go through as given, never as a float.
        sent = workflow.send_to_gc(
            change_id,
            terms.scope,
            impact_days=terms.requested_timeline_days,
            actor_name=caller.name if caller else "Estimator",
            actor_user_id=_actor_id(caller),
            currency=terms.currency,
            proposed_cost_cents=terms.proposed_cost_cents,
        )
        link = _approval_link(sent["token"])
        c = workflow.get_change(change_id)
    # Email only after the transaction commits: a link is never sent for a
    # review that was rolled back, and a slow provider never holds the lock.
    subject, body = email.approval_request(c, link)
    sent_by_email = email.send(email_settings()["gc_address"], subject, body)
    # The console link is the fallback and stays printed either way, so the
    # demo works with no email key and when the provider is down.
    print("GC LINK:", link, "(emailed)" if sent_by_email else "(not emailed)")
    return _with_photos([c], _company_id(caller))[0]


@router.post("/changes/{change_id}/authorize", response_model=ChangeWithPhotos)
def manager_authorize(change_id: str, caller: Caller | None = Depends(MANAGER)):
    """Fast track: the manager lets work start before the estimate exists.

    This authorizes work only. The GC still decides, so no timeout and no
    authorization here ever approves a change.
    """
    with _workflow_errors(), _transaction(caller):
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
        if c["severity"] != "high":
            raise HTTPException(409, "Only a high-priority change can be fast tracked")
        if c["status"] not in ("submitted", "in_review"):
            raise HTTPException(409, "This change is past the point of authorizing work")
        workflow.authorize_to_proceed(
            change_id,
            actor_name=caller.name if caller else "Manager",
            actor_user_id=_actor_id(caller),
        )
        c = workflow.get_change(change_id)
    # A heads-up only, sent after the commit. It carries no link, because there
    # is nothing to decide until the estimator adds the cost.
    subject, body = email.fast_track_notice(c)
    email.send(email_settings()["gc_address"], subject, body)
    return _with_photos([c], _company_id(caller))[0]


# The GC link is token-only: no staff account, and no role check.
@router.get("/approval-session", response_model=ChangeWithPhotos)
def approval_session(token: str):
    with workflow.atomic():
        c = workflow.change_for_token(token)
        if not c:
            raise HTTPException(404, "Invalid link")
    return _with_photos_for_gc(c)


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
def notifications(to: str, caller: Caller | None = Depends(STAFF)):
    with _transaction(caller):
        return workflow.list_notifications(to)


@router.get("/projects/{project_id}/work-order")
def project_work_order(project_id: ProjectId, caller: Caller | None = Depends(STAFF)):
    # Derived from committed approvals: retries/reloads cannot double-count a change.
    with _transaction(caller):
        return workflow.work_order(project_id)


@router.post("/changes/{change_id}/suggestion", response_model=Suggestion)
def suggest(
    change_id: str,
    request: SuggestionRequest,
    caller: Caller | None = Depends(ESTIMATOR),
):
    from services.suggestions import suggest_terms

    with _workflow_errors(), _transaction(caller):
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
        if c["status"] != "submitted":
            raise HTTPException(409, "This change has already been reviewed")
        record = dict(c)
    result = suggest_terms(record, request.original_scope)
    with _workflow_errors(), _transaction(caller):
        workflow.save_suggestion(change_id, result.model_dump(), request.original_scope)
    return result
