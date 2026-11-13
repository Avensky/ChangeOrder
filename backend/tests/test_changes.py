"""Exercise real multipart requests, file storage, and the existing workflow."""

import base64
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1sAAAAASUVORK5CYII="
)


class ChangeSubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set the upload directory before importing the app; never touch real uploads.
        import core.config as config

        cls.temporary = tempfile.TemporaryDirectory()
        cls.upload_dir = Path(cls.temporary.name)
        config.UPLOAD_DIR = cls.upload_dir
        from services import store

        store.DB_PATH = cls.upload_dir / "test.sqlite3"
        from main import app

        cls.app = app
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.temporary.cleanup()

    def setUp(self):
        from services import store

        with store.atomic():
            store.CHANGES.clear()
            store.TOKENS.clear()
            store.NOTIFICATIONS.clear()
        for file in self.upload_dir.iterdir():
            if file.suffix != ".sqlite3":
                file.unlink()

    def submit(
        self,
        description="Move the outlet left",
        severity="normal",
        photo=PNG,
        mime="image/png",
    ):
        return self.submit_photos(description, severity, [(photo, mime)])

    def submit_photos(
        self,
        description="Move the outlet left",
        severity="normal",
        photos=((PNG, "image/png"),),
    ):
        return self.client.post(
            "/api/v1/changes",
            data={"description": description, "severity": severity},
            files=[
                ("photos", ("same-name.png", photo, mime)) for photo, mime in photos
            ],
        )

    def test_health_has_one_definition(self):
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/health", schema["paths"])
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertNotIn(
            "on_startup", [handler.__name__ for handler in self.app.router.on_startup]
        )

    def test_submission_saves_image_and_notifies_office(self):
        response = self.submit("  Move the outlet left  ", "high")
        self.assertEqual(response.status_code, 201)
        change = response.json()
        self.assertEqual(change["description"], "Move the outlet left")
        self.assertEqual(change["severity"], "high")
        self.assertEqual(change["status"], "submitted")
        self.assertEqual(len(change["photo_keys"]), 1)
        self.assertEqual(
            self.client.get("/uploads/" + change["photo_keys"][0]).content, PNG
        )
        self.assertEqual(self.client.get("/api/v1/changes").json(), [change])
        notices = self.client.get(
            "/api/v1/notifications", params={"to": "admin"}
        ).json()
        self.assertEqual([notice["change_id"] for notice in notices], [change["id"]])

    def test_same_filename_does_not_overwrite_previous_photo(self):
        first = self.submit().json()
        second = self.submit().json()
        self.assertNotEqual(first["photo_keys"], second["photo_keys"])
        self.assertEqual(len(list(self.upload_dir.glob("*.png"))), 2)

    def test_several_photos_are_all_saved_and_returned(self):
        response = self.submit_photos(photos=[(PNG, "image/png")] * 3)
        self.assertEqual(response.status_code, 201)
        keys = response.json()["photo_keys"]
        self.assertEqual(len(set(keys)), 3)
        for key in keys:
            self.assertEqual(self.client.get("/uploads/" + key).content, PNG)
        self.assertEqual(len(list(self.upload_dir.glob("*.png"))), 3)

    def test_one_invalid_photo_rejects_the_whole_submission(self):
        response = self.submit_photos(
            photos=[(PNG, "image/png"), (b"not an image", "image/png")]
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(self.client.get("/api/v1/changes").json(), [])
        self.assertEqual(list(self.upload_dir.glob("*.png")), [])

    def test_invalid_form_data_creates_nothing(self):
        cases = [
            ({"description": "   "}, 422),
            ({"description": "x" * 501}, 422),
            ({"severity": "urgent"}, 422),
            ({"photo": b"", "mime": "image/png"}, 400),
            ({"photo": b"not an image", "mime": "text/plain"}, 415),
            ({"photo": b"not an image", "mime": "image/png"}, 415),
            ({"photo": PNG + b"x" * (10 * 1024 * 1024)}, 413),
        ]
        for values, status in cases:
            with self.subTest(
                values={key: value for key, value in values.items() if key != "photo"}
            ):
                self.assertEqual(self.submit(**values).status_code, status)
        missing_photos = self.client.post(
            "/api/v1/changes", data={"description": "Move outlet"}
        )
        self.assertEqual(missing_photos.status_code, 422)
        self.assertEqual(self.client.get("/api/v1/changes").json(), [])
        self.assertEqual(list(self.upload_dir.glob("*.png")), [])

    def test_normal_priority_retains_client_approval_flow(self):
        change = self.submit().json()
        review = "/api/v1/changes/" + change["id"] + "/admin-approve"
        self.assertEqual(
            self.client.post(review, json={"amount": 123.45, "impact_days": 2}).json(),
            {"status": "awaiting_client"},
        )
        notice = self.client.get(
            "/api/v1/notifications", params={"to": "client"}
        ).json()[0]
        token = notice["msg"].split("token=")[1]
        self.assertEqual(
            self.client.get(
                "/api/v1/approval-session", params={"token": token}
            ).status_code,
            200,
        )
        decision = self.client.post(
            "/api/v1/approval-session/approve", params={"token": token}
        )
        self.assertEqual(decision.json(), {"status": "approved"})
        self.assertEqual(
            self.client.post(
                review, json={"amount": 123.45, "impact_days": 2}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/approval-session/decline", params={"token": token}
            ).status_code,
            409,
        )

    def test_high_priority_retains_existing_admin_approval_rule(self):
        change = self.submit(severity="high").json()
        review = "/api/v1/changes/" + change["id"] + "/admin-approve"
        self.assertEqual(
            self.client.post(review, json={"amount": 123.45, "impact_days": 2}).json(),
            {"status": "approved"},
        )
        self.assertEqual(
            self.client.post(
                review, json={"amount": 123.45, "impact_days": 2}
            ).status_code,
            409,
        )

    def test_status_filter_is_validated(self):
        self.submit()
        self.assertEqual(self.client.get("/api/v1/changes?status=approved").json(), [])
        self.assertEqual(
            len(self.client.get("/api/v1/changes?status=submitted").json()), 1
        )
        self.assertEqual(
            self.client.get("/api/v1/changes?status=wrong").status_code, 422
        )

    def test_web_upload_preflight_is_allowed(self):
        response = self.client.options(
            "/api/v1/changes",
            headers={
                "Origin": "http://localhost:8081",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"], "http://localhost:8081"
        )

    def test_approved_work_order_is_durable_and_never_double_counts(self):
        from services import store

        change = self.client.post(
            "/api/v1/changes",
            data={
                "title": "Relocate outlet",
                "description": "Move the outlet left",
                "project_id": "harbor",
                "submitted_by": "subcontractor",
            },
            files=[
                ("photos", ("a.png", PNG, "image/png")),
                ("photos", ("b.png", PNG, "image/png")),
            ],
        ).json()
        route = "/api/v1/changes/" + change["id"] + "/admin-approve"
        terms = {
            "amount": 123.45,
            "impact_days": 2,
            "scope": "Relocate and test outlet per revised plan",
        }
        self.assertEqual(self.client.post(route, json=terms).status_code, 200)
        self.assertEqual(
            self.client.get("/api/v1/projects/harbor/work-order").json()["revision"], 0
        )
        notices = self.client.get("/api/v1/notifications?to=client").json()
        token = notices[-1]["msg"].split("token=")[1]
        self.assertEqual(
            self.client.post(
                "/api/v1/approval-session/approve", params={"token": token}
            ).status_code,
            200,
        )
        # Discard in-process state: the next request must restore the committed data.
        store.CHANGES.clear()
        store.TOKENS.clear()
        store.NOTIFICATIONS.clear()
        order = self.client.get("/api/v1/projects/harbor/work-order").json()
        self.assertEqual(
            (order["revision"], order["additional_amount"], order["additional_days"]),
            (1, 123.45, 2),
        )
        self.assertEqual(order["changes"][0]["scope"], terms["scope"])
        self.assertEqual(order["changes"][0]["photo_keys"], change["photo_keys"])
        saved = self.client.get("/api/v1/changes").json()[0]
        self.assertEqual(saved["submitted_by"], "subcontractor")
        self.assertEqual(saved["title"], "Relocate outlet")
        self.assertEqual(saved["status"], "approved")
        self.assertEqual(len(saved["history"]), 3)
        self.assertEqual(
            self.client.post(
                "/api/v1/approval-session/approve", params={"token": token}
            ).status_code,
            409,
        )
        self.assertEqual(self.client.post(route, json=terms).status_code, 409)
        self.assertEqual(
            self.client.get("/api/v1/projects/harbor/work-order").json(), order
        )
        self.assertEqual(
            self.client.get("/api/v1/projects/cedar/work-order").json()["revision"], 0
        )

    def test_declined_changes_do_not_update_work_order(self):
        change = self.submit().json()
        self.client.post(
            "/api/v1/changes/" + change["id"] + "/admin-approve",
            json={"amount": 500, "impact_days": 1},
        )
        token = (
            self.client.get("/api/v1/notifications?to=client")
            .json()[-1]["msg"]
            .split("token=")[1]
        )
        self.client.post("/api/v1/approval-session/decline", params={"token": token})
        self.assertEqual(
            self.client.get("/api/v1/projects/north-park/work-order").json()[
                "revision"
            ],
            0,
        )

    def test_invalid_terms_cannot_partially_review_a_change(self):
        change = self.submit().json()
        route = "/api/v1/changes/" + change["id"] + "/admin-approve"
        for terms in [
            {"amount": -1, "impact_days": 0},
            {"amount": 1.001, "impact_days": 0},
            {"amount": 1, "impact_days": 0.5},
            {"amount": 1, "impact_days": -1},
        ]:
            self.assertEqual(self.client.post(route, json=terms).status_code, 422)
        self.assertEqual(
            self.client.get("/api/v1/changes").json()[0]["status"], "submitted"
        )
        self.assertEqual(self.client.get("/api/v1/notifications?to=client").json(), [])

    def test_failed_transaction_rolls_back_decision_and_notices(self):
        from services import store

        change = self.submit().json()
        with self.assertRaises(RuntimeError):
            with store.atomic():
                store.CHANGES[change["id"]]["status"] = "approved"
                store.notify("client", change["id"], "should roll back")
                raise RuntimeError("simulated write failure")
        self.assertEqual(
            self.client.get("/api/v1/changes").json()[0]["status"], "submitted"
        )
        self.assertEqual(self.client.get("/api/v1/notifications?to=client").json(), [])

    def test_ai_is_explicitly_unavailable_without_configuration(self):
        from unittest.mock import patch

        change = self.submit().json()
        with patch.dict("os.environ", {"BEDROCK_MODEL_ID": ""}):
            response = self.client.post(
                "/api/v1/changes/" + change["id"] + "/suggestion",
                json={"original_scope": "Replace kitchen cabinetry only"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(self.client.get("/api/v1/changes").json()[0]["suggestion"])

    def test_ai_advice_does_not_approve_or_set_terms(self):
        from unittest.mock import patch
        from schemas.changes import Suggestion

        change = self.submit().json()
        advice = Suggestion(
            scope="Move and test outlet",
            amount=200,
            impact_days=1,
            rationale="Assumes existing wiring is adequate",
            in_scope=False,
        )
        with patch("services.suggestions.suggest_terms", return_value=advice):
            response = self.client.post(
                "/api/v1/changes/" + change["id"] + "/suggestion",
                json={"original_scope": "Replace kitchen cabinetry only"},
            )
        self.assertEqual(response.status_code, 200)
        saved = self.client.get("/api/v1/changes").json()[0]
        self.assertEqual(saved["suggestion"]["amount"], 200)
        self.assertEqual(saved["amount"], 0)
        self.assertEqual(saved["status"], "submitted")
        self.assertEqual(
            self.client.get("/api/v1/projects/north-park/work-order").json()[
                "revision"
            ],
            0,
        )

    def test_bedrock_response_is_validated_and_receives_saved_photos(self):
        from unittest.mock import MagicMock, patch
        import json

        change = self.submit().json()
        model = MagicMock()
        advice = dict(
            scope="Relocate the outlet",
            amount=123.45,
            impact_days=2,
            rationale="Subject to site verification",
            in_scope=False,
        )
        model.converse.return_value = {
            "output": {"message": {"content": [{"text": json.dumps(advice)}]}}
        }
        route = "/api/v1/changes/" + change["id"] + "/suggestion"
        with patch.dict("os.environ", {"BEDROCK_MODEL_ID": "test-model"}), patch(
            "boto3.client", return_value=model
        ):
            self.assertEqual(
                self.client.post(
                    route, json={"original_scope": "Install kitchen cabinets only"}
                ).json(),
                advice,
            )
            call = model.converse.call_args.kwargs
            self.assertEqual(call["modelId"], "test-model")
            self.assertEqual(
                call["messages"][0]["content"][1]["image"]["source"]["bytes"], PNG
            )
            model.converse.return_value = {
                "output": {"message": {"content": [{"text": "not valid JSON"}]}}
            }
            self.assertEqual(
                self.client.post(
                    route, json={"original_scope": "Install kitchen cabinets only"}
                ).status_code,
                502,
            )
        self.assertEqual(
            self.client.get("/api/v1/changes").json()[0]["status"], "submitted"
        )

    def test_concurrent_approval_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor

        change = self.submit().json()
        self.client.post(
            "/api/v1/changes/" + change["id"] + "/admin-approve",
            json={"amount": 500, "impact_days": 1},
        )
        token = (
            self.client.get("/api/v1/notifications?to=client")
            .json()[-1]["msg"]
            .split("token=")[1]
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(
                pool.map(
                    lambda _: self.client.post(
                        "/api/v1/approval-session/approve", params={"token": token}
                    ).status_code,
                    range(2),
                )
            )
        self.assertEqual(sorted(statuses), [200, 409])
        order = self.client.get("/api/v1/projects/north-park/work-order").json()
        self.assertEqual((order["revision"], order["additional_amount"]), (1, 500))


if __name__ == "__main__":
    unittest.main()
