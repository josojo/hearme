-- Add the per-question options list. Default ['yes','no'] so every existing
-- yes/no question becomes a valid 2-option poll automatically; the broker's
-- aggregate tally shape `{label: count, ...}` is already a superset of the
-- old `{yes:N,no:M}` shape, so historical aggregates remain valid.
--
-- IF NOT EXISTS / pg_constraint guards make this script idempotent — safe to
-- re-run, and safe to apply to a fresh volume that already saw 0000_init.sql.

ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '["yes","no"]'::jsonb;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'questions_options_chk'
      AND conrelid = 'questions'::regclass
  ) THEN
    ALTER TABLE questions
      ADD CONSTRAINT questions_options_chk CHECK (
        jsonb_typeof(options) = 'array'
        AND jsonb_array_length(options) BETWEEN 2 AND 8
      );
  END IF;
END $$;
