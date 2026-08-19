ALTER TABLE independent_review_attempts
  ADD COLUMN processing_epoch INTEGER NOT NULL DEFAULT 0;

ALTER TABLE independent_review_attempts
  ADD COLUMN processing_expires_at REAL;

ALTER TABLE independent_review_attempts
  ADD COLUMN processing_phase TEXT
  CHECK(processing_phase IS NULL OR processing_phase IN ('reserved','effects_started'));

DROP INDEX independent_review_leases_run_idx;
DROP INDEX independent_review_one_active_lease_idx;
DROP INDEX independent_review_lifecycle_lease_idx;

ALTER TABLE independent_review_lifecycle_events
  RENAME TO independent_review_lifecycle_events_legacy_provider;
ALTER TABLE independent_review_leases
  RENAME TO independent_review_leases_legacy_provider;

CREATE TABLE independent_review_leases (
  lease_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  candidate_fingerprint TEXT NOT NULL,
  job_id TEXT NOT NULL,
  input_fingerprint TEXT NOT NULL,
  packet_bytes BLOB NOT NULL,
  packet_fingerprint TEXT NOT NULL,
  relay_nonce TEXT NOT NULL,
  provider TEXT NOT NULL CHECK(provider IN ('codex_native_subagent','claude_native_subagent')),
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

INSERT INTO independent_review_leases(
  lease_id,project_id,run_id,candidate_fingerprint,job_id,input_fingerprint,
  packet_bytes,packet_fingerprint,relay_nonce,provider,transport,assurance_class,
  parent_session_id,reviewer_session_id,agent_type,host_agent_id,host_invocation_id,
  completion_event_json,completion_result_fingerprint,status,result_fingerprint,
  receipt_json,receipt_fingerprint,infrastructure_error_json,created_at,claimed_at,
  completed_at,updated_at
)
SELECT
  lease_id,project_id,run_id,candidate_fingerprint,job_id,input_fingerprint,
  packet_bytes,packet_fingerprint,relay_nonce,
  CASE provider
    WHEN 'codex' THEN 'codex_native_subagent'
    WHEN 'claude' THEN 'claude_native_subagent'
    ELSE provider
  END,
  transport,assurance_class,parent_session_id,reviewer_session_id,agent_type,
  host_agent_id,host_invocation_id,completion_event_json,
  completion_result_fingerprint,status,result_fingerprint,receipt_json,
  receipt_fingerprint,infrastructure_error_json,created_at,claimed_at,completed_at,
  updated_at
FROM independent_review_leases_legacy_provider;

CREATE INDEX independent_review_leases_run_idx
  ON independent_review_leases(run_id, candidate_fingerprint, status, created_at);
CREATE UNIQUE INDEX independent_review_one_active_lease_idx
  ON independent_review_leases(run_id, candidate_fingerprint)
  WHERE status IN ('pending','claimed');

CREATE TABLE independent_review_lifecycle_events (
  event_id TEXT PRIMARY KEY,
  lease_id TEXT NOT NULL REFERENCES independent_review_leases(lease_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  event_kind TEXT NOT NULL CHECK(event_kind IN ('prepared','claimed','completed','infrastructure_failed')),
  event_fingerprint TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

INSERT INTO independent_review_lifecycle_events(
  event_id,lease_id,run_id,event_kind,event_fingerprint,payload_json,created_at
)
SELECT event_id,lease_id,run_id,event_kind,event_fingerprint,payload_json,created_at
FROM independent_review_lifecycle_events_legacy_provider;

CREATE INDEX independent_review_lifecycle_lease_idx
  ON independent_review_lifecycle_events(lease_id, created_at);

DROP TABLE independent_review_lifecycle_events_legacy_provider;
DROP TABLE independent_review_leases_legacy_provider;
