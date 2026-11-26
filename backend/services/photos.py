"""Validate, store and serve the photos of a change report (J9).

Photos are evidence for people, so they are private. With SUPABASE_SECRET_KEY
set they go to the private Supabase Storage bucket (docs/photo-storage.md):
the key is "<company_id>/<uuid><ext>", and the API hands out signed links that
expire after PHOTO_URL_TTL_SECONDS, only after it has checked the caller. The
bucket has no public access, so a plain storage URL is refused.

Without the secret key (a laptop with no key, and the tests), photos stay in
the local uploads folder as before and are served from /uploads.

Storage is reached with its REST API over httpx (already installed with
fastapi[standard]), so there is no new dependency. The secret key never leaves
the backend, and no error message carries it.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from fastapi import HTTPException, UploadFile

import core.config as config
from core.config import MAX_PHOTO_BYTES, photo_settings, photos_in_bucket

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/avif": ".avif",
}
STORAGE_DOWN = "Photo storage is not available right now. Try again in a minute."
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def matches_image_type(data: bytes, content_type: str) -> bool:
    # A MIME label alone does not establish that the upload is an image.
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    brands = {
        "image/heic": (b"heic", b"heix", b"hevc", b"hevx"),
        "image/heif": (b"mif1", b"msf1", b"heic", b"heix"),
        "image/avif": (b"avif", b"avis"),
    }
    return data[4:8] == b"ftyp" and any(
        brand in data[8:64] for brand in brands.get(content_type, ())
    )


# ------------------------------------------------------------ storage client


def _client() -> httpx.Client:
    """The HTTP client for Storage. Tests replace this with a fake transport."""
    return httpx.Client(timeout=TIMEOUT)


def _storage(method: str, path: str, **kwargs) -> httpx.Response:
    """One call to the Storage REST API with the backend-only secret key."""
    settings = photo_settings()
    headers = {
        "apikey": settings["secret_key"],
        "Authorization": "Bearer " + settings["secret_key"],
        **kwargs.pop("headers", {}),
    }
    url = f"{settings['supabase_url']}/storage/v1/{path}"
    try:
        with _client() as client:
            response = client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError:
        # Name nothing: the request carried the secret key.
        raise HTTPException(502, STORAGE_DOWN) from None
    if response.status_code >= 400:
        raise HTTPException(502, STORAGE_DOWN)
    return response


def _object_path(key: str) -> str:
    return quote(photo_settings()["bucket"], safe="") + "/" + quote(key, safe="/")


def _upload(key: str, data: bytes, content_type: str) -> None:
    # Always send the real type: Storage would store it as text/html otherwise.
    _storage(
        "POST",
        "object/" + _object_path(key),
        content=data,
        headers={"Content-Type": content_type, "x-upsert": "false"},
    )


def _company_of(key: str) -> str | None:
    head, slash, _rest = key.partition("/")
    return head if slash else None


def key_company(key: str) -> int | None:
    """The company a bucket key belongs to, or None for an old local key."""
    head = _company_of(key)
    return int(head) if head and head.isdigit() else None


# ----------------------------------------------------------------- contract


async def save_photo(photo: UploadFile, company_id: int | None = None) -> str:
    """Validate one upload, store it, and return its storage key.

    415 for a wrong type or bytes that do not match it, 413 over 10 MB, 400 when
    empty, 502 when the bucket cannot take it (nothing is stored then).
    """
    try:
        content_type = (photo.content_type or "").split(";")[0].lower()
        extension = EXTENSIONS.get(content_type)
        if extension is None:
            raise HTTPException(415, "Use a JPEG, PNG, WebP, HEIC, HEIF, or AVIF image.")

        # Read at most the limit plus one byte, enough to detect an oversized
        # image without reading an unbounded file into application memory.
        data = await photo.read(MAX_PHOTO_BYTES + 1)
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "The image must be 10 MB or smaller.")
        if not data:
            raise HTTPException(400, "The image is empty.")
        if not matches_image_type(data, content_type):
            raise HTTPException(415, "The file does not match its image type.")

        # Ignore the original filename: two uploads must never overwrite each other.
        name = uuid.uuid4().hex + extension
        if photos_in_bucket():
            if company_id is None:
                raise HTTPException(500, "A photo needs a company to be stored")
            key = f"{int(company_id)}/{name}"
            await asyncio.to_thread(_upload, key, data, content_type)
            return key
        # Local folder. Disk writes can block, so run this one in a thread.
        await asyncio.to_thread((config.UPLOAD_DIR / name).write_bytes, data)
        return name
    finally:
        # Close the uploaded temporary file on both success and validation errors.
        await photo.close()


def photo_links(keys: list[str], company_id: int | None) -> list[dict]:
    """Links for a change's photos: [{key, url, expires_at}], in the same order.

    Bucket: one signed link per photo of this company, valid for the configured
    lifetime, from one batch call. Keys of another company, and old local keys
    with no company prefix, are left out, never signed. Local folder: the
    /uploads path, with no expiry.
    """
    if not keys:
        return []
    if not photos_in_bucket():
        return [
            {"key": key, "url": "/uploads/" + quote(key, safe=""), "expires_at": None}
            for key in keys
            if _company_of(key) is None
        ]
    if company_id is None:
        return []
    mine = [key for key in keys if _company_of(key) == str(int(company_id))]
    if not mine:
        return []
    settings = photo_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings["ttl_seconds"])
    response = _storage(
        "POST",
        "object/sign/" + quote(settings["bucket"], safe=""),
        json={"expiresIn": settings["ttl_seconds"], "paths": mine},
    )
    signed = {}
    for item in response.json():
        if item.get("signedURL") and not item.get("error"):
            signed[item.get("path")] = settings["supabase_url"] + "/storage/v1" + item["signedURL"]
    return [
        {"key": key, "url": signed[key], "expires_at": expires_at}
        for key in mine
        if key in signed
    ]


async def photo_url(storage_key: str, company_id: int) -> str:
    """One signed link (the B11 contract). 404 for another company's key."""
    if photos_in_bucket() and _company_of(storage_key) != str(int(company_id)):
        raise HTTPException(404, "Not found")
    links = await asyncio.to_thread(photo_links, [storage_key], company_id)
    if not links:
        raise HTTPException(404, "Not found")
    return links[0]["url"]


def _delete(storage_key: str) -> None:
    if photos_in_bucket():
        if _company_of(storage_key) is not None:
            _storage("DELETE", "object/" + _object_path(storage_key))
        return
    (config.UPLOAD_DIR / storage_key).unlink(missing_ok=True)


async def delete_photo(storage_key: str) -> None:
    """Remove an uploaded photo, for cleanup when the change could not be saved.

    Best effort: a cleanup failure never hides the error that caused it.
    """
    try:
        await asyncio.to_thread(_delete, storage_key)
    except HTTPException:
        pass
