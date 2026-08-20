CREATE TABLE IF NOT EXISTS publication_build_attempts (
  build_id TEXT PRIMARY KEY,
  identity_fingerprint TEXT NOT NULL UNIQUE,
  project_id TEXT NOT NULL,
  source_acceptance_id TEXT NOT NULL REFERENCES acceptance_evidence(acceptance_id) ON DELETE RESTRICT,
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

CREATE UNIQUE INDEX IF NOT EXISTS publication_build_attempts_source_identity_uq
ON publication_build_attempts(source_acceptance_id, format, source_fingerprint, compiler_contract);

CREATE UNIQUE INDEX IF NOT EXISTS publication_builds_source_identity_uq
ON publication_builds(source_acceptance_id, format, source_fingerprint, compiler_contract);
