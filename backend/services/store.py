"""In-memory prototype storage. Records and notifications reset on restart."""

import hashlib
import secrets
import uuid

CHANGES: dict[str, dict] = {}
TOKENS: dict[str, str] = {}
NOTIFICATIONS: list[dict] = []


def notify(recipient: str, change_id: str, message: str):
    # CHANGED: Centralize the notification dictionary formerly repeated in
    # the route functions and create_change(). This queues an in-memory item;
    # it does not send an Expo push notification, email, or text message yet.
    NOTIFICATIONS.append(dict(to=recipient, change_id=change_id, msg=message))

def create_change(description, severity, photo_key):
    cid = str(uuid.uuid4())
    CHANGES[cid] = dict(id=cid, description=description, severity=severity,
                        status="submitted", photo_key=photo_key)
    # CHANGED: The office uses the existing "admin" inbox. Notify only after
    # the validated submission and its saved photo key have been recorded.
    notify("admin", cid, "New change order submitted")
    return CHANGES[cid]

def issue_client_token(change_id) -> str:
    raw = secrets.token_urlsafe(32)
    TOKENS[hashlib.sha256(raw.encode()).hexdigest()] = change_id
    return raw

def change_for_token(raw):
    cid = TOKENS.get(hashlib.sha256(raw.encode()).hexdigest())
    return CHANGES.get(cid) if cid else None
