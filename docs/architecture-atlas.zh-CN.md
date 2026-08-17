# 架构图谱

这份 Quillframe Atlas 只把 concept 映射到 current implementation owner，不再复制一遍完整 production pipeline。

## Story 与 Authority

- `core/STORY_SYSTEM.*`：通用 story mechanics。
- `core/CHARACTER_SYSTEM.*`：character / relationship mechanics。
- `core/CANON_STATE.*`：Canon authority 与 state boundary。
- `harness/settlement_runtime.py`：authorized settlement transaction。

## Context 与 Memory

- `harness/context_inspector.py`：mechanical eligibility 与 protected-state inspection。
- `harness/context_assembly.py`：semantic selection 之后，对 exact selected set、stage、authority、provenance 与 fingerprint 做验证。
- `harness/memory_tiers.py`、`harness/memory_bank.py`：derived memory control，不获得 Canon mutation 权限。

## Semantic Execution

- `harness/semantic_workers/model_contract_catalog.json`：contract registry index。
- `harness/semantic_workers/contracts/`：progressive-disclosure contract packs。
- `semantic_worker_router.py`：exact job packaging / validation。
- `semantic_worker_runner.py` 与 adapters：eligible execution transport。

## Quality

- `quality/candidate_qualification.py`：pre-independent candidate qualification。
- `quality/objective_envelope.py`：fingerprinted FIX + PRESERVE objective envelope。
- `quality/quality_evolution.py`：incumbent/challenger comparison ledger；semantic winner 仍由 `quality.compare` 判断。
- `quality/repair_objective_regression.py`：repair-induced regression observation。
- `quality/regression_escape.py`：known-regression escape observability。
- `quality/candidate_lineage.py`：comparison ancestry、prose derivation、exact review receipt binding、non-authoritative acceptance evidence。
- `quality/candidate_lineage_runtime.py`：fail-closed lineage-aware facade。
- `quality/production_readiness.py`、`quality/production_release.py`：release-role invariant。

<img src="assets/concepts/objective-preserving-repair.zh-CN.svg" alt="FIX + PRESERVE：修复局部缺陷，同时保持 objective envelope 完整" width="100%" />

## Session 与 Control Plane

- `harness/session_runtime/`：session/run/checkpoint identity、resume preflight、authorized runtime command。
- `harness/control_plane/`：durable event、handoff、receipt 与 external work lifecycle。
- `harness/runtime_capabilities.py`：current host capability evidence。

## Learning 与 Corpus

- `learning/feedback_intake.py`：automatic bounded feedback capture。
- `learning/author_model.py`、`learning/learning_store.py`：durable evidence/hypothesis state。
- `learning/promotion_gate.py`：deterministic promotion prerequisite，不授予 write authority。
- `corpus/`：discovery、rights、provenance 与 mechanism evidence。

## Project Engineering

- `project_sdk.py`、`project_adapter.py`：standalone Project contract 与 mapped legacy layout。
- `release/build_framework_bundle.py`：deterministic framework bundle。

面向使用者的 mental model 见[总体架构](architecture.zh-CN.md)。
