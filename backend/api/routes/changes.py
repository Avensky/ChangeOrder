import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, UploadFile
from api.routes import session
from core.auth import Caller, require_roles
from schemas.changes import (
    ApprovalExchange,
    ApprovalSessionOut,
    Description,
    EstimatorReview,
    GcDecision,
    ReviewTerms,
    Severity,
    Status,
    Suggestion,
    SuggestionRequest,
    WorkspaceChangeOut,
)
from services import email, gc_session, prototype_workflow
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


# The GC link is token-only: no staff account, and no role check. The page
# exchanges the emailed token once for a short-lived session (J8), so the token
# leaves the address bar, the history and the access logs. Every request looks
# the link up again, so an expired or revoked link stops working at once.
# Opening, exchanging or reloading never decides anything.

INVALID_LINK = "This link is not valid. It may have expired or been replaced by a newer one."
SESSION_ENDED = "This session has ended. Open the link in the email again."


def _session_token(authorization: str | None) -> str:
    """The link token inside an "Authorization: Bearer <session>" header, or 401."""
    scheme, _, session = (authorization or "").partition(" ")
    token = None
    if scheme.lower() == "bearer" and session.strip():
        token = gc_session.link_token(session.strip())
    if token is None:
        raise HTTPException(401, SESSION_ENDED, headers={"WWW-Authenticate": "Bearer"})
    return token


def _proposal(token: str):
    with workflow.atomic():
        c = workflow.change_for_token(token)
        if not c:
            raise HTTPException(404, INVALID_LINK)
        return c


@router.post("/approval-session/exchange", response_model=ApprovalSessionOut)
def exchange_link(body: ApprovalExchange):
    change = _proposal(body.token)
    session, expires_at = gc_session.issue(body.token)
    return {"session": session, "expires_at": expires_at, "change": change}


@router.get("/approval-session/proposal", response_model=WorkspaceChangeOut)
def session_proposal(authorization: str | None = Header(None)):
    return _proposal(_session_token(authorization))


def _recorded(token: str, decision: str) -> dict | None:
    """The answer for a decision that is already recorded, or None."""
    with workflow.atomic():
        c = workflow.change_for_token(token)
    wanted = ("approved",) if decision == "approved" else ("declined", "rejected")
    if c and c["status"] in wanted:
        return {"status": c["status"]}
    return None


def _decide(token: str, decision: str, key: str | None = None):
    """Record the GC's one decision. A retry with the same key gets the first answer.

    The database allows one decision per request, so a retry never records a
    second one. With a key, a retry that finds this same decision already
    recorded gets 200 and the same body instead of a 409, so a page that lost
    the first response does not show an error. A different decision is a 409.
    """
    link_hash = gc_session.token_hash(token)
    if key:
        seen = gc_session.idempotency_keys.get(link_hash, key)
        if seen is not None:
            if seen[0] != decision:
                raise HTTPException(422, "This key was already used for a different decision")
            return seen[1]
    try:
        with _workflow_errors(), workflow.atomic():
            result = workflow.decide(token, decision)
    except HTTPException as error:
        # The key was forgotten (a restart) or two presses raced: fall back to
        # what is recorded. Same decision: the same answer. Otherwise the 409.
        replay = _recorded(token, decision) if key and error.status_code == 409 else None
        if replay is None:
            raise
        result = replay
    if key:
        gc_session.idempotency_keys.put(link_hash, key, decision, result)
    return result


def _key(body: GcDecision | None) -> str | None:
    return body.idempotency_key if body else None


@router.post("/approval-session/proposal/approve")
def session_approve(
    body: GcDecision | None = Body(None), authorization: str | None = Header(None)
):
    return _decide(_session_token(authorization), "approved", _key(body))


@router.post("/approval-session/proposal/decline")
def session_decline(
    body: GcDecision | None = Body(None), authorization: str | None = Header(None)
):
    return _decide(_session_token(authorization), "declined", _key(body))


# LEGACY: the token in the query string, which the merged GC page still uses.
# Remove when U8 moves the page onto /exchange and /proposal.
@router.get("/approval-session", response_model=WorkspaceChangeOut)
def approval_session(token: str):
    return _proposal(token)


@router.post("/approval-session/approve")
def client_approve(token: str, body: GcDecision | None = Body(None)):
    return _decide(token, "approved", _key(body))


@router.post("/approval-session/decline")
def client_decline(token: str, body: GcDecision | None = Body(None)):
    return _decide(token, "declined", _key(body))


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
