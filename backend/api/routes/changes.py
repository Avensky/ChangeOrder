import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from api.routes import session
from core.auth import Caller, require_roles
from schemas.changes import (
    Description,
    EstimatorReview,
    ReviewTerms,
    Severity,
    Status,
    SuggestionOut,
    SuggestionRequest,
    SuggestionResponse,
    WorkspaceChangeOut,
)
from ai import suggest as ai_suggest
from services import email, prototype_workflow
from services.photos import save_photo
import core.config as config
from core.config import email_settings
from db.repository import Conflict, NotFound
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


def _actor_id(caller: Caller | None):
    return None if caller is None else caller.id


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
    caller: Caller | None = Depends(FIELD),
):
    if not 1 <= len(photos) <= 10:
        raise HTTPException(422, "Attach between 1 and 10 photos.")
    keys = []
    try:
        for photo in photos:
            keys.append(await save_photo(photo))
        with _workflow_errors(), _transaction(caller):
            return workflow.create_change(
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
            (config.UPLOAD_DIR / key).unlink(missing_ok=True)
        raise
    finally:
        for photo in photos:
            await photo.close()


@router.get("/changes", response_model=list[WorkspaceChangeOut])
def list_changes(status: Status | None = None, caller: Caller | None = Depends(STAFF)):
    with _workflow_errors(), _transaction(caller):
        return workflow.list_changes(status)


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


@router.post("/changes/{change_id}/review", response_model=WorkspaceChangeOut)
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
    return c


@router.post("/changes/{change_id}/authorize", response_model=WorkspaceChangeOut)
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
    return c


# The GC link is token-only: no staff account, and no role check.
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
def notifications(to: str, caller: Caller | None = Depends(STAFF)):
    with _transaction(caller):
        return workflow.list_notifications(to)


@router.get("/projects/{project_id}/work-order")
def project_work_order(project_id: ProjectId, caller: Caller | None = Depends(STAFF)):
    # Derived from committed approvals: retries/reloads cannot double-count a change.
    with _transaction(caller):
        return workflow.work_order(project_id)


AI_UNAVAILABLE = "AI suggestions are not available. The office can enter cost and days manually."
AI_UNUSABLE = "The AI reply could not be used. Try again, or enter cost and days manually."
SUGGESTION_READERS = require_roles("estimator", "manager")


@contextmanager
def _suggestion_errors():
    """The workflow errors, plus a bad response or rating as 422."""
    with _workflow_errors():
        try:
            yield
        except ValueError as error:
            raise HTTPException(422, str(error)) from None


def _change_text(c: dict) -> str:
    """What the field reported: title and description. Text only, never photos."""
    return "\n".join(part.strip() for part in (c.get("title") or "", c["description"]) if part.strip())


@router.post("/changes/{change_id}/suggestion", response_model=SuggestionOut)
def suggest(
    change_id: str,
    request: SuggestionRequest,
    caller: Caller | None = Depends(ESTIMATOR),
):
    """Ask the AI worker (B9) for a scope flag and a cost range, store it, return it.

    Advice only: it sets no terms and no status, and the estimator still
    enters the cost. The worker takes text only, so no photo reaches the model.
    """
    with _workflow_errors(), _transaction(caller):
        c = workflow.get_change(change_id)
        if c is None:
            raise HTTPException(404, "Not found")
        if c["status"] not in ("submitted", "in_review"):
            raise HTTPException(409, "This change has already been reviewed")
        description = _change_text(c)
    # Outside the transaction, so a slow model never holds the change's lock.
    try:
        result = ai_suggest.suggest(
            change_description=description, original_proposal=request.original_scope
        )
    except ai_suggest.SuggestionUnavailable:
        raise HTTPException(503, AI_UNAVAILABLE) from None
    except ai_suggest.SuggestionError:
        raise HTTPException(502, AI_UNUSABLE) from None
    with _suggestion_errors(), _transaction(caller):
        return workflow.create_suggestion(
            change_id, result.as_repository_dict(), request.original_scope
        )


@router.get("/changes/{change_id}/suggestions", response_model=list[SuggestionOut])
def list_suggestions(change_id: str, caller: Caller | None = Depends(SUGGESTION_READERS)):
    """A change's suggestions, newest first, with the estimator's response if any."""
    with _workflow_errors(), _transaction(caller):
        return workflow.list_suggestions(change_id)


@router.post("/suggestions/{suggestion_id}/response", response_model=SuggestionOut)
def respond_to_suggestion(
    suggestion_id: str,
    body: SuggestionResponse,
    caller: Caller | None = Depends(ESTIMATOR),
):
    """Record accepted, edited or dismissed, and an optional 1 to 5 rating, once.

    Who answered comes from the verified token, never the body. Answering
    records the choice only: the change's terms and status do not move.
    """
    with _suggestion_errors(), _transaction(caller):
        return workflow.respond_to_suggestion(
            suggestion_id, body.response, _actor_id(caller), rating=body.rating
        )
