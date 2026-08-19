CREATE TABLE IF NOT EXISTS project_projection_target_ownership (
  target_type TEXT NOT NULL CHECK(target_type IN ('story_node','document')),
  target_id TEXT NOT NULL,
  projection_owned INTEGER NOT NULL CHECK(projection_owned IN (0,1)),
  first_projection_fingerprint TEXT NOT NULL,
  PRIMARY KEY(target_type, target_id)
);
