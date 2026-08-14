# Tasks · NovelForge 7.1 Adaptive Runtime

## Phase 1 · Capability Contract
- [ ] T101 Add `harness/runtime_capabilities.py` + self-test.
- [ ] T102 Add bilingual Runtime Capability docs.
- [ ] T103 Integrate capability requirements with Runtime Routing.

## Phase 2 · Corpus Discovery Runtime
- [ ] T201 Upgrade `corpus_scout.py` to capability-aware discovery request v2.
- [ ] T202 Add `corpus/discovery_runtime.py` + typed provenance/result validation.
- [ ] T203 Enforce rights/storage gate, dedupe and diversity accounting.

## Phase 3 · Durable Learning Cycle
- [ ] T301 Add `learning/learning_cycle.py` with SQLite lifecycle/state/versioning.
- [ ] T302 Add logical consume-once for discovery/analysis/eval results.
- [ ] T303 Add resume/idempotency/illegal-transition self-tests.

## Phase 4 · Semantic Learning Work
- [ ] T401 Add `learning/learning_eval.py` for corpus analysis and learning eval jobs.
- [ ] T402 Reuse semantic fingerprint contract and exclude execution lineage.
- [ ] T403 Add blind packet / answer-key leakage regression tests.

## Phase 5 · Promotion Gate
- [ ] T501 Add `learning/promotion_gate.py`.
- [ ] T502 Enforce scope-specific evidence thresholds.
- [ ] T503 Require cross-work + counterexample + eval + rollback + CI for General Craft.

## Phase 6 · Immutable Bundle
- [ ] T601 Add `release/build_framework_bundle.py` build/verify/self-test.
- [ ] T602 Add bilingual bundle policy docs.
- [ ] T603 Add optional release-bundle GitHub workflow.
- [ ] T604 Produce deterministic 7.1 bundle fingerprint.

## Phase 7 · CLI / CI / Maintenance
- [ ] T701 Upgrade `novelforge.py` routers/version/self-test.
- [ ] T702 Upgrade reusable CI with all 7.1 deterministic contracts.
- [ ] T703 Upgrade weekly maintenance to capability-aware learning queues.
- [ ] T704 Assert normal CI and weekly maintenance execute no model and auto-promote nothing.

## Phase 8 · Docs / Manifest / Version
- [ ] T801 Update `HARNESS_MANIFEST.yaml` to 7.1.0 and declare new modules/contracts.
- [ ] T802 Update Skill/Harness/Self-Improvement/Adaptive-Learning/Corpus/Integration docs in EN + zh-CN.
- [ ] T803 Update README/CHANGELOG/Project SDK docs and default framework version.
- [ ] T804 Record external mechanism evidence/provenance from official framework docs.

## Phase 9 · Framework Verification
- [ ] T901 Final NovelForge CI green on exact 7.1 commit.
- [ ] T902 Bundle build/verify green and fingerprint recorded.
- [ ] T903 No consumer-project leakage in Framework source.

## Phase 10 · Chinatown Consumer Upgrade
- [ ] T1001 Update project minimum framework version to 7.1.0.
- [ ] T1002 Update exact lock commit + bundle fingerprint.
- [ ] T1003 Update framework attestation and 7.1 project validator contract.
- [ ] T1004 Run Chinatown Project CI green.
- [ ] T1005 Verify Canon/active-story state unchanged.

## Non-blocking follow-up
- [ ] F001 Physical removal/archive of historical embedded Generic OS source in `frostloom` after a separate bulk dependency-cleanup migration.
- [ ] F002 Original anime/manga-inspired repository hero binary and provenance.
