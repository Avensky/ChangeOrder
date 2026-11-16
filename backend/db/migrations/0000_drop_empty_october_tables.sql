-- 0000_drop_empty_october_tables.sql
--
-- Removes the three tables left from the October prototype (change_orders,
-- notifications and "user"), so 0001_nov3_baseline.sql can create the Nov 3
-- tables in a clean database. Two of them share a name with Nov 3 tables but
-- have a different shape, which is why 0001 refuses a database that has them.
--
-- It drops the tables only when all of this is true:
--   * all three October tables exist, each with exactly its October columns
--   * every one of them has 0 rows
--   * no Nov 3 or schema v2 table exists, and no migration is recorded
--
--   * No change_orders table (an empty database, or one already on the Nov 3
--     schema): changes nothing, only records itself.
--   * Anything else (a row in any table, an unexpected column, a mix of
--     October and newer tables): stops with an error and changes nothing.
--
-- Runs in one transaction. Read README.md in this folder before running it.

BEGIN;
SET LOCAL search_path TO public;

CREATE TABLE IF NOT EXISTS schema_migration (
    version VARCHAR PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

DO $$
DECLARE
    newer_tables TEXT;
    found_columns TEXT;
    row_total BIGINT;
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migration) THEN
        RAISE EXCEPTION
            'Migrations are already recorded in schema_migration. 0000 only runs first, on a database with no migrations. Nothing was changed.';
    END IF;

    IF to_regclass('public.change_orders') IS NULL THEN
        RAISE NOTICE 'No change_orders table: there are no October tables to drop. Recording 0000 only.';
        RETURN;
    END IF;

    -- A change_orders table next to newer tables is a state nobody planned for.
    SELECT string_agg(table_name::text, ', ' ORDER BY table_name) INTO newer_tables
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('change_event', 'change_order', 'change_order_revision',
                         'approval_request', 'approval_decision', 'company', 'project',
                         'photo', 'change_history', 'ai_suggestion', 'approval_link');
    IF newer_tables IS NOT NULL THEN
        RAISE EXCEPTION
            'change_orders exists together with newer tables (%). Nothing was changed.', newer_tables;
    END IF;

    IF to_regclass('public.notifications') IS NULL OR to_regclass('public."user"') IS NULL THEN
        RAISE EXCEPTION
            'Expected all three October tables (change_orders, notifications, "user"), but one is missing. Nothing was changed.';
    END IF;

    -- Each table must have exactly its October columns.
    SELECT string_agg(column_name::text, ', ' ORDER BY column_name) INTO found_columns
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'change_orders';
    IF found_columns IS DISTINCT FROM
       'approved_at, approved_by_id, client_id, contractor_id, created_at, id, photo_key, status' THEN
        RAISE EXCEPTION
            'change_orders is not the October table. Its columns are: %. Nothing was changed.', found_columns;
    END IF;

    SELECT string_agg(column_name::text, ', ' ORDER BY column_name) INTO found_columns
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'notifications';
    IF found_columns IS DISTINCT FROM
       'created_at, id, recipient_user_id, report_id, sent_at, status, type' THEN
        RAISE EXCEPTION
            'notifications is not the October table. Its columns are: %. Nothing was changed.', found_columns;
    END IF;

    SELECT string_agg(column_name::text, ', ' ORDER BY column_name) INTO found_columns
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'user';
    IF found_columns IS DISTINCT FROM 'id, name, phone, role' THEN
        RAISE EXCEPTION
            '"user" is not the October table. Its columns are: %. Nothing was changed.', found_columns;
    END IF;

    -- Hold the tables so no row can arrive between the count and the drop.
    LOCK TABLE change_orders, notifications, "user" IN ACCESS EXCLUSIVE MODE;

    SELECT (SELECT count(*) FROM change_orders)
         + (SELECT count(*) FROM notifications)
         + (SELECT count(*) FROM "user")
    INTO row_total;
    IF row_total > 0 THEN
        RAISE EXCEPTION
            'The October tables are not empty: change_orders has % row(s), notifications has %, "user" has %. Nothing was changed.',
            (SELECT count(*) FROM change_orders),
            (SELECT count(*) FROM notifications),
            (SELECT count(*) FROM "user");
    END IF;

    -- No CASCADE: if anything else depends on these tables, the drop fails
    -- and the whole file is rolled back.
    DROP TABLE change_orders, notifications, "user";
    RAISE NOTICE 'Dropped the three empty October tables: change_orders, notifications, "user".';
END $$;

INSERT INTO schema_migration (version) VALUES ('0000_drop_empty_october_tables');

COMMIT;
