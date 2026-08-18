# Quillframe

**A production framework for long-form fiction that keeps story truth, creative judgment, and execution state from quietly becoming the same thing.**

<img src="docs/assets/brand/quillframe-mark.svg" alt="Quillframe mark: a manuscript page crossed by a single narrative thread" width="92" />

Quillframe is built for fiction that lasts longer than one prompt, one model call, or one session. It treats continuity, authority, revision, review, learning, and recovery as first-class production problems while leaving literary judgment where it belongs: with capable models or humans.

<img src="docs/assets/architecture/framework-mental-model.en.svg" alt="Quillframe mental model: Project authority feeds a manager, sparse execution and verification, then an explicitly authorized settlement boundary" width="100%" />

## Why this exists

Long-form fiction accumulates different kinds of truth. A plan describes future intent. A Review Draft is a candidate. Accepted prose is an explicit editorial decision. Settled state is the durable consequence of that decision. Research, Corpus evidence, telemetry, learning hypotheses, and runtime receipts are useful, but none of them become story truth merely because the system has seen them.

Quillframe keeps those categories separate, then makes them collaborate through explicit contracts.

## Core architecture

**Project authority owns story facts.** `locked`, `accepted`, `active_plan`, `review`, and `proposal` remain distinct. Plan is not Canon. Review is not Accepted. Accepted is not Settled.

**Models own semantic judgment.** Story interpretation, character plausibility, reader response, repair diagnosis, relevance, comparison, and learning interpretation use bounded model-readable contracts.

**Deterministic code owns execution truth.** Identity, permissions, fingerprints, provenance, persistence, consume-once receipts, hard budgets, routing, transactions, and fail-closed state transitions are mechanically verifiable.

**Independent review is actually independent.** When a gate requires independence, the reviewer must be a genuinely separate invocation or session and must judge the exact fingerprinted candidate.

## Writing is a production graph

A chapter does not move directly from prompt to publication. Context is selected sparsely, story and character conditions are simulated, an internal candidate is generated, quality evidence is gathered, defects are routed to the mechanism that owns them, and only a qualified candidate reaches independent review and the user-visible gate.

Repairs follow **FIX + PRESERVE**: improve the targeted defect without silently degrading the objective envelope, reader value, or character/relationship energy. Fresh regeneration may compete with an incumbent without inheriting rejected prose. Candidate Lineage records both comparison ancestry and prose derivation so those two meanings cannot be conflated.

## Quick start

```bash
python project_sdk.py init <path> --id PROJECT-X --title "Novel"
python project_sdk.py validate <path>
python project_sdk.py build <path>
```

A production Project pins an exact framework revision for runtime reproducibility. Documentation for active framework development follows current `main`; a consumer pin remains a separate integration fact.

## Key concepts

- [Architecture](docs/architecture.en.md) — authority, semantic execution, deterministic runtime, and settlement.
- [Production pipeline](docs/production-pipeline.en.md) — from sparse context to the user-visible gate.
- [Quality assurance](docs/quality-assurance.en.md) — pre-independent qualification, FIX + PRESERVE, fingerprint binding, and release truth.
- [Candidate Lineage](docs/CANDIDATE_LINEAGE_V1.en.md) — comparison parent, prose parent, review receipts, and non-authoritative acceptance evidence.
- [Context & memory](docs/context-and-memory.en.md) — sparse context without turning memory into hidden Canon.
- [Adaptive learning](docs/adaptive-learning.en.md) — automatic capture with governed promotion.
- [Runtime & integrations](docs/integrations.en.md) — sessions, runs, checkpoints, capabilities, and independent execution.
- [Project SDK](docs/project-sdk.en.md) — the Project/Framework boundary.

## Compatibility note

**Quillframe is the public brand. `Quillframe` remains the legacy technical namespace for compatibility.** Identifiers such as `quillframe.toml`, `quillframe.lock.json`, `quillframe_*` schemas, existing workflow names, repository paths, and stable contract IDs are not renamed by this documentation migration.

The framework is currently on the pre-1.0 `0.9.0` development line. During active development, current implementation truth comes from the exact `main` commit being documented, not from older prose documentation.

[Documentation home](docs/README.en.md) · [中文](README.zh-CN.md)
