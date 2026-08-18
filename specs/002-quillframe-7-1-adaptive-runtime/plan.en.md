# Plan · NovelForge 7.1 Adaptive Runtime

## Strategy

Implement 7.1 as a deterministic shell around optional host/model capabilities. The shell owns identity, state transitions, fingerprints, provenance, rights/storage policy, idempotency, queue construction, promotion prerequisites, bundle materialization and verification. Hosts/models perform only the work they actually have capability for.

## Phase 1 · Capability Contract

Create `harness/runtime_capabilities.py` with:
- `novelforge_host_capabilities_v1` schema;
- local probe for executable/runtime facts that can be proven locally;
- normalization for externally supplied Chat/MCP/Web/GitHub capability declarations;
- requirement resolution that never selects undeclared/unavailable capability;
- usage/cost/user-interaction metadata;
- self-test.

Add paired runtime-capability documentation and wire it into Runtime Routing.

## Phase 2 · Discovery Runtime

Create `corpus/discovery_runtime.py` with:
- typed dispatch plan built from Corpus Scout requests + host capabilities;
- typed discovery result validation;
- source/tool/channel provenance binding;
- evidence fingerprint;
- deterministic rights/storage validation using `rights_gate.py`;
- dedupe by source locator/content fingerprint;
- diversity summary by work/source/channel;
- self-test.

Upgrade `corpus_scout.py` request schema so each requested channel declares a capability requirement rather than assuming host access.

## Phase 3 · Learning Cycle

Create `learning/learning_cycle.py` with a SQLite-backed state machine in the same learning DB, but separate cycle tables. It will:
- start from an existing Corpus gap/hypothesis;
- persist cycle identity/state/version;
- register discovery queues/results;
- register analysis/eval queues/results by fingerprint;
- enforce legal transitions;
- enforce logical consume-once;
- resume from durable state;
- never grant Canon/Framework-write authority;
- self-test crash/retry/idempotency semantics.

## Phase 4 · Semantic Learning Work

Create `learning/learning_eval.py` to package:
- `corpus_analyze` semantic jobs from verified discovery evidence;
- `preference_distill` or `external_review` jobs when scope requires;
- `eval_judge` jobs for capability/regression evidence;
- typed output contracts for mechanism, counterexample, boundary, evidence refs and confidence.

Use the existing semantic fingerprint function; execution lineage remains outside semantic fingerprint.

No hidden gold or expected labels enter worker packets.

## Phase 5 · Promotion Gate

Create `learning/promotion_gate.py`.

Rules:
- `one_off`: never durable promotion;
- `project`: may become project proposal/active preference only with project authority, not from Generic Framework code;
- `user_taste`: requires explicit/repeated human evidence + contradiction review + eval evidence; gate can mark ready but not persist private taste to Generic source;
- `general_craft`: requires cross-work evidence, counterexample/profile boundary, capability+regression eval, target version, rollback ref and green CI evidence.

The gate outputs evidence completeness and blockers. It never edits Framework behavior.

## Phase 6 · Immutable Bundle

Create `release/build_framework_bundle.py` and paired docs.

Bundle rules:
- sorted paths;
- deterministic tar metadata (`mtime=0`, fixed uid/gid/mode normalization);
- exclude `.git`, generated artifacts, runtime DBs, specs and bundle metadata from runtime bundle by policy;
- include Generic Core/Surface/Harness/Learning/Corpus/Evals/SDK/docs/runtime bootstrap;
- content manifest with per-file SHA-256;
- overall bundle SHA-256;
- verify command;
- self-test reproduces identical fingerprint and detects tamper.

Create optional `novelforge-release-bundle.yml` to build/verify/upload the immutable artifact. Normal CI validates the builder but does not publish a release or spend model usage.

## Phase 7 · CLI / CI / Maintenance

Upgrade `novelforge.py`:
- framework version 7.1.0;
- `capabilities` router;
- `learning-cycle` router;
- `learning-gate` router;
- `corpus discovery` router;
- `bundle` router;
- self-test covers all deterministic modules.

Upgrade reusable CI:
- compile all modules;
- run new self-tests;
- assert no model execution;
- build bundle twice and compare fingerprints;
- inspect adaptive queue invariants.

Upgrade weekly maintenance:
- probe only available deterministic/local capabilities;
- create learning/discovery work queues;
- report pending capability requirements;
- never claim unexecuted Web/model work;
- never auto-promote.

## Phase 8 · Docs / Manifest / Version

Update:
- `HARNESS_MANIFEST.yaml` → 7.1.0;
- `SKILL.md`, `SKILL.en.md`, `SKILL.zh-CN.md`;
- Harness/Runtime Routing/Self-Improvement docs;
- adaptive-learning docs;
- Corpus docs/policy;
- integrations docs;
- Project SDK docs;
- README + CHANGELOG;
- `project_sdk.py` default/minimum version behavior.

Record external mechanism evidence from official OpenAI Agents SDK, LangGraph, MCP and Google ADK docs without turning them into dependencies.

## Phase 9 · Framework Release Verification

1. Push implementation on `main`.
2. Wait for final NovelForge CI.
3. If failed, repair the owning mechanism; do not bless a failing commit.
4. Once green, run deterministic bundle workflow/build and capture fingerprint.
5. Commit bundle attestation metadata if needed; bundle metadata itself remains outside fingerprint input so no circular hash.
6. Re-run CI and verify final framework HEAD.

## Phase 10 · Chinatown Consumer Upgrade

After final 7.1 framework HEAD is green:
- update `novelforge.toml` minimum framework version to 7.1.0;
- update `novelforge.lock.json` exact commit + bundle fingerprint;
- update framework attestation;
- update Project bootstrap docs only where 7.1 capability/bundle semantics matter;
- strengthen project validator to require bundle fingerprint for 7.1 locks;
- run Chinatown Project CI;
- verify no Canon/active-story mutation.

## Rollback

Framework rollback: `de05666cc4eae13f09868d87659e76f2aa524314`.

Consumer rollback: restore the last 7.0 lock/attestation and project bootstrap commit if the 7.1 consumer gate fails. No Canon migration is part of this release.
