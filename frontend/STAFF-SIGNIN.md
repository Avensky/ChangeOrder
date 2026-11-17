# Staff sign-in (U6)

Set EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY in local frontend/.env, plus EXPO_PUBLIC_API_URL. Bona supplies the public URL/key. Never use a service-role key, database connection string or password in frontend source or EXPO_PUBLIC variables. Restart Expo after changing settings.

The app signs in with Supabase, sends Authorization: Bearer <access_token> to GET /api/v1/me, and uses only its {id, name, role} response to open the field, estimator or manager workspace. Tokens and passwords are never persisted to disk by this frontend. Reloading requires sign-in again; token expiry or an API 401 ends the local session. Automatic token refresh and persistent sessions are not part of this increment.

Backend prerequisites: J5 (#23), B7 account links and the repository auth-user lookup are merged into main. Jalen runs the backend with WORKSPACE_BACKEND=postgres and its private connection settings. Uriel needs only the public Supabase URL/key and the reachable API address for the frontend, not the database connection string. The backend verifies tokens and enforces tenant and role checks; the SQLite prototype is not a substitute for these checks.

The external /approve link stays public and sends no staff bearer token. Staff cannot switch roles or activate a demo session. Field can report and follow changes; estimator reviews and sends terms; manager authorizes urgent work. Wrong-role direct links to reporting/work-order screens are blocked by the frontend as well as requiring server authorization.

Before merging: test all three accounts on Expo Go against the real backend, verify /me matches their database roles, test expiry/sign-out and a wrong-role 403, and check anonymous GC viewing/approval. Use passwords supplied privately. Browser tests with mock Supabase and API responses do not verify the shared Supabase setup.

## Reproducible browser checks

From frontend, run `npm ci`, `npx playwright install chromium`, then `npm run test:e2e`. The suite builds a static web export and serves it on loopback port 8123. It overrides public settings with synthetic values and intercepts Supabase/API calls; no real account, key, database or password is needed. Run it separately from live device tests.

Legacy internal workspace keys (`subcontractor`, `office`, `approver`) remain behind a mapping from verified field/estimator/manager roles. The authenticated UI never offers a role picker; removing these internal compatibility names is deferred to a separate rename after integration. They do not authorize requests or define extra user roles.

## Live test status

Bona reports all three accounts and the full phone workflow passed against Supabase on Nov 16. Re-confirm on Tuesday's demo network after #30 and #24 integration. #29's NativeWind web crash fix is merged. Email uses the private console link and the email template for the demo; no provider delivery is claimed. Human review and merge of #24 remain with Bona.
