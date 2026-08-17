# Tasks 015 — Candidate Lineage

- [x] Bootstrap pinned consumer authority and freeze current Framework base.
- [x] Research external lineage/version/revision designs and current NovelForge equivalents.
- [x] Define comparison-parent versus prose-parent semantics.
- [x] Implement additive companion schema and immutable lineage registration.
- [x] Bind exact semantic review receipts and stale invalidation.
- [x] Harden acceptance handling to opaque, non-authoritative evidence references.
- [x] Add read-only SETTLE reference-consistency check with `settlement_authorized=false`.
- [x] Add versioned machine-readable `quality/candidate_lineage.schema.json`.
- [x] Add lineage-aware evolution runtime facade that fails closed on missing/invalid provenance.
- [x] Preserve legacy `quality_evolution.py` compatibility without treating legacy rows as lineage-complete.
- [x] Add required deterministic tests A-H.
- [x] Add runtime bypass-detection and explicit-recovery test.
- [x] Add legacy-vs-lineage architecture ablation.
- [x] Add migration, rollback, authority, and Cold Read decision documentation.
- [x] Add dedicated CI workflow including runtime integration and typed-schema identity validation.
- [ ] Pass all relevant repository-wide CI/host contracts on the final exact head.
- [ ] Complete acceptance review; keep PR draft until then.
- [ ] Recommend consumer repin only after merge/acceptance; never perform it automatically.
