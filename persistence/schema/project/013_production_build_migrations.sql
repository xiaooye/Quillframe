-- A frozen production request may cross a Framework build only through an
-- explicit, offline-regression-bound checkpoint migration. Original request
-- bytes and every activated request version remain append-only audit evidence.
CREATE TABLE IF NOT EXISTS production_verified_regression_receipts (
  receipt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  preview_fingerprint TEXT NOT NULL,
  from_request_fingerprint TEXT NOT NULL,
  to_request_fingerprint TEXT NOT NULL,
  from_build_fingerprint TEXT NOT NULL,
  to_build_fingerprint TEXT NOT NULL,
  confirmed_checkpoint_core_fingerprints_json TEXT NOT NULL,
  test_evidence_fingerprints_json TEXT NOT NULL,
  test_command_fingerprint TEXT NOT NULL,
  test_output_fingerprint TEXT NOT NULL,
  runner_kind TEXT NOT NULL CHECK(runner_kind = 'quillframe_offline_regression_runner'),
  status TEXT NOT NULL CHECK(status = 'passed'),
  receipt_json TEXT NOT NULL,
  receipt_fingerprint TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  UNIQUE(run_id, preview_fingerprint)
);

CREATE TABLE IF NOT EXISTS production_build_migrations (
  migration_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  from_request_fingerprint TEXT NOT NULL,
  to_request_fingerprint TEXT NOT NULL,
  from_build_fingerprint TEXT NOT NULL,
  to_build_fingerprint TEXT NOT NULL,
  regression_receipt_id TEXT NOT NULL REFERENCES production_verified_regression_receipts(receipt_id) ON DELETE RESTRICT,
  regression_receipt_fingerprint TEXT NOT NULL,
  confirmed_checkpoint_core_fingerprints_json TEXT NOT NULL,
  prior_run_status TEXT NOT NULL,
  from_request_version INTEGER NOT NULL CHECK(from_request_version >= 1),
  to_request_version INTEGER NOT NULL CHECK(to_request_version = from_request_version + 1),
  authorization_ref TEXT NOT NULL,
  migration_fingerprint TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  UNIQUE(run_id, to_request_fingerprint),
  UNIQUE(run_id, to_request_version)
);

CREATE TABLE IF NOT EXISTS production_execution_request_versions (
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK(version >= 1),
  request_fingerprint TEXT NOT NULL,
  request_json TEXT NOT NULL,
  framework_build_fingerprint TEXT NOT NULL,
  run_status_at_activation TEXT NOT NULL,
  activation_kind TEXT NOT NULL CHECK(activation_kind IN ('initial','framework_migration')),
  migration_id TEXT REFERENCES production_build_migrations(migration_id) ON DELETE RESTRICT,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  PRIMARY KEY(run_id, version),
  UNIQUE(run_id, request_fingerprint),
  CHECK((activation_kind = 'initial' AND migration_id IS NULL)
     OR (activation_kind = 'framework_migration' AND migration_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_production_build_migrations_run
  ON production_build_migrations(run_id, to_request_version);

CREATE INDEX IF NOT EXISTS idx_production_request_versions_run
  ON production_execution_request_versions(run_id, version);
