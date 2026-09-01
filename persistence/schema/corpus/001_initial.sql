CREATE TABLE corpus_schema_identity (
  scope TEXT NOT NULL CHECK(scope='corpus'),
  release TEXT NOT NULL CHECK(release='1.0'),
  schema_checksum TEXT NOT NULL
);

CREATE TABLE corpus_collections (
  collection_id TEXT PRIMARY KEY,
  root_path TEXT NOT NULL,
  root_identity_json TEXT NOT NULL CHECK(json_valid(root_identity_json)=1),
  scan_fingerprint TEXT NOT NULL UNIQUE,
  work_count INTEGER NOT NULL CHECK(work_count >= 0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE corpus_work_versions (
  work_version_id TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL REFERENCES corpus_collections(collection_id) ON DELETE CASCADE,
  public_work_id TEXT NOT NULL,
  display_title TEXT NOT NULL,
  relative_ref TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK(byte_size > 0),
  boundaries_json TEXT NOT NULL CHECK(json_valid(boundaries_json)=1),
  rights_class TEXT NOT NULL CHECK(rights_class IN ('local_user_provided')),
  state TEXT NOT NULL CHECK(state IN ('eligible','quarantined')),
  created_at TEXT NOT NULL,
  UNIQUE(collection_id,relative_ref,source_fingerprint),
  UNIQUE(collection_id,public_work_id)
);

CREATE TABLE corpus_selection_proposals (
  study_id TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL REFERENCES corpus_collections(collection_id) ON DELETE RESTRICT,
  profile TEXT NOT NULL CHECK(profile IN ('general','adult_explicit')),
  proposal_fingerprint TEXT NOT NULL UNIQUE,
  selection_json TEXT NOT NULL CHECK(json_valid(selection_json)=1),
  status TEXT NOT NULL CHECK(status IN ('proposed','confirmed','running','paused_golden_three','complete','cancelled')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE corpus_studies (
  study_id TEXT PRIMARY KEY REFERENCES corpus_selection_proposals(study_id) ON DELETE CASCADE,
  current_stage TEXT NOT NULL CHECK(current_stage IN ('boundary_index','golden_three','chapter_extraction','aggregate_mechanisms','story_entities','report','style_profile')),
  checkpoint_fingerprint TEXT NOT NULL,
  progress_json TEXT NOT NULL CHECK(json_valid(progress_json)=1),
  service_id TEXT,
  model_id TEXT,
  cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE corpus_stage_calls (
  call_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES corpus_studies(study_id) ON DELETE CASCADE,
  stage_key TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  request_id TEXT NOT NULL UNIQUE,
  input_fingerprint TEXT NOT NULL,
  job_json TEXT NOT NULL CHECK(json_valid(job_json)=1),
  state TEXT NOT NULL CHECK(state IN ('dispatched','confirmed','unconfirmed','cancelled','invalid')),
  result_json TEXT,
  result_fingerprint TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(study_id,stage_key,unit_key)
);

CREATE TABLE corpus_artifacts (
  artifact_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES corpus_studies(study_id) ON DELETE CASCADE,
  stage_key TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)=1),
  artifact_fingerprint TEXT NOT NULL,
  evidence_bundle_fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(study_id,stage_key,unit_key)
);

CREATE TABLE corpus_continue_authorizations (
  authorization_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL UNIQUE REFERENCES corpus_studies(study_id) ON DELETE CASCADE,
  expected_checkpoint_fingerprint TEXT NOT NULL,
  authorization_fingerprint TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE corpus_pack_candidates (
  pack_fingerprint TEXT PRIMARY KEY,
  study_id TEXT NOT NULL UNIQUE REFERENCES corpus_studies(study_id) ON DELETE RESTRICT,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)=1),
  evidence_bundle_fingerprint TEXT NOT NULL,
  leakage_gate TEXT NOT NULL CHECK(leakage_gate IN ('pass','fail')),
  created_at TEXT NOT NULL
);
