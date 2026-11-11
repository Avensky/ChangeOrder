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

        store.CHANGES.clear()
        store.TOKENS.clear()
        store.NOTIFICATIONS.clear()
        for file in self.upload_dir.iterdir():
            file.unlink()

    def submit(self, description="Move the outlet left", severity="normal", photo=PNG, mime="image/png"):
        return self.client.post(
            "/api/v1/changes",
            data={"description": description, "severity": severity},
            files={"photo": ("same-name.png", photo, mime)},
        )

    def test_health_has_one_definition(self):
        schema = self.client.get("/openapi.json").json()
        self.assertIn("/health", schema["paths"])
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertNotIn("on_startup", [handler.__name__ for handler in self.app.router.on_startup])

    def test_submission_saves_image_and_notifies_office(self):
        response = self.submit("  Move the outlet left  ", "high")
        self.assertEqual(response.status_code, 201)
        change = response.json()
        self.assertEqual(change["description"], "Move the outlet left")
        self.assertEqual(change["severity"], "high")
        self.assertEqual(change["status"], "submitted")
        self.assertEqual(self.client.get("/uploads/" + change["photo_key"]).content, PNG)
        self.assertEqual(self.client.get("/api/v1/changes").json(), [change])
        notices = self.client.get("/api/v1/notifications", params={"to": "admin"}).json()
        self.assertEqual([notice["change_id"] for notice in notices], [change["id"]])

    def test_same_filename_does_not_overwrite_previous_photo(self):
        first = self.submit().json()
        second = self.submit().json()
        self.assertNotEqual(first["photo_key"], second["photo_key"])
        self.assertEqual(len(list(self.upload_dir.iterdir())), 2)

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
            with self.subTest(values={key: value for key, value in values.items() if key != "photo"}):
                self.assertEqual(self.submit(**values).status_code, status)
        missing_photo = self.client.post("/api/v1/changes", data={"description": "Move outlet"})
        self.assertEqual(missing_photo.status_code, 422)
        self.assertEqual(self.client.get("/api/v1/changes").json(), [])
        self.assertEqual(list(self.upload_dir.iterdir()), [])

    def test_normal_priority_retains_client_approval_flow(self):
        change = self.submit().json()
        review = "/api/v1/changes/" + change["id"] + "/admin-approve"
        self.assertEqual(self.client.post(review).json(), {"status": "awaiting_client"})
        notice = self.client.get("/api/v1/notifications", params={"to": "client"}).json()[0]
        token = notice["msg"].split("token=")[1]
        self.assertEqual(self.client.get("/api/v1/approval-session", params={"token": token}).status_code, 200)
        decision = self.client.post("/api/v1/approval-session/approve", params={"token": token})
        self.assertEqual(decision.json(), {"status": "approved"})
        self.assertEqual(self.client.post(review).status_code, 409)
        self.assertEqual(self.client.post("/api/v1/approval-session/decline", params={"token": token}).status_code, 409)

    def test_high_priority_retains_existing_admin_approval_rule(self):
        change = self.submit(severity="high").json()
        review = "/api/v1/changes/" + change["id"] + "/admin-approve"
        self.assertEqual(self.client.post(review).json(), {"status": "approved"})
        self.assertEqual(self.client.post(review).status_code, 409)

    def test_status_filter_is_validated(self):
        self.submit()
        self.assertEqual(self.client.get("/api/v1/changes?status=approved").json(), [])
        self.assertEqual(len(self.client.get("/api/v1/changes?status=submitted").json()), 1)
        self.assertEqual(self.client.get("/api/v1/changes?status=wrong").status_code, 422)

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
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:8081")


if __name__ == "__main__":
    unittest.main()
