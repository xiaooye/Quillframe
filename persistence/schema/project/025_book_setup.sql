DROP INDEX narrative_state_sources_chapter_idx;
DROP TABLE narrative_state_sources;
CREATE TABLE narrative_state_sources (
  entity_type TEXT NOT NULL CHECK(entity_type IN ('character','relationship','world','timeline','knowledge','expectation')),
  entity_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
  acceptance_id TEXT NOT NULL REFERENCES acceptance_evidence(acceptance_id),
  source_fingerprint TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('current','stale')),
  updated_at TEXT NOT NULL,
  PRIMARY KEY(entity_type,entity_id)
);
CREATE INDEX narrative_state_sources_chapter_idx
ON narrative_state_sources(chapter_id,source_fingerprint,state);

CREATE UNIQUE INDEX documents_one_manuscript_per_story_node_idx
ON documents(story_node_id)
WHERE document_kind = 'manuscript';

CREATE TABLE book_setup_proposals (
  setup_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project_identity(project_id) ON DELETE CASCADE,
  expected_setup_version INTEGER NOT NULL CHECK(expected_setup_version >= 0),
  expected_book_plan_version INTEGER NOT NULL CHECK(expected_book_plan_version >= 0),
  status TEXT NOT NULL CHECK(status IN ('proposal_ready','approved','superseded')),
  setup_json TEXT NOT NULL,
  setup_fingerprint TEXT NOT NULL,
  request_fingerprint TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  UNIQUE(project_id, setup_fingerprint)
);

CREATE INDEX book_setup_proposals_project_idx
ON book_setup_proposals(project_id, created_at, setup_id);

CREATE TABLE book_setup_approvals (
  approval_id TEXT PRIMARY KEY,
  setup_id TEXT NOT NULL UNIQUE REFERENCES book_setup_proposals(setup_id) ON DELETE RESTRICT,
  project_id TEXT NOT NULL REFERENCES project_identity(project_id) ON DELETE CASCADE,
  expected_setup_version INTEGER NOT NULL CHECK(expected_setup_version >= 0),
  book_plan_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE RESTRICT,
  book_plan_fingerprint TEXT NOT NULL,
  authorized_by TEXT NOT NULL,
  approval_json TEXT NOT NULL,
  approval_fingerprint TEXT NOT NULL UNIQUE,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE book_setup_heads (
  project_id TEXT PRIMARY KEY REFERENCES project_identity(project_id) ON DELETE CASCADE,
  setup_id TEXT NOT NULL UNIQUE REFERENCES book_setup_proposals(setup_id) ON DELETE RESTRICT,
  version INTEGER NOT NULL CHECK(version > 0),
  status TEXT NOT NULL CHECK(status = 'ready'),
  setup_fingerprint TEXT NOT NULL,
  book_plan_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE RESTRICT,
  book_plan_fingerprint TEXT NOT NULL,
  approval_fingerprint TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
