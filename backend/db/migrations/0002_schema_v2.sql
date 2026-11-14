-- 0002_schema_v2.sql
--
-- Moves a database from the Nov 3 schema (0001_nov3_baseline) to schema v2,
-- the schema in backend/db/models.py (task B2).
--
-- Runs in one transaction: if any statement fails, nothing is changed.
-- Read README.md in this folder before running it. Do not run it against the
-- shared Supabase project without Bona.
--
-- What happens to existing rows:
--   * Every row is put in one new company named 'Default company', and every
--     change in one new project named 'Default project'. Rename them
--     afterwards.
--   * Each change gets a number (1, 2, 3, ... in id order), a title (the
--     first 80 characters of its description) and one history entry for its
--     submission. Each notification gets a message that matches its type.
--   * Roles: contractor -> field, client -> gc, admin -> estimator.
--     'admin' covered both the estimator and the manager. This file picks
--     estimator, the role that cannot authorize work. Promote the right
--     people to manager by hand afterwards.
--   * Status: the change's one status is change_event.status. It is taken
--     from the change order when one exists (draft -> in_review,
--     awaiting_client -> awaiting_gc, approved/declined/withdrawn unchanged),
--     otherwise from the report (office_review and needs_information ->
--     in_review, resolved -> withdrawn). change_order.status is then dropped.
--   * change_event.photo_key becomes a row in photo; the column is dropped.
--   * Notification types: report_submitted -> change_submitted,
--     report_approved -> change_approved, report_rejected -> change_declined.

BEGIN;
SET LOCAL search_path TO public;

-- ---------------------------------------------------------------------------
-- 0. Check the starting point
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF to_regclass('public.schema_migration') IS NULL THEN
        RAISE EXCEPTION 'Run 0001_nov3_baseline.sql first.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM schema_migration WHERE version = '0001_nov3_baseline') THEN
        RAISE EXCEPTION 'Run 0001_nov3_baseline.sql first.';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migration WHERE version = '0002_schema_v2') THEN
        RAISE EXCEPTION '0002_schema_v2 is already applied to this database.';
    END IF;
    IF to_regclass('public.company') IS NOT NULL
       OR to_regclass('public.project') IS NOT NULL
       OR to_regclass('public.photo') IS NOT NULL
       OR to_regclass('public.change_history') IS NOT NULL
       OR to_regclass('public.ai_suggestion') IS NOT NULL
       OR to_regclass('public.approval_link') IS NOT NULL THEN
        RAISE EXCEPTION 'A schema v2 table (company, project, photo, change_history, ai_suggestion or approval_link) already exists. Nothing was changed.';
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. Companies, and a company on every existing row
-- ---------------------------------------------------------------------------
CREATE TABLE company (
    id SERIAL NOT NULL,
    name VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX ix_company_name ON company (name);

-- Rows written before tenants existed all go to one company. With no users
-- there are no rows in any table, and no company is created.
INSERT INTO company (name, created_at)
SELECT 'Default company', now()
WHERE EXISTS (SELECT 1 FROM "user");

ALTER TABLE "user"                ADD COLUMN company_id INTEGER REFERENCES company (id);
ALTER TABLE change_event          ADD COLUMN company_id INTEGER REFERENCES company (id);
ALTER TABLE change_order          ADD COLUMN company_id INTEGER REFERENCES company (id);
ALTER TABLE change_order_revision ADD COLUMN company_id INTEGER REFERENCES company (id);
ALTER TABLE approval_request      ADD COLUMN company_id INTEGER REFERENCES company (id);
ALTER TABLE approval_decision     ADD COLUMN company_id INTEGER REFERENCES company (id);
ALTER TABLE notifications         ADD COLUMN company_id INTEGER REFERENCES company (id);

UPDATE "user"                SET company_id = (SELECT min(id) FROM company);
UPDATE change_event          SET company_id = (SELECT min(id) FROM company);
UPDATE change_order          SET company_id = (SELECT min(id) FROM company);
UPDATE change_order_revision SET company_id = (SELECT min(id) FROM company);
UPDATE approval_request      SET company_id = (SELECT min(id) FROM company);
UPDATE approval_decision     SET company_id = (SELECT min(id) FROM company);
UPDATE notifications         SET company_id = (SELECT min(id) FROM company);

ALTER TABLE "user"                ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE change_event          ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE change_order          ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE change_order_revision ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE approval_request      ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE approval_decision     ALTER COLUMN company_id SET NOT NULL;
ALTER TABLE notifications         ALTER COLUMN company_id SET NOT NULL;

-- (company_id, id) keys. Other tables reference these with two-column
-- foreign keys, so a row can only point at rows of its own company.
ALTER TABLE "user"                ADD CONSTRAINT uq_user_company_id_id UNIQUE (company_id, id);
ALTER TABLE change_event          ADD CONSTRAINT uq_change_event_company_id_id UNIQUE (company_id, id);
ALTER TABLE change_order          ADD CONSTRAINT uq_change_order_company_id_id UNIQUE (company_id, id);
ALTER TABLE change_order_revision ADD CONSTRAINT uq_change_order_revision_company_id_id UNIQUE (company_id, id);
ALTER TABLE approval_request      ADD CONSTRAINT uq_approval_request_company_id_id UNIQUE (company_id, id);

-- ---------------------------------------------------------------------------
-- 2. user: personas, email, Supabase account id
-- ---------------------------------------------------------------------------
ALTER TABLE "user" DROP CONSTRAINT user_role_valid;

UPDATE "user"
SET role = CASE role
               WHEN 'contractor' THEN 'field'
               WHEN 'client' THEN 'gc'
               WHEN 'admin' THEN 'estimator'  -- see the note at the top of this file
               ELSE role
           END;

ALTER TABLE "user"
    ADD COLUMN email VARCHAR,
    ADD COLUMN auth_user_id UUID,
    ADD CONSTRAINT user_role_valid CHECK (role IN ('field', 'estimator', 'manager', 'gc')),
    ADD CONSTRAINT user_gc_has_no_account CHECK (role <> 'gc' OR auth_user_id IS NULL),
    ADD CONSTRAINT uq_user_company_id_email UNIQUE (company_id, email);

CREATE UNIQUE INDEX ix_user_auth_user_id ON "user" (auth_user_id);
CREATE INDEX ix_user_company_id_role ON "user" (company_id, role);

-- ---------------------------------------------------------------------------
-- 3. project: the job a change belongs to
-- ---------------------------------------------------------------------------
-- A project's work order is not stored. It is the project's approved changes,
-- each with the revision the GC approved (query in README.md).
CREATE TABLE project (
    id SERIAL NOT NULL,
    company_id INTEGER NOT NULL,
    slug VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    base_budget_cents BIGINT,
    currency VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT project_currency_valid CHECK (length(currency) = 3 AND currency = upper(currency)),
    CONSTRAINT uq_project_company_id_id UNIQUE (company_id, id),
    CONSTRAINT uq_project_company_id_slug UNIQUE (company_id, slug),
    FOREIGN KEY (company_id) REFERENCES company (id)
);

-- Changes reported before projects existed all go to one project.
INSERT INTO project (company_id, slug, name, currency, created_at)
SELECT (SELECT min(id) FROM company), 'default', 'Default project', 'USD', now()
WHERE EXISTS (SELECT 1 FROM change_event);

-- ---------------------------------------------------------------------------
-- 4. change_event: project, number, title, the one status set, fast track
-- ---------------------------------------------------------------------------
ALTER TABLE change_event RENAME COLUMN contractor_id TO submitted_by_id;
ALTER INDEX ix_change_event_contractor_id RENAME TO ix_change_event_submitted_by_id;

ALTER TABLE change_event
    DROP CONSTRAINT change_event_contractor_id_fkey,
    DROP CONSTRAINT change_event_status_valid,
    ADD COLUMN project_id INTEGER,
    ADD COLUMN number INTEGER,
    ADD COLUMN title VARCHAR,
    ADD COLUMN authorized_by_id INTEGER,
    ADD COLUMN authorized_at TIMESTAMP WITH TIME ZONE;

UPDATE change_event AS e
SET project_id = (SELECT min(id) FROM project),
    title = left(e.description, 80),
    number = numbered.n
FROM (SELECT id, row_number() OVER (PARTITION BY company_id ORDER BY id) AS n
      FROM change_event) AS numbered
WHERE numbered.id = e.id;

ALTER TABLE change_event
    ALTER COLUMN project_id SET NOT NULL,
    ALTER COLUMN number SET NOT NULL,
    ALTER COLUMN title SET NOT NULL;

UPDATE change_event AS e
SET status = COALESCE(
    (SELECT CASE o.status
                WHEN 'draft' THEN 'in_review'
                WHEN 'awaiting_client' THEN 'awaiting_gc'
                ELSE o.status  -- approved, declined, withdrawn
            END
     FROM change_order AS o
     WHERE o.change_event_id = e.id),
    CASE e.status
        WHEN 'office_review' THEN 'in_review'
        WHEN 'needs_information' THEN 'in_review'
        WHEN 'resolved' THEN 'withdrawn'
        ELSE e.status  -- submitted
    END
);

ALTER TABLE change_event
    ADD CONSTRAINT change_event_status_valid
        CHECK (status IN ('submitted', 'in_review', 'authorized_to_proceed', 'awaiting_gc',
                          'approved', 'declined', 'withdrawn')),
    ADD CONSTRAINT change_event_authorization_complete
        CHECK ((authorized_by_id IS NULL) = (authorized_at IS NULL)),
    ADD CONSTRAINT change_event_authorization_high_priority_only
        CHECK (authorized_at IS NULL OR severity = 'high'),
    ADD CONSTRAINT change_event_authorized_status_needs_authorization
        CHECK (status <> 'authorized_to_proceed' OR authorized_at IS NOT NULL),
    ADD CONSTRAINT uq_change_event_company_id_number UNIQUE (company_id, number),
    ADD CONSTRAINT fk_change_event_project_id_company
        FOREIGN KEY (company_id, project_id) REFERENCES project (company_id, id),
    ADD CONSTRAINT fk_change_event_submitted_by_id_company
        FOREIGN KEY (company_id, submitted_by_id) REFERENCES "user" (company_id, id),
    ADD CONSTRAINT fk_change_event_authorized_by_id_company
        FOREIGN KEY (company_id, authorized_by_id) REFERENCES "user" (company_id, id);

DROP INDEX ix_change_event_status;
CREATE INDEX ix_change_event_company_id_status ON change_event (company_id, status);
CREATE INDEX ix_change_event_company_id_project_id ON change_event (company_id, project_id);

-- ---------------------------------------------------------------------------
-- 5. change_history: the timeline of a change
-- ---------------------------------------------------------------------------
CREATE TABLE change_history (
    id SERIAL NOT NULL,
    company_id INTEGER NOT NULL,
    change_event_id INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    actor_user_id INTEGER,
    actor_name VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT change_history_status_valid
        CHECK (status IN ('submitted', 'in_review', 'authorized_to_proceed', 'awaiting_gc',
                          'approved', 'declined', 'withdrawn')),
    CONSTRAINT fk_change_history_change_event_id_company
        FOREIGN KEY (company_id, change_event_id) REFERENCES change_event (company_id, id),
    CONSTRAINT fk_change_history_actor_user_id_company
        FOREIGN KEY (company_id, actor_user_id) REFERENCES "user" (company_id, id),
    FOREIGN KEY (company_id) REFERENCES company (id)
);
CREATE INDEX ix_change_history_company_id_change_event_id
    ON change_history (company_id, change_event_id);

-- The one event known for an old change: who submitted it, and when.
INSERT INTO change_history (company_id, change_event_id, status, title, actor_user_id, actor_name, created_at)
SELECT e.company_id, e.id, 'submitted', 'Change request submitted', u.id, u.name, e.created_at
FROM change_event AS e
JOIN "user" AS u ON u.id = e.submitted_by_id
ORDER BY e.id;

-- ---------------------------------------------------------------------------
-- 6. ai_suggestion: advisory estimates kept for the estimator
-- ---------------------------------------------------------------------------
CREATE TABLE ai_suggestion (
    id SERIAL NOT NULL,
    company_id INTEGER NOT NULL,
    change_event_id INTEGER NOT NULL,
    original_scope VARCHAR NOT NULL,
    suggested_scope VARCHAR NOT NULL,
    suggested_cost_cents BIGINT NOT NULL,
    currency VARCHAR NOT NULL,
    suggested_timeline_days INTEGER NOT NULL,
    rationale VARCHAR NOT NULL,
    in_scope BOOLEAN NOT NULL,
    model_id VARCHAR,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ai_suggestion_currency_valid CHECK (length(currency) = 3 AND currency = upper(currency)),
    CONSTRAINT ai_suggestion_cost_valid CHECK (suggested_cost_cents >= 0),
    CONSTRAINT ai_suggestion_timeline_valid CHECK (suggested_timeline_days >= 0),
    CONSTRAINT ai_suggestion_confidence_valid
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    CONSTRAINT fk_ai_suggestion_change_event_id_company
        FOREIGN KEY (company_id, change_event_id) REFERENCES change_event (company_id, id),
    FOREIGN KEY (company_id) REFERENCES company (id)
);
CREATE INDEX ix_ai_suggestion_company_id_change_event_id
    ON ai_suggestion (company_id, change_event_id);

-- ---------------------------------------------------------------------------
-- 7. photo: several photos per change
-- ---------------------------------------------------------------------------
CREATE TABLE photo (
    id SERIAL NOT NULL,
    company_id INTEGER NOT NULL,
    change_event_id INTEGER NOT NULL,
    storage_key VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_photo_change_event_id_company
        FOREIGN KEY (company_id, change_event_id) REFERENCES change_event (company_id, id),
    FOREIGN KEY (company_id) REFERENCES company (id)
);
CREATE INDEX ix_photo_company_id_change_event_id ON photo (company_id, change_event_id);
CREATE UNIQUE INDEX ix_photo_storage_key ON photo (storage_key);

INSERT INTO photo (company_id, change_event_id, storage_key, created_at)
SELECT company_id, id, photo_key, created_at
FROM change_event
WHERE photo_key IS NOT NULL AND photo_key <> ''
ORDER BY id;

ALTER TABLE change_event DROP COLUMN photo_key;

-- ---------------------------------------------------------------------------
-- 8. change_order: its status now lives on the change
-- ---------------------------------------------------------------------------
-- Dropping the column also drops ix_change_order_status and
-- change_order_status_valid.
ALTER TABLE change_order
    DROP COLUMN status,
    DROP CONSTRAINT change_order_change_event_id_fkey,
    ADD CONSTRAINT fk_change_order_change_event_id_company
        FOREIGN KEY (company_id, change_event_id) REFERENCES change_event (company_id, id);

-- ---------------------------------------------------------------------------
-- 9. change_order_revision: proposed cost and requested timeline
-- ---------------------------------------------------------------------------
ALTER TABLE change_order_revision
    ADD COLUMN proposed_cost_cents BIGINT,
    ADD COLUMN currency VARCHAR,
    ADD COLUMN requested_timeline_days INTEGER;

UPDATE change_order_revision SET currency = 'USD';

ALTER TABLE change_order_revision
    ALTER COLUMN currency SET NOT NULL,
    -- The review form has scope, cost and days only; title and reason are optional.
    ALTER COLUMN title DROP NOT NULL,
    ALTER COLUMN reason DROP NOT NULL,
    DROP CONSTRAINT change_order_revision_change_order_id_fkey,
    ADD CONSTRAINT change_order_revision_currency_valid
        CHECK (length(currency) = 3 AND currency = upper(currency)),
    ADD CONSTRAINT change_order_revision_timeline_valid
        CHECK (requested_timeline_days >= 0),
    ADD CONSTRAINT fk_change_order_revision_change_order_id_company
        FOREIGN KEY (company_id, change_order_id) REFERENCES change_order (company_id, id);

-- A sent (frozen) revision must carry cost and timeline. Revisions sent under
-- the Nov 3 schema have neither, so the rule is added without checking old
-- rows, then checked in full only when no old row breaks it. Either way it
-- applies to every row written from now on.
ALTER TABLE change_order_revision
    ADD CONSTRAINT change_order_revision_sent_has_terms
        CHECK (frozen_at IS NULL
               OR (proposed_cost_cents IS NOT NULL AND requested_timeline_days IS NOT NULL))
        NOT VALID;

DO $$
DECLARE
    old_sent INTEGER;
BEGIN
    SELECT count(*) INTO old_sent FROM change_order_revision WHERE frozen_at IS NOT NULL;
    IF old_sent = 0 THEN
        ALTER TABLE change_order_revision VALIDATE CONSTRAINT change_order_revision_sent_has_terms;
    ELSE
        RAISE NOTICE '% revision(s) sent before v2 have no cost or timeline. change_order_revision_sent_has_terms is left NOT VALID for them.', old_sent;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 10. approval_request: the GC, not the "client"
-- ---------------------------------------------------------------------------
ALTER TABLE approval_request RENAME COLUMN client_id TO gc_user_id;
ALTER INDEX ix_approval_request_client_id RENAME TO ix_approval_request_gc_user_id;

ALTER TABLE approval_request
    DROP CONSTRAINT approval_request_revision_id_fkey,
    DROP CONSTRAINT approval_request_client_id_fkey,
    ADD CONSTRAINT fk_approval_request_revision_id_company
        FOREIGN KEY (company_id, revision_id) REFERENCES change_order_revision (company_id, id),
    ADD CONSTRAINT fk_approval_request_gc_user_id_company
        FOREIGN KEY (company_id, gc_user_id) REFERENCES "user" (company_id, id);

-- ---------------------------------------------------------------------------
-- 11. approval_link: the emailed GC link, token hash only
-- ---------------------------------------------------------------------------
CREATE TABLE approval_link (
    id SERIAL NOT NULL,
    company_id INTEGER NOT NULL,
    approval_request_id INTEGER NOT NULL,
    token_hash VARCHAR NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    -- A SHA-256 hex digest is 64 characters; the raw token is shorter.
    CONSTRAINT approval_link_token_hash_is_sha256 CHECK (length(token_hash) = 64),
    CONSTRAINT fk_approval_link_approval_request_id_company
        FOREIGN KEY (company_id, approval_request_id) REFERENCES approval_request (company_id, id),
    FOREIGN KEY (company_id) REFERENCES company (id)
);
CREATE INDEX ix_approval_link_company_id_approval_request_id
    ON approval_link (company_id, approval_request_id);
CREATE UNIQUE INDEX ix_approval_link_token_hash ON approval_link (token_hash);
-- At most one link per request that has not been revoked.
CREATE UNIQUE INDEX uq_approval_link_live_request
    ON approval_link (approval_request_id) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- 12. approval_decision
-- ---------------------------------------------------------------------------
ALTER TABLE approval_decision RENAME COLUMN approved_by_id TO decided_by_id;
ALTER INDEX ix_approval_decision_approved_by_id RENAME TO ix_approval_decision_decided_by_id;

ALTER TABLE approval_decision
    DROP CONSTRAINT approval_decision_request_id_fkey,
    DROP CONSTRAINT approval_decision_revision_id_fkey,
    DROP CONSTRAINT approval_decision_approved_by_id_fkey,
    ADD CONSTRAINT fk_approval_decision_request_id_company
        FOREIGN KEY (company_id, request_id) REFERENCES approval_request (company_id, id),
    ADD CONSTRAINT fk_approval_decision_revision_id_company
        FOREIGN KEY (company_id, revision_id) REFERENCES change_order_revision (company_id, id),
    ADD CONSTRAINT fk_approval_decision_decided_by_id_company
        FOREIGN KEY (company_id, decided_by_id) REFERENCES "user" (company_id, id);

CREATE INDEX ix_approval_decision_company_id ON approval_decision (company_id);

-- ---------------------------------------------------------------------------
-- 13. notifications: message text, link target, one type per status
-- ---------------------------------------------------------------------------
ALTER TABLE notifications
    DROP CONSTRAINT notification_type_valid,
    DROP CONSTRAINT notifications_report_id_fkey,
    DROP CONSTRAINT notifications_recipient_user_id_fkey,
    ADD COLUMN message VARCHAR,
    ADD COLUMN link_target VARCHAR;

UPDATE notifications
SET type = CASE type
               WHEN 'report_submitted' THEN 'change_submitted'
               WHEN 'report_approved' THEN 'change_approved'
               WHEN 'report_rejected' THEN 'change_declined'
               ELSE type  -- approval_requested
           END;

-- Old rows had no text. Give each the line that matches its type.
UPDATE notifications
SET message = CASE type
                  WHEN 'change_submitted' THEN 'New change order submitted'
                  WHEN 'approval_requested' THEN 'Sent to the GC for approval'
                  WHEN 'change_approved' THEN 'Change approved'
                  WHEN 'change_declined' THEN 'Change declined'
              END;

ALTER TABLE notifications
    ALTER COLUMN message SET NOT NULL,
    -- The GC token exists only in the email. It must never be saved here.
    ADD CONSTRAINT notification_holds_no_token
        CHECK (message NOT LIKE '%token=%'
               AND (link_target IS NULL OR link_target NOT LIKE '%token=%')),
    ADD CONSTRAINT notification_type_valid
        CHECK (type IN ('change_submitted', 'change_in_review', 'work_authorized',
                        'approval_requested', 'change_approved', 'change_declined',
                        'change_withdrawn')),
    ADD CONSTRAINT fk_notifications_report_id_company
        FOREIGN KEY (company_id, report_id) REFERENCES change_event (company_id, id),
    ADD CONSTRAINT fk_notifications_recipient_user_id_company
        FOREIGN KEY (company_id, recipient_user_id) REFERENCES "user" (company_id, id);

DROP INDEX ix_notifications_recipient_user_id;
CREATE INDEX ix_notifications_company_id_recipient_user_id
    ON notifications (company_id, recipient_user_id);

-- ---------------------------------------------------------------------------
-- 14. Close the tables to Supabase's public Data API
-- ---------------------------------------------------------------------------
-- Supabase serves every table in the public schema over its REST API to
-- anyone holding the project's anon key, unless row level security is on.
-- With it on and no policies, only the backend's own database connection
-- (the table owner) can read or write these tables. The app talks to the
-- backend, never to the database, so nothing else should need access.
ALTER TABLE company               ENABLE ROW LEVEL SECURITY;
ALTER TABLE "user"                ENABLE ROW LEVEL SECURITY;
ALTER TABLE project               ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_event          ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_history        ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_suggestion         ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_order          ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_order_revision ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_request      ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_link         ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_decision     ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications         ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_migration      ENABLE ROW LEVEL SECURITY;

INSERT INTO schema_migration (version) VALUES ('0002_schema_v2');

COMMIT;
