CREATE TABLE narrative_state_sources (
  entity_type TEXT NOT NULL CHECK(entity_type IN ('character','relationship','world','timeline','knowledge')),
  entity_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
  acceptance_id TEXT NOT NULL REFERENCES acceptance_evidence(acceptance_id),
  source_fingerprint TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('current','stale')),
  updated_at TEXT NOT NULL,
  PRIMARY KEY(entity_type,entity_id)
);
CREATE INDEX narrative_state_sources_chapter_idx ON narrative_state_sources(chapter_id,source_fingerprint,state);
