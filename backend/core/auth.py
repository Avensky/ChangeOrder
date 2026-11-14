"""Staff sign-in for the API (J5).

The app sends the Supabase access token as `Authorization: Bearer <jwt>`. The
server verifies it against the project's public keys (ES256 only, so `none`
and HS256 are refused), reads the user id from `sub`, and loads that user's
role and company from the database. The role or company the app sends is never
trusted. The GC never signs in; the GC link is token-only and does not use this.

On the default sqlite backend (the prototype fallback) no check runs, because
the prototype has no users table and its tests send no token. The checks apply
whenever WORKSPACE_BACKEND=postgres. See the J5 pull request for that decision.
"""

import os
from dataclasses import dataclass
from typing import Callable

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from db.store_selector import backend_name

ALGORITHMS = ["ES256"]
DEFAULT_AUDIENCE = "authenticated"


@dataclass(frozen=True)
class Caller:
    id: int
    company_id: int
    role: str
    name: str


# Set by the app at start-up (or by a test): sub (a UUID string) -> Caller or None.
_lookup: Callable[[str], Caller | None] | None = None
_jwks_client: PyJWKClient | None = None


def configure_lookup(lookup: Callable[[str], Caller | None] | None) -> None:
    global _lookup
    _lookup = lookup


def checks_enabled() -> bool:
    return backend_name() == "postgres"


def _project_url() -> str:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not url:
        raise HTTPException(503, "Sign-in is not configured on the server")
    return url


def _issuer() -> str:
    return f"{_project_url()}/auth/v1"


def _signing_key(token: str):
    global _jwks_client
    if _jwks_client is None:
        url = os.getenv("SUPABASE_JWKS_URL", "").strip() or f"{_issuer()}/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url, cache_keys=True)
    try:
        return _jwks_client.get_signing_key_from_jwt(token).key
    except PyJWKClientConnectionError:
        raise HTTPException(503, "Sign-in keys are unavailable; try again") from None
    except PyJWTError:
        raise HTTPException(401, "Sign in again") from None


def verify_access_token(token: str) -> str:
    """Return the verified user id (`sub`) or raise 401."""
    key = _signing_key(token)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=ALGORITHMS,
            audience=os.getenv("SUPABASE_JWT_AUDIENCE", "").strip() or DEFAULT_AUDIENCE,
            issuer=_issuer(),
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except PyJWTError:
        raise HTTPException(401, "Sign in again") from None
    return str(claims["sub"])


def current_caller(authorization: str | None = Header(default=None)) -> Caller:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in first")
    sub = verify_access_token(authorization[7:].strip())
    if _lookup is None:
        raise HTTPException(503, "Staff lookup is not available on this server yet")
    caller = _lookup(sub)
    if caller is None:
        raise HTTPException(403, "This account is not a ChangeOrder staff user")
    return caller


def require_roles(*roles: str):
    """A dependency: the signed-in caller must have one of these roles.

    Returns None (no check) on the sqlite prototype; see the module docstring.
    """

    def dependency(caller: Caller | None = Depends(_caller_if_enabled)) -> Caller | None:
        if caller is None:
            return None
        if caller.role not in roles:
            raise HTTPException(403, "Your role cannot do this")
        return caller

    return dependency


def _caller_if_enabled(authorization: str | None = Header(default=None)) -> Caller | None:
    if not checks_enabled():
        return None
    return current_caller(authorization)
