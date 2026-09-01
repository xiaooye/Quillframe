CREATE TABLE plan_editor_views (
  proposal_id TEXT PRIMARY KEY REFERENCES plans(plan_id) ON DELETE CASCADE,
  target_ref TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  reader_intent_json TEXT NOT NULL,
  expectation_refs_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX plan_editor_target_idx ON plan_editor_views(target_ref, created_at);
