"""J8: the GC link token is exchanged for a short-lived session.

Runs on the repository backend (WORKSPACE_BACKEND=postgres) in memory, as
test_routes_on_repository.py does, because that is where link expiry and
revocation are stored. test_changes.py covers the exchange on the prototype.
"""

import unittest
from datetime import timedelta
from unittest.mock import patch

from sqlmodel import Session, select

from db import repository
from db.models import ApprovalDecision, ApprovalLink, utc_now
from services import gc_session
# The module, not the class, so the routes tests are not collected twice here.
from tests import test_routes_on_repository as base


class GcSessionTests(unittest.TestCase):
    # The same in-memory app, data and token capture as the routes tests.
    setUpClass = classmethod(base.RoutesOnRepositoryTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RoutesOnRepositoryTests.tearDownClass.__func__)
    submit = base.RoutesOnRepositoryTests.submit
    review = base.RoutesOnRepositoryTests.review

    def setUp(self):
        base.RoutesOnRepositoryTests.setUp(self)
        gc_session.idempotency_keys.clear()
        change = self.submit().json()
        self.change_id = change["id"]
        self.assertEqual(self.review(self.change_id).status_code, 200)
        self.token = self.tokens[-1]

    def tearDown(self):
        base.RoutesOnRepositoryTests.tearDown(self)

    # helpers
    def exchange(self, token=None):
        return self.client.post(
            "/api/v1/approval-session/exchange", json={"token": token or self.token}
        )

    def session(self):
        response = self.exchange()
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": "Bearer " + response.json()["session"]}

    def decide(self, headers, decision="approve", key=None):
        body = {"idempotency_key": key} if key else None
        return self.client.post(
            f"/api/v1/approval-session/proposal/{decision}", headers=headers, json=body
        )

    def status(self):
        return self.client.get("/api/v1/changes").json()[0]["status"]

    def decisions(self):
        with Session(self.engine) as s:
            return len(s.exec(select(ApprovalDecision)).all())

    # the exchange
    def test_exchange_returns_a_session_and_the_proposal_and_decides_nothing(self):
        response = self.exchange()
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["change"]["id"], self.change_id)
        self.assertEqual(body["change"]["proposed_cost_cents"], 12345)
        self.assertNotIn(self.token, body["session"])
        self.assertIn("expires_at", body)
        # The page reads the proposal with the session alone, no token in the URL.
        headers = {"Authorization": "Bearer " + body["session"]}
        for _ in range(2):  # reloading decides nothing either
            seen = self.client.get("/api/v1/approval-session/proposal", headers=headers)
            self.assertEqual(seen.status_code, 200, seen.text)
            self.assertEqual(seen.json()["id"], self.change_id)
        self.assertEqual(self.status(), "awaiting_client")
        self.assertEqual(self.decisions(), 0)

    def test_a_wrong_token_is_404(self):
        self.assertEqual(self.exchange("not-a-real-token").status_code, 404)

    def test_a_missing_forged_or_old_session_is_401(self):
        headers = self.session()
        for bad in ({}, {"Authorization": "Bearer forged"}, {"Authorization": "Basic x"}):
            with self.subTest(bad=bad):
                response = self.client.get("/api/v1/approval-session/proposal", headers=bad)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(self.decide(bad).status_code, 401)
        # Past its lifetime, the session ends; the emailed link still works.
        later = gc_session._now() + (gc_session.session_minutes() + 1) * 60
        with patch.object(gc_session, "_now", return_value=later):
            self.assertEqual(
                self.client.get("/api/v1/approval-session/proposal", headers=headers).status_code,
                401,
            )
            self.assertEqual(self.decide(headers).status_code, 401)
        self.assertEqual(self.decisions(), 0)
        self.assertEqual(self.exchange().status_code, 200)

    # expiry and revocation
    def test_an_expired_link_is_refused_even_with_a_session(self):
        headers = self.session()
        with Session(self.engine) as s:
            link = s.exec(select(ApprovalLink)).one()
            link.expires_at = utc_now() - timedelta(minutes=1)
            s.add(link)
            s.commit()
        self.assertEqual(self.exchange().status_code, 404)
        self.assertEqual(
            self.client.get("/api/v1/approval-session/proposal", headers=headers).status_code, 404
        )
        self.assertEqual(self.decide(headers).status_code, 404)
        self.assertEqual(
            self.client.get("/api/v1/approval-session", params={"token": self.token}).status_code,
            404,
        )
        self.assertEqual(self.decisions(), 0)
        self.assertEqual(self.status(), "awaiting_client")

    def test_a_revoked_link_is_refused_and_the_new_one_works(self):
        headers = self.session()
        with repository.atomic(1):
            new_token = repository.issue_client_token(self.change_id)  # revokes the old link
        self.assertEqual(self.exchange().status_code, 404)
        self.assertEqual(
            self.client.get("/api/v1/approval-session/proposal", headers=headers).status_code, 404
        )
        self.assertEqual(self.decide(headers).status_code, 404)
        self.assertEqual(self.decisions(), 0)
        fresh = self.exchange(new_token)
        self.assertEqual(fresh.status_code, 200)
        approved = self.decide({"Authorization": "Bearer " + fresh.json()["session"]})
        self.assertEqual(approved.json(), {"status": "approved"})

    # one decision, retries and idempotency
    def test_a_retry_with_the_same_key_gets_the_same_answer_and_one_decision(self):
        headers = self.session()
        first = self.decide(headers, key="press-0001")
        again = self.decide(headers, key="press-0001")
        self.assertEqual((first.status_code, first.json()), (200, {"status": "approved"}))
        self.assertEqual((again.status_code, again.json()), (200, first.json()))
        self.assertEqual(self.decisions(), 1)
        work_order = self.client.get("/api/v1/projects/north-park/work-order").json()
        self.assertEqual(work_order["revision"], 1)

    def test_a_retry_after_the_key_is_forgotten_still_records_once(self):
        headers = self.session()
        self.assertEqual(self.decide(headers, "decline", key="press-0002").status_code, 200)
        gc_session.idempotency_keys.clear()  # as after a restart
        again = self.decide(headers, "decline", key="press-0002")
        self.assertEqual((again.status_code, again.json()), (200, {"status": "rejected"}))
        self.assertEqual(self.decisions(), 1)

    def test_the_other_decision_is_refused_after_one_is_recorded(self):
        headers = self.session()
        self.assertEqual(self.decide(headers, key="press-0003").status_code, 200)
        # The same key for the other button is a client error...
        self.assertEqual(self.decide(headers, "decline", key="press-0003").status_code, 422)
        # ...and a fresh key, or no key, cannot change what was decided.
        self.assertEqual(self.decide(headers, "decline", key="press-0004").status_code, 409)
        self.assertEqual(self.decide(headers, "decline").status_code, 409)
        self.assertEqual(self.decisions(), 1)
        self.assertEqual(self.status(), "approved")

    def test_without_a_key_a_repeat_is_still_a_409(self):
        headers = self.session()
        self.assertEqual(self.decide(headers).status_code, 200)
        self.assertEqual(self.decide(headers).status_code, 409)
        self.assertEqual(self.decisions(), 1)

    def test_the_legacy_query_token_routes_still_work_and_take_a_key(self):
        params = {"token": self.token}
        body = {"idempotency_key": "press-0005"}
        first = self.client.post("/api/v1/approval-session/approve", params=params, json=body)
        again = self.client.post("/api/v1/approval-session/approve", params=params, json=body)
        self.assertEqual((first.status_code, again.status_code), (200, 200))
        self.assertEqual(self.decisions(), 1)

    def test_a_short_key_is_rejected(self):
        headers = self.session()
        self.assertEqual(self.decide(headers, key="short").status_code, 422)
        self.assertEqual(self.decisions(), 0)


if __name__ == "__main__":
    unittest.main()
