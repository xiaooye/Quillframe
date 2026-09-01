CREATE TABLE candidate_revision_requests (
  request_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL UNIQUE REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  candidate_fingerprint TEXT NOT NULL,
  request_fingerprint TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  requested_by TEXT NOT NULL,
  reason TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('requested','consumed','cancelled')),
  created_at TEXT NOT NULL
);

CREATE TABLE downstream_impacts (
  impact_id TEXT PRIMARY KEY,
  source_chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
  old_fingerprint TEXT NOT NULL,
  new_fingerprint TEXT NOT NULL,
  affected_chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
  owner_layer TEXT NOT NULL CHECK(owner_layer IN ('plan','scene','character','continuity','reader_expectation')),
  status TEXT NOT NULL CHECK(status IN ('open','resolved','accepted_debt')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(source_chapter_id,old_fingerprint,new_fingerprint,affected_chapter_id,owner_layer)
);

CREATE TABLE propagation_debt (
  debt_id TEXT PRIMARY KEY,
  impact_id TEXT NOT NULL UNIQUE REFERENCES downstream_impacts(impact_id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK(version >= 1),
  status TEXT NOT NULL CHECK(status IN ('open','resolved','accepted')),
  resolution_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
