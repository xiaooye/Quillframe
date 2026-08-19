ALTER TABLE independent_review_attempts
  ADD COLUMN processing_epoch INTEGER NOT NULL DEFAULT 0;

ALTER TABLE independent_review_attempts
  ADD COLUMN processing_expires_at REAL;

ALTER TABLE independent_review_attempts
  ADD COLUMN processing_phase TEXT
  CHECK(processing_phase IS NULL OR processing_phase IN ('reserved','effects_started'));

-- Released v9 did not forbid multiple PASS rows for one run.  Preserve those
-- historical facts during migration, while preventing any new second PASS.
CREATE TRIGGER production_candidate_one_pass_per_run_insert
BEFORE INSERT ON candidates
WHEN NEW.run_id IS NOT NULL
  AND NEW.user_visible_gate='PASS'
  AND EXISTS (
    SELECT 1 FROM candidates
    WHERE run_id=NEW.run_id AND user_visible_gate='PASS'
  )
BEGIN
  SELECT RAISE(ABORT, 'production run already has a PASS candidate');
END;

CREATE TRIGGER production_candidate_one_pass_per_run_update
BEFORE UPDATE OF run_id, user_visible_gate ON candidates
WHEN NEW.run_id IS NOT NULL
  AND NEW.user_visible_gate='PASS'
  AND EXISTS (
    SELECT 1 FROM candidates
    WHERE run_id=NEW.run_id
      AND user_visible_gate='PASS'
      AND candidate_id<>OLD.candidate_id
  )
BEGIN
  SELECT RAISE(ABORT, 'production run already has a PASS candidate');
END;
