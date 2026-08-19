CREATE TABLE IF NOT EXISTS project_context_sources (
  stable_id TEXT PRIMARY KEY,
  source_path TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  object_type TEXT NOT NULL,
  authority_class TEXT NOT NULL,
  lifecycle TEXT NOT NULL,
  domain TEXT NOT NULL,
  allowed_stages_json TEXT NOT NULL,
  target_json TEXT NOT NULL,
  runtime_payload_json TEXT NOT NULL,
  manifest_fingerprint TEXT NOT NULL,
  projection_fingerprint TEXT NOT NULL,
  applied_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0)
);

CREATE INDEX IF NOT EXISTS project_context_sources_stage_idx
  ON project_context_sources(manifest_fingerprint, domain);

CREATE TABLE IF NOT EXISTS project_projection_receipts (
  projection_fingerprint TEXT PRIMARY KEY,
  manifest_fingerprint TEXT NOT NULL,
  source_universe_fingerprint TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('applied')),
  receipt_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0)
);

CREATE INDEX IF NOT EXISTS project_projection_receipts_manifest_idx
  ON project_projection_receipts(manifest_fingerprint, created_at);
