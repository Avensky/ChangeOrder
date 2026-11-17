-- Seed 0002: link the three staff users to their Supabase accounts (task B7).
--
-- Run this AFTER seed 0001 and AFTER creating the three accounts in the
-- Supabase dashboard (docs/auth-setup.md), with these exact emails:
--   field@changeorder.test, estimator@changeorder.test, manager@changeorder.test
--
-- It sets "user".auth_user_id to auth.users.id, matched on email, for those
-- three staff users of company "Cohyric Demo" only. It never touches the gc
-- user. If seed 0001 was not run, or any of the three accounts is missing, it
-- stops with an error and changes nothing (the whole file is one transaction).
-- Running it again after a success changes nothing more.
--
-- Run in the Supabase SQL editor (which can read the auth schema), or with
-- psql -v ON_ERROR_STOP=1 -f 0002_link_auth_users.sql

BEGIN;

DO $$
DECLARE
    demo_company_id INTEGER;
    missing TEXT;
    linked INTEGER;
BEGIN
    SELECT min(id) INTO demo_company_id FROM company WHERE name = 'Cohyric Demo';
    IF demo_company_id IS NULL THEN
        RAISE EXCEPTION 'Company "Cohyric Demo" not found: run seed 0001 first.';
    END IF;

    -- Every staff user must exist in the app and have a Supabase account.
    SELECT string_agg(e.email, ', ' ORDER BY e.email) INTO missing
    FROM (VALUES ('field@changeorder.test'),
                 ('estimator@changeorder.test'),
                 ('manager@changeorder.test')) AS e (email)
    WHERE NOT EXISTS (
              SELECT 1 FROM "user" AS u
              WHERE u.company_id = demo_company_id AND u.email = e.email
                AND u.role <> 'gc')
       OR NOT EXISTS (SELECT 1 FROM auth.users AS a WHERE lower(a.email) = e.email);
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'Missing app user or Supabase account for: %. Nothing was changed.', missing;
    END IF;

    UPDATE "user" AS u
    SET auth_user_id = a.id
    FROM auth.users AS a
    WHERE u.company_id = demo_company_id
      AND u.role <> 'gc'
      AND u.email IN ('field@changeorder.test',
                      'estimator@changeorder.test',
                      'manager@changeorder.test')
      AND lower(a.email) = u.email
      AND u.auth_user_id IS DISTINCT FROM a.id;
    GET DIAGNOSTICS linked = ROW_COUNT;

    RAISE NOTICE 'Linked % staff user(s).', linked;
END
$$;

-- Check: three rows with an auth_user_id, and the gc row with none.
SELECT role, email, auth_user_id
FROM "user"
WHERE company_id = (SELECT min(id) FROM company WHERE name = 'Cohyric Demo')
ORDER BY role;

COMMIT;
