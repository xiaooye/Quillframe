CREATE TABLE chapter_creation_receipts (
  idempotency_key TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project_identity(project_id) ON DELETE CASCADE,
  unit_id TEXT NOT NULL REFERENCES story_nodes(node_id) ON DELETE RESTRICT,
  chapter_id TEXT NOT NULL UNIQUE REFERENCES story_nodes(node_id) ON DELETE RESTRICT,
  document_id TEXT NOT NULL UNIQUE REFERENCES documents(document_id) ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL CHECK(ordinal >= 1),
  title TEXT NOT NULL CHECK(length(trim(title)) > 0),
  request_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(unit_id, ordinal)
);
