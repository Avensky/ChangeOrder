# Photo storage decision (B11)

**Recommendation: store photos in a private Supabase Storage bucket in the existing project, upload from the backend with the Supabase secret key, and serve them with short-lived signed links that the backend hands out only after it has checked the caller's company.** The reason: the project, its US region and its backend-only secret already exist, so there is no second account, no second credential and no new IAM policy to get wrong. The `photo.storage_key` column already holds a key, not a URL, so no migration is needed. Private S3 would work equally well technically, but it adds an account, a credential type and a policy for a few hundred small images.

Decided for: Bona (B11). Builds on this: Jalen (J9), Uriel (U9). Documentation was read on **2026-11-23** (cited per row). Nothing was created or changed in Supabase or AWS while writing this.

## Comparison

| Question | Private Supabase Storage bucket | Private S3 bucket (US region) |
| --- | --- | --- |
| Create and keep private | Dashboard: Storage, New Bucket, leave "Public bucket" off. Buckets are private by default; public buckets bypass access controls for downloads. ([fundamentals](https://supabase.com/docs/guides/storage/buckets/fundamentals), [creating buckets](https://supabase.com/docs/guides/storage/buckets/creating-buckets)) | Create bucket in a US region. New buckets don't allow public access, and all four Block Public Access settings are on by default. ([create-bucket-overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html)) |
| Region | The project is in us-east-1 (given in the task). Supabase lists "East US (North Virginia), us-east-1". ([regions](https://supabase.com/docs/guides/platform/regions)) | Choose us-east-1 or another US region at creation. |
| Backend upload | `supabase-py` `storage.from_(bucket).upload(path, file, file_options)`. The bucket must already exist. If no content type is passed it defaults to `text/html`, so always pass it. ([upload reference](https://supabase.com/docs/reference/python/storage-from-upload)) | `boto3` `put_object` with an IAM credential. ([boto3 put_object](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/put_object.html)) |
| Serving | `create_signed_url(path, expires_in)`; `expires_in` is in seconds. A single signed URL cannot be revoked; deleting or moving the object invalidates it. ([downloads](https://supabase.com/docs/guides/storage/serving/downloads), [python reference](https://supabase.com/docs/reference/python/storage-from-createsignedurl)) | `generate_presigned_url(..., ExpiresIn=3600)` by default; seconds. IAM-user URLs are valid up to 7 days; URLs signed with temporary credentials die when those credentials expire. Use `signature_version='s3v4'`. ([boto3](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/generate_presigned_url.html), [presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)) |
| Who may read which company | Our backend decides. The secret key bypasses RLS ([access control](https://supabase.com/docs/guides/storage/security/access-control)), so the backend must check company (and, for the GC, the token) before signing. Policies are checked when the URL is created, not when it is used. Add no policies on `storage.objects`: Storage allows no uploads without RLS policies, so the bucket is then closed to anyone without the secret key. | Same model: the backend checks, then signs. The IAM user should only be allowed object read/write on this one bucket (least privilege, [IAM best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)). |
| Size limits | Global limit: Free 50 MB, Pro up to 500 GB. A per-bucket limit and allowed types can be set and cannot exceed the global limit. ([file limits](https://supabase.com/docs/guides/storage/uploads/file-limits)) Standard upload is recommended for files up to 6 MB; larger files should use resumable upload ([standard uploads](https://supabase.com/docs/guides/storage/uploads/standard-uploads)). | Not verified (the limits page would not load). Our 10 MB cap is far below any S3 limit. |
| Cost at our scale | Free: 1 GB storage, 5 GB egress, **projects pause after 1 week of inactivity**. Pro: from $25/month, 100 GB storage then $0.0213/GB, 250 GB egress then $0.09/GB. ([pricing](https://supabase.com/pricing), [storage billing](https://supabase.com/docs/guides/storage/management/pricing)) | Storage and request prices **not verified** (the pricing tables did not load). New AWS customers get up to $200 in credits per the pricing page, and the first 100 GB/month of internet egress is free. ([pricing](https://aws.amazon.com/s3/pricing/)) |
| Setup | One bucket in the existing project; no new account. | AWS bucket, IAM user or role, policy, region, and CORS if a browser loads images from a different origin. |
| Failure modes | Free project paused (uploads and views fail until it is resumed); signed link expired; secret key wrong or rotated; bucket name typo; the key is a legacy `service_role` JWT, which Supabase is deprecating by the end of 2026. ([API keys](https://supabase.com/docs/guides/api/api-keys)) | Credential expired or rotated; presigned URL signed with the wrong signature version; policy too narrow or too wide; link expired. |
| What the credential is for | The Supabase secret key (`sb_secret_...`) gives full project access and bypasses RLS ([API keys](https://supabase.com/docs/guides/api/api-keys)). In this design the backend uses it only to upload and to sign links. | An AWS access key or role with access to this bucket only. |

## Decision on serving: short-lived signed links, issued by the API

- The API returns a signed link only after checking the caller (staff: company from the verified token; GC: the emailed-link token). Opening a photo never needs the app to hold any storage credential.
- Signed links, not streaming through the API: the phone and browser load the image straight from storage, so the API does not carry image traffic. The cost is that a link works for anyone who has it until it expires, which is why the lifetime is short.
- Lifetime: **5 minutes (300 s)**, set by `PHOTO_URL_TTL_SECONDS`. A link is requested again whenever the screen loads or an image fails.
- Streaming through the API is the fallback if signed links turn out to be a problem for the GC page.

## Interface for Jalen (J9) and Uriel (U9)

**Storage key.** `photo.storage_key` stays the only thing in the database. New keys have the form `<company_id>/<uuid><ext>` (extension from the validated content type, as today). Old keys with no slash are local-disk files and are not migrated; they simply stop being served.

**Backend configuration** (`backend/core/config.py`, read from the environment, never committed):

| Variable | Meaning |
| --- | --- |
| `SUPABASE_URL` | Project URL (not secret). |
| `SUPABASE_SECRET_KEY` | Secret key. Backend only. |
| `PHOTO_BUCKET` | Bucket name, default `change-photos`. |
| `PHOTO_URL_TTL_SECONDS` | Signed-link lifetime, default `300`. |

None of these may start with `EXPO_PUBLIC_` or appear in the repo.

**Functions in `backend/services/photos.py`** (names are the contract; internals are Jalen's):

```python
async def save_photo(photo: UploadFile, company_id: int) -> str
    # Validates as today (type, magic bytes, 10 MB, not empty), uploads to the
    # bucket with the real content type, returns the storage key.

async def photo_url(storage_key: str, company_id: int) -> str
    # Returns a signed link valid for PHOTO_URL_TTL_SECONDS.
    # Raises 404 if the key does not start with "<company_id>/".

async def delete_photo(storage_key: str) -> None   # for cleanup if the database write fails
```

Order of operations on `POST /changes`: upload each photo, then insert the `photo` rows; if the insert fails, call `delete_photo` for the keys already uploaded.

**API shape for the app.** Wherever a change is returned with `photo_keys` today, the API also returns:

```json
"photos": [{ "key": "12/ab12...f.jpg", "url": "https://...signed...", "expires_at": "2026-12-01T10:05:00Z" }]
```

Plus `GET /changes/{id}/photos` returning the same list, to refresh expired links. The GC page gets the same list from the existing token-checked route for that change. U9 must show a placeholder while loading and, on a load error or past `expires_at`, call the refresh route once before showing the failure placeholder. The app must not store links.

**Error cases.**

| Case | Response |
| --- | --- |
| Wrong type / magic bytes | 415 (unchanged) |
| Larger than 10 MB | 413 (unchanged) |
| Empty file | 400 (unchanged) |
| Storage unreachable, paused or rejects the upload | 502 with a plain message; no `photo` row is written |
| Photo of another company, or unknown change | 404 (never 403, so existence is not revealed) |
| Link expired | Storage refuses the link; the app refreshes it as above |

Tests (J9): upload, access by role, another company's key refused, and a direct unsigned storage URL refused. These need a fake storage object in tests, not the real project.

## Manual steps for Bona (dashboard only; nothing here has been done)

1. Supabase dashboard, project (us-east-1): **Storage, New Bucket**, name `change-photos`, **Public bucket off**.
2. In the bucket settings set a file size limit of 10 MB and allowed types `image/jpeg, image/png, image/webp, image/heic, image/heif, image/avif` (the same list as the backend).
3. Add **no** policies on `storage.objects` for this bucket.
4. Get the secret key (`sb_secret_...`) from the project's API keys page. Do not use the legacy `service_role` key. Give it to Jalen through Pane Secrets or his own local `.env` and the host's secret settings, never in chat or the repo.
5. Confirm the project is on a plan that does not pause. On Free it pauses after a week of inactivity, which would break photos during a demo.
6. After J9 merges: open a photo's direct bucket URL without a link and confirm it is refused.

The brief's "done when" says the bucket exists and is private. That step is yours; this PR contains only the decision.

## Not verified

- S3 Standard price per GB-month and per-request prices: the pricing tables did not load. Check [aws.amazon.com/s3/pricing](https://aws.amazon.com/s3/pricing/) or the AWS calculator before relying on S3.
- S3 single-upload size limit: the page did not load. The 10 MB cap is far below it either way.
- The exact return shape of `supabase-py` `create_signed_url` and `upload` (key name `signedURL` vs `signedUrl`, behaviour on duplicate path): the Python reference did not describe the return value. Jalen should check against the installed version.
- Whether signed-URL downloads count toward the egress quota: the docs define storage egress as data sent to the client but do not name signed URLs; assumed yes.
- Whether a private bucket with a size limit and allowed types can be created together in the dashboard: inferred from the options being independent, not stated.
- How many photos fit in 1 GB: depends on real phone photo sizes (up to our 10 MB cap); not measured.
- Whether the existing Supabase project is on Free or Pro: not checked, because the project must not be touched.
- Prices and limits on the Supabase and AWS pages can change; they were read on 2026-11-23.
