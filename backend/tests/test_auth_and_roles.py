"""Staff sign-in and role checks (J5), on the repository backend in memory.

Tokens are real ES256 JWTs signed with a test key. The key set that normally
comes from the project's JWKS address is replaced by that test key, so no
network is used. The role comes from the seeded "user" row, never the token.
"""

import base64
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from db import repository
from db.database import _enforce_sqlite_foreign_keys
from db.models import Company, Project, User
from core.auth import Caller

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1sAAAAASUVORK5CYII="
)
ISSUER = "https://example.supabase.co/auth/v1"
UPLOAD_TMP = Path(tempfile.mkdtemp(prefix="changeorder-auth-"))


class FakeKeySet:
    """Stands in for PyJWKClient: returns the public half of the test key."""

    def __init__(self, private_key):
        self.public = private_key.public_key()

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self.public)


class AuthAndRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        import api.routes.changes as routes
        import core.auth as auth

        # A bare app: importing main would mount /uploads from the real folder
        # and break test_changes.py, which depends on that mount's folder.
        app = FastAPI()
        app.include_router(routes.router)
        cls.app, cls.routes, cls.auth = app, routes, auth
        cls.key = ec.generate_private_key(ec.SECP256R1())

    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "WORKSPACE_BACKEND": "postgres",
                "SUPABASE_URL": "https://example.supabase.co",
                "WORKSPACE_COMPANY_ID": "1",
            },
        )
        self.environment.start()
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
        event.listen(self.engine, "connect", _enforce_sqlite_foreign_keys)
        SQLModel.metadata.create_all(self.engine)
        repository.set_engine(self.engine)
        self.uuids = {
            "field": uuid.uuid4(),
            "estimator": uuid.uuid4(),
            "manager": uuid.uuid4(),
        }
        with Session(self.engine) as s:
            company = Company(name="Cohyric Demo")
            s.add(company)
            s.flush()
            s.add_all(
                Project(company_id=company.id, slug=slug, name=slug)
                for slug in ("north-park", "harbor", "cedar")
            )
            s.add_all(
                [
                    User(company_id=company.id, role="field", name="Demo Field", auth_user_id=self.uuids["field"]),
                    User(company_id=company.id, role="estimator", name="Erin Estimator", auth_user_id=self.uuids["estimator"]),
                    User(company_id=company.id, role="manager", name="Demo Manager", auth_user_id=self.uuids["manager"]),
                    User(company_id=company.id, role="gc", name="Gina GC", email="gc@example.com"),
                ]
            )
            s.commit()
            self.ids = {u.name: u.id for u in s.exec(select(User))}

        self.keys = FakeKeySet(self.key)
        self.saved_keys = self.auth._jwks_client
        self.auth._jwks_client = self.keys
        self.auth.configure_lookup(self.lookup)
        self.patches = [patch.object(self.routes, "workflow", repository)]
        self.patches.append(patch("core.config.UPLOAD_DIR", UPLOAD_TMP))
        self.link_tokens = []

        def capture(token):
            self.link_tokens.append(token)
            return f"http://x/approve?token={token}"

        self.patches.append(patch.object(self.routes, "_approval_link", side_effect=capture))
        for p in self.patches:
            p.start()
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for p in reversed(self.patches):
            p.stop()
        self.auth._jwks_client = self.saved_keys
        self.auth.configure_lookup(None)
        repository.set_engine(None)
        self.engine.dispose()
        self.environment.stop()

    # the database lookup this module asks Bona for, implemented for the test
    def lookup(self, sub):
        try:
            auth_id = uuid.UUID(sub)
        except ValueError:
            return None
        with Session(self.engine) as s:
            user = s.exec(select(User).where(User.auth_user_id == auth_id)).first()
            if user is None:
                return None
            return Caller(id=user.id, company_id=user.company_id, role=user.role, name=user.name)

    def token(self, who="estimator", *, sub=None, alg="ES256", key=None, exp=3600, aud="authenticated", iss=ISSUER, extra=None):
        now = int(time.time())
        payload = {
            "sub": sub or str(self.uuids[who]),
            "aud": aud,
            "iss": iss,
            "iat": now,
            "exp": now + exp,
            "role": "authenticated",
        }
        payload.update(extra or {})
        signing_key = key if key is not None else self.key
        return jwt.encode(payload, signing_key, algorithm=alg)

    def auth_header(self, who="estimator", **kwargs):
        return {"Authorization": f"Bearer {self.token(who, **kwargs)}"}

    def submit(self, who="field", severity="normal"):
        return self.client.post(
            "/api/v1/changes",
            data={"description": "Move the outlet left", "severity": severity},
            files=[("photos", ("a.png", PNG, "image/png"))],
            headers=self.auth_header(who),
        )

    def review(self, change_id, who="estimator"):
        return self.client.post(
            f"/api/v1/changes/{change_id}/review",
            json={"scope": "Relocate", "proposed_cost_cents": 1000, "requested_timeline_days": 1, "currency": "USD"},
            headers=self.auth_header(who),
        )

    # ------------------------------------------------------------ roles

    def test_each_role_can_do_its_own_step(self):
        change = self.submit("field").json()
        self.assertEqual(self.review(change["id"], "estimator").status_code, 200)

    def test_a_wrong_role_gets_403(self):
        change = self.submit("field").json()
        self.assertEqual(self.review(change["id"], "field").status_code, 403)
        self.assertEqual(self.review(change["id"], "manager").status_code, 403)
        self.assertEqual(self.submit("manager").status_code, 403)

    def test_only_a_manager_authorizes_fast_track(self):
        change = self.submit("field", severity="high").json()
        path = f"/api/v1/changes/{change['id']}/authorize"
        self.assertEqual(self.client.post(path, headers=self.auth_header("estimator")).status_code, 403)
        self.assertEqual(self.client.post(path, headers=self.auth_header("field")).status_code, 403)
        self.assertEqual(self.client.post(path, headers=self.auth_header("manager")).status_code, 200)

    def test_role_comes_from_the_database_not_the_token(self):
        change = self.submit("field", severity="high").json()
        # The estimator's token claims the manager role in user_metadata: ignored.
        claimed = {"user_metadata": {"role": "manager"}, "app_metadata": {"role": "manager"}}
        headers = {"Authorization": f"Bearer {self.token('estimator', extra=claimed)}"}
        path = f"/api/v1/changes/{change['id']}/authorize"
        self.assertEqual(self.client.post(path, headers=headers).status_code, 403)

    def test_the_company_comes_from_the_user_row(self):
        change = self.submit("field").json()
        self.assertEqual(self.review(change["id"], "estimator").status_code, 200)
        listed = self.client.get("/api/v1/changes", headers=self.auth_header("manager")).json()
        self.assertEqual([c["id"] for c in listed], [change["id"]])

    # ------------------------------------------------------- the token

    def test_no_token_or_a_bad_token_is_401(self):
        self.assertEqual(self.client.get("/api/v1/changes").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/changes", headers={"Authorization": "Bearer garbage"}).status_code, 401)

    def test_only_es256_is_accepted(self):
        hs256 = jwt.encode({"sub": str(self.uuids["estimator"]), "aud": "authenticated", "iss": ISSUER, "exp": int(time.time()) + 60}, b"x" * 32, algorithm="HS256")
        none_alg = jwt.encode({"sub": str(self.uuids["estimator"]), "aud": "authenticated", "iss": ISSUER, "exp": int(time.time()) + 60}, None, algorithm="none")
        for bad in (hs256, none_alg):
            response = self.client.get("/api/v1/changes", headers={"Authorization": f"Bearer {bad}"})
            self.assertEqual(response.status_code, 401, bad)

    def test_expired_wrong_issuer_or_wrong_audience_is_401(self):
        for kwargs in ({"exp": -60}, {"iss": "https://evil.example/auth/v1"}, {"aud": "anon"}):
            response = self.client.get("/api/v1/changes", headers=self.auth_header("estimator", **kwargs))
            self.assertEqual(response.status_code, 401, kwargs)

    def test_a_token_signed_by_another_key_is_401(self):
        other = ec.generate_private_key(ec.SECP256R1())
        response = self.client.get("/api/v1/changes", headers=self.auth_header("estimator", key=other))
        self.assertEqual(response.status_code, 401)

    def test_a_valid_token_with_no_user_row_is_403(self):
        stranger = self.auth_header("estimator", sub=str(uuid.uuid4()))
        self.assertEqual(self.client.get("/api/v1/changes", headers=stranger).status_code, 403)
        not_a_uuid = self.auth_header("estimator", sub="not-a-uuid")
        self.assertEqual(self.client.get("/api/v1/changes", headers=not_a_uuid).status_code, 403)

    # --------------------------------------------------------- /me and the GC

    def test_me_returns_id_name_and_role(self):
        response = self.client.get("/api/v1/me", headers=self.auth_header("estimator"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": self.ids["Erin Estimator"], "name": "Erin Estimator", "role": "estimator"},
        )
        self.assertEqual(self.client.get("/api/v1/me").status_code, 401)

    def test_gc_link_works_with_no_account(self):
        change = self.submit("field").json()
        self.assertEqual(self.review(change["id"]).status_code, 200)
        token = self.link_tokens[-1]
        # No Authorization header: the link is the GC's only credential, and
        # opening it decides nothing.
        opened = self.client.get("/api/v1/approval-session", params={"token": token})
        self.assertEqual(opened.status_code, 200)
        decided = self.client.post("/api/v1/approval-session/approve", params={"token": token})
        self.assertEqual(decided.json(), {"status": "approved"})

    def test_the_gc_cannot_sign_in(self):
        # The GC row has no account; no token can resolve to it.
        gc_token = self.auth_header("estimator", sub=str(uuid.uuid4()))
        self.assertEqual(self.client.get("/api/v1/changes", headers=gc_token).status_code, 403)


if __name__ == "__main__":
    unittest.main()
