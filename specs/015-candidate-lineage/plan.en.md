# Plan 015 — Candidate Lineage

1. Freeze current `main`, consumer pin, and authority boundaries.
2. Reuse the existing `quality_evolution` schema and semantic comparison contract rather than introducing a parallel candidate system.
3. Add companion lineage, review-receipt, and opaque acceptance-evidence tables to the same SQLite database.
4. Implement immutable lineage registration and exact fingerprint validation.
5. Implement review receipt binding with typed semantic-result validation and stale-result rejection.
6. Implement acceptance-evidence reference consistency while explicitly refusing authority verification or SETTLE authorization.
7. Add deterministic A-H tests, legacy-vs-lineage ablation, migration/rollback documentation, and CI.
8. Run repository-wide compatibility/hygiene gates; repair structural integration failures rather than weakening gates.
9. Keep the PR draft until acceptance conditions are green; do not repin any consumer automatically.
