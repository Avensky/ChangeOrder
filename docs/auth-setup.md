# Staff sign-in setup (Supabase)

Task B7. These are the steps Bona does by hand, in order, to get staff sign-in working for the Nov 18 demo. Nothing here contains a key, a password or a connection string, and nothing like that may be added to this file or to any commit.

What the repository already gives you:

- `backend/db/seeds/0001_demo_seed.sql` creates the company "Cohyric Demo", the projects `north-park`, `harbor` and `cedar`, and four users: field, estimator, manager and gc (`<role>@changeorder.test`, no Supabase account yet).
- `backend/db/seeds/0002_link_auth_users.sql` links the three staff users to their Supabase accounts by email.

The migrations `0000`, `0001` and `0002` are already applied and the tables were empty, so the seed can run straight away.

## Secrets: what is public and what is not

- Test account **passwords are shared privately** with Jalen and Uriel (not in the repository, an issue, a PR or a chat that is saved).
- The **anon key** (Supabase now also calls it the *publishable key*, `sb_publishable_...`) is public by design. It ships inside the app. It is safe only because row level security is on for every table with no policies.
- The **service-role key** (new name: *secret key*, `sb_secret_...`), the **database password** and the `DATABASE_URL` that contains it must **never** be committed, pasted into a PR, or put in `frontend/` (anything starting with `EXPO_PUBLIC_` is sent to every phone). They live only in each person's local `backend/.env` and in the host's secret settings.
- The backend in this plan does not need the service-role key at all. Do not give it one.

## Steps

### 1. Run seed 0001

Supabase dashboard, SQL editor, paste the whole of `backend/db/seeds/0001_demo_seed.sql`, run. It is safe to run twice; the second run prints a notice and changes nothing. It stops with an error if schema v2 is not there.

Check:

```sql
SELECT id, name FROM company;
SELECT slug, name, base_budget_cents, currency FROM project ORDER BY id;
SELECT role, name, email, auth_user_id FROM "user" ORDER BY id;
```

Expect one company, three projects, four users, every `auth_user_id` empty. Note the company `id`. The repository layer reads `WORKSPACE_COMPANY_ID` (default `1`); if the company id is not 1, set that variable in `backend/.env`.

### 2. Enable the email sign-in provider

Dashboard, Authentication, Sign In / Providers (the Auth Providers page), Email. Make sure **Enable Email provider** is on. (On hosted projects it is on by default.)

### 3. Turn off email confirmation for the demo

On the same Email provider settings, turn **Confirm email** off. The `.test` addresses cannot receive mail, so an account that needed confirmation could never sign in. Turn it back on before real users exist.

Source: Supabase, Password-based Auth, https://supabase.com/docs/guides/auth/passwords (says email confirmation is on by default on hosted projects and is changed on the Auth Providers page).

### 4. Create the three staff accounts

Dashboard, Authentication, Users, **Add user**, **Create new user**. Create exactly these three, with **Auto Confirm User** ticked:

| Email | Role it will get in the app |
| --- | --- |
| `field@changeorder.test` | field |
| `estimator@changeorder.test` | estimator |
| `manager@changeorder.test` | manager |

Choose a password for each, share them privately with Jalen and Uriel, and do not write them anywhere in the repository. Do **not** create an account for `gc@changeorder.test`: the GC never signs in, and the database refuses a GC with an account.

The role is not stored in Supabase. It is the `role` column of the matching `"user"` row, found through `auth_user_id` (step 5). The server reads it from the database, so a role sent by the app is never trusted.

### 5. Link the accounts to the app users

SQL editor, paste `backend/db/seeds/0002_link_auth_users.sql`, run. It sets `"user".auth_user_id` from `auth.users` by email for the three staff users only. It never touches the gc user. If any account is missing it stops with an error naming the missing emails and changes nothing; fix step 4 and run it again. Running it again after success changes nothing. The check query at the end of the file should show three linked rows and the gc row empty.

### 6. Get the values for `frontend/.env`

Dashboard, Project Settings, **API Keys** (and the **Connect** button at the top of the project). Copy into your local `frontend/.env` (gitignored):

```
EXPO_PUBLIC_SUPABASE_URL=<Project URL, https://<project-ref>.supabase.co>
EXPO_PUBLIC_SUPABASE_ANON_KEY=<the anon key, or the publishable key sb_publishable_...>
```

Either key works in the app; the publishable key is the current name. Source: https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys (the publishable key replaces `anon` in browsers and mobile apps; the secret key replaces `service_role` on servers only).

### 7. Get the values the backend needs to verify tokens

The backend verifies the access token the app sends in `Authorization: Bearer <jwt>`. Supabase's current guidance is to verify with the project's public signing keys, not a shared secret:

- The token header names its key (`kid`) and algorithm (`alg`, HS256, ES256 or RS256).
- The `iss` claim is `https://<project-ref>.supabase.co/auth/v1`. Appending `/.well-known/jwks.json` gives the public keys.
- The endpoint is `GET https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`. It is public, safe to fetch, and cached by Supabase for 10 minutes.
- The legacy shared JWT secret is "no longer recommended"; it exists for backward compatibility.

Sources: https://supabase.com/docs/guides/auth/jwts and https://supabase.com/docs/guides/auth/signing-keys

Check which system the project uses: Dashboard, Project Settings, **JWT Keys** (the JWT signing keys page).

- If it lists an asymmetric key (ES256 or RS256) as current: use the JWKS endpoint. Nothing secret is needed.
- If it still shows only the legacy JWT secret (HS256): either click **Migrate JWT secret** on that page (the docs say this causes no downtime) and then use the JWKS endpoint, or, as a fallback only, give the backend the legacy secret.

Backend variables (names only, values go in local `backend/.env` and the host's secrets):

| Variable | Value | Secret? |
| --- | --- | --- |
| `SUPABASE_URL` | the Project URL, same as the frontend one | no |
| `SUPABASE_JWKS_URL` | optional; defaults to `$SUPABASE_URL/auth/v1/.well-known/jwks.json` | no |
| `SUPABASE_JWT_SECRET` | only for the legacy HS256 fallback; leave unset when using JWKS | **yes, never commit** |
| `SUPABASE_JWT_AUDIENCE` | optional; Supabase user tokens carry `aud` = `authenticated` | no |
| `DATABASE_URL` | see below | **yes, never commit** |

### 8. DATABASE_URL: which connection string

Dashboard, **Connect**. There are two options for a backend that stays running (source: https://supabase.com/docs/guides/database/connecting-to-postgres):

| Option | Host and port shape | Network |
| --- | --- | --- |
| Direct connection | `db.<project-ref>.supabase.co:5432` | IPv6 only, unless the project has the paid IPv4 add-on |
| Session pooler (Supavisor, session mode) | `aws-<region>.pooler.supabase.com:5432`, user `postgres.<project-ref>` | IPv4, on every tier |

**From a home network, use the session pooler**, unless you have confirmed your network has IPv6 (test at https://test-ipv6.com). Most home networks are IPv4-only, and the direct host then fails with "connection refused" or a name that does not resolve. The session pooler is the documented choice for a persistent backend on an IPv4-only network. Do not use the transaction pooler (port 6543) for this backend: it does not support prepared statements. The direct connection is the right one for running migrations with `psql`, where you have IPv6.

Put the string in local `backend/.env` as `DATABASE_URL=...`, with `WORKSPACE_BACKEND=postgres`. Add `?sslmode=require` if your driver does not turn SSL on itself.

### 9. Check the sign-in works

With the three accounts and the anon key, a sign-in from the app (or the dashboard's user list) for each of the three emails should succeed. A quick backend-side check after J5 lands: the token's `sub` matches `"user".auth_user_id` for that email.

## What Jalen (J5) and Uriel (U6) need from this

**Jalen (J5, role checks on routes):**

- Send `Authorization: Bearer <access token>` and verify it: signature from the JWKS (`SUPABASE_JWKS_URL`, default `$SUPABASE_URL/auth/v1/.well-known/jwks.json`), `exp` not passed, `iss` equal to `$SUPABASE_URL/auth/v1`, `aud` equal to `authenticated`. Use a JWT library; do not write the algorithm yourself.
- **Read the user's id from the `sub` claim.** It is a UUID. Look up `"user"` where `auth_user_id = sub`; that row gives `id`, `company_id` and `role`. Reject a valid token with no matching row. Never take a role or company from the request body or from token claims you did not verify.
- The gc user has no `auth_user_id` and must never pass this check; GC access stays on the emailed link.
- Variables: `SUPABASE_URL`, optional `SUPABASE_JWKS_URL`, optional `SUPABASE_JWT_AUDIENCE`, legacy fallback `SUPABASE_JWT_SECRET`, `DATABASE_URL`, `WORKSPACE_BACKEND=postgres`.
- Test accounts: `field@`, `estimator@`, `manager@changeorder.test`. Passwords come from Bona privately.

**Uriel (U6, sign-in in the app):**

- Variables in `frontend/.env`: `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` (plus the existing `EXPO_PUBLIC_API_URL`).
- Sign in with email and password through Supabase, then send the session's `access_token` to the API as `Authorization: Bearer <access_token>`. The user's id is the `sub` claim in that token (`session.user.id` in the client library).
- The app must not decide the role itself. Ask the API who the caller is and show the screens for that role.
- Never put the service-role or secret key, or any database string, in the app.

## Not covered here

- Passwords: chosen in step 4 and shared privately.
- Real staff accounts: later, with confirmation turned back on.
