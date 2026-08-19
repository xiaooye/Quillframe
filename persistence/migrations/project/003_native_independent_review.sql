CREATE TABLE IF NOT EXISTS independent_review_attempts (
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  candidate_fingerprint TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('available','processing','terminal')),
  processing_token TEXT,
  processing_evidence_fingerprint TEXT,
  processing_transport TEXT,
  terminal_evidence_fingerprint TEXT,
  terminal_response_json TEXT,
  terminal_response_fingerprint TEXT,
  terminal_status TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(run_id, candidate_fingerprint),
  CHECK(
    (status='available' AND processing_token IS NULL AND terminal_response_json IS NULL)
    OR (status='processing' AND processing_token IS NOT NULL AND processing_evidence_fingerprint IS NOT NULL AND terminal_response_json IS NULL)
    OR (status='terminal' AND processing_token IS NULL AND terminal_evidence_fingerprint IS NOT NULL AND terminal_response_json IS NOT NULL)
  )
);

CREATE TABLE IF NOT EXISTS independent_review_leases (
  lease_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  candidate_fingerprint TEXT NOT NULL,
  job_id TEXT NOT NULL,
  input_fingerprint TEXT NOT NULL,
  packet_bytes BLOB NOT NULL,
  packet_fingerprint TEXT NOT NULL,
  relay_nonce TEXT NOT NULL,
  provider TEXT NOT NULL CHECK(provider IN ('codex','claude')),
  transport TEXT NOT NULL CHECK(transport IN ('codex_native','claude_code_native')),
  assurance_class TEXT NOT NULL CHECK(assurance_class='host_native_separate_context'),
  parent_session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
  reviewer_session_id TEXT REFERENCES sessions(session_id) ON DELETE RESTRICT,
  agent_type TEXT,
  host_agent_id TEXT UNIQUE,
  host_invocation_id TEXT UNIQUE,
  completion_event_json TEXT,
  completion_result_fingerprint TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','claimed','completed','infrastructure_failed')),
  result_fingerprint TEXT,
  receipt_json TEXT,
  receipt_fingerprint TEXT,
  infrastructure_error_json TEXT,
  created_at TEXT NOT NULL,
  claimed_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(run_id, candidate_fingerprint)
    REFERENCES independent_review_attempts(run_id, candidate_fingerprint)
    ON DELETE CASCADE,
  CHECK(parent_session_id <> COALESCE(reviewer_session_id, '')),
  CHECK(
    (status='pending' AND reviewer_session_id IS NULL AND host_agent_id IS NULL AND host_invocation_id IS NULL AND completion_event_json IS NULL)
    OR (status='claimed' AND reviewer_session_id IS NOT NULL AND host_agent_id IS NOT NULL AND host_invocation_id IS NOT NULL)
    OR (status='completed' AND reviewer_session_id IS NOT NULL AND completion_event_json IS NOT NULL AND completion_result_fingerprint=result_fingerprint AND result_fingerprint IS NOT NULL AND receipt_json IS NOT NULL AND receipt_fingerprint IS NOT NULL)
    OR (status='infrastructure_failed' AND infrastructure_error_json IS NOT NULL)
  )
);
CREATE INDEX IF NOT EXISTS independent_review_leases_run_idx
  ON independent_review_leases(run_id, candidate_fingerprint, status, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS independent_review_one_active_lease_idx
  ON independent_review_leases(run_id, candidate_fingerprint)
  WHERE status IN ('pending','claimed');

CREATE TABLE IF NOT EXISTS independent_review_lifecycle_events (
  event_id TEXT PRIMARY KEY,
  lease_id TEXT NOT NULL REFERENCES independent_review_leases(lease_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  event_kind TEXT NOT NULL CHECK(event_kind IN ('prepared','claimed','completed','infrastructure_failed')),
  event_fingerprint TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS independent_review_lifecycle_lease_idx
  ON independent_review_lifecycle_events(lease_id, created_at);
