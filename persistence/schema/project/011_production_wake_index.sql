-- Bound coordinator wake scans as the durable event journal grows.
CREATE INDEX IF NOT EXISTS idx_runtime_events_run_kind_id
  ON runtime_events(run_id, event_kind, event_id);
