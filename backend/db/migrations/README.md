# Database migrations

`SQLModel.metadata.create_all()` creates missing tables but never changes an existing one. The shared Supabase database is changed only by the numbered SQL files in this folder, in order. Only Bona's agents add files here, and they are run against Supabase only with Bona's go-ahead, after review.

Run them in this order: `0000`, `0001`, `0002`.

| File | What it does |
| --- | --- |
| `0000_drop_empty_october_tables.sql` | Drops the three October prototype tables (`change_orders`, `notifications`, `"user"`), and only when all three are there in their October shape and every one is empty. With no `change_orders` table it changes nothing. |
| `0001_nov3_baseline.sql` | Brings a database to the Nov 3 schema: creates the seven tables in an empty database, or just records the baseline when they already exist. |
| `0002_schema_v2.sql` | Moves the Nov 3 schema to schema v2, the one in `backend/db/models.py` (task B2). |

Each file runs in one transaction and records itself in the `schema_migration` table. A file stops with an error, and changes nothing, when the database is not in the state it expects or when it was already applied.

`0002_schema_v2.sql` was edited in place on Nov 13 to add projects, change numbers and titles, history, AI suggestions and notification text. That was allowed only because no file here had been run against any shared database. Once a file has been run, it is never edited again.

## Before running

A read-only check on Nov 13 found that the Supabase project (PostgreSQL 17) holds only the three October tables, all with 0 rows, and no recorded migrations. So the plan is `0000`, then `0001`, then `0002`. `0000` checks all of that again when it runs.

1. Confirm what the database holds. This query only reads:

   ```sql
   SELECT table_name, column_name
   FROM information_schema.columns
   WHERE table_schema = 'public'
   ORDER BY table_name, ordinal_position;
   ```

   | What you see | What to do |
   | --- | --- |
   | Only `change_orders` (8 columns), `notifications` (7 columns) and `user` (4 columns), all empty | The October tables. Run `0000`, `0001`, `0002`. `0000` drops them. |
   | The October tables, with a row in any of them | Stop. `0000` refuses, and so does `0001`. Decide what to do with the rows first. |
   | No tables | Run `0000`, `0001`, `0002`. `0000` changes nothing here. |
   | `change_event` with a `contractor_id` column, plus `change_order`, `change_order_revision`, `approval_request`, `approval_decision`, `notifications`, `user` | This is the Nov 3 schema. Run `0000`, `0001`, `0002`. `0000` changes nothing here and leaves `user` and `notifications` alone. |
   | A `company` table | Schema v2 is already there. Check `SELECT * FROM schema_migration;`. |

2. Take a backup (Supabase dashboard, Database, Backups) or export the tables, if they hold anything worth keeping.
3. Read the note at the top of each file. `0000` lists exactly when it drops the October tables; `0002` lists what happens to existing rows.

## Running

Paste the whole file into the Supabase SQL editor and run it, one file at a time, in order. With `psql`, use `psql -v ON_ERROR_STOP=1 -f <file>` and take the connection string from your local `.env`; never paste it into a file, a commit, or a chat.

If a file fails, the transaction is rolled back and the database is as it was. Fix the cause and run the file again.

## After running `0002`

- Rename the company and the project that old rows were put in: `UPDATE company SET name = '<real name>' WHERE name = 'Default company';` and `UPDATE project SET slug = '<slug>', name = '<real name>' WHERE slug = 'default';`
- Every old `admin` user is now an `estimator`. Make the right people managers: `UPDATE "user" SET role = 'manager' WHERE id = <id>;`
- Compare the tables with the models. These should show the v2 columns and the three files `0000`, `0001` and `0002`:

  ```sql
  SELECT table_name, column_name, data_type, is_nullable
  FROM information_schema.columns
  WHERE table_schema = 'public'
  ORDER BY table_name, ordinal_position;

  SELECT * FROM schema_migration ORDER BY version;
  ```

- Row level security is now on for every table, with no policies. The backend's own database connection still reads and writes everything; Supabase's public REST API with the anon key gets nothing. If the backend suddenly reads zero rows, its `DATABASE_URL` is using a role that does not own the tables.
- If the notice "revision(s) sent before v2 have no cost or timeline" appeared, the rule `change_order_revision_sent_has_terms` applies to new and edited rows only. Once the old rows are priced or removed, finish it with `ALTER TABLE change_order_revision VALIDATE CONSTRAINT change_order_revision_sent_has_terms;`
- The app needs rows that no migration creates: a company, its projects (the prototype uses the slugs `north-park`, `harbor` and `cedar`), and one user for each person who submits, reviews, authorizes or approves, including a `gc` user with an email address.

## Adding a migration

- Never edit a file that has been applied anywhere. Add the next number.
- Change `backend/db/models.py` in the same pull request, so the models and the tables stay the same.
- Wrap the file in `BEGIN; ... COMMIT;`, check the starting state, and end by inserting the file's name into `schema_migration`.
- No drop, truncate or reset against the shared project outside a reviewed migration. A migration that drops a table checks first that the table is the one it expects and that it is empty, as `0000` does.

## How these files were checked

They have not been run against Supabase. They were run against a throwaway in-memory PostgreSQL (PGlite, PostgreSQL 18; the Supabase project may run a different major version) on:

- the October tables present and empty, which is what Supabase holds: `0000` drops them, `0001` creates the baseline, `0002` gives schema v2
- the October tables with one row in any one of them: `0000` stops and leaves the tables and the row as they were
- an empty database, and Nov 3 tables with and without rows: `0000` changes nothing
- October tables next to newer tables, an October table with an unexpected column, one October table missing, and a view that depends on one: `0000` stops each time
- a second run of each file, `0001` without `0000` on the October tables, `0002` without `0001`, and a failure half way through `0002`

After `0002`, the columns, constraints and indexes were compared with the ones `create_all()` produces from the v2 models, and they match.

## From the prototype store to schema v2

The prototype in `backend/services/store.py` keeps everything in one JSON snapshot. This section says where each piece goes in schema v2. It is the contract for the repository layer (B3) and for moving the routes onto it (J4).

Every query filters by `company_id`. Start from `db.database.company_select()`.

### Statuses

| Prototype status | Schema v2 status |
| --- | --- |
| `submitted` | `submitted` |
| `awaiting_client` | `awaiting_gc` |
| `approved`, set by the approver | `approved` |
| `approved`, set by office review of a high-priority change with no approver | `authorized_to_proceed`, and only when a manager authorizes it. It becomes `awaiting_gc` when the estimate is sent, and `approved` only when the GC approves. |
| `rejected` | `declined` |
| none | `in_review` (the estimator has started), `withdrawn` |

### Fields of a change

| Prototype field | Schema v2 |
| --- | --- |
| `id` (UUID text) | `change_event.id` (integer) |
| `code` (`CO-1049`) | `"CO-"` + `change_event.number`. The number is unique in the company; take the highest plus one in the same transaction as the insert. |
| `title` | `change_event.title` |
| `description` | `change_event.description`. The original report; never overwritten. |
| `severity` | `change_event.severity` |
| `status` | `change_event.status`, with the mapping above |
| `photo_keys` | one `photo` row per key (`photo.storage_key`), in `photo.id` order |
| `project_id` (`north-park`) | `change_event.project_id`, found through `project.slug` |
| `submitted_by`, `author` | `change_event.submitted_by_id`; `author` is that user's `name` |
| `created_at` | `change_event.created_at` |
| `amount` (dollars) | `change_order_revision.proposed_cost_cents` (dollars times 100, as an integer) with `currency`. 0 while no revision exists. |
| `impact_days` | `change_order_revision.requested_timeline_days` |
| `approved_scope` | `change_order_revision.scope`, the reviewed wording |
| `sent_for_approval` | true when the change's latest revision has `frozen_at` set |
| `history[]` | `change_history` rows: `kind` is `status`, `title` is `title`, `person` is `actor_name` (with `actor_user_id` when a user did it), `time` is `created_at` |
| `suggestion` | the newest `ai_suggestion` row: `scope` is `suggested_scope`, `amount` is `suggested_cost_cents`, `impact_days` is `suggested_timeline_days`, plus `rationale` and `in_scope` |
| `original_scope` | `ai_suggestion.original_scope` |

A change has at most one `change_order`. Each review writes a new `change_order_revision` with the next `revision_number`; the latest one holds the current terms.

### Functions and routes

| Prototype | Reads | Writes |
| --- | --- | --- |
| `store.atomic()` | none | No table. One database transaction: everything in a row of this table commits together or not at all. |
| `store.create_change()` | `project` (by slug), `user` (the submitter; the estimators to alert), highest `change_event.number` | `change_event`, `photo`, `change_history` (`submitted`), `notifications` (`change_submitted`, one per estimator, and per manager when high priority) |
| `store.add_event()` | none | `change_history` |
| `store.notify()` | `user` (the recipients) | `notifications`: `type`, `message`, `link_target`. One row per recipient user. |
| `store.issue_client_token()` | `approval_request`, earlier `approval_link` rows for it | `approval_link` with the SHA-256 hex digest of the token and an `expires_at`. Set `revoked_at` on the earlier link first; only one unrevoked link per request is allowed. The token itself is returned once and stored nowhere. |
| `store.change_for_token()` | `approval_link` by `token_hash`, with `revoked_at` empty and `expires_at` in the future, then `approval_request`, `change_order_revision`, `change_order`, `change_event`, `photo`, `change_history` | none. Opening a link never changes anything. |
| `store.work_order()` | `project`, `change_event`, `change_order`, `change_order_revision`, `approval_decision`, `photo` (query below) | none |
| `GET /changes` (reads `store.CHANGES`) | `change_event`, `photo`, `change_history`, latest `change_order_revision`, newest `ai_suggestion` | none |
| `POST /changes/{id}/admin-approve`, normal priority | `change_event`, `change_order`, `user` (the GC) | `change_order` (if none yet), `change_order_revision` (scope, cents, days, `frozen_at`), `approval_request`, `approval_link`, `change_event.status` to `awaiting_gc`, `change_history`, `notifications` (`approval_requested`) |
| `POST /changes/{id}/admin-approve`, high priority | `change_event` | Not the prototype's immediate approval. The manager's authorization writes `change_event.status` to `authorized_to_proceed` with `authorized_by_id` and `authorized_at`, `change_history`, and `notifications` (`work_authorized`). The estimate then follows the normal-priority row. |
| `POST /approval-session/approve` and `/decline` | as `store.change_for_token()` | `approval_decision` (one per request; a retry fails on the unique `request_id`), `approval_request.status`, `change_event.status` to `approved` or `declined`, `change_history`, `notifications` (`change_approved` or `change_declined`) |
| `POST /changes/{id}/suggestion` | `change_event`, `photo` | `ai_suggestion` (a new row each time) |
| `GET /notifications` (reads `store.NOTIFICATIONS`) | `notifications` by `recipient_user_id` | none |
| `store.now()` | none | none. Use `db.models.utc_now()`. |

### The work order

A project's work order is not stored. It is the project's approved changes, each with the revision the GC approved, so a change can never be counted twice:

```sql
SELECT e.id AS change_id, e.number, e.title, r.scope,
       r.proposed_cost_cents, r.currency, r.requested_timeline_days
FROM change_event AS e
JOIN change_order AS o
  ON o.company_id = e.company_id AND o.change_event_id = e.id
JOIN change_order_revision AS r
  ON r.company_id = o.company_id AND r.change_order_id = o.id
JOIN approval_decision AS d
  ON d.company_id = r.company_id AND d.revision_id = r.id AND d.decision = 'approved'
WHERE e.company_id = :company_id
  AND e.project_id = :project_id
  AND e.status = 'approved'
ORDER BY d.decided_at, e.id;
```

The prototype's `revision` is the number of rows, `additional_amount` is the sum of `proposed_cost_cents`, and `additional_days` is the sum of `requested_timeline_days`. The photos of each change come from `photo`. `project.base_budget_cents` holds the contract amount before changes, once someone enters it.

### What does not map one to one

- **`submitted_by` as `contractor` or `subcontractor`.** Schema v2 has no such label; both are the `field` role. The change points at the user who submitted it.
- **The approval link in the client notification.** The prototype saves the full link, token included, as the notification message. Schema v2 refuses any notification whose message or link target contains `token=`. The token exists only in the email (or the console fallback) at the moment it is created.
- **Immediate approval of a high-priority change.** Schema v2 has no way to mark a change `approved` on the office's word alone that the work order would count: the work order needs a GC decision.
- **Links without an expiry.** `approval_link.expires_at` is required.
- **Notifications to a role.** The prototype addresses `admin`, `contractor` and `client`. Schema v2 addresses users, so the repository writes one row per recipient.
- **Ids.** Change ids are integers, not UUID text. History entries have their own integer id, not `<change id>-<status>`.
- **Project details in the app's sample data** (address, client name, progress, colours) are not stored. `project` holds the slug, the name and an optional base budget.
