# Database migrations

`SQLModel.metadata.create_all()` creates missing tables but never changes an existing one. The shared Supabase database is changed only by the numbered SQL files in this folder, in order. Only Bona's agents add files here, and only Bona runs them against Supabase.

| File | What it does |
| --- | --- |
| `0001_nov3_baseline.sql` | Brings a database to the Nov 3 schema: creates the seven tables in an empty database, or just records the baseline when they already exist. |
| `0002_schema_v2.sql` | Moves the Nov 3 schema to schema v2, the one in `backend/db/models.py` (task B2). |

Each file runs in one transaction and records itself in the `schema_migration` table. A file stops with an error, and changes nothing, when the database is not in the state it expects or when it was already applied.

## Before running

1. Find out what the database holds today. This query only reads:

   ```sql
   SELECT table_name, column_name
   FROM information_schema.columns
   WHERE table_schema = 'public'
   ORDER BY table_name, ordinal_position;
   ```

   | What you see | What to do |
   | --- | --- |
   | No tables | Run `0001`, then `0002`. |
   | `change_event` with a `contractor_id` column, plus `change_order`, `change_order_revision`, `approval_request`, `approval_decision`, `notifications`, `user` | This is the Nov 3 schema. Run `0001`, then `0002`. |
   | A `change_orders` table (the October tables) | Stop. `0001` refuses this database. The old tables need a decision first: drop them if they hold only test rows, or write a migration for them. |
   | A `company` table | Schema v2 is already there. Check `SELECT * FROM schema_migration;`. |

2. Take a backup (Supabase dashboard, Database, Backups) or export the tables, if they hold anything worth keeping.
3. Read the note at the top of `0002_schema_v2.sql`. It lists what happens to existing rows.

## Running

Paste the whole file into the Supabase SQL editor and run it, one file at a time. With `psql`, use `psql -v ON_ERROR_STOP=1 -f <file>` and take the connection string from your local `.env`; never paste it into a file, a commit, or a chat.

If a file fails, the transaction is rolled back and the database is as it was. Fix the cause and run the file again.

## After running `0002`

- Rename the company: `UPDATE company SET name = '<real name>' WHERE name = 'Default company';`
- Every old `admin` user is now an `estimator`. Make the right people managers: `UPDATE "user" SET role = 'manager' WHERE id = <id>;`
- Compare the tables with the models. Both of these should show the v2 columns and `0001` and `0002`:

  ```sql
  SELECT table_name, column_name, data_type, is_nullable
  FROM information_schema.columns
  WHERE table_schema = 'public'
  ORDER BY table_name, ordinal_position;

  SELECT * FROM schema_migration ORDER BY version;
  ```

- Row level security is now on for every table, with no policies. The backend's own database connection still reads and writes everything; Supabase's public REST API with the anon key gets nothing. If the backend suddenly reads zero rows, its `DATABASE_URL` is using a role that does not own the tables.
- If the notice "revision(s) sent before v2 have no cost or timeline" appeared, the rule `change_order_revision_sent_has_terms` applies to new and edited rows only. Once the old rows are priced or removed, finish it with `ALTER TABLE change_order_revision VALIDATE CONSTRAINT change_order_revision_sent_has_terms;`

## Adding a migration

- Never edit a file that has been applied anywhere. Add the next number.
- Change `backend/db/models.py` in the same pull request, so the models and the tables stay the same.
- Wrap the file in `BEGIN; ... COMMIT;`, check the starting state, and end by inserting the file's name into `schema_migration`.
- No drop, truncate or reset against the shared project outside a reviewed migration.

## How these files were checked

They have not been run against Supabase. They were run against a throwaway in-memory PostgreSQL (PGlite, PostgreSQL 18; the Supabase project may run a different major version) on: an empty database, Nov 3 tables with and without rows, a second run, the October tables, and a failure half way. After `0002`, the columns, constraints and indexes were compared with the ones `create_all()` produces from the v2 models, and they match.
