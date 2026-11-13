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
