"""J10: lists, notifications and the GC email depend on who is signed in.

Real signed tokens on the repository backend in memory, as in
test_auth_and_roles.py. Two repository additions this needs from Bona are
simulated by a thin wrapper (see WithJ10Fields) until they land in
db/repository.py: submitted_by_user_id on each change dict, and gc_email in
what send_to_gc and authorize_to_proceed return.
"""

import os
import unittest
import uuid
from unittest.mock import patch

from sqlmodel import Session, select

from db import repository
from db.models import ChangeEvent, User
# The module, not the class, so the auth tests are not collected twice here.
from tests import test_auth_and_roles as base


class WithJ10Fields:
    """The repository, plus the two fields J10 asks Bona to add."""

    # Reads go through the open transaction's session: a second session on the
    # one in-memory connection would roll that transaction back when it closes.
    def __getattr__(self, name):
        return getattr(repository, name)

    def _session(self):
        return repository._ctx().session

    def _gc_email(self):
        gc = self._session().exec(select(User).where(User.role == "gc")).first()
        return gc.email if gc else None

    def list_changes(self, status=None):
        changes = repository.list_changes(status)
        owner = {str(e.id): e.submitted_by_id for e in self._session().exec(select(ChangeEvent))}
        return [dict(c, submitted_by_user_id=owner[c["id"]]) for c in changes]

    def send_to_gc(self, *args, **kwargs):
        return dict(repository.send_to_gc(*args, **kwargs), gc_email=self._gc_email())

    def authorize_to_proceed(self, *args, **kwargs):
        return dict(repository.authorize_to_proceed(*args, **kwargs), gc_email=self._gc_email())


class RoleScopingTests(unittest.TestCase):
    setUpClass = classmethod(base.AuthAndRoleTests.setUpClass.__func__)
    token = base.AuthAndRoleTests.token
    auth_header = base.AuthAndRoleTests.auth_header
    submit = base.AuthAndRoleTests.submit
    review = base.AuthAndRoleTests.review

    def setUp(self):
        base.AuthAndRoleTests.setUp(self)
        # A second field worker in the same company.
        self.uuids["field2"] = uuid.uuid4()
        with Session(self.engine) as s:
            s.add(User(company_id=1, role="field", name="Second Field", auth_user_id=self.uuids["field2"]))
            s.commit()
        self.workflow = patch.object(self.routes, "workflow", WithJ10Fields())
        self.workflow.start()
        self.sent = []
        self.mail = patch.object(
            self.routes.email, "send", side_effect=lambda to, subject, body: self.sent.append(to) or False
        )
        self.mail.start()

    def tearDown(self):
        self.mail.stop()
        self.workflow.stop()
        base.AuthAndRoleTests.tearDown(self)

    def listed(self, who):
        response = self.client.get("/api/v1/changes", headers=self.auth_header(who))
        self.assertEqual(response.status_code, 200, response.text)
        return sorted(c["id"] for c in response.json())

    def notices(self, who, **params):
        response = self.client.get("/api/v1/notifications", params=params, headers=self.auth_header(who))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # the change list
    def test_a_field_user_sees_only_their_own_changes(self):
        mine = self.submit("field").json()["id"]
        theirs = self.submit("field2").json()["id"]
        self.assertEqual(self.listed("field"), [mine])
        self.assertEqual(self.listed("field2"), [theirs])
        # The office sees every change in the company.
        self.assertEqual(self.listed("estimator"), sorted([mine, theirs]))
        self.assertEqual(self.listed("manager"), sorted([mine, theirs]))

    def test_the_list_fails_closed_without_the_submitter_id(self):
        self.submit("field")
        with patch.object(self.routes, "workflow", repository):
            self.assertEqual(self.listed("field"), [])
            self.assertEqual(len(self.listed("estimator")), 1)

    # notifications
    def test_notifications_are_the_signed_in_persons_own(self):
        change = self.submit("field").json()
        self.assertEqual(self.review(change["id"]).status_code, 200)
        self.assertEqual(self.client.post(
            "/api/v1/approval-session/approve", params={"token": self.link_tokens[-1]}
        ).status_code, 200)
        for who in ("field", "estimator", "manager"):
            with self.subTest(who=who):
                own = self.notices(who)
                self.assertTrue(own, f"{who} should have notifications")
                self.assertTrue(all(n["to"] == base_label(who) for n in own))
                # `to` is ignored when signed in: asking for someone else's gives your own.
                self.assertEqual(self.notices(who, to="client"), own)
        # The second field worker submitted nothing and hears nothing about it.
        self.assertEqual(self.notices("field2"), [])

    def test_notifications_need_a_sign_in(self):
        self.assertEqual(self.client.get("/api/v1/notifications?to=admin").status_code, 401)

    # the GC email
    def test_the_gc_link_goes_to_the_companys_gc(self):
        change = self.submit("field").json()
        with patch.dict(os.environ, {"GC_EMAIL": "fallback@example.com"}):
            self.assertEqual(self.review(change["id"]).status_code, 200)
        self.assertEqual(self.sent, ["gc@example.com"])

    def test_the_fast_track_notice_goes_to_the_companys_gc(self):
        change = self.submit("field", severity="high").json()
        with patch.dict(os.environ, {"GC_EMAIL": "fallback@example.com"}):
            response = self.client.post(
                f"/api/v1/changes/{change['id']}/authorize", headers=self.auth_header("manager")
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.sent, ["gc@example.com"])

    def test_gc_email_is_only_the_fallback(self):
        change = self.submit("field").json()
        with patch.object(self.routes, "workflow", repository), patch.dict(
            os.environ, {"GC_EMAIL": "fallback@example.com"}
        ):
            self.assertEqual(self.review(change["id"]).status_code, 200)
        self.assertEqual(self.sent, ["fallback@example.com"])

    # the legacy route
    def test_admin_approve_is_gone(self):
        change = self.submit("field", severity="high").json()
        response = self.client.post(
            f"/api/v1/changes/{change['id']}/admin-approve",
            json={"amount": 1.0, "impact_days": 0},
            headers=self.auth_header("estimator"),
        )
        self.assertIn(response.status_code, (404, 405))


def base_label(who: str) -> str:
    """The repository's prototype label for each role in a notification's `to`."""
    return {"field": "contractor", "estimator": "admin", "manager": "admin"}[who]


if __name__ == "__main__":
    unittest.main()
