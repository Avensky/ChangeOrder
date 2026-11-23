-- 0003_ai_suggestion_v2.sql
--
-- Extends ai_suggestion for the Phase 2 AI prototype (task B9, week 2): the
-- cost as a range, the prompt version, and what the estimator did with the
-- suggestion (accepted, edited or dismissed, a 1 to 5 rating, who and when).
--
-- Runs in one transaction: if any statement fails, nothing is changed.
-- Do not run it against the shared Supabase project without Bona.
--
-- Existing rows are kept: every new column is empty for them, so an old
-- suggestion has no range and no response.

BEGIN;

DO $$
BEGIN
    IF to_regclass('public.ai_suggestion') IS NULL THEN
        RAISE EXCEPTION 'ai_suggestion does not exist: run 0001 and 0002 first. Nothing was changed.';
    END IF;
    IF EXISTS (SELECT 1 FROM schema_migration WHERE version = '0003_ai_suggestion_v2') THEN
        RAISE EXCEPTION '0003_ai_suggestion_v2 has already run. Nothing was changed.';
    END IF;
END
$$;

ALTER TABLE ai_suggestion
    ADD COLUMN suggested_cost_low_cents BIGINT,
    ADD COLUMN suggested_cost_high_cents BIGINT,
    ADD COLUMN prompt_version VARCHAR,
    ADD COLUMN response VARCHAR,
    ADD COLUMN rating INTEGER,
    ADD COLUMN responded_by_id INTEGER,
    ADD COLUMN responded_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE ai_suggestion
    ADD CONSTRAINT ai_suggestion_cost_range_valid CHECK (
        suggested_cost_low_cents IS NULL OR suggested_cost_high_cents IS NULL
        OR (suggested_cost_low_cents >= 0
            AND suggested_cost_low_cents <= suggested_cost_cents
            AND suggested_cost_cents <= suggested_cost_high_cents)),
    ADD CONSTRAINT ai_suggestion_cost_range_both_or_neither CHECK (
        (suggested_cost_low_cents IS NULL) = (suggested_cost_high_cents IS NULL)),
    ADD CONSTRAINT ai_suggestion_response_valid CHECK (
        response IS NULL OR response IN ('accepted', 'edited', 'dismissed')),
    ADD CONSTRAINT ai_suggestion_rating_valid CHECK (
        rating IS NULL OR (rating >= 1 AND rating <= 5)),
    ADD CONSTRAINT ai_suggestion_response_complete CHECK (
        (response IS NULL) = (responded_by_id IS NULL)
        AND (response IS NULL) = (responded_at IS NULL)),
    ADD CONSTRAINT ai_suggestion_rating_needs_response CHECK (
        rating IS NULL OR response IS NOT NULL),
    ADD CONSTRAINT fk_ai_suggestion_responded_by_id_company
        FOREIGN KEY (company_id, responded_by_id) REFERENCES "user" (company_id, id);

INSERT INTO schema_migration (version) VALUES ('0003_ai_suggestion_v2');

COMMIT;
