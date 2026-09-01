CREATE TABLE writer_pack_plan_bindings (
  writer_pack_fingerprint TEXT NOT NULL
    REFERENCES writer_pack_freezes(writer_pack_fingerprint) ON DELETE CASCADE,
  layer_ordinal INTEGER NOT NULL CHECK(layer_ordinal BETWEEN 1 AND 4),
  target_ref TEXT NOT NULL,
  proposal_id TEXT NOT NULL REFERENCES plans(plan_id) ON DELETE RESTRICT,
  active_version INTEGER NOT NULL CHECK(active_version >= 1),
  proposal_fingerprint TEXT NOT NULL,
  PRIMARY KEY(writer_pack_fingerprint, layer_ordinal),
  UNIQUE(writer_pack_fingerprint, target_ref)
);

CREATE INDEX writer_pack_plan_target_idx
  ON writer_pack_plan_bindings(target_ref, proposal_fingerprint);
