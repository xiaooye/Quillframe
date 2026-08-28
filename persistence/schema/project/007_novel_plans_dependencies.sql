CREATE TABLE IF NOT EXISTS plan_versions (
    plan_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK(version >= 1),
    payload_json TEXT NOT NULL,
    content_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(plan_id, version)
);

CREATE TABLE IF NOT EXISTS chapter_dependencies (
    chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
    source_chapter_id TEXT NOT NULL REFERENCES story_nodes(node_id),
    source_fingerprint TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    status TEXT NOT NULL CHECK(status IN ('current', 'stale')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(chapter_id, source_chapter_id, run_id),
    CHECK(chapter_id != source_chapter_id)
);
CREATE INDEX IF NOT EXISTS idx_chapter_dependency_source
    ON chapter_dependencies(source_chapter_id, source_fingerprint, status);
