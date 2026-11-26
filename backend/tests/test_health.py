"""J11 prep: /health answers without the database, so a host's health check
never fails (or restarts the API) just because Supabase is paused or slow."""

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import health


class HealthTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(health.router)
        self.client = TestClient(app)

    def test_health_is_ok(self):
        response = self.client.get("/health")
        self.assertEqual((response.status_code, response.json()), (200, {"status": "ok"}))

    def test_health_does_not_touch_the_database(self):
        def no_database(*args, **kwargs):
            raise AssertionError("/health must not open a database connection")

        with patch("db.database.get_engine", side_effect=no_database), patch(
            "db.repository.atomic", side_effect=no_database
        ):
            self.assertEqual(self.client.get("/health").status_code, 200)

    def test_health_needs_no_sign_in(self):
        self.assertEqual(self.client.get("/health", headers={}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
