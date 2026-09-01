CREATE TABLE project_preference_activations (
  hypothesis_id TEXT PRIMARY KEY REFERENCES project_preference_hypotheses(hypothesis_id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK(version >= 1),
  state TEXT NOT NULL CHECK(state IN ('active','inactive')),
  authorized_by TEXT NOT NULL,
  authorization_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE TABLE preference_activation_receipts (
  receipt_id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES project_preference_hypotheses(hypothesis_id) ON DELETE CASCADE,
  expected_version INTEGER NOT NULL CHECK(expected_version >= 0),
  resulting_version INTEGER NOT NULL CHECK(resulting_version = expected_version + 1),
  resulting_state TEXT NOT NULL CHECK(resulting_state IN ('active','inactive')),
  idempotency_key TEXT NOT NULL UNIQUE,
  authorization_json TEXT NOT NULL CHECK(json_valid(authorization_json)),
  authorization_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE INDEX preference_activation_state_idx
  ON project_preference_activations(state, updated_at, hypothesis_id);

CREATE TABLE learning_feedback_events (
  event_id TEXT PRIMARY KEY,
  feedback_text TEXT NOT NULL,
  evidence_kind TEXT NOT NULL,
  candidate_id TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  candidate_fingerprint TEXT,
  document_id TEXT REFERENCES documents(document_id) ON DELETE SET NULL,
  run_id TEXT REFERENCES runs(run_id) ON DELETE SET NULL,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  payload_fingerprint TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('captured','interpreted','skipped','rejected')),
  hypothesis_id TEXT REFERENCES project_preference_hypotheses(hypothesis_id) ON DELETE SET NULL,
  version INTEGER NOT NULL CHECK(version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE TABLE learning_feedback_interpretations (
  event_id TEXT PRIMARY KEY REFERENCES learning_feedback_events(event_id) ON DELETE CASCADE,
  result_fingerprint TEXT NOT NULL,
  interpretation_json TEXT NOT NULL CHECK(json_valid(interpretation_json)),
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE TABLE preference_review_heads (
  hypothesis_id TEXT PRIMARY KEY REFERENCES project_preference_hypotheses(hypothesis_id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK(version >= 1),
  decision TEXT NOT NULL CHECK(decision IN ('candidate','validated','contested')),
  review_fingerprint TEXT,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE TABLE learning_semantic_calls (
  call_id TEXT PRIMARY KEY,
  aggregate_id TEXT NOT NULL,
  stage_key TEXT NOT NULL,
  request_id TEXT NOT NULL UNIQUE,
  input_fingerprint TEXT NOT NULL,
  request_json TEXT NOT NULL CHECK(json_valid(request_json)),
  state TEXT NOT NULL CHECK(state IN ('dispatched','confirmed','unconfirmed')),
  result_json TEXT,
  result_fingerprint TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(aggregate_id, stage_key),
  CHECK((state='confirmed' AND result_json IS NOT NULL AND result_fingerprint IS NOT NULL)
     OR (state!='confirmed' AND result_json IS NULL AND result_fingerprint IS NULL))
);
