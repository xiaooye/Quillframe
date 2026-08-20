CREATE TABLE IF NOT EXISTS semantic_context_profiles (
  profile_id TEXT PRIMARY KEY,
  source_object_id TEXT NOT NULL,
  source_object_type TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  profile_fingerprint TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  trigger_when TEXT NOT NULL DEFAULT '',
  estimated_tokens INTEGER NOT NULL DEFAULT 0 CHECK(estimated_tokens >= 0),
  semantic_tags_json TEXT NOT NULL DEFAULT '[]',
  stage_affinities_json TEXT NOT NULL DEFAULT '[]',
  generator_provenance_json TEXT NOT NULL,
  manual_override_fingerprint TEXT,
  status TEXT NOT NULL CHECK(status IN ('current','stale')),
  stale_reason TEXT,
  generated_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);
CREATE INDEX IF NOT EXISTS semantic_context_profiles_source_idx
  ON semantic_context_profiles(source_object_id, status, updated_at);
CREATE INDEX IF NOT EXISTS semantic_context_profiles_source_fp_idx
  ON semantic_context_profiles(source_object_id, source_fingerprint);

CREATE TABLE IF NOT EXISTS context_profile_overrides (
  source_object_id TEXT PRIMARY KEY,
  override_id TEXT NOT NULL UNIQUE,
  override_fingerprint TEXT NOT NULL,
  fields_json TEXT NOT NULL,
  updated_by TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);

CREATE TABLE IF NOT EXISTS context_stage_selections (
  selection_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  stage_id TEXT NOT NULL,
  candidate_universe_fingerprint TEXT NOT NULL,
  selection_fingerprint TEXT NOT NULL UNIQUE,
  pool_json TEXT NOT NULL,
  greenlight_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  UNIQUE(run_id, stage_id, selection_fingerprint)
);
CREATE INDEX IF NOT EXISTS context_stage_selections_run_idx
  ON context_stage_selections(run_id, stage_id, created_at);

CREATE TABLE IF NOT EXISTS context_freezes (
  freeze_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  task_mode TEXT NOT NULL,
  freeze_fingerprint TEXT NOT NULL UNIQUE,
  snapshot_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('frozen','stale_conflict','superseded')),
  supersedes_freeze_id TEXT REFERENCES context_freezes(freeze_id) ON DELETE SET NULL,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0)
);
CREATE INDEX IF NOT EXISTS context_freezes_run_idx
  ON context_freezes(run_id, created_at);
