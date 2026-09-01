CREATE TABLE project_state_heads (
  project_id TEXT PRIMARY KEY REFERENCES project_identity(project_id) ON DELETE CASCADE,
  revision INTEGER NOT NULL CHECK(revision >= 0),
  latest_event_seq INTEGER,
  latest_snapshot_id TEXT,
  state_fingerprint TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(latest_event_seq) REFERENCES story_events(event_seq) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE story_events (
  event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  project_id TEXT NOT NULL REFERENCES project_identity(project_id) ON DELETE CASCADE,
  run_id TEXT,
  chapter_id TEXT REFERENCES story_nodes(node_id) ON DELETE RESTRICT,
  aggregate_kind TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  event_kind TEXT NOT NULL,
  base_revision INTEGER NOT NULL CHECK(base_revision >= 0),
  commit_revision INTEGER NOT NULL CHECK(commit_revision = base_revision + 1),
  payload_json TEXT NOT NULL,
  payload_fingerprint TEXT NOT NULL,
  event_fingerprint TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, commit_revision)
);

CREATE INDEX story_event_aggregate_idx
  ON story_events(project_id, aggregate_kind, aggregate_id, event_seq);

CREATE TABLE story_state_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project_identity(project_id) ON DELETE CASCADE,
  through_event_seq INTEGER NOT NULL REFERENCES story_events(event_seq) ON DELETE RESTRICT,
  schema_version INTEGER NOT NULL CHECK(schema_version >= 1),
  state_fingerprint TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, through_event_seq)
);
