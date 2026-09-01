CREATE TABLE project_corpus_pack_activations (
  activation_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project_identity(project_id) ON DELETE CASCADE,
  pack_fingerprint TEXT NOT NULL REFERENCES corpus_source_free_packs(pack_fingerprint) ON DELETE RESTRICT,
  version INTEGER NOT NULL CHECK(version >= 1),
  applicability_json TEXT NOT NULL CHECK(json_valid(applicability_json) = 1),
  authorization_json TEXT NOT NULL CHECK(json_valid(authorization_json) = 1),
  authorization_fingerprint TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK(state IN ('active','inactive')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(project_id,pack_fingerprint,version)
);

CREATE UNIQUE INDEX project_corpus_pack_one_active_idx
ON project_corpus_pack_activations(project_id,pack_fingerprint) WHERE state='active';
