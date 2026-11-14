"""The routes on the repository backend (WORKSPACE_BACKEND=postgres), in memory.

test_changes.py covers the default sqlite backend through HTTP. These run the
same workflow through HTTP with the routes switched to db/repository.py, using
in-memory SQLite with foreign keys on, so no Supabase and no DATABASE_URL.
"""

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from db import repository
from db.database import _enforce_sqlite_foreign_keys
from db.models import Company, Project, User

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1sAAAAASUVORK5CYII="
)


def make_engine():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(engine, "connect", _enforce_sqlite_foreign_keys)
    SQLModel.metadata.create_all(engine)
    return engine


class RoutesOnRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.upload_dir = Path(cls.temporary.name)
        from fastapi import FastAPI

        import api.routes.changes as routes

        # A bare app: importing main would mount /uploads from the real folder
        # and break test_changes.py, which depends on that mount's folder.
        app = FastAPI()
        app.include_router(routes.router)
        cls.routes = routes
        cls.app = app

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.engine = make_engine()
        repository.set_engine(self.engine)
        with Session(self.engine) as s:
            company = Company(name="Cohyric Demo")  # id 1: the default company
            s.add(company)
            s.flush()
            cid = company.id
            s.add_all(
                Project(company_id=cid, slug=slug, name=slug)
                for slug in ("north-park", "harbor", "cedar")
            )
            s.add_all(
                [
                    User(company_id=cid, role="field", name="Contractor"),
                    User(company_id=cid, role="estimator", name="Erin Estimator"),
                    User(company_id=cid, role="manager", name="Max Manager"),
                    User(company_id=cid, role="gc", name="Gina GC", email="gc@example.com"),
                ]
            )
            s.commit()
        # Route uploads and the GC token capture to this test.
        self.patches = [
            patch.object(self.routes, "workflow", repository),
            patch("core.config.UPLOAD_DIR", self.upload_dir),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.tokens: list[str] = []
        original_link = self.routes._approval_link

        def capture(token):
            self.tokens.append(token)
            return original_link(token)

        self.capture = patch.object(self.routes, "_approval_link", side_effect=capture)
        self.capture.start()

    def tearDown(self):
        self.capture.stop()
        self.client.__exit__(None, None, None)
        for p in reversed(self.patches):
            p.stop()
        repository.set_engine(None)
        self.engine.dispose()

    # helpers
    def submit(self, severity="normal"):
        return self.client.post(
            "/api/v1/changes",
            data={"description": "Move the outlet left", "severity": severity},
            files=[("photos", ("a.png", PNG, "image/png"))],
        )

    def review(self, change_id, cents=12345, days=2):
        return self.client.post(
            f"/api/v1/changes/{change_id}/review",
            json={
                "scope": "Relocate outlet 2 ft",
                "proposed_cost_cents": cents,
                "requested_timeline_days": days,
                "currency": "USD",
            },
        )

    def test_submit_review_and_gc_approval_on_the_database(self):
        created = self.submit()
        self.assertEqual(created.status_code, 201, created.text)
        change = created.json()
        self.assertEqual(change["status"], "submitted")
        self.assertEqual(len(change["photo_keys"]), 1)

        review = self.review(change["id"])
        self.assertEqual(review.status_code, 200, review.text)
        # Legacy names: the repository answers with the prototype vocabulary the
        # merged frontend reads until U3 (see db/repository.py _legacy).
        self.assertEqual(review.json()["status"], "awaiting_client")
        self.assertEqual(len(self.tokens), 1)
        token = self.tokens[0]

        self.assertEqual(
            self.client.get("/api/v1/approval-session", params={"token": token}).status_code,
            200,
        )
        # Opening the link decides nothing.
        self.assertEqual(
            self.client.get("/api/v1/changes").json()[0]["status"], "awaiting_client"
        )

        decision = self.client.post("/api/v1/approval-session/approve", params={"token": token})
        self.assertEqual(decision.json(), {"status": "approved"})
        again = self.client.post("/api/v1/approval-session/approve", params={"token": token})
        self.assertEqual(again.status_code, 409)

        work_order = self.client.get("/api/v1/projects/north-park/work-order").json()
        self.assertEqual(work_order["revision"], 1)
        self.assertEqual(work_order["additional_days"], 2)

    @unittest.expectedFailure
    def test_estimator_terms_appear_on_the_gc_link(self):
        # Known gap in db/repository.py _build (B3, Bona's area): the change dict
        # has no proposed_cost_cents, requested_timeline_days or currency, so the
        # GC link shows no terms. This passes once _build includes them; then
        # remove the expectedFailure decorator.
        change = self.submit().json()
        self.review(change["id"], cents=12345, days=2)
        token = self.tokens[0]
        body = self.client.get("/api/v1/approval-session", params={"token": token}).json()
        self.assertEqual(body["proposed_cost_cents"], 12345)
        self.assertEqual(body["requested_timeline_days"], 2)

    def test_fast_track_authorizes_then_the_gc_still_decides(self):
        change = self.submit(severity="high").json()
        authorized = self.client.post(f"/api/v1/changes/{change['id']}/authorize")
        self.assertEqual(authorized.status_code, 200, authorized.text)
        self.assertEqual(authorized.json()["status"], "authorized_to_proceed")
        # Authorizing issues no link and approves nothing.
        self.assertEqual(self.tokens, [])
        self.assertEqual(
            self.client.get("/api/v1/projects/north-park/work-order").json()["revision"], 0
        )

        self.review(change["id"])
        token = self.tokens[0]
        self.assertEqual(
            self.client.post("/api/v1/approval-session/decline", params={"token": token}).json(),
            {"status": "rejected"},
        )
        self.assertEqual(
            self.client.get("/api/v1/projects/north-park/work-order").json()["revision"], 0
        )

    def test_legacy_route_never_approves_high_priority_without_the_gc(self):
        change = self.submit(severity="high").json()
        response = self.client.post(
            f"/api/v1/changes/{change['id']}/admin-approve",
            json={"amount": 100.0, "impact_days": 1, "scope": "x"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.client.get("/api/v1/projects/north-park/work-order").json()["revision"], 0
        )

    def test_unknown_change_is_404_and_bad_terms_change_nothing(self):
        self.assertEqual(self.review("999").status_code, 404)
        change = self.submit().json()
        bad = self.review(change["id"], cents=-5)
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(self.client.get("/api/v1/changes").json()[0]["status"], "submitted")


if __name__ == "__main__":
    unittest.main()
