"""J7: the suggestion routes on the repository backend, with real sign-in and roles.

Uses the same in-memory database, test signing key and seeded staff as
test_auth_and_roles.py. Bedrock is a fake client, so no AWS is used.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from sqlmodel import Session, select

from db.models import AiSuggestion
# The module, not the class, so the auth tests are not collected twice here.
from tests import test_auth_and_roles as base

US_MODEL = "us.anthropic.claude-sonnet-5-5"


def bedrock(**reply):
    body = dict(
        in_scope=False,
        scope="Relocate the outlet two feet left.",
        cost_low=400,
        cost_best=525.25,
        cost_high=700,
        timeline_days=1,
        rationale="The proposal does not cover moving outlets.",
        confidence=0.65,
    )
    body.update(reply)
    model = MagicMock()
    model.converse.return_value = {
        "output": {"message": {"content": [{"text": json.dumps(body)}]}},
        "usage": {"inputTokens": 100, "outputTokens": 50},
    }
    return model


class SuggestionRouteTests(unittest.TestCase):
    setUpClass = classmethod(base.AuthAndRoleTests.setUpClass.__func__)
    token = base.AuthAndRoleTests.token
    auth_header = base.AuthAndRoleTests.auth_header
    submit = base.AuthAndRoleTests.submit
    review = base.AuthAndRoleTests.review

    def setUp(self):
        base.AuthAndRoleTests.setUp(self)
        self.change = self.submit("field").json()
        self.model = bedrock()
        self.bedrock = [
            patch.dict(os.environ, {"BEDROCK_MODEL_ID": US_MODEL, "AWS_REGION": "us-east-1"}),
            patch("boto3.client", side_effect=lambda *a, **k: self.model),
        ]
        for p in self.bedrock:
            p.start()

    def tearDown(self):
        for p in reversed(self.bedrock):
            p.stop()
        base.AuthAndRoleTests.tearDown(self)

    # helpers
    def ask(self, who="estimator", change_id=None):
        return self.client.post(
            f"/api/v1/changes/{change_id or self.change['id']}/suggestion",
            json={"original_scope": "Rough-in plumbing for two bathrooms only."},
            headers=self.auth_header(who),
        )

    def listed(self, who="estimator"):
        return self.client.get(
            f"/api/v1/changes/{self.change['id']}/suggestions", headers=self.auth_header(who)
        )

    def answer(self, suggestion_id, body, who="estimator"):
        return self.client.post(
            f"/api/v1/suggestions/{suggestion_id}/response", json=body, headers=self.auth_header(who)
        )

    def rows(self):
        with Session(self.engine) as s:
            return s.exec(select(AiSuggestion)).all()

    # request, read and rate
    def test_an_estimator_requests_reads_and_rates_a_suggestion(self):
        asked = self.ask()
        self.assertEqual(asked.status_code, 200, asked.text)
        stored = asked.json()
        self.assertEqual(
            (stored["cost_low_cents"], stored["cost_cents"], stored["cost_high_cents"]),
            (40000, 52525, 70000),
        )
        self.assertEqual((stored["model_id"], stored["confidence"]), (US_MODEL, 0.65))
        self.assertTrue(stored["prompt_version"])
        self.assertFalse(stored["in_scope"])

        listed = self.listed()
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([s["id"] for s in listed.json()], [stored["id"]])

        # responded_by_id in the body is ignored: it comes from the token.
        answered = self.answer(stored["id"], {"response": "accepted", "rating": 5, "responded_by_id": 1})
        self.assertEqual(answered.status_code, 200, answered.text)
        body = answered.json()
        self.assertEqual((body["response"], body["rating"]), ("accepted", 5))
        self.assertEqual(body["responded_by_id"], self.ids["Erin Estimator"])
        self.assertIsNotNone(body["responded_at"])
        # Answered once; a second answer is a 409.
        self.assertEqual(self.answer(stored["id"], {"response": "dismissed"}).status_code, 409)

    def test_a_suggestion_decides_nothing(self):
        stored = self.ask().json()
        self.answer(stored["id"], {"response": "accepted", "rating": 4})
        change = self.client.get("/api/v1/changes", headers=self.auth_header("estimator")).json()[0]
        self.assertEqual((change["status"], change["amount"]), ("submitted", 0))
        self.assertIsNone(change["proposed_cost_cents"])

    def test_no_photo_reaches_the_model(self):
        self.assertEqual(self.ask().status_code, 200)
        call = self.model.converse.call_args.kwargs
        content = call["messages"][0]["content"]
        self.assertTrue(all(set(part) == {"text"} for part in content))
        self.assertNotIn("image", repr(call))
        self.assertNotIn(self.change["photo_keys"][0], repr(call))
        # The field's report is what the model assesses.
        self.assertIn("Move the outlet left", content[0]["text"])

    # roles
    def test_only_the_estimator_asks_for_or_rates_a_suggestion(self):
        for who in ("field", "manager"):
            with self.subTest(who=who):
                self.assertEqual(self.ask(who).status_code, 403)
        self.model.converse.assert_not_called()
        stored = self.ask().json()
        for who in ("field", "manager"):
            with self.subTest(who=who):
                self.assertEqual(self.answer(stored["id"], {"response": "accepted"}, who).status_code, 403)
        self.assertIsNone(self.rows()[0].response)

    def test_the_estimator_and_manager_can_read_suggestions_but_not_the_field(self):
        self.ask()
        self.assertEqual(self.listed("estimator").status_code, 200)
        self.assertEqual(self.listed("manager").status_code, 200)
        self.assertEqual(self.listed("field").status_code, 403)
        self.assertEqual(
            self.client.get(f"/api/v1/changes/{self.change['id']}/suggestions").status_code, 401
        )

    # errors
    def test_no_model_is_503_and_nothing_is_stored(self):
        with patch.dict(os.environ, {"BEDROCK_MODEL_ID": ""}):
            response = self.ask()
        self.assertEqual(response.status_code, 503)
        self.assertIn("enter cost and days manually", response.json()["detail"])
        self.assertEqual(self.rows(), [])

    def test_an_unusable_reply_is_502_and_nothing_is_stored(self):
        self.model = bedrock(cost_low=900, cost_best=100, cost_high=50)
        self.assertEqual(self.ask().status_code, 502)
        self.assertEqual(self.rows(), [])

    def test_a_reviewed_change_cannot_get_a_suggestion(self):
        self.assertEqual(self.review(self.change["id"]).status_code, 200)
        self.assertEqual(self.ask().status_code, 409)
        self.model.converse.assert_not_called()

    def test_unknown_ids_are_404_and_bad_answers_are_422(self):
        self.assertEqual(self.ask(change_id="999").status_code, 404)
        stored = self.ask().json()
        self.assertEqual(self.answer(999999, {"response": "accepted"}).status_code, 404)
        for bad in (
            {"response": "approved"},
            {"response": "accepted", "rating": 0},
            {"response": "accepted", "rating": 6},
            {"response": "accepted", "rating": 2.5},
            {"response": "accepted", "rating": "4"},
            {},
        ):
            with self.subTest(bad=bad):
                self.assertEqual(self.answer(stored["id"], bad).status_code, 422)
        self.assertIsNone(self.rows()[0].response)


if __name__ == "__main__":
    unittest.main()
