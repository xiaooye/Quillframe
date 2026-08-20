# Architecture Atlas

This Quillframe atlas is a map from concepts to current implementation owners. It is intentionally not another copy of the full production pipeline.

## Story and authority

- `core/STORY_SYSTEM.*` — generic story mechanics.
- `core/CHARACTER_SYSTEM.*` — character and relationship mechanics.
- `core/CANON_STATE.*` — Canon authority and state boundary.
- `harness/settlement_runtime.py` — authorized settlement transaction.

## Context and memory

- `harness/context_inspector.py` — mechanical eligibility and protected-state inspection.
- `harness/context_assembly.py` — exact selected-set, stage, authority, provenance, and fingerprint validation after semantic selection.
- `harness/memory_tiers.py` and `harness/memory_bank.py` — derived memory controls without Canon mutation.

## Semantic execution

- `harness/semantic_workers/model_contract_catalog.json` — contract registry index.
- `harness/semantic_workers/contracts/` — progressive-disclosure contract packs.
- `semantic_worker_router.py` — exact job packaging and validation.
- `semantic_worker_runner.py` and adapters — eligible execution transports.

## Quality

- `quality/candidate_qualification.py` — pre-independent candidate qualification.
- `quality/objective_envelope.py` — fingerprinted FIX + PRESERVE objective envelope.
- `quality/quality_evolution.py` — incumbent/challenger comparison ledger; `quality.compare` owns semantic winner judgment.
- `quality/repair_objective_regression.py` — repair-induced regression observation.
- `quality/regression_escape.py` — known-regression escape observability.
- `quality/candidate_lineage.py` — comparison ancestry, prose derivation, exact review receipt binding, non-authoritative acceptance evidence.
- `quality/candidate_lineage_runtime.py` — fail-closed lineage-aware facade.
- `quality/production_readiness.py` and `quality/production_release.py` — release-role invariants.

<img src="assets/concepts/objective-preserving-repair.en.svg" alt="FIX plus PRESERVE: repair the local defect while keeping the objective envelope intact" width="100%" />

## Session and control plane

- `harness/session_runtime/` — session/run/checkpoint identity, resume preflight, authorized runtime commands.
- `harness/control_plane/` — durable events, handoffs, receipts, and external work lifecycle.
- `harness/runtime_capabilities.py` — current host capability evidence.

## Learning and Corpus

- `learning/feedback_intake.py` — automatic bounded feedback capture.
- `learning/author_model.py` and `learning/learning_store.py` — durable evidence/hypothesis state.
- `learning/promotion_gate.py` — deterministic promotion prerequisites without write authority.
- `corpus/` — discovery, rights, provenance, and mechanism evidence.

## Project engineering

- `quillframe/launch.py` and `project_resolution.py` — canonical launch and native Project resolution.
- `release/build_framework_bundle.py` — deterministic framework bundle.

For the user-facing mental model, return to [Architecture](architecture.en.md).
