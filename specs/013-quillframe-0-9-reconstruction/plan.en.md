# Plan — Quillframe 0.9.0 Reconstruction

Frozen base: `0d583b25616e7e3b009efcf256ee4b21ecb5f8f7`
Branch: `system-improve/quillframe-0.9.0`
Primary task mode: `SYSTEM-IMPROVE`

## Execution graph

1. Freeze and inventory current architecture, technical identity, product routes, persistence and deployment.
2. Record the breaking 0.9 specification, deletion matrix, Studio IA and command/authority matrix.
3. Remove Godot and migration-only product compatibility from the live tree.
4. Migrate active technical identity to Quillframe while preserving historical records.
5. Introduce canonical SQLite global/project stores, ordered migrations, revisions, FTS5, backup/restore and Doctor.
6. Expose those capabilities through operation-specific typed Core/Product contracts; keep all authority flags false unless an exact operation proves otherwise.
7. Reconstruct Studio around Writer Mode and progressive-disclosure Inspector Mode; keep the existing SolidJS visual language as the design north star.
8. Add real Core-backed author workflow dispatch for planning, DRAFT, REVISE, AUDIT, RESEARCH, CORPUS-INGEST, LEARN and SETTLE. UI states must remain pending/unsupported where semantic execution is not actually available.
9. Add a persistent non-authoritative AI dock and truthful context inspection.
10. Add thin Tauri 2 host and deployment/auth bootstrap for localhost and self-hosted web.
11. Rewrite current documentation, migration guidance and design/UX contracts.
12. Replace obsolete CI with current Framework/Product/Studio/Tauri/persistence/negative-regression validation.
13. Execute visual matrix, accessibility/localization and performance measurements; record evidence rather than inferred claims.
14. Remove temporary migration machinery, run dead-file/stale-reference audits, repair CI, and leave PR #106 draft until all merge-readiness conditions are proven.

## Deletion classification

- `CURRENT`: retained and migrated to the 0.9 architecture.
- `MIGRATION_ONLY`: allowed only while applying the one-shot repository/project migration; removed from live build authority afterward.
- `DEAD`: deleted.
- `HISTORICAL`: retained outside live runtime/build authority and excluded from current namespace gates.

## Authority invariants

- Plan != Canon.
- Revision != Accepted.
- Review Draft != Accepted artifact.
- Accepted != Settled.
- Chat history != Candidate Lineage.
- Research truth != Character Knowledge.
- Corpus evidence != Canon.
- Feedback capture != preference promotion.
- `AUDIT` reports; it never rewrites.
- `DRAFT` produces a candidate only after the current user-visible gate; it never settles.
- Exactly one primary task mode is stored on each author execution.

## Rollback

The work is isolated on a dedicated branch and draft PR. The frozen base SHA is the rollback anchor. SQLite migrations must have explicit schema versions and fail closed on checksum mismatch. Data restore is snapshot-based and verifies integrity/fingerprints before replacement. No downstream project is mutated during this reconstruction.
