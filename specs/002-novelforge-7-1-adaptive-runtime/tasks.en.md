# Tasks · NovelForge 7.1 Adaptive Runtime

> Historical status: **7.1 was completed and passed release verification**. The empty checkboxes were ledger drift left behind after implementation; this file now records historical completion only and does not re-execute the stopped consumer project.

## Phase 1 · Capability Contract
- [x] T101 Add `harness/runtime_capabilities.py` + self-test.
- [x] T102 Add bilingual Runtime Capability docs.
- [x] T103 Integrate capability requirements with Runtime Routing.

## Phase 2 · Corpus Discovery Runtime
- [x] T201 Upgrade `corpus_scout.py` to capability-aware discovery request v2.
- [x] T202 Add `corpus/discovery_runtime.py` + typed provenance/result validation.
- [x] T203 Enforce rights/storage gate, dedupe and diversity accounting.

## Phase 3 · Durable Learning Cycle
- [x] T301 Add `learning/learning_cycle.py` with SQLite lifecycle/state/versioning.
- [x] T302 Add logical consume-once for discovery/analysis/eval results.
- [x] T303 Add resume/idempotency/illegal-transition self-tests.

## Phase 4 · Semantic Learning Work
- [x] T401 Add `learning/learning_eval.py` for corpus analysis and learning eval jobs.
- [x] T402 Reuse semantic fingerprint contract and exclude execution lineage.
- [x] T403 Add blind packet / answer-key leakage regression tests.

## Phase 5 · Promotion Gate
- [x] T501 Add `learning/promotion_gate.py`.
- [x] T502 Enforce scope-specific evidence thresholds.
- [x] T503 Require cross-work + counterexample + eval + rollback + CI for General Craft.

## Phase 6 · Immutable Bundle
- [x] T601 Add `release/build_framework_bundle.py` build/verify/self-test.
- [x] T602 Add bilingual bundle policy docs.
- [x] T603 Add optional release-bundle GitHub workflow.
- [x] T604 Produce deterministic 7.1 bundle fingerprint.

## Phase 7 · CLI / CI / Maintenance
- [x] T701 Upgrade `novelforge.py` routers/version/self-test.
- [x] T702 Upgrade reusable CI with all 7.1 deterministic contracts.
- [x] T703 Upgrade weekly maintenance to capability-aware learning queues.
- [x] T704 Assert normal CI and weekly maintenance execute no model and auto-promote nothing.

## Phase 8 · Docs / Manifest / Version
- [x] T801 Update `HARNESS_MANIFEST.yaml` to 7.1.0 and declare new modules/contracts.
- [x] T802 Update Skill/Harness/Self-Improvement/Adaptive-Learning/Corpus/Integration docs in EN + zh-CN.
- [x] T803 Update README/CHANGELOG/Project SDK docs and default framework version.
- [x] T804 Record external mechanism evidence/provenance from official framework docs.

## Phase 9 · Framework Verification
- [x] T901 Final NovelForge CI green on the exact 7.1 commit.
- [x] T902 Bundle build/verify green and fingerprint recorded.
- [x] T903 No consumer-project leakage in Framework source.

## Phase 10 · Historical Consumer Upgrade
- [x] T1001 The consumer project minimum Framework version was updated to 7.1.0 at the time.
- [x] T1002 Its lock recorded the exact commit + bundle fingerprint.
- [x] T1003 Framework attestation + 7.1 project validator contract were updated.
- [x] T1004 The consumer Project CI was green at the time.
- [x] T1005 Canon / active-story state was verified unchanged by the dependency migration.

> That consumer repository has since been stopped by the user; the 7.2 work does not read, modify, or migrate it.

## Non-blocking follow-up
- [ ] F001 Physically remove/archive historical embedded Generic OS source only if a maintained consumer needs that cleanup later.
- [ ] F002 Original repository hero binary + provenance (not a runtime blocker).
