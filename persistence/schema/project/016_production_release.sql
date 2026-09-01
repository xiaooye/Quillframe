CREATE TABLE production_releases (
  release_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
  candidate_fingerprint TEXT NOT NULL,
  writer_pack_fingerprint TEXT NOT NULL REFERENCES writer_pack_freezes(writer_pack_fingerprint) ON DELETE RESTRICT,
  tracking_fingerprint TEXT NOT NULL,
  review_report_fingerprint TEXT NOT NULL REFERENCES structured_review_reports(report_fingerprint) ON DELETE RESTRICT,
  stage_receipt_fingerprints_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  release_fingerprint TEXT NOT NULL UNIQUE,
  user_visible INTEGER NOT NULL CHECK(user_visible = 1),
  released_at TEXT NOT NULL,
  UNIQUE(candidate_id, candidate_fingerprint)
);
