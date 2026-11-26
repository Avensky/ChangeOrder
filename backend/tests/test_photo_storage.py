"""J9: photos in the private bucket, served with short-lived signed links.

Real signed tokens on the repository backend in memory (as in
test_auth_and_roles.py), and a fake Supabase Storage behind httpx's
MockTransport, so no real project or secret key is used.
"""

import asyncio
import importlib.util
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from db.models import ChangeEvent, Photo
from services import photos
# The module, not the class, so the auth tests are not collected twice here.
from tests import test_auth_and_roles as base

SECRET = "sb_secret_test_only_not_real"
BUCKET = "change-photos"


class FakeStorage:
    """A private bucket: objects need the secret key, links need a signature."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.down = False
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        if self.down:
            raise httpx.ConnectError("storage unreachable")
        path = request.url.path.removeprefix("/storage/v1/")
        authorized = (
            request.headers.get("apikey") == SECRET
            and request.headers.get("authorization") == "Bearer " + SECRET
        )
        if path.startswith(f"object/sign/{BUCKET}") and request.method == "POST":
            if not authorized:
                return httpx.Response(403)
            body = json.loads(request.content)
            return httpx.Response(200, json=[
                {"path": p, "signedURL": f"/object/sign/{BUCKET}/{p}?token=signed-{body['expiresIn']}", "error": None}
                if p in self.objects
                else {"path": p, "signedURL": None, "error": "Object not found"}
                for p in body["paths"]
            ])
        if path.startswith(f"object/{BUCKET}/"):
            key = path.removeprefix(f"object/{BUCKET}/")
            if not authorized:
                # A private bucket: no plain or public URL serves an object.
                return httpx.Response(400, json={"error": "not allowed"})
            if request.method == "POST":
                if key in self.objects:
                    return httpx.Response(409)
                self.objects[key] = (request.content, request.headers.get("content-type"))
                return httpx.Response(200, json={"Key": f"{BUCKET}/{key}"})
            if request.method == "DELETE":
                self.objects.pop(key, None)
                return httpx.Response(200, json={})
            if request.method == "GET":
                return httpx.Response(200, content=self.objects[key][0])
        return httpx.Response(400)


class PhotoStorageTests(unittest.TestCase):
    setUpClass = classmethod(base.AuthAndRoleTests.setUpClass.__func__)
    token = base.AuthAndRoleTests.token
    auth_header = base.AuthAndRoleTests.auth_header
    submit = base.AuthAndRoleTests.submit
    review = base.AuthAndRoleTests.review

    def setUp(self):
        base.AuthAndRoleTests.setUp(self)
        self.storage = FakeStorage()
        self.bucket = [
            patch.dict(os.environ, {"SUPABASE_SECRET_KEY": SECRET, "PHOTO_URL_TTL_SECONDS": "300"}),
            patch.object(
                photos, "_client",
                side_effect=lambda: httpx.Client(transport=httpx.MockTransport(self.storage.handler)),
            ),
        ]
        for p in self.bucket:
            p.start()

    def tearDown(self):
        for p in reversed(self.bucket):
            p.stop()
        base.AuthAndRoleTests.tearDown(self)

    def changes(self):
        with Session(self.engine) as s:
            return s.exec(select(ChangeEvent)).all(), s.exec(select(Photo)).all()

    # upload
    def test_a_field_upload_goes_to_the_bucket_under_its_company(self):
        response = self.submit("field")
        self.assertEqual(response.status_code, 201, response.text)
        change = response.json()
        [key] = change["photo_keys"]
        self.assertTrue(key.startswith("1/") and key.endswith(".png"), key)
        data, content_type = self.storage.objects[key]
        self.assertEqual(content_type, "image/png")
        self.assertEqual(data, base.PNG)
        # Only the key is stored, never a URL.
        self.assertEqual([p.storage_key for p in self.changes()[1]], [key])
        # The response carries a signed link that expires in about 5 minutes.
        [link] = change["photos"]
        self.assertEqual(link["key"], key)
        self.assertIn("/storage/v1/object/sign/change-photos/" + key, link["url"])
        self.assertIn("token=signed-300", link["url"])
        expires = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
        self.assertLess(abs(expires - datetime.now(timezone.utc) - timedelta(seconds=300)), timedelta(seconds=30))
        # Nothing is local: no file in the uploads folder.
        self.assertEqual(list(Path(base.UPLOAD_TMP).glob("*.png")), [])

    def test_storage_down_is_502_and_nothing_is_written(self):
        self.storage.down = True
        response = self.submit("field")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn(SECRET, response.text)
        self.assertEqual(self.changes(), ([], []))

    def test_a_failed_database_write_removes_the_uploads(self):
        with patch("db.repository.create_change", side_effect=RuntimeError("database down")):
            with self.assertRaises(RuntimeError):
                self.submit("field")
        self.assertEqual(self.storage.objects, {})
        self.assertIn("DELETE", [method for method, _ in self.storage.calls])

    # access by role
    def test_the_estimator_and_manager_see_the_field_users_photo(self):
        change = self.submit("field").json()
        for who in ("estimator", "manager", "field"):
            with self.subTest(who=who):
                listed = self.client.get("/api/v1/changes", headers=self.auth_header(who)).json()
                [link] = listed[0]["photos"]
                self.assertIn("token=", link["url"])
                fresh = self.client.get(f"/api/v1/changes/{change['id']}/photos", headers=self.auth_header(who))
                self.assertEqual(fresh.status_code, 200)
                self.assertEqual([l["key"] for l in fresh.json()], change["photo_keys"])

    def test_photo_links_need_a_sign_in_and_a_known_change(self):
        change = self.submit("field").json()
        self.assertEqual(self.client.get(f"/api/v1/changes/{change['id']}/photos").status_code, 401)
        self.assertEqual(
            self.client.get("/api/v1/changes/999/photos", headers=self.auth_header("estimator")).status_code,
            404,
        )

    def test_the_gc_sees_the_photos_through_the_link(self):
        change = self.submit("field").json()
        self.assertEqual(self.review(change["id"]).status_code, 200)
        opened = self.client.get("/api/v1/approval-session", params={"token": self.link_tokens[-1]})
        self.assertEqual(opened.status_code, 200)
        self.assertEqual([l["key"] for l in opened.json()["photos"]], change["photo_keys"])

    # another company and old keys
    def test_another_companys_key_is_never_signed(self):
        key = self.submit("field").json()["photo_keys"][0]
        self.assertEqual(photos.photo_links([key], 2), [])
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(photos.photo_url(key, 2))
        self.assertEqual(caught.exception.status_code, 404)
        self.assertTrue(asyncio.run(photos.photo_url(key, 1)).startswith("https://example.supabase.co/"))

    def test_old_local_keys_are_not_served_from_the_bucket(self):
        self.assertEqual(photos.photo_links(["abc123.png"], 1), [])

    def test_a_plain_storage_url_is_refused(self):
        key = self.submit("field").json()["photo_keys"][0]
        with httpx.Client(transport=httpx.MockTransport(self.storage.handler)) as client:
            plain = client.get(f"https://example.supabase.co/storage/v1/object/{BUCKET}/{key}")
            public = client.get(f"https://example.supabase.co/storage/v1/object/public/{BUCKET}/{key}")
        self.assertEqual((plain.status_code, public.status_code), (400, 400))

    # the public folder
    def test_no_public_uploads_folder_when_the_bucket_is_used(self):
        def load_main():
            spec = importlib.util.spec_from_file_location(
                "main_under_test", Path(__file__).resolve().parents[1] / "main.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.app

        bucket_app = load_main()
        self.assertNotIn("uploads", [getattr(r, "name", None) for r in bucket_app.routes])
        self.assertEqual(TestClient(bucket_app).get("/uploads/anything.png").status_code, 404)
        with patch.dict(os.environ, {"SUPABASE_SECRET_KEY": ""}):
            local_app = load_main()
        self.assertIn("uploads", [getattr(r, "name", None) for r in local_app.routes])


class LocalFolderTests(unittest.TestCase):
    """Without the secret key, photos stay in the local folder as before."""

    def test_links_are_the_uploads_path(self):
        with patch.dict(os.environ, {"SUPABASE_SECRET_KEY": ""}):
            self.assertEqual(
                photos.photo_links(["abc.png"], 1),
                [{"key": "abc.png", "url": "/uploads/abc.png", "expires_at": None}],
            )


if __name__ == "__main__":
    unittest.main()
