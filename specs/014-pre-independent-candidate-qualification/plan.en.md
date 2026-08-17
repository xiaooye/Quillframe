# Plan 014 · Pre-Independent Candidate Qualification

## Phase 1 · Authority and drift
- [x] Consumer lock and attestation match exactly.
- [x] Framework `main` HEAD and consumer pin are `f7732856311814d82012159e5856c4aa592007a5`.
- [x] PR #102 remains separate and unmerged; this work branches independently from `main`.
- [x] Generic/consumer post-generation ordering drift is confirmed.
- [x] Surface, Reader, semantic, readiness/release, repair, session/runtime contracts inspected.
- [x] Current primary-source research completed.

## Phase 2 · Contracts
1. Add `quality.candidate_self_audit` to the existing quality semantic pack.
2. Add `quality/candidate_qualification.py` and schema for fingerprint-bound `independent=false` qualification receipts.
3. Require qualification proof before constructing a `quality.production_review` job while keeping proof out of reviewer-visible semantic input.
4. Add qualification defense-in-depth to production readiness/release.
5. Preserve regression isolation and fresh-realization rejected-prose isolation.

## Phase 3 · Semantic behavior
Self-audit covers sentence/block/cluster scales plus Delete Test, micro-action function, explanation-after-evidence, synthetic coolness, AI explanation tone, SAFE-BUT-FLAT interface, semantic ownership, and the addendum's function → ownership → natural realization test.

It also distinguishes character-owned humor from author-optimized wit and checks narrator clever reframing plus punchline stacking. No lexical bans and no new HF code in this change.

## Phase 4 · Deterministic tests
Cover missing/failed/pending qualification, fingerprint mismatch, stale qualification after repair, unresolved blocking findings, independent PASS unable to override self-audit failure, manager self-audit never satisfying independence, qualification metadata not contaminating reviewer input, first-pass regression isolation, and normal CI with no live model usage.

## Phase 5 · Semantic fixtures / ablation
Use anonymized synthetic fixtures for the requested 20 controls plus functional-but-overwritten dialogue/natural control, narrator clever reframing/POV-owned metaphor control, and punchline stacking/sparse natural humor control.

Pair BEFORE (functional implies pass) with AFTER (function then ownership and natural realization). Deterministic CI only packages/validates the semantic work; live semantic execution remains separate and reports `PENDING_MODEL` when no eligible reviewer is available.

## Phase 6 · Docs / release
Synchronize HARNESS_MANIFEST, Skill/Harness, production pipeline, semantic catalog/pack, quality gates, CI, and required documentation governance. Do not modify the consumer Project inside the Framework PR; report its stale `START_HERE` order as a separate migration recommendation.

## Phase 7 · Verification
Run PR deterministic CI, inspect exact diff/privacy/bundle-fingerprint implications and semantic-ablation state, open a draft PR, and do not merge or repin automatically.

## Objective-preservation extension

1. Bind a compact current objective envelope before material repair.
2. Make Editor repair plans carry FIX and PRESERVE.
3. Isolate fresh realization from rejected trajectories while retaining authoritative current state.
4. Upgrade incumbent/challenger comparison to classify target-not-fixed vs objective-regression vs successful-repair.
5. Require repair-preservation evidence before independent dispatch for repaired candidates.
6. Run deterministic synthetic controls in normal CI; keep multi-turn/negative-context semantic ablations `PENDING_MODEL` until separate writer/evaluator execution is available.
