-- Exact billing evidence is separate from the immutable model result. A
-- returned result remains valid even when its charge needs later reconciliation.
CREATE TABLE IF NOT EXISTS production_billing_receipts (
  call_id TEXT PRIMARY KEY REFERENCES production_stage_calls(call_id) ON DELETE CASCADE,
  run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
  result_fingerprint TEXT NOT NULL,
  cost_micros INTEGER NOT NULL CHECK(cost_micros >= 0),
  receipt_source TEXT NOT NULL CHECK(receipt_source IN (
    'provider_result','no_model_request','authorized_reconciliation'
  )),
  evidence_ref TEXT NOT NULL,
  evidence_fingerprint TEXT NOT NULL,
  receipt_fingerprint TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  authority INTEGER NOT NULL DEFAULT 0 CHECK(authority = 0),
  UNIQUE(run_id, call_id)
);

CREATE INDEX IF NOT EXISTS idx_production_billing_run
  ON production_billing_receipts(run_id, call_id);

CREATE TRIGGER IF NOT EXISTS production_billing_receipt_insert_binding
BEFORE INSERT ON production_billing_receipts
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM production_stage_calls AS c
    WHERE c.call_id = NEW.call_id
      AND c.run_id = NEW.run_id
      AND c.result_fingerprint = NEW.result_fingerprint
      AND c.state = 'confirmed'
  ) THEN RAISE(ABORT, 'production billing receipt binding mismatch') END;
END;

CREATE TRIGGER IF NOT EXISTS production_billing_receipt_update_binding
BEFORE UPDATE ON production_billing_receipts
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM production_stage_calls AS c
    WHERE c.call_id = NEW.call_id
      AND c.run_id = NEW.run_id
      AND c.result_fingerprint = NEW.result_fingerprint
      AND c.state = 'confirmed'
  ) THEN RAISE(ABORT, 'production billing receipt binding mismatch') END;
END;
