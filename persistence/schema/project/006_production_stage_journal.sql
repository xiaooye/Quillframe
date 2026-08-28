CREATE TABLE IF NOT EXISTS production_executions (
  run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
  request_fingerprint TEXT NOT NULL,
  request_json TEXT NOT NULL,
  owner_token TEXT,
  lease_expires_at_ms INTEGER,
  cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE TABLE IF NOT EXISTS production_stage_calls (
  call_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  stage_key TEXT NOT NULL,
  runtime_role TEXT NOT NULL,
  input_fingerprint TEXT NOT NULL,
  job_json TEXT NOT NULL,
  owner_token TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('dispatched','confirmed','unconfirmed','cancelled')),
  deadline_at_ms INTEGER NOT NULL,
  result_json TEXT,
  result_fingerprint TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  UNIQUE(run_id, stage_key),
  CHECK((state = 'confirmed' AND result_json IS NOT NULL AND result_fingerprint IS NOT NULL)
     OR (state != 'confirmed' AND result_json IS NULL AND result_fingerprint IS NULL))
);
CREATE INDEX IF NOT EXISTS production_stage_calls_run_state_idx
  ON production_stage_calls(run_id, state, created_at);
