"""Prototype logic for the estimator's review and the manager's fast track (J2).

This lives outside services/store.py, which stays as on main (the decision
record says no new behaviour goes into the prototype store). The repository
path does not use this module; see db/repository.py.
"""

import os

from services.store import add_event, issue_client_token, now, notify


def approval_link(change_id):
    """Issue a GC token and return the link that carries it.

    The link is returned to the caller only. It is not stored in a notification:
    the GC gets it in the email or the console line (see db/models.py,
    notification_holds_no_token).
    """
    token = issue_client_token(change_id)
    base = os.getenv("APP_URL", "http://localhost:8081").rstrip("/")
    return f"{base}/approve?token={token}"


def record_review(change, scope, proposed_cost_cents, requested_timeline_days, currency):
    """Save the estimator's terms and send the change to the GC.

    Money arrives as integer cents. `amount` is kept in step for the merged
    frontend, which still reads the float; drop it when U3 lands.
    """
    change.update(
        approved_scope=scope or change["description"],
        proposed_cost_cents=proposed_cost_cents,
        requested_timeline_days=requested_timeline_days,
        currency=currency,
        amount=proposed_cost_cents / 100,
        impact_days=requested_timeline_days,
        status="awaiting_gc",
        sent_for_approval=True,
    )
    add_event(change, "awaiting_gc", "Estimate saved and sent to the GC", "Estimator")
    return approval_link(change["id"])


def authorize_fast_track(change, person="Manager"):
    """Let work start on a high-priority change before the estimate exists.

    This authorizes work only. The GC still approves or declines the change,
    so the status never becomes `approved` here.
    """
    change.update(
        status="authorized_to_proceed",
        authorized_at=now(),
        authorized_by=person,
    )
    add_event(
        change,
        "authorized_to_proceed",
        "Work authorized to proceed before the estimate",
        person,
    )
    notify("field", change["id"], "Work authorized to proceed")
    notify("estimator", change["id"], "Fast-tracked change needs an estimate")
