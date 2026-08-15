# 008 Plan · State Integrity P0

1. Freeze/synchronize an exact current Framework main; never mutate downstream Project locks during development.
2. Stabilize #69 property write-source policy with deterministic route semantics and legacy compatibility.
3. Re-read current-main state graph, Settlement, memory invalidation, quality-evolution, dependency and resume mechanisms.
4. Implement #63 as a non-authoritative durable ledger that opens only from explicit fingerprint-bound dependency evidence.
5. Make open/discharge/supersede/waive idempotent and evidence-bound; prove restart does not duplicate work.
6. Keep open debt advisory by default; workflow-specific debt-free preconditions must be explicit rather than global resume locks.
7. Wire state-integrity tests into normal full CI, then add Framework manifest discovery after executable semantics are green.
8. Re-synchronize concurrent main without overwriting Studio/runtime work; review exact diff and public CI before promotion.

Rollback: revert P0 and remove/rebuild the derived debt DB. Existing Canon, Settlement transactions, Project files and locks remain unchanged.
