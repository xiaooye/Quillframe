CREATE TABLE IF NOT EXISTS project_identity (
  project_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  language TEXT NOT NULL,
  project_schema_version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS story_nodes (
  node_id TEXT PRIMARY KEY,
  parent_id TEXT REFERENCES story_nodes(node_id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK(kind IN ('book','volume','arc','unit','chapter','scene')),
  ordinal INTEGER NOT NULL,
  title TEXT NOT NULL,
  pov_character_id TEXT,
  location_id TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(parent_id, kind, ordinal)
);
CREATE INDEX IF NOT EXISTS story_nodes_parent_idx ON story_nodes(parent_id, ordinal);

CREATE TABLE IF NOT EXISTS documents (
  document_id TEXT PRIMARY KEY,
  story_node_id TEXT REFERENCES story_nodes(node_id) ON DELETE SET NULL,
  document_kind TEXT NOT NULL CHECK(document_kind IN ('manuscript','note','plan','research_note','publication_source')),
  title TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_revisions (
  revision_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  parent_revision_id TEXT REFERENCES document_revisions(revision_id) ON DELETE RESTRICT,
  content TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  source TEXT NOT NULL,
  authority_class TEXT NOT NULL CHECK(authority_class IN ('proposal','review','accepted')),
  provenance_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(document_id, content_fingerprint)
);
CREATE INDEX IF NOT EXISTS document_revisions_doc_idx ON document_revisions(document_id, created_at);

CREATE TABLE IF NOT EXISTS characters (
  character_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  agenda TEXT,
  voice_notes TEXT,
  state_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
  relationship_id TEXT PRIMARY KEY,
  participant_a TEXT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
  participant_b TEXT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL,
  state_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL,
  CHECK(participant_a <> participant_b)
);

CREATE TABLE IF NOT EXISTS world_entities (
  entity_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  name TEXT NOT NULL,
  truth_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
  location_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  state_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timeline_events (
  event_id TEXT PRIMARY KEY,
  story_order INTEGER NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  authority_class TEXT NOT NULL CHECK(authority_class IN ('locked','accepted','active_plan','review','proposal')),
  source_ref TEXT,
  UNIQUE(story_order, event_id)
);

CREATE TABLE IF NOT EXISTS plans (
  plan_id TEXT PRIMARY KEY,
  task_mode TEXT NOT NULL CHECK(task_mode IN ('DESIGN-BOOK','DESIGN-VOLUME','PLAN-UNIT','PLAN-CHAPTER')),
  target_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('active','superseded','completed','proposal')),
  plan_json TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scene_cards (
  scene_card_id TEXT PRIMARY KEY,
  scene_id TEXT REFERENCES story_nodes(node_id) ON DELETE CASCADE,
  plan_id TEXT REFERENCES plans(plan_id) ON DELETE CASCADE,
  objective TEXT,
  conflict TEXT,
  stakes TEXT,
  reader_reward TEXT,
  plotlines_json TEXT NOT NULL DEFAULT '[]',
  dependencies_json TEXT NOT NULL DEFAULT '[]',
  card_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS canon_claims (
  claim_id TEXT PRIMARY KEY,
  subject_ref TEXT NOT NULL,
  predicate TEXT NOT NULL,
  value_json TEXT NOT NULL,
  authority_class TEXT NOT NULL CHECK(authority_class IN ('locked','accepted','active_plan','review','proposal')),
  evidence_ref TEXT,
  valid_from_story_order INTEGER,
  valid_to_story_order INTEGER,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS canon_state (
  state_key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  authority_class TEXT NOT NULL CHECK(authority_class IN ('locked','accepted')),
  evidence_ref TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS character_knowledge (
  knowledge_id TEXT PRIMARY KEY,
  character_id TEXT NOT NULL REFERENCES characters(character_id) ON DELETE CASCADE,
  claim_ref TEXT,
  fact_json TEXT NOT NULL,
  available_from_story_order INTEGER NOT NULL,
  evidence_ref TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'known'
);

CREATE TABLE IF NOT EXISTS research_sources (
  source_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  source_uri TEXT,
  source_kind TEXT NOT NULL,
  rights_json TEXT NOT NULL DEFAULT '{}',
  provenance_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_claims (
  research_claim_id TEXT PRIMARY KEY,
  source_id TEXT REFERENCES research_sources(source_id) ON DELETE SET NULL,
  claim_text TEXT NOT NULL,
  citation_json TEXT NOT NULL DEFAULT '{}',
  fictionalization_notes TEXT,
  character_knowledge_boundary_json TEXT NOT NULL DEFAULT '{}',
  canon_status TEXT NOT NULL DEFAULT 'research_only' CHECK(canon_status IN ('research_only','proposal','accepted_by_settlement')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
  candidate_id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES documents(document_id) ON DELETE SET NULL,
  revision_id TEXT REFERENCES document_revisions(revision_id) ON DELETE SET NULL,
  run_id TEXT,
  task_mode TEXT NOT NULL CHECK(task_mode IN ('DRAFT','REVISE')),
  candidate_kind TEXT NOT NULL CHECK(candidate_kind IN ('draft','repair','fresh_regeneration','user_edit')),
  status TEXT NOT NULL CHECK(status IN ('internal','review_draft','rejected','accepted')),
  content_fingerprint TEXT NOT NULL,
  user_visible_gate TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_lineage (
  candidate_id TEXT PRIMARY KEY REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  comparison_parent_id TEXT REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
  prose_parent_id TEXT REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
  lineage_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS review_evidence (
  review_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  evidence_kind TEXT NOT NULL,
  result_json TEXT NOT NULL,
  candidate_fingerprint TEXT NOT NULL,
  reviewer_fingerprint TEXT,
  independent INTEGER NOT NULL DEFAULT 0 CHECK(independent IN (0,1)),
  stale INTEGER NOT NULL DEFAULT 0 CHECK(stale IN (0,1)),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS acceptance_evidence (
  acceptance_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
  candidate_fingerprint TEXT NOT NULL,
  authorized_by TEXT NOT NULL,
  authorization_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settlements (
  settlement_id TEXT PRIMARY KEY,
  acceptance_id TEXT NOT NULL REFERENCES acceptance_evidence(acceptance_id) ON DELETE RESTRICT,
  target_ref TEXT NOT NULL,
  before_fingerprint TEXT NOT NULL,
  after_fingerprint TEXT,
  state_delta_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('prepared','settled','settlement_incomplete')),
  receipt_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS context_manifests (
  manifest_id TEXT PRIMARY KEY,
  run_id TEXT,
  task_mode TEXT NOT NULL,
  selected_json TEXT NOT NULL,
  loaded_json TEXT NOT NULL,
  dropped_json TEXT NOT NULL,
  visibility_excluded_json TEXT NOT NULL,
  budget_json TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS derived_memory (
  memory_id TEXT PRIMARY KEY,
  memory_tier TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  source_refs_json TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority=0),
  created_at TEXT NOT NULL,
  expires_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  provider_session_ref TEXT,
  framework_fingerprint TEXT,
  status TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
  task_mode TEXT NOT NULL CHECK(task_mode IN ('DESIGN-BOOK','DESIGN-VOLUME','PLAN-UNIT','PLAN-CHAPTER','DRAFT','REVISE','RESEARCH','SETTLE','AUDIT','CORPUS-INGEST','LEARN','SYSTEM-IMPROVE')),
  target_ref TEXT,
  status TEXT NOT NULL,
  request_fingerprint TEXT NOT NULL,
  result_fingerprint TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  checkpoint_kind TEXT NOT NULL,
  state_json TEXT NOT NULL,
  artifact_fingerprint TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
  event_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handoffs (
  handoff_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id) ON DELETE CASCADE,
  worker_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  artifact_fingerprint TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
  receipt_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id) ON DELETE SET NULL,
  receipt_kind TEXT NOT NULL,
  idempotency_key TEXT UNIQUE,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_evidence (
  evidence_id TEXT PRIMARY KEY,
  evidence_kind TEXT NOT NULL,
  source_ref TEXT,
  payload_json TEXT NOT NULL,
  interpreted_scope TEXT CHECK(interpreted_scope IN ('one_off','project','user_taste','general_craft')),
  state TEXT NOT NULL DEFAULT 'captured' CHECK(state IN ('captured','awaiting_semantic','validated','rejected')),
  promotion_eligible INTEGER NOT NULL DEFAULT 0 CHECK(promotion_eligible IN (0,1)),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_preference_hypotheses (
  hypothesis_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL CHECK(scope IN ('one_off','project','user_taste','general_craft')),
  statement TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('candidate','validated','contested','superseded')),
  evidence_json TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corpus_references (
  corpus_ref_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  rights_json TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  mechanism_json TEXT NOT NULL DEFAULT '{}',
  evidence_polarity TEXT NOT NULL DEFAULT 'neutral' CHECK(evidence_polarity IN ('positive','negative','contrast','neutral')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_references (
  benchmark_ref_id TEXT PRIMARY KEY,
  corpus_ref_id TEXT REFERENCES corpus_references(corpus_ref_id) ON DELETE SET NULL,
  benchmark_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publication_builds (
  build_id TEXT PRIMARY KEY,
  source_acceptance_id TEXT NOT NULL REFERENCES acceptance_evidence(acceptance_id) ON DELETE RESTRICT,
  format TEXT NOT NULL,
  output_ref TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  validation_json TEXT NOT NULL,
  persistent INTEGER NOT NULL CHECK(persistent IN (0,1)),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blob_refs (
  fingerprint TEXT PRIMARY KEY,
  relative_path TEXT NOT NULL UNIQUE,
  media_type TEXT,
  byte_size INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
  entity_type UNINDEXED,
  entity_id UNINDEXED,
  title,
  body,
  tokenize='unicode61 remove_diacritics 2'
);
