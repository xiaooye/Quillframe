ALTER TABLE publication_build_attempts ADD COLUMN source_binding_json TEXT;
ALTER TABLE publication_build_attempts ADD COLUMN source_binding_fingerprint TEXT;
ALTER TABLE publication_build_attempts ADD COLUMN stage_identity_json TEXT;
ALTER TABLE publication_build_attempts ADD COLUMN final_identity_json TEXT;
ALTER TABLE publication_build_attempts ADD COLUMN durability_json TEXT;
ALTER TABLE publication_build_attempts ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1 CHECK(state_version >= 1);

ALTER TABLE publication_collection_attempts ADD COLUMN source_binding_json TEXT;
ALTER TABLE publication_collection_attempts ADD COLUMN source_binding_fingerprint TEXT;
ALTER TABLE publication_collection_attempts ADD COLUMN stage_identity_json TEXT;
ALTER TABLE publication_collection_attempts ADD COLUMN final_identity_json TEXT;
ALTER TABLE publication_collection_attempts ADD COLUMN durability_json TEXT;
ALTER TABLE publication_collection_attempts ADD COLUMN state_version INTEGER NOT NULL DEFAULT 1 CHECK(state_version >= 1);

ALTER TABLE publication_builds ADD COLUMN source_binding_json TEXT;
ALTER TABLE publication_builds ADD COLUMN source_binding_fingerprint TEXT;
ALTER TABLE publication_builds ADD COLUMN artifact_fingerprint TEXT;
ALTER TABLE publication_builds ADD COLUMN byte_size INTEGER CHECK(byte_size >= 0);
ALTER TABLE publication_builds ADD COLUMN artifact_manifest_json TEXT;
ALTER TABLE publication_builds ADD COLUMN artifact_manifest_fingerprint TEXT;

ALTER TABLE publication_collection_builds ADD COLUMN source_binding_json TEXT;
ALTER TABLE publication_collection_builds ADD COLUMN source_binding_fingerprint TEXT;
ALTER TABLE publication_collection_builds ADD COLUMN artifact_fingerprint TEXT;
ALTER TABLE publication_collection_builds ADD COLUMN byte_size INTEGER CHECK(byte_size >= 0);
ALTER TABLE publication_collection_builds ADD COLUMN artifact_manifest_json TEXT;
ALTER TABLE publication_collection_builds ADD COLUMN artifact_manifest_fingerprint TEXT;

CREATE TABLE publication_build_requests (
  idempotency_key TEXT PRIMARY KEY,
  request_fingerprint TEXT NOT NULL,
  build_id TEXT NOT NULL REFERENCES publication_build_attempts(build_id) DEFERRABLE INITIALLY DEFERRED,
  created_at TEXT NOT NULL
);

CREATE INDEX publication_build_attempts_recovery_idx
ON publication_build_attempts(project_id,state,created_at,build_id);

CREATE INDEX publication_collection_attempts_recovery_idx
ON publication_collection_attempts(project_id,state,created_at,build_id);

CREATE TRIGGER publication_build_attempt_contract_insert
BEFORE INSERT ON publication_build_attempts
WHEN NEW.source_binding_json IS NULL
  OR json_valid(NEW.source_binding_json) <> 1
  OR NEW.source_binding_fingerprint IS NULL
  OR (NEW.stage_identity_json IS NOT NULL AND json_valid(NEW.stage_identity_json) <> 1)
  OR (NEW.final_identity_json IS NOT NULL AND json_valid(NEW.final_identity_json) <> 1)
  OR (NEW.durability_json IS NOT NULL AND json_valid(NEW.durability_json) <> 1)
BEGIN
  SELECT RAISE(ABORT,'publication attempt native contract missing');
END;

CREATE TRIGGER publication_collection_attempt_contract_insert
BEFORE INSERT ON publication_collection_attempts
WHEN NEW.source_binding_json IS NULL
  OR json_valid(NEW.source_binding_json) <> 1
  OR NEW.source_binding_fingerprint IS NULL
  OR (NEW.stage_identity_json IS NOT NULL AND json_valid(NEW.stage_identity_json) <> 1)
  OR (NEW.final_identity_json IS NOT NULL AND json_valid(NEW.final_identity_json) <> 1)
  OR (NEW.durability_json IS NOT NULL AND json_valid(NEW.durability_json) <> 1)
BEGIN
  SELECT RAISE(ABORT,'publication collection attempt native contract missing');
END;

CREATE TRIGGER publication_build_manifest_insert
BEFORE INSERT ON publication_builds
WHEN NEW.source_binding_json IS NULL
  OR json_valid(NEW.source_binding_json) <> 1
  OR NEW.source_binding_fingerprint IS NULL
  OR NEW.artifact_fingerprint IS NULL
  OR NEW.byte_size IS NULL
  OR NEW.artifact_manifest_json IS NULL
  OR json_valid(NEW.artifact_manifest_json) <> 1
  OR NEW.artifact_manifest_fingerprint IS NULL
BEGIN
  SELECT RAISE(ABORT,'publication build manifest missing');
END;

CREATE TRIGGER publication_collection_build_manifest_insert
BEFORE INSERT ON publication_collection_builds
WHEN NEW.source_binding_json IS NULL
  OR json_valid(NEW.source_binding_json) <> 1
  OR NEW.source_binding_fingerprint IS NULL
  OR NEW.artifact_fingerprint IS NULL
  OR NEW.byte_size IS NULL
  OR NEW.artifact_manifest_json IS NULL
  OR json_valid(NEW.artifact_manifest_json) <> 1
  OR NEW.artifact_manifest_fingerprint IS NULL
BEGIN
  SELECT RAISE(ABORT,'publication collection build manifest missing');
END;
