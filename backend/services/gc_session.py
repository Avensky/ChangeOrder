"""The GC's short-lived session, exchanged for the emailed link token (task J8).

The emailed link carries a long random token. The GC page sends it once to
POST /approval-session/exchange and gets back a session that expires after a
few minutes, so the page can drop the token from the address bar and the
browser history, and later requests never put it in a URL or an access log.

The session is the link token encrypted and timestamped with Fernet
(cryptography, already installed through PyJWT[crypto]). Nothing is stored:
every request decrypts it and looks the link up again, so a link that expires
or is revoked stops working at once, session or not.

Idempotency: approve and decline accept a key. A retry with the same key gets
the first answer back instead of a 409, and the decision is still recorded
once, because the database allows one decision per request. The keys are
remembered in this process only (see IdempotencyKeys).
"""

import base64
import hashlib
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

DEFAULT_SESSION_MINUTES = 30

# With no secret set, a random key per process: sessions then end when the
# server restarts, and the GC simply opens the emailed link again.
_process_key = Fernet.generate_key()


def _fernet() -> Fernet:
    secret = os.getenv("GC_SESSION_SECRET", "").strip()
    if not secret:
        return Fernet(_process_key)
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def session_minutes() -> int:
    try:
        minutes = int(os.getenv("GC_SESSION_MINUTES", DEFAULT_SESSION_MINUTES))
    except ValueError:
        return DEFAULT_SESSION_MINUTES
    return max(1, min(minutes, 24 * 60))


def _now() -> float:
    return time.time()


def issue(link_token: str) -> tuple[str, datetime]:
    """A session for a link token the caller has already checked is live."""
    now = int(_now())
    session = _fernet().encrypt_at_time(link_token.encode(), now).decode()
    expires_at = datetime.fromtimestamp(now, timezone.utc) + timedelta(minutes=session_minutes())
    return session, expires_at


def link_token(session: str) -> str | None:
    """The link token inside a session, or None when it is forged or too old."""
    try:
        return (
            _fernet()
            .decrypt_at_time(session.encode(), session_minutes() * 60, int(_now()))
            .decode()
        )
    except (InvalidToken, ValueError, TypeError):
        return None


def token_hash(link_token: str) -> str:
    return hashlib.sha256(link_token.encode()).hexdigest()


class IdempotencyKeys:
    """Remembers the answer given for (link, key) so a retry gets it again.

    In memory, bounded and expiring: enough for a page that retries after a
    dropped connection. After a restart the key is forgotten, and the route
    falls back to the recorded decision itself (see routes/changes.py), so a
    retry still never records a second decision.
    """

    def __init__(self, max_entries: int = 5000, ttl_seconds: int = 24 * 3600):
        self._entries: OrderedDict[tuple[str, str], tuple[float, str, dict]] = OrderedDict()
        self._lock = threading.Lock()
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds

    def get(self, link_hash: str, key: str) -> tuple[str, dict] | None:
        with self._lock:
            entry = self._entries.get((link_hash, key))
            if entry is None:
                return None
            stored_at, decision, response = entry
            if time.monotonic() - stored_at > self.ttl_seconds:
                del self._entries[(link_hash, key)]
                return None
            return decision, dict(response)

    def put(self, link_hash: str, key: str, decision: str, response: dict) -> None:
        with self._lock:
            self._entries[(link_hash, key)] = (time.monotonic(), decision, dict(response))
            self._entries.move_to_end((link_hash, key))
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


idempotency_keys = IdempotencyKeys()
