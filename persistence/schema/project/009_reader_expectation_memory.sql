CREATE TABLE IF NOT EXISTS expectations (
  expectation_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('question','promise','setup','relationship','goal','mystery')),
  scope TEXT NOT NULL,
  description TEXT NOT NULL,
  opened_order INTEGER NOT NULL CHECK(opened_order >= 0),
  due_by_order INTEGER,
  last_touched_order INTEGER NOT NULL CHECK(last_touched_order >= opened_order),
  status TEXT NOT NULL CHECK(status IN ('open','partial','paid','invalidated','abandoned')),
  source_ref TEXT NOT NULL,
  source_fingerprint TEXT,
  version INTEGER NOT NULL CHECK(version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS expectation_events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  expectation_id TEXT NOT NULL REFERENCES expectations(expectation_id),
  event_type TEXT NOT NULL,
  at_order INTEGER NOT NULL CHECK(at_order >= 0),
  detail TEXT,
  evidence_ref TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reader_expectation_observations (
  observation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
  document_id TEXT NOT NULL REFERENCES documents(document_id),
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id),
  candidate_fingerprint TEXT NOT NULL,
  reading_order INTEGER NOT NULL CHECK(reading_order >= 0),
  binding_fingerprint TEXT NOT NULL,
  binding_json TEXT NOT NULL,
  updates_json TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('proposed','applied','invalidated')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  UNIQUE(run_id,candidate_fingerprint)
);
CREATE TABLE IF NOT EXISTS reader_observation_sources (
  observation_id TEXT NOT NULL REFERENCES reader_expectation_observations(observation_id),
  source_chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
  source_fingerprint TEXT NOT NULL,
  PRIMARY KEY(observation_id,source_chapter_id)
);
CREATE TABLE IF NOT EXISTS reader_observation_expectation_dependencies (
  observation_id TEXT NOT NULL REFERENCES reader_expectation_observations(observation_id),
  expectation_id TEXT NOT NULL REFERENCES expectations(expectation_id),
  expected_version INTEGER NOT NULL,
  PRIMARY KEY(observation_id,expectation_id)
);
CREATE TABLE IF NOT EXISTS reader_expectation_effects (
  observation_id TEXT NOT NULL REFERENCES reader_expectation_observations(observation_id),
  expectation_id TEXT NOT NULL REFERENCES expectations(expectation_id),
  before_json TEXT,
  after_json TEXT NOT NULL,
  PRIMARY KEY(observation_id,expectation_id)
);
