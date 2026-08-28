CREATE TABLE IF NOT EXISTS publication_collection_attempts (
  build_id TEXT PRIMARY KEY,
  identity_fingerprint TEXT NOT NULL UNIQUE,
  project_id TEXT NOT NULL,
  source_acceptance_ids_json TEXT NOT NULL,
  format TEXT NOT NULL CHECK(format IN ('md','txt')),
  compiler_contract TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  artifact_fingerprint TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK(byte_size >= 0),
  stage_ref TEXT NOT NULL,
  final_ref TEXT NOT NULL,
  owner_token TEXT NOT NULL,
  stage_dev INTEGER,
  stage_ino INTEGER,
  final_dev INTEGER,
  final_ino INTEGER,
  state TEXT NOT NULL CHECK(state IN ('staged','published','committed','failed')),
  error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publication_collection_members (
  build_id TEXT NOT NULL REFERENCES publication_collection_attempts(build_id) ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
  acceptance_id TEXT NOT NULL REFERENCES acceptance_evidence(acceptance_id) ON DELETE RESTRICT,
  PRIMARY KEY(build_id, ordinal),
  UNIQUE(build_id, acceptance_id)
);

CREATE TABLE IF NOT EXISTS publication_collection_builds (
  build_id TEXT PRIMARY KEY REFERENCES publication_collection_attempts(build_id) ON DELETE RESTRICT,
  source_acceptance_ids_json TEXT NOT NULL,
  format TEXT NOT NULL CHECK(format IN ('md','txt')),
  compiler_contract TEXT NOT NULL,
  output_ref TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  validation_json TEXT NOT NULL,
  persistent INTEGER NOT NULL CHECK(persistent = 1),
  created_at TEXT NOT NULL,
  UNIQUE(source_acceptance_ids_json, format, source_fingerprint, compiler_contract)
);

CREATE TABLE IF NOT EXISTS publication_collection_requests (
  idempotency_key TEXT PRIMARY KEY,
  request_fingerprint TEXT NOT NULL,
  build_id TEXT NOT NULL REFERENCES publication_collection_attempts(build_id) DEFERRABLE INITIALLY DEFERRED,
  created_at TEXT NOT NULL
);
