-- Seed 0001: demo data for the Nov 18 demo (task B7).
--
-- Creates company "Cohyric Demo", the three demo projects the frontend uses
-- (north-park, harbor, cedar) and one user per persona: field, estimator,
-- manager and gc. Staff users get an email in the reserved form
-- <role>@changeorder.test and auth_user_id NULL; seed 0002 links them to their
-- Supabase accounts later. The gc user has an email and never an account.
--
-- Safe to run twice. The file records itself in schema_migration as
-- 'seed_0001_demo'; when that row exists the whole file does nothing. Every
-- insert is also guarded on its own, so a half-seeded database is completed
-- without duplicates.
--
-- Needs schema v2 (0002_schema_v2) to be applied first. Changes nothing and
-- stops with an error otherwise.
--
-- No real names, emails, phone numbers or passwords belong in this file. The
-- display names are the fictional ones from the frontend demo data, except the
-- manager, which has no demo name there.
--
-- Run it like the migrations: paste into the Supabase SQL editor, or
-- psql -v ON_ERROR_STOP=1 -f 0001_demo_seed.sql

BEGIN;

DO $$
DECLARE
    demo_company_id INTEGER;
BEGIN
    IF to_regclass('public.schema_migration') IS NULL
       OR NOT EXISTS (SELECT 1 FROM schema_migration WHERE version = '0002_schema_v2') THEN
        RAISE EXCEPTION 'Seed 0001 needs schema v2: run migrations 0000, 0001 and 0002 first.';
    END IF;

    IF EXISTS (SELECT 1 FROM schema_migration WHERE version = 'seed_0001_demo') THEN
        RAISE NOTICE 'Seed 0001 was already applied. Nothing changed.';
        RETURN;
    END IF;

    -- Company (its name is not unique in the schema, so guard by name).
    INSERT INTO company (name, created_at)
    SELECT 'Cohyric Demo', now()
    WHERE NOT EXISTS (SELECT 1 FROM company WHERE name = 'Cohyric Demo');

    SELECT min(id) INTO demo_company_id FROM company WHERE name = 'Cohyric Demo';

    -- Projects. Budgets are integer cents: $185,000, $320,000, $245,000.
    INSERT INTO project (company_id, slug, name, base_budget_cents, currency, created_at)
    VALUES
        (demo_company_id, 'north-park', 'North Park Residence', 18500000, 'USD', now()),
        (demo_company_id, 'harbor',     'Harbor Office Fit-out', 32000000, 'USD', now()),
        (demo_company_id, 'cedar',      'Cedar Ridge Duplex',    24500000, 'USD', now())
    ON CONFLICT (company_id, slug) DO NOTHING;

    -- Users. auth_user_id stays NULL here; the gc never gets one.
    INSERT INTO "user" (company_id, role, name, email, auth_user_id)
    VALUES
        (demo_company_id, 'field',     'Marcus Rivera', 'field@changeorder.test',     NULL),
        (demo_company_id, 'estimator', 'Avery Morgan',  'estimator@changeorder.test', NULL),
        (demo_company_id, 'manager',   'Demo Manager',  'manager@changeorder.test',   NULL),
        (demo_company_id, 'gc',        'Jordan Ellis',  'gc@changeorder.test',        NULL)
    ON CONFLICT (company_id, email) DO NOTHING;

    INSERT INTO schema_migration (version) VALUES ('seed_0001_demo')
    ON CONFLICT (version) DO NOTHING;
END
$$;

COMMIT;
