CREATE TABLE IF NOT EXISTS model_services (
  service_id TEXT PRIMARY KEY,
  endpoint TEXT NOT NULL UNIQUE,
  credential_ref TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  auth_style TEXT NOT NULL DEFAULT 'unknown' CHECK(auth_style IN ('bearer','x_api_key','none','unknown')),
  discovery_state TEXT NOT NULL DEFAULT 'unknown' CHECK(discovery_state IN ('unknown','connected','failed')),
  snapshot_fingerprint TEXT,
  snapshot_json TEXT NOT NULL DEFAULT '{}',
  last_checked_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discovered_models (
  service_id TEXT NOT NULL REFERENCES model_services(service_id) ON DELETE CASCADE,
  model_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  protocol_family TEXT CHECK(protocol_family IS NULL OR protocol_family IN ('openai_chat_completions','openai_responses','anthropic_messages')),
  auth_style TEXT CHECK(auth_style IS NULL OR auth_style IN ('bearer','x_api_key','none')),
  enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  context_window INTEGER,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  cost_metadata_json TEXT NOT NULL DEFAULT '{}',
  capability_snapshot_json TEXT NOT NULL DEFAULT '{}',
  discovered_at TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(service_id, model_id)
);

CREATE TABLE IF NOT EXISTS model_capability_evidence (
  evidence_id TEXT PRIMARY KEY,
  service_id TEXT NOT NULL,
  model_id TEXT NOT NULL,
  capability TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('verified','detected','manually_configured','unavailable','unknown')),
  provenance TEXT NOT NULL CHECK(provenance IN ('declared','probed','verified','manual_override','unknown')),
  protocol_family TEXT CHECK(protocol_family IS NULL OR protocol_family IN ('openai_chat_completions','openai_responses','anthropic_messages')),
  detail TEXT,
  evidence_ref TEXT,
  evidence_fingerprint TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  FOREIGN KEY(service_id, model_id) REFERENCES discovered_models(service_id, model_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_discovered_models_service ON discovered_models(service_id, enabled);
CREATE INDEX IF NOT EXISTS idx_model_capability_evidence_model ON model_capability_evidence(service_id, model_id, capability, observed_at);
