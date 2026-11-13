"""Durable local workspace for the prototype, independent of the planned Supabase schema.

Every route transaction reloads state under SQLite's write lock. This keeps decisions,
notifications and work-order inputs atomic, including across API worker processes.
"""

import hashlib
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

CHANGES: dict[str, dict] = {}
TOKENS: dict[str, str] = {}
NOTIFICATIONS: list[dict] = []
DB_PATH = Path(
    os.getenv(
        "WORKSPACE_DB_PATH",
        str(Path(__file__).resolve().parents[1] / "workspace.sqlite3"),
    )
)
LOCK = RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def atomic():
    with LOCK, sqlite3.connect(DB_PATH, timeout=30) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS workspace_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)"
        )
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT payload FROM workspace_state WHERE id=1").fetchone()
        state = (
            json.loads(row[0])
            if row
            else {"changes": {}, "tokens": {}, "notifications": []}
        )
        original = json.dumps(state)

        def restore():
            state = json.loads(original)
            CHANGES.clear()
            CHANGES.update(state["changes"])
            TOKENS.clear()
            TOKENS.update(state["tokens"])
            NOTIFICATIONS[:] = state["notifications"]

        restore()
        try:
            yield
            payload = json.dumps(
                dict(changes=CHANGES, tokens=TOKENS, notifications=NOTIFICATIONS)
            )
            db.execute(
                "INSERT OR REPLACE INTO workspace_state VALUES (1, ?)", (payload,)
            )
            db.commit()
        except BaseException:
            db.rollback()
            restore()
            raise


def notify(recipient, change_id, message):
    NOTIFICATIONS.append(dict(to=recipient, change_id=change_id, msg=message))


def add_event(change, status, title, person):
    change["history"].append(
        dict(
            id=f'{change["id"]}-{status}',
            changeId=change["id"],
            title=title,
            person=person,
            time=now(),
            kind=status,
        )
    )


def create_change(
    description,
    severity,
    photo_keys,
    title="",
    project_id="north-park",
    submitted_by="contractor",
):
    cid = str(uuid.uuid4())
    c = dict(
        id=cid,
        code="CO-" + str(1049 + len(CHANGES)),
        title=title or description[:80],
        description=description,
        severity=severity,
        status="submitted",
        photo_keys=photo_keys,
        project_id=project_id,
        submitted_by=submitted_by,
        author=submitted_by.title(),
        created_at=now(),
        amount=0,
        impact_days=0,
        sent_for_approval=False,
        history=[],
        suggestion=None,
    )
    add_event(c, "submitted", "Change request submitted", c["author"])
    CHANGES[cid] = c
    notify("admin", cid, "New change order submitted")
    return c


def issue_client_token(change_id):
    raw = secrets.token_urlsafe(32)
    TOKENS[hashlib.sha256(raw.encode()).hexdigest()] = change_id
    return raw


def approval_link(change_id):
    """Issue a GC token and return the link that carries it.

    Only the hash of the token is stored, so this is the one chance to read it.
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
    link = approval_link(change["id"])
    notify("gc", change["id"], link)
    return link


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


def change_for_token(raw):
    cid = TOKENS.get(hashlib.sha256(raw.encode()).hexdigest())
    return CHANGES.get(cid) if cid else None


def work_order(project_id):
    from decimal import Decimal

    approved = [
        c
        for c in CHANGES.values()
        if c["project_id"] == project_id and c["status"] == "approved"
    ]
    return dict(
        project_id=project_id,
        revision=len(approved),
        additional_amount=float(
            sum((Decimal(str(c["amount"])) for c in approved), Decimal(0))
        ),
        additional_days=sum(c["impact_days"] for c in approved),
        changes=[
            dict(
                change_id=c["id"],
                title=c["title"],
                scope=c.get("approved_scope") or c["description"],
                amount=c["amount"],
                impact_days=c["impact_days"],
                photo_keys=c["photo_keys"],
            )
            for c in approved
        ],
    )
