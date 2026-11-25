"""The prototype's side of the workflow contract that the routes call.

The routes call the same functions on either backend (see db/store_selector.py).
With WORKSPACE_BACKEND=sqlite (the default) they come from this module, which
works on services/store.py's dicts. With postgres they come from
db/repository.py. The logic below is what the routes used to do inline against
store.CHANGES, moved here unchanged in behaviour so the routes can be shared.
store.py itself gets no new behaviour.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

from db.repository import Conflict, NotFound
from services import store

# The same re-exports the repository offers, so routes use one name for both.
atomic = store.atomic


def create_change(*args, submitted_by_user_id=None, **kwargs):
    """The prototype ignores the verified user id; the label stays its submitter."""
    return store.create_change(*args, **kwargs)

add_event = store.add_event
notify = store.notify
change_for_token = store.change_for_token
issue_client_token = store.issue_client_token
work_order = store.work_order

REVIEWABLE = ("submitted", "in_review", "authorized_to_proceed")


def approval_link_for(token: str) -> str:
    """The GC's link. Only the prototype keeps the link in a notification."""
    base = os.getenv("APP_URL", "http://localhost:8081").rstrip("/")
    return f"{base}/approve?token={token}"

# Legacy names the merged frontend still sends; the GC's words are the same.
_ALIASES = {"awaiting_client": "awaiting_gc", "rejected": "declined"}


def _normal(status) -> str:
    status = str(getattr(status, "value", status))
    return _ALIASES.get(status, status)


def list_changes(status=None) -> list[dict]:
    wanted = None if status is None else _normal(status)
    return [
        c
        for c in store.CHANGES.values()
        if wanted is None or _normal(c["status"]) == wanted
    ]


def get_change(change_id) -> dict | None:
    return store.CHANGES.get(str(change_id))


def _cents(amount) -> int:
    return int((Decimal(str(amount)) * 100).to_integral_value())


def send_to_gc(
    change_id,
    scope=None,
    amount=0,
    impact_days=0,
    actor_name="Estimator",
    actor_user_id=None,
    gc_user_id=None,
    *,
    currency: str = "USD",
    proposed_cost_cents: int | None = None,
) -> dict:
    """Save the estimator's terms and send the change to the GC.

    The cost is proposed_cost_cents (integer cents, preferred) or amount
    (dollars), the same as the repository's send_to_gc.

    Returns {"status": "awaiting_gc", "token": <raw token>}. The token is
    returned once; only its hash is kept. The caller builds the link from it.
    """
    c = store.CHANGES.get(str(change_id))
    if c is None:
        raise NotFound("Not found")
    if c["status"] not in REVIEWABLE:
        raise Conflict("This change is no longer open for review")
    cents = _cents(amount) if proposed_cost_cents is None else proposed_cost_cents
    token = issue_client_token(c["id"])
    c.update(
        approved_scope=scope or c["description"],
        proposed_cost_cents=cents,
        requested_timeline_days=impact_days,
        currency=currency,
        amount=float(Decimal(cents) / 100),
        impact_days=impact_days,
        status="awaiting_gc",
        sent_for_approval=True,
    )
    add_event(c, "awaiting_gc", "Estimate saved and sent to the GC", actor_name)
    # The GC's link goes in the console line and the email, never a notification.
    return {"status": "awaiting_gc", "token": token}


def authorize_to_proceed(change_id, actor_name="Manager", actor_user_id=None) -> dict:
    """Fast track: work starts before the estimate. Not an approval."""
    c = store.CHANGES.get(str(change_id))
    if c is None:
        raise NotFound("Not found")
    if c["severity"] != "high":
        raise Conflict("Only a high-priority change can be fast tracked")
    if c["status"] not in ("submitted", "in_review"):
        raise Conflict("This change is past the point of authorizing work")
    c.update(status="authorized_to_proceed", authorized_at=store.now(), authorized_by=actor_name)
    add_event(c, "authorized_to_proceed", "Work authorized to proceed before the estimate", actor_name)
    notify("field", c["id"], "Work authorized to proceed")
    notify("estimator", c["id"], "Fast-tracked change needs an estimate")
    return c


def decide(token: str, decision: str, actor_name: str | None = None) -> dict:
    """The GC's one decision on a live link. Returns {"status": ...}."""
    c = store.change_for_token(token)
    if c is None:
        raise NotFound("Invalid link")
    if c["status"] not in ("awaiting_gc", "awaiting_client"):
        raise Conflict("Already decided")
    # Answer a legacy request in legacy words so the merged frontend, which
    # tests for "rejected", keeps working until U3 lands.
    legacy = c["status"] == "awaiting_client"
    if decision == "approved":
        new_status = "approved"
    else:
        new_status = "rejected" if legacy else "declined"
    c["status"] = new_status
    title = "Change approved; work order updated" if decision == "approved" else "Change declined"
    add_event(c, new_status, title, actor_name or "GC")
    notify("contractor" if legacy else "office", c["id"], title)
    return {"status": new_status}


def save_suggestion(change_id, suggestion: dict, original_scope: str) -> dict:
    """Keep an AI suggestion (advisory). Changes no terms or status."""
    c = store.CHANGES.get(str(change_id))
    if c is None:
        raise NotFound("Not found")
    if c["status"] not in ("submitted", "in_review"):
        raise Conflict("This change has already been reviewed")
    c["suggestion"] = suggestion
    c["original_scope"] = original_scope
    return suggestion


# J7: the repository's create_suggestion, list_suggestions and
# respond_to_suggestion (B9 contract), on the prototype's change dicts so the
# routes are the same on both backends. Kept on the change itself, like
# c["suggestion"] above; store.py gains nothing.
SUGGESTION_RESPONSES = ("accepted", "edited", "dismissed")
_LEGACY_KEYS = ("scope", "amount", "impact_days", "rationale", "in_scope")


def create_suggestion(change_id, suggestion: dict, original_scope: str) -> dict:
    save_suggestion(change_id, {k: suggestion[k] for k in _LEGACY_KEYS}, original_scope)
    c = store.CHANGES[str(change_id)]
    low, high = suggestion.get("amount_low"), suggestion.get("amount_high")
    if (low is None) != (high is None):
        raise ValueError("Give both ends of the cost range, or neither.")
    existing = [s["id"] for ch in store.CHANGES.values() for s in ch.get("ai_suggestions", [])]
    row = dict(
        id=max(existing, default=0) + 1,
        change_id=str(change_id),
        in_scope=suggestion["in_scope"],
        scope=suggestion["scope"],
        original_scope=original_scope,
        rationale=suggestion["rationale"],
        currency="USD",
        cost_cents=_cents(suggestion["amount"]),
        cost_low_cents=None if low is None else _cents(low),
        cost_high_cents=None if high is None else _cents(high),
        amount=suggestion["amount"],
        impact_days=suggestion["impact_days"],
        confidence=suggestion.get("confidence"),
        model_id=suggestion.get("model_id"),
        prompt_version=suggestion.get("prompt_version"),
        created_at=datetime.now(timezone.utc).isoformat(),
        response=None,
        rating=None,
        responded_by_id=None,
        responded_at=None,
    )
    c.setdefault("ai_suggestions", []).append(row)
    return dict(row)


def list_suggestions(change_id) -> list[dict]:
    c = get_change(change_id)
    if c is None:
        raise NotFound("Not found")
    return [dict(s) for s in reversed(c.get("ai_suggestions", []))]


def respond_to_suggestion(suggestion_id, response: str, actor_user_id, rating=None) -> dict:
    if response not in SUGGESTION_RESPONSES:
        raise ValueError("The response must be accepted, edited or dismissed.")
    if rating is not None and (
        isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5
    ):
        raise ValueError("The rating must be a whole number from 1 to 5.")
    for c in store.CHANGES.values():
        for row in c.get("ai_suggestions", []):
            if str(row["id"]) == str(suggestion_id):
                if row["response"] is not None:
                    raise Conflict("This suggestion has already been answered")
                row.update(
                    response=response,
                    rating=rating,
                    responded_by_id=actor_user_id,
                    responded_at=datetime.now(timezone.utc).isoformat(),
                )
                return dict(row)
    raise NotFound("Not found")


def list_notifications(to: str) -> list[dict]:
    return [n for n in store.NOTIFICATIONS if n["to"] == to]


def legacy_admin_approve(change_id, amount, impact_days, scope) -> dict:
    """LEGACY /admin-approve, prototype only. Remove with the route (see changes.py).

    A high-priority change is approved here without the GC; that is the old
    prototype rule and is kept only until the app moves to /authorize and /review.
    """
    c = store.CHANGES.get(str(change_id))
    if c is None:
        raise NotFound("Not found")
    if c["status"] != "submitted":
        raise Conflict("This change has already been reviewed")
    c.update(amount=amount, impact_days=impact_days, approved_scope=scope or c["description"])
    if c["severity"] == "high":
        c["status"] = "approved"
        add_event(c, "approved", "Urgent change approved; work order updated", "Office Manager")
        notify("contractor", c["id"], "Approved; project work order updated")
        return {"status": c["status"]}
    token = issue_client_token(c["id"])
    c.update(status="awaiting_client", sent_for_approval=True)
    notify("client", c["id"], approval_link_for(token))
    add_event(c, "awaiting_client", "Sent to approver", "Office Manager")
    return {"status": c["status"]}
