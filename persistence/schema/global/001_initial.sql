CREATE TABLE quillframe_schema_identity (
  scope TEXT NOT NULL CHECK(scope = 'global'),
  release TEXT NOT NULL CHECK(release = '1.0')
);
INSERT INTO quillframe_schema_identity(scope, release) VALUES('global', '1.0');

CREATE TABLE IF NOT EXISTS application_settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_registry (
  project_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  language TEXT NOT NULL,
  project_schema_version INTEGER NOT NULL,
  project_dir TEXT NOT NULL UNIQUE,
  registered_at TEXT NOT NULL,
  last_opened_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_preference_hypotheses (
  hypothesis_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL CHECK(scope IN ('user_taste','one_off')),
  statement TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('candidate','validated','contested','superseded')),
  evidence_json TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS global_learning_evidence (
  evidence_id TEXT PRIMARY KEY,
  evidence_kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  interpreted_scope TEXT CHECK(interpreted_scope IN ('one_off','project','user_taste','general_craft')),
  promotion_state TEXT NOT NULL DEFAULT 'captured' CHECK(promotion_state IN ('captured','awaiting_semantic','validated','rejected')),
  provenance_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_local_work (
  work_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  schedule_json TEXT NOT NULL,
  state TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS backup_metadata (
  backup_id TEXT PRIMARY KEY,
  project_id TEXT,
  bundle_path TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  verified INTEGER NOT NULL CHECK(verified IN (0,1)),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnostics_metadata (
  diagnostic_id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  status TEXT NOT NULL,
  details_json TEXT NOT NULL,
  observed_at TEXT NOT NULL
);
