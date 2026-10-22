import hashlib, secrets, uuid

CHANGES: dict[str, dict] = {}
TOKENS: dict[str, str] = {}
NOTIFICATIONS: list[dict] = []

def create_change(description, severity, photo_key):
    cid = str(uuid.uuid4())
    CHANGES[cid] = dict(id=cid, description=description, severity=severity,
                        status="submitted", photo_key=photo_key)
    NOTIFICATIONS.append(dict(to="admin", change_id=cid, msg="New change order submitted"))
    return CHANGES[cid]

def issue_client_token(change_id) -> str:
    raw = secrets.token_urlsafe(32)
    TOKENS[hashlib.sha256(raw.encode()).hexdigest()] = change_id
    return raw

def change_for_token(raw):
    cid = TOKENS.get(hashlib.sha256(raw.encode()).hexdigest())
    return CHANGES.get(cid) if cid else None
