CREATE TABLE story_tracking_authority (
  project_id TEXT PRIMARY KEY REFERENCES project_identity(project_id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK(version >= 0),
  payload_json TEXT NOT NULL,
  content_fingerprint TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE plan_activations (
  activation_id TEXT PRIMARY KEY,
  proposal_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE RESTRICT,
  target_ref TEXT NOT NULL,
  active_version INTEGER NOT NULL CHECK(active_version >= 1),
  proposal_fingerprint TEXT NOT NULL,
  authorization_fingerprint TEXT NOT NULL UNIQUE,
  authorization_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('active','superseded')),
  created_at TEXT NOT NULL,
  UNIQUE(target_ref, active_version)
);
CREATE UNIQUE INDEX plan_one_active_target_idx
  ON plan_activations(target_ref) WHERE status='active';

CREATE TABLE corpus_analysis_states (
  source_id TEXT PRIMARY KEY,
  source_fingerprint TEXT NOT NULL,
  stage TEXT NOT NULL CHECK(stage IN (
    'boundary_index','golden_three','chapter_extraction','aggregate_mechanisms',
    'story_entities','report','style_profile'
  )),
  paused_after_golden_three INTEGER NOT NULL CHECK(paused_after_golden_three IN (0,1)),
  progress_json TEXT NOT NULL,
  checkpoint_fingerprint TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE corpus_source_free_packs (
  pack_fingerprint TEXT PRIMARY KEY,
  genre TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  source_identities_removed INTEGER NOT NULL CHECK(source_identities_removed = 1),
  created_at TEXT NOT NULL
);

CREATE TABLE writer_pack_freezes (
  writer_pack_fingerprint TEXT PRIMARY KEY,
  chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id) ON DELETE CASCADE,
  active_plan_fingerprint TEXT NOT NULL,
  context_freeze_fingerprint TEXT NOT NULL,
  tracking_fingerprint TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE structured_review_reports (
  report_fingerprint TEXT PRIMARY KEY,
  candidate_fingerprint TEXT NOT NULL,
  mode TEXT NOT NULL CHECK(mode IN ('full','lean','solo')),
  decision TEXT NOT NULL CHECK(decision IN ('accept','revise','infrastructure_failed')),
  independent_context INTEGER NOT NULL CHECK(independent_context IN (0,1)),
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX structured_review_candidate_idx
  ON structured_review_reports(candidate_fingerprint, created_at);

CREATE TABLE production_pipeline_snapshots (
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK(version >= 1),
  state TEXT NOT NULL CHECK(state IN (
    'ready','writer_pack_frozen','drafted','awaiting_review','revision_required',
    'accepted','infrastructure_failed'
  )),
  current_candidate_fingerprint TEXT,
  snapshot_json TEXT NOT NULL,
  snapshot_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(run_id, version)
);
