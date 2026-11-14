# Staff sign-in (U6)

Set EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY in local frontend/.env, plus EXPO_PUBLIC_API_URL. Bona supplies the public URL/key. Never use a service-role key, database connection string or password in frontend source or EXPO_PUBLIC variables. Restart Expo after changing settings.

The app signs in with Supabase, sends Authorization: Bearer <access_token> to GET /api/v1/me, and uses only its {id, name, role} response to open the field, estimator or manager workspace. Tokens and passwords are never persisted to disk by this frontend. Reloading requires sign-in again; token expiry or an API 401 ends the local session. Automatic token refresh and persistent sessions are not part of this increment.

Backend prerequisites: J5 (#23), B7 account links, WORKSPACE_BACKEND=postgres and Bona's caller_for_auth_user lookup. The backend must verify tokens and enforce tenant and role checks. The SQLite prototype is not a substitute for server role checks. Main without J5 cannot complete sign-in: /api/v1/me will return 404.

The external /approve link stays public and sends no staff bearer token. Staff cannot switch roles or activate a demo session. Field can report and follow changes; estimator reviews and sends terms; manager authorizes urgent work. Wrong-role direct links to reporting/work-order screens are blocked by the frontend as well as requiring server authorization.

Before merging: test all three accounts on Expo Go against the real backend, verify /me matches their database roles, test expiry/sign-out and a wrong-role 403, and check anonymous GC viewing/approval. Use passwords supplied privately. Browser tests with mock Supabase and API responses do not verify the shared Supabase setup.
