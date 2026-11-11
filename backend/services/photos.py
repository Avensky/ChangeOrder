"""NEW: Save prototype photos locally while keeping the existing photo_key API.

This separates file handling from the HTTP route. A future storage provider
can replace this function without changing the frontend's multipart fields.
"""

import asyncio
import uuid

from fastapi import HTTPException, UploadFile

from core.config import MAX_PHOTO_BYTES, UPLOAD_DIR

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/avif": ".avif",
}


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


async def save_photo(photo: UploadFile) -> str:
    """Validate one upload and return its unique filename after saving it."""
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
        key = uuid.uuid4().hex + extension
        # Disk writes can block. Run this one in a thread so the async server
        # can keep accepting other requests while the image is written.
        await asyncio.to_thread((UPLOAD_DIR / key).write_bytes, data)
        return key
    finally:
        # Close the uploaded temporary file on both success and validation errors.
        await photo.close()
