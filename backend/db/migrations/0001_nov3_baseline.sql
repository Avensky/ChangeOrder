-- 0001_nov3_baseline.sql
--
-- Brings a database to the Nov 3 schema (commit 4698664), the starting point
-- for 0002_schema_v2.sql, and starts the schema_migration record.
--
--   * Empty database: creates the seven Nov 3 tables, exactly as
--     SQLModel.metadata.create_all() would have.
--   * Nov 3 tables already there: changes nothing, only records the baseline.
--   * Anything else (some tables missing, or tables in another shape):
--     stops with an error and changes nothing.
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
    found INTEGER;
    is_nov3 BOOLEAN;
BEGIN
    IF EXISTS (SELECT 1 FROM schema_migration WHERE version = '0001_nov3_baseline') THEN
        RAISE EXCEPTION '0001_nov3_baseline is already applied to this database.';
    END IF;

    SELECT count(*) INTO found
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('user', 'change_event', 'change_order', 'change_order_revision',
                         'approval_request', 'approval_decision', 'notifications');

    -- Columns that exist only in the Nov 3 shape of these tables.
    SELECT count(*) = 3 INTO is_nov3
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND (table_name, column_name) IN (('change_event', 'contractor_id'),
                                        ('change_order', 'status'),
                                        ('approval_request', 'client_id'));

    IF found = 7 AND is_nov3 THEN
        RAISE NOTICE 'The Nov 3 tables already exist. Recording the baseline only.';
    ELSIF found = 0 THEN
        CREATE TABLE "user" (
            id SERIAL NOT NULL,
            role VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            phone VARCHAR,
            PRIMARY KEY (id),
            CONSTRAINT user_role_valid CHECK (role IN ('contractor', 'admin', 'client'))
        );
        CREATE INDEX ix_user_name ON "user" (name);
        CREATE INDEX ix_user_phone ON "user" (phone);

        CREATE TABLE change_event (
            id SERIAL NOT NULL,
            contractor_id INTEGER NOT NULL,
            description VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            photo_key VARCHAR,
            status VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT change_event_severity_valid CHECK (severity IN ('normal', 'high')),
            CONSTRAINT change_event_status_valid
                CHECK (status IN ('submitted', 'office_review', 'needs_information', 'resolved')),
            FOREIGN KEY (contractor_id) REFERENCES "user" (id)
        );
        CREATE INDEX ix_change_event_contractor_id ON change_event (contractor_id);
        CREATE INDEX ix_change_event_status ON change_event (status);

        CREATE TABLE change_order (
            id SERIAL NOT NULL,
            change_event_id INTEGER NOT NULL,
            status VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT change_order_status_valid
                CHECK (status IN ('draft', 'awaiting_client', 'approved', 'declined', 'withdrawn')),
            FOREIGN KEY (change_event_id) REFERENCES change_event (id)
        );
        CREATE UNIQUE INDEX ix_change_order_change_event_id ON change_order (change_event_id);
        CREATE INDEX ix_change_order_status ON change_order (status);

        CREATE TABLE notifications (
            id SERIAL NOT NULL,
            report_id INTEGER NOT NULL,
            recipient_user_id INTEGER NOT NULL,
            type VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id),
            CONSTRAINT notification_type_valid
                CHECK (type IN ('report_submitted', 'approval_requested', 'report_approved', 'report_rejected')),
            CONSTRAINT notification_status_valid CHECK (status IN ('pending', 'sent')),
            FOREIGN KEY (report_id) REFERENCES change_event (id),
            FOREIGN KEY (recipient_user_id) REFERENCES "user" (id)
        );
        CREATE INDEX ix_notifications_recipient_user_id ON notifications (recipient_user_id);
        CREATE INDEX ix_notifications_report_id ON notifications (report_id);

        CREATE TABLE change_order_revision (
            id SERIAL NOT NULL,
            change_order_id INTEGER NOT NULL,
            revision_number INTEGER NOT NULL,
            title VARCHAR NOT NULL,
            reason VARCHAR NOT NULL,
            scope VARCHAR NOT NULL,
            frozen_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_order_revision_number UNIQUE (change_order_id, revision_number),
            FOREIGN KEY (change_order_id) REFERENCES change_order (id)
        );
        CREATE INDEX ix_change_order_revision_change_order_id ON change_order_revision (change_order_id);

        CREATE TABLE approval_request (
            id SERIAL NOT NULL,
            revision_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            status VARCHAR NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT approval_request_status_valid
                CHECK (status IN ('pending', 'approved', 'declined', 'expired', 'canceled')),
            FOREIGN KEY (revision_id) REFERENCES change_order_revision (id),
            FOREIGN KEY (client_id) REFERENCES "user" (id)
        );
        CREATE INDEX ix_approval_request_client_id ON approval_request (client_id);
        CREATE INDEX ix_approval_request_revision_id ON approval_request (revision_id);
        CREATE INDEX ix_approval_request_status ON approval_request (status);

        CREATE TABLE approval_decision (
            id SERIAL NOT NULL,
            request_id INTEGER NOT NULL,
            revision_id INTEGER NOT NULL,
            approved_by_id INTEGER NOT NULL,
            decision VARCHAR NOT NULL,
            decided_at TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT approval_decision_valid CHECK (decision IN ('approved', 'declined')),
            FOREIGN KEY (request_id) REFERENCES approval_request (id),
            FOREIGN KEY (revision_id) REFERENCES change_order_revision (id),
            FOREIGN KEY (approved_by_id) REFERENCES "user" (id)
        );
        CREATE INDEX ix_approval_decision_approved_by_id ON approval_decision (approved_by_id);
        CREATE UNIQUE INDEX ix_approval_decision_request_id ON approval_decision (request_id);
    ELSE
        RAISE EXCEPTION
            'Expected either no ChangeOrder tables or all seven Nov 3 tables, but found % of them (Nov 3 shape: %). Nothing was changed. See backend/db/migrations/README.md.',
            found, is_nov3;
    END IF;
END $$;

INSERT INTO schema_migration (version) VALUES ('0001_nov3_baseline');

COMMIT;
