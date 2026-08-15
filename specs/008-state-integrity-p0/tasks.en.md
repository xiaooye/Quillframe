# 008 Tasks · State Integrity P0

## Stage A · #69 property ownership
- [x] Evidence/overlap review against state graph, Settlement, Canon/State and Project Adapter.
- [x] Define minimal mutation classes and deterministic route vocabulary.
- [x] Implement resolver/schema + Project-path integration without reinterpreting legacy Projects.
- [x] Preserve the validated implementation as content-addressed blobs while salvaging from stale PR #75 onto current main.
- [x] Add cross-contract regression proving valid Runtime operational authorization cannot bypass a `settlement_only` Project property.
- [x] Fresh salvage full NovelForge CI `31905483778` green; state-integrity job `95062461054` executed all P0 steps.

## Stage B · #63 propagation debt
- [x] Review state graph, Settlement, memory invalidation, quality evolution and resume semantics for overlap.
- [x] Implement explicit-dependency, fingerprint-bound debt identity/lifecycle with no global invalidation.
- [x] Deterministic regressions cover idempotent replay, conflicting replay rejection, discharge binding, contiguous supersession, evidence-bound waiver and restart.
- [x] Keep debt non-authoritative and non-executing: no automatic repair, replan, regeneration, Canon write or Framework write.
- [x] Revalidate both P0 mechanisms against the post-#83 Runtime Control baseline.

## Integration / promotion gate
- [x] Wire the dedicated State Integrity workflow into current full NovelForge CI.
- [x] Register tool/schema/write-boundary semantics in `HARNESS_MANIFEST.yaml` without removing current Runtime Control entries.
- [x] Add property policy, propagation debt and Runtime/property cross-contract checks to reusable deterministic contracts.
- [x] Register paired 008 spec/plan/tasks in documentation governance.
- [ ] Run final exact-head full NovelForge CI after this manifest/docs/contracts integration and inspect jobs/artifacts.
- [ ] Recheck current main, exact diff and rollback boundary; keep all downstream Project locks unchanged.
- [ ] Supersede stale PR #75 only after this fresh salvage candidate fully replaces its evidence.
