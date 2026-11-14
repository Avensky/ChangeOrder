"""Repository layer: the prototype store's functions, on the schema v2 tables.

The function names, arguments and returned dicts follow services/store.py, so
the routes can move over with little change. The mapping between the
prototype's shapes (dollars, impact_days, old status names, history events) and
the schema's (integer cents, requested_timeline_days, the v2 status set) is the
table in db/migrations/README.md, "From the prototype store to schema v2".

How it is used:

    with repository.atomic():                      # one database transaction
        change = repository.create_change(...)     # commits when the block ends
    # an exception inside the block rolls everything back, notifications too.

Every function runs inside atomic() and filters by the company that atomic()
was opened for (db.database.company_select). Until sign-in provides the
caller's company (tasks B7 and J5), atomic() falls back to the company in the
WORKSPACE_COMPANY_ID setting (default 1). Pass company_id explicitly as soon as
the caller's verified token gives one; never take it from the request body.

Errors are plain exceptions for the routes to turn into HTTP codes:
NotFound -> 404, Conflict -> 409 (a retried or late decision, a change that was
already reviewed). A Conflict rolls the transaction back, as the prototype did.
"""

import hashlib
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from .database import company_select, get_engine
from .models import (
    AiSuggestion,
    ApprovalDecision,
    ApprovalLink,
    ApprovalRequest,
    ChangeEvent,
    ChangeHistory,
    ChangeOrder,
    ChangeOrderRevision,
    Company,
    Notification,
    Photo,
    Project,
    User,
    utc_now,
)

# ---------------------------------------------------------------- vocabulary

# Prototype status names the routes and the app still use, and their v2 names.
_LEGACY_TO_V2 = {"awaiting_client": "awaiting_gc", "rejected": "declined"}
_V2_TO_LEGACY = {value: key for key, value in _LEGACY_TO_V2.items()}

# The prototype addressed notifications to a role label, not to a user.
_LABEL_ROLES = {
    "admin": ("estimator", "manager"),
    "contractor": ("field",),
    "client": ("gc",),
}
_ROLE_LABEL = {
    "estimator": "admin",
    "manager": "admin",
    "field": "contractor",
    "gc": "client",
}
_SUBMITTER_LABELS = ("contractor", "subcontractor")

DEFAULT_FIRST_NUMBER = 1049  # the prototype's first code, CO-1049
DEFAULT_LINK_DAYS = 14

REVIEWABLE = ("submitted", "in_review", "authorized_to_proceed")


class NotFound(LookupError):
    """The record does not exist in this company, or the link is not valid."""


class Conflict(Exception):
    """The change is not in a state that allows this action (HTTP 409)."""


# ------------------------------------------------------------ transactions


@dataclass
class _Context:
    session: Session
    company_id: int


_current: ContextVar[_Context | None] = ContextVar("repository_context", default=None)
_engine_override: Engine | None = None


def set_engine(engine: Engine | None) -> None:
    """Use this engine instead of the one built from DATABASE_URL (tests)."""
    global _engine_override
    _engine_override = engine


def default_company_id() -> int:
    return int(os.environ.get("WORKSPACE_COMPANY_ID", "1"))


def now() -> str:
    return utc_now().isoformat()


@contextmanager
def atomic(company_id: int | None = None) -> Iterator[None]:
    """One database transaction for one company.

    Everything written inside commits together when the block ends and is
    rolled back if it raises. A nested atomic() joins the outer transaction.
    """
    outer = _current.get()
    if outer is not None:
        if company_id not in (None, outer.company_id):
            raise ValueError("A transaction cannot switch company.")
        yield
        return
    company = default_company_id() if company_id is None else company_id
    with Session(_engine_override or get_engine()) as session:
        marker = _current.set(_Context(session, company))
        try:
            yield
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            _current.reset(marker)


def _ctx() -> _Context:
    context = _current.get()
    if context is None:
        raise RuntimeError("Call repository functions inside `with repository.atomic():`.")
    return context


# ------------------------------------------------------------------ helpers


def _utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes; the values are always UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat()


def _cents(dollars) -> int:
    """Dollars (float or Decimal) to integer cents. Refuses fractions of a cent."""
    value = Decimal(str(dollars)) * 100
    if value < 0 or value != value.to_integral_value():
        raise ValueError("Amount must be a non-negative number of whole cents.")
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _dollars(cents: int | None) -> float:
    return float(Decimal(cents or 0) / 100)


def _v2(status: str) -> str:
    return _LEGACY_TO_V2.get(status, status)


def _legacy(status: str) -> str:
    return _V2_TO_LEGACY.get(status, status)


def _id(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise NotFound("Not found") from None


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _code(number: int) -> str:
    return f"CO-{number}"


def _lock_change(change_id) -> ChangeEvent:
    """The company's change, locked for update where the database supports it."""
    context = _ctx()
    row = context.session.exec(
        company_select(ChangeEvent, context.company_id)
        .where(ChangeEvent.id == _id(change_id))
        .with_for_update()
    ).first()
    if row is None:
        raise NotFound("Not found")
    return row


def _users_with_roles(*roles: str) -> list[User]:
    context = _ctx()
    return list(
        context.session.exec(
            company_select(User, context.company_id)
            .where(col(User.role).in_(roles))
            .order_by(User.id)
        )
    )


def _link_target(change_id: int) -> str:
    return f"/changes/{change_id}"


def _write_notice(user_id: int, change_id: int, kind: str, message: str) -> None:
    context = _ctx()
    context.session.add(
        Notification(
            company_id=context.company_id,
            report_id=change_id,
            recipient_user_id=user_id,
            type=kind,
            message=message,
            link_target=_link_target(change_id),
        )
    )


def _notify_users(users, change_id: int, kind: str, message: str) -> None:
    seen: set[int] = set()
    for user in users:
        if user.id not in seen:
            seen.add(user.id)
            _write_notice(user.id, change_id, kind, message)


def _record(event: ChangeEvent, status: str, title: str, name: str, user_id=None) -> None:
    context = _ctx()
    context.session.add(
        ChangeHistory(
            company_id=context.company_id,
            change_event_id=event.id,
            status=_v2(status),
            title=title,
            actor_user_id=user_id,
            actor_name=name,
        )
    )


def _submitter(event: ChangeEvent) -> User:
    context = _ctx()
    user = context.session.exec(
        company_select(User, context.company_id).where(User.id == event.submitted_by_id)
    ).first()
    if user is None:  # unreachable: a two-column foreign key guarantees it
        raise NotFound("Submitter not found")
    return user


# ----------------------------------------------------------- reading changes


def _build(events: list[ChangeEvent]) -> list[dict]:
    """The prototype's change dicts for these events, in the order given."""
    if not events:
        return []
    context = _ctx()
    session, company = context.session, context.company_id
    ids = [event.id for event in events]

    projects = {p.id: p for p in session.exec(company_select(Project, company))}
    users = {u.id: u for u in session.exec(company_select(User, company))}
    photos: dict[int, list[str]] = {}
    for photo in session.exec(
        company_select(Photo, company).where(col(Photo.change_event_id).in_(ids)).order_by(Photo.id)
    ):
        photos.setdefault(photo.change_event_id, []).append(photo.storage_key)
    history: dict[int, list[dict]] = {}
    for row in session.exec(
        company_select(ChangeHistory, company)
        .where(col(ChangeHistory.change_event_id).in_(ids))
        .order_by(ChangeHistory.id)
    ):
        history.setdefault(row.change_event_id, []).append(
            dict(
                id=str(row.id),
                changeId=str(row.change_event_id),
                title=row.title,
                person=row.actor_name,
                time=_iso(row.created_at),
                kind=_legacy(row.status),
            )
        )
    order_event = {
        o.id: o.change_event_id
        for o in session.exec(
            company_select(ChangeOrder, company).where(col(ChangeOrder.change_event_id).in_(ids))
        )
    }
    latest: dict[int, ChangeOrderRevision] = {}
    if order_event:
        for revision in session.exec(
            company_select(ChangeOrderRevision, company)
            .where(col(ChangeOrderRevision.change_order_id).in_(list(order_event)))
            .order_by(ChangeOrderRevision.revision_number)
        ):
            latest[order_event[revision.change_order_id]] = revision
    suggestion: dict[int, AiSuggestion] = {}
    for row in session.exec(
        company_select(AiSuggestion, company)
        .where(col(AiSuggestion.change_event_id).in_(ids))
        .order_by(AiSuggestion.id)
    ):
        suggestion[row.change_event_id] = row

    result = []
    for event in events:
        revision = latest.get(event.id)
        submitter = users[event.submitted_by_id]
        label = submitter.name.lower()
        change = dict(
            id=str(event.id),
            code=_code(event.number),
            title=event.title,
            description=event.description,
            severity=event.severity,
            status=_legacy(event.status),
            photo_keys=photos.get(event.id, []),
            project_id=projects[event.project_id].slug,
            submitted_by=label if label in _SUBMITTER_LABELS else "contractor",
            author=submitter.name,
            created_at=_iso(event.created_at),
            amount=_dollars(revision.proposed_cost_cents) if revision else 0,
            impact_days=(revision.requested_timeline_days or 0) if revision else 0,
            sent_for_approval=bool(revision and revision.frozen_at),
            history=history.get(event.id, []),
            suggestion=None,
        )
        if revision:
            change["approved_scope"] = revision.scope
        advice = suggestion.get(event.id)
        if advice:
            change["suggestion"] = dict(
                scope=advice.suggested_scope,
                amount=_dollars(advice.suggested_cost_cents),
                impact_days=advice.suggested_timeline_days,
                rationale=advice.rationale,
                in_scope=advice.in_scope,
            )
            change["original_scope"] = advice.original_scope
        result.append(change)
    return result


def get_change(change_id) -> dict | None:
    """One change of this company, or None (the prototype's CHANGES.get)."""
    context = _ctx()
    try:
        key = int(change_id)
    except (TypeError, ValueError):
        return None
    event = context.session.exec(
        company_select(ChangeEvent, context.company_id).where(ChangeEvent.id == key)
    ).first()
    return _build([event])[0] if event else None


def list_changes(status: str | None = None) -> list[dict]:
    """The company's changes, oldest first, optionally with one status.

    status may be a v2 name or a prototype name (awaiting_client, rejected).
    """
    context = _ctx()
    query = company_select(ChangeEvent, context.company_id).order_by(ChangeEvent.id)
    if status is not None:
        query = query.where(ChangeEvent.status == _v2(str(getattr(status, "value", status))))
    return _build(list(context.session.exec(query)))


# ----------------------------------------------------------------- notices


def notify(recipient, change_id, message, kind: str = "change_submitted") -> None:
    """Write one notification row per recipient user.

    recipient is a prototype label ("admin", "contractor", "client"), which
    reaches every user with that role, or a user id. kind is one of
    db.models.NOTIFICATION_TYPES. Never put an approval token in message.
    """
    context = _ctx()
    cid = _id(change_id)
    if isinstance(recipient, int) or str(recipient).isdigit():
        users = list(
            context.session.exec(
                company_select(User, context.company_id).where(User.id == int(recipient))
            )
        )
    else:
        if recipient not in _LABEL_ROLES:
            raise ValueError(f"Unknown recipient {recipient!r}")
        users = _users_with_roles(*_LABEL_ROLES[recipient])
    if recipient in ("contractor",):
        # The submitter, not every field worker, hears about their own change.
        event = context.session.exec(
            company_select(ChangeEvent, context.company_id).where(ChangeEvent.id == cid)
        ).first()
        if event is not None:
            users = [u for u in users if u.id == event.submitted_by_id]
    _notify_users(users, cid, kind, message)


def list_notifications(to: str) -> list[dict]:
    """The prototype's GET /notifications: dicts with to, change_id and msg."""
    context = _ctx()
    query = company_select(Notification, context.company_id).order_by(Notification.id)
    users = {u.id: u for u in context.session.exec(company_select(User, context.company_id))}
    if to in _LABEL_ROLES:
        ids = [u.id for u in users.values() if u.role in _LABEL_ROLES[to]]
    elif str(to).isdigit():
        ids = [int(to)]
    else:
        return []
    rows = context.session.exec(query.where(col(Notification.recipient_user_id).in_(ids)))
    return [
        dict(
            id=str(n.id),
            to=_ROLE_LABEL[users[n.recipient_user_id].role],
            change_id=str(n.report_id),
            msg=n.message,
            type=n.type,
            status=n.status,
            link_target=n.link_target,
            created_at=_iso(n.created_at),
        )
        for n in rows
    ]


# ----------------------------------------------------------------- history


def add_event(change: dict, status: str, title: str, person: str, actor_user_id=None) -> dict:
    """Append a timeline entry and return it. Also appends it to change["history"]."""
    context = _ctx()
    event = _lock_change(change["id"])
    _record(event, status, title, person, actor_user_id)
    context.session.flush()
    row = context.session.exec(
        company_select(ChangeHistory, context.company_id)
        .where(ChangeHistory.change_event_id == event.id)
        .order_by(col(ChangeHistory.id).desc())
    ).first()
    entry = dict(
        id=str(row.id),
        changeId=str(event.id),
        title=title,
        person=person,
        time=_iso(row.created_at),
        kind=_legacy(_v2(status)),
    )
    change.setdefault("history", []).append(entry)
    return entry


# --------------------------------------------------------------- submitting


def create_change(
    description,
    severity,
    photo_keys,
    title="",
    project_id="north-park",
    submitted_by="contractor",
):
    """Save a field report with its photos and alert the office."""
    context = _ctx()
    session, company = context.session, context.company_id
    severity = str(getattr(severity, "value", severity))
    project = session.exec(
        company_select(Project, company).where(Project.slug == project_id)
    ).first()
    if project is None:
        raise NotFound(f"Project {project_id!r} not found")
    fields = _users_with_roles("field")
    if not fields:
        raise NotFound("The company has no field user to submit the change")
    # Schema v2 has no contractor/subcontractor label: both are the field role.
    # Prefer the field user named like the label, else the first field user.
    user = next((u for u in fields if u.name.lower() == str(submitted_by).lower()), fields[0])

    # Serialize number assignment per company; the unique key is the backstop.
    session.exec(select(Company).where(Company.id == company).with_for_update()).first()
    highest = session.exec(
        select(ChangeEvent.number)
        .where(ChangeEvent.company_id == company)
        .order_by(col(ChangeEvent.number).desc())
    ).first()
    event = ChangeEvent(
        company_id=company,
        project_id=project.id,
        number=(highest + 1) if highest is not None else DEFAULT_FIRST_NUMBER,
        submitted_by_id=user.id,
        title=title or description[:80],
        description=description,
        severity=severity,
        status="submitted",
    )
    session.add(event)
    session.flush()
    for key in photo_keys:
        session.add(Photo(company_id=company, change_event_id=event.id, storage_key=key))
    _record(event, "submitted", "Change request submitted", user.name, user.id)
    recipients = _users_with_roles("estimator", "manager" if severity == "high" else "estimator")
    _notify_users(recipients, event.id, "change_submitted", "New change order submitted")
    session.flush()
    return _build([event])[0]


# ----------------------------------------------------------------- review


def _write_terms(event: ChangeEvent, scope, amount, impact_days, freeze: bool):
    """Save the proposal on the change's latest unsent revision, or start one."""
    context = _ctx()
    session, company = context.session, context.company_id
    cents = _cents(amount)
    if impact_days < 0:
        raise ValueError("impact_days must not be negative")
    order = session.exec(
        company_select(ChangeOrder, company).where(ChangeOrder.change_event_id == event.id)
    ).first()
    if order is None:
        order = ChangeOrder(company_id=company, change_event_id=event.id)
        session.add(order)
        session.flush()
    revisions = list(
        session.exec(
            company_select(ChangeOrderRevision, company)
            .where(ChangeOrderRevision.change_order_id == order.id)
            .order_by(ChangeOrderRevision.revision_number)
        )
    )
    revision = revisions[-1] if revisions else None
    if revision is not None and revision.frozen_at is not None:
        raise Conflict("Sent terms cannot be overwritten")
    if revision is None:
        revision = ChangeOrderRevision(
            company_id=company,
            change_order_id=order.id,
            revision_number=1,
            scope=scope or event.description,
        )
    revision.scope = scope or event.description
    revision.proposed_cost_cents = cents
    revision.requested_timeline_days = impact_days
    if freeze:
        revision.frozen_at = utc_now()
    session.add(revision)
    session.flush()
    return revision


def record_review(
    change_id, scope, amount, impact_days, actor_name="Estimator", actor_user_id=None
) -> dict:
    """Save the estimator's proposal without sending it. Returns {"status": ...}.

    The first save moves a submitted change to in_review. A fast-track change
    that is already authorized_to_proceed keeps that status.
    """
    context = _ctx()
    event = _lock_change(change_id)
    if event.status not in REVIEWABLE:
        raise Conflict("This change has already been reviewed")
    _write_terms(event, scope, amount, impact_days, freeze=False)
    if event.status == "submitted":
        event.status = "in_review"
        context.session.add(event)
        _record(event, "in_review", "Review started", actor_name, actor_user_id)
        _notify_users(
            [_submitter(event)], event.id, "change_in_review", "Your change is in review"
        )
    context.session.flush()
    return {"status": _legacy(event.status)}


def authorize_to_proceed(change_id, actor_name="Office Manager", actor_user_id=None) -> dict:
    """Fast track: a manager lets a high-priority change start before the estimate.

    Not an approval. The estimate and the GC's decision still follow, and
    only the GC's decision adds the change to the work order.
    """
    context = _ctx()
    event = _lock_change(change_id)
    if event.severity != "high":
        raise Conflict("Only a high-priority change can be authorized to proceed")
    if event.status not in ("submitted", "in_review"):
        raise Conflict("This change has already been reviewed")
    if actor_user_id is None:
        managers = _users_with_roles("manager")
        actor_user_id = managers[0].id if managers else None
    if actor_user_id is None:
        raise NotFound("The company has no manager to authorize the change")
    event.status = "authorized_to_proceed"
    event.authorized_by_id = actor_user_id
    event.authorized_at = utc_now()
    context.session.add(event)
    _record(event, "authorized_to_proceed", "Work authorized to proceed", actor_name, actor_user_id)
    _notify_users(
        [_submitter(event), *_users_with_roles("estimator")],
        event.id,
        "work_authorized",
        "Work authorized to proceed; the estimate and GC approval still follow",
    )
    context.session.flush()
    return {"status": event.status}


def _issue_link(request: ApprovalRequest) -> str:
    """Revoke the request's earlier link, store the new token's hash, return the token."""
    context = _ctx()
    session, company = context.session, context.company_id
    for link in session.exec(
        company_select(ApprovalLink, company)
        .where(ApprovalLink.approval_request_id == request.id)
        .where(col(ApprovalLink.revoked_at).is_(None))
    ):
        link.revoked_at = utc_now()
        session.add(link)
    session.flush()  # the one-live-link index needs the old link revoked first
    raw = secrets.token_urlsafe(32)
    days = int(os.environ.get("APPROVAL_LINK_DAYS", DEFAULT_LINK_DAYS))
    session.add(
        ApprovalLink(
            company_id=company,
            approval_request_id=request.id,
            token_hash=_hash(raw),
            expires_at=utc_now() + timedelta(days=days),
        )
    )
    session.flush()
    return raw


def send_to_gc(
    change_id,
    scope=None,
    amount=0,
    impact_days=0,
    actor_name="Office Manager",
    actor_user_id=None,
    gc_user_id=None,
) -> dict:
    """Freeze the proposal, ask the GC to decide, and return the link token.

    Returns {"status": "awaiting_client", "token": <raw token>}. The token is
    shown here once and stored nowhere (only its hash is); the route puts it in
    the email or the console fallback. No notification ever holds it.
    """
    context = _ctx()
    session, company = context.session, context.company_id
    event = _lock_change(change_id)
    if event.status not in REVIEWABLE:
        raise Conflict("This change has already been reviewed")
    revision = _write_terms(event, scope, amount, impact_days, freeze=True)
    gcs = _users_with_roles("gc")
    if gc_user_id is not None:
        gcs = [u for u in gcs if u.id == int(gc_user_id)]
    if not gcs:
        raise NotFound("The company has no GC user to send the change to")
    gc = gcs[0]
    gc_user_id = gc.id
    request = ApprovalRequest(company_id=company, revision_id=revision.id, gc_user_id=gc_user_id)
    session.add(request)
    session.flush()
    token = _issue_link(request)
    event.status = "awaiting_gc"
    session.add(event)
    _record(event, "awaiting_gc", "Sent to approver", actor_name, actor_user_id)
    _notify_users(
        [gc],
        event.id,
        "approval_requested",
        f"Approval requested for {_code(event.number)}",
    )
    session.flush()
    return {"status": _legacy(event.status), "token": token}


# ------------------------------------------------------------ GC approval


def _pending_request(change_id: int) -> ApprovalRequest:
    context = _ctx()
    row = context.session.exec(
        company_select(ApprovalRequest, context.company_id)
        .join(
            ChangeOrderRevision,
            (ChangeOrderRevision.company_id == ApprovalRequest.company_id)
            & (ChangeOrderRevision.id == ApprovalRequest.revision_id),
        )
        .join(
            ChangeOrder,
            (ChangeOrder.company_id == ChangeOrderRevision.company_id)
            & (ChangeOrder.id == ChangeOrderRevision.change_order_id),
        )
        .where(ChangeOrder.change_event_id == change_id)
        .where(ApprovalRequest.status == "pending")
        .order_by(col(ApprovalRequest.id).desc())
    ).first()
    if row is None:
        raise Conflict("This change has no pending approval request")
    return row


def issue_client_token(change_id) -> str:
    """A fresh link token for a change that is waiting for the GC.

    Revokes the earlier link. Returns the raw token once; stores only its hash.
    """
    event = _lock_change(change_id)
    if event.status != "awaiting_gc":
        raise Conflict("This change is not waiting for the GC")
    return _issue_link(_pending_request(event.id))


def _resolve(raw: str):
    """(link, request, event) for a link that is live: not revoked, not expired."""
    context = _ctx()
    session, company = context.session, context.company_id
    link = session.exec(
        company_select(ApprovalLink, company)
        .where(ApprovalLink.token_hash == _hash(raw))
        .where(col(ApprovalLink.revoked_at).is_(None))
    ).first()
    if link is None or _utc(link.expires_at) <= utc_now():
        return None
    request = session.exec(
        company_select(ApprovalRequest, company).where(ApprovalRequest.id == link.approval_request_id)
    ).first()
    revision = session.exec(
        company_select(ChangeOrderRevision, company).where(ChangeOrderRevision.id == request.revision_id)
    ).first()
    order = session.exec(
        company_select(ChangeOrder, company).where(ChangeOrder.id == revision.change_order_id)
    ).first()
    return link, request, _lock_change(order.change_event_id)


def change_for_token(raw: str) -> dict | None:
    """The change a live link points at, or None. Opening a link changes nothing."""
    found = _resolve(raw)
    return _build([found[2]])[0] if found else None


def decide(token: str, decision: str, actor_name: str | None = None) -> dict:
    """Record the GC's one decision. Returns {"status": "approved" | "rejected"}.

    Raises NotFound for a link that is not valid and Conflict when the request
    was already decided, so a retry gets the same 409 as the prototype and can
    never count a change twice (approval_decision.request_id is unique).
    """
    context = _ctx()
    session, company = context.session, context.company_id
    decision = _v2(decision)
    if decision not in ("approved", "declined"):
        raise ValueError("decision must be approved or declined")
    found = _resolve(token)
    if found is None:
        raise NotFound("Invalid link")
    _link, request, event = found
    if event.status != "awaiting_gc" or request.status != "pending":
        raise Conflict("Already decided")
    gc = session.exec(
        company_select(User, company).where(User.id == request.gc_user_id)
    ).one()
    session.add(
        ApprovalDecision(
            company_id=company,
            request_id=request.id,
            revision_id=request.revision_id,
            decided_by_id=gc.id,
            decision=decision,
        )
    )
    request.status = decision
    event.status = decision
    session.add_all([request, event])
    title = "Change approved; work order updated" if decision == "approved" else "Change declined"
    _record(event, decision, title, actor_name or gc.name, gc.id)
    kind = "change_approved" if decision == "approved" else "change_declined"
    _notify_users(
        [_submitter(event), *_users_with_roles("estimator", "manager")], event.id, kind, title
    )
    try:
        session.flush()
    except IntegrityError:
        raise Conflict("Already decided") from None
    return {"status": _legacy(decision)}


# -------------------------------------------------------------- suggestion


def save_suggestion(change_id, suggestion: dict, original_scope: str) -> dict:
    """Keep an AI suggestion (advisory) as a new row. Changes no terms or status."""
    context = _ctx()
    event = _lock_change(change_id)
    if event.status not in ("submitted", "in_review"):
        raise Conflict("This change has already been reviewed")
    context.session.add(
        AiSuggestion(
            company_id=context.company_id,
            change_event_id=event.id,
            original_scope=original_scope,
            suggested_scope=suggestion["scope"],
            suggested_cost_cents=_cents(suggestion["amount"]),
            suggested_timeline_days=suggestion["impact_days"],
            rationale=suggestion["rationale"],
            in_scope=suggestion["in_scope"],
        )
    )
    context.session.flush()
    return suggestion


# --------------------------------------------------------------- work order


def work_order(project_id) -> dict:
    """The project's approved additions, counted once each.

    Not stored: the changes whose approval decision is "approved", with the
    revision the GC approved (see the query in migrations/README.md).
    """
    context = _ctx()
    session, company = context.session, context.company_id
    project = session.exec(
        company_select(Project, company).where(Project.slug == project_id)
    ).first()
    rows = []
    if project is not None:
        rows = session.exec(
            select(ChangeEvent, ChangeOrderRevision)
            .join(
                ChangeOrder,
                (ChangeOrder.company_id == ChangeEvent.company_id)
                & (ChangeOrder.change_event_id == ChangeEvent.id),
            )
            .join(
                ChangeOrderRevision,
                (ChangeOrderRevision.company_id == ChangeOrder.company_id)
                & (ChangeOrderRevision.change_order_id == ChangeOrder.id),
            )
            .join(
                ApprovalDecision,
                (ApprovalDecision.company_id == ChangeOrderRevision.company_id)
                & (ApprovalDecision.revision_id == ChangeOrderRevision.id)
                & (ApprovalDecision.decision == "approved"),
            )
            .where(ChangeEvent.company_id == company)
            .where(ChangeEvent.project_id == project.id)
            .where(ChangeEvent.status == "approved")
            .order_by(ApprovalDecision.decided_at, ChangeEvent.id)
        ).all()
    photos: dict[int, list[str]] = {}
    if rows:
        ids = [event.id for event, _ in rows]
        for photo in session.exec(
            company_select(Photo, company)
            .where(col(Photo.change_event_id).in_(ids))
            .order_by(Photo.id)
        ):
            photos.setdefault(photo.change_event_id, []).append(photo.storage_key)
    cents = sum((revision.proposed_cost_cents or 0) for _, revision in rows)
    return dict(
        project_id=project_id,
        revision=len(rows),
        additional_amount=_dollars(cents),
        additional_days=sum((revision.requested_timeline_days or 0) for _, revision in rows),
        changes=[
            dict(
                change_id=str(event.id),
                title=event.title,
                scope=revision.scope,
                amount=_dollars(revision.proposed_cost_cents),
                impact_days=revision.requested_timeline_days or 0,
                photo_keys=photos.get(event.id, []),
            )
            for event, revision in rows
        ],
    )
