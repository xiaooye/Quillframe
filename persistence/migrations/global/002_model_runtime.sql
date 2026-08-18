CREATE TABLE IF NOT EXISTS model_services (
  service_id TEXT PRIMARY KEY,
  endpoint TEXT NOT NULL UNIQUE,
  credential_ref TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
  auth_style TEXT NOT NULL DEFAULT 'unknown' CHECK(auth_style IN ('bearer','x_api_key','none','unknown')),
  discovery_state TEXT NOT NULL DEFAULT 'unknown' CHECK(discovery_state IN ('unknown','connected','failed','migrated_unverified')),
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

INSERT OR IGNORE INTO model_services(
  service_id, endpoint, credential_ref, enabled, auth_style, discovery_state,
  snapshot_json, created_at, updated_at
)
SELECT
  'legacy_' || provider_id,
  rtrim(endpoint, '/'),
  credential_ref,
  enabled,
  'unknown',
  'migrated_unverified',
  metadata_json,
  updated_at,
  updated_at
FROM provider_configuration
WHERE endpoint IS NOT NULL AND trim(endpoint) <> '';

INSERT OR IGNORE INTO discovered_models(
  service_id, model_id, display_name, enabled, context_window, metadata_json,
  cost_metadata_json, capability_snapshot_json, updated_at
)
SELECT
  'legacy_' || m.provider_id,
  m.model_id,
  m.display_name,
  m.enabled,
  m.context_size,
  '{}',
  m.cost_metadata_json,
  m.capability_json,
  m.updated_at
FROM model_registry AS m
JOIN provider_configuration AS p ON p.provider_id = m.provider_id
WHERE p.endpoint IS NOT NULL AND trim(p.endpoint) <> '';

DROP TABLE model_registry;
DROP TABLE provider_configuration;
