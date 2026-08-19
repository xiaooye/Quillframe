ALTER TABLE independent_review_attempts
  ADD COLUMN processing_epoch INTEGER NOT NULL DEFAULT 0;

ALTER TABLE independent_review_attempts
  ADD COLUMN processing_expires_at REAL;

ALTER TABLE independent_review_attempts
  ADD COLUMN processing_phase TEXT
  CHECK(processing_phase IS NULL OR processing_phase IN ('reserved','effects_started'));

CREATE UNIQUE INDEX production_candidate_one_per_run_idx
  ON candidates(run_id)
  WHERE run_id IS NOT NULL AND user_visible_gate='PASS';
