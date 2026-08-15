<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="580" />
  <p><strong>Start with the product model. Drop into contracts only when you need exact execution semantics.</strong></p>
  <p><kbd>ORIENT</kbd>&nbsp;&nbsp;<kbd>BUILD</kbd>&nbsp;&nbsp;<kbd>WRITE</kbd>&nbsp;&nbsp;<kbd>VERIFY</kbd>&nbsp;&nbsp;<kbd>OPERATE</kbd></p>
  <p><strong>English</strong> · <a href="README.zh-CN.md">简体中文</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge Documentation

NovelForge documentation is organized by **reader intent**, not by source-tree shape.

The current development implementation is AI-native and contract-first: models own semantic fiction judgment; deterministic code owns authority, permissions, fingerprints, persistence, routing, typed validation, transactions, hard budgets, and reproducibility. Release authority remains `HARNESS_MANIFEST.yaml`; development implementation metadata does not promote a Framework release. See the [Changelog](../CHANGELOG.en.md) for the current release-truth ledger.

This documentation follows the same separation. Product pages explain the mental model and tradeoffs. Guides show how to use a subsystem. Deep contracts define exact invariants.

---

## 01 · If you are evaluating NovelForge ✦

Start with these four pages:

**[Why NovelForge](why-novelforge.en.md)** explains the product thesis, direct novel-agent/framework alternatives, mature author products, tradeoffs, and where NovelForge is not the best fit.

**[Architecture](architecture.en.md)** gives the system-level mental model: Project authority, semantic intelligence, deterministic runtime, state separation, and write boundaries.

**[Production Pipeline](production-pipeline.en.md)** explains how DRAFT/REVISE become production runs rather than one-shot model calls.

**[Quality & QA](quality-assurance.en.md)** explains deterministic QA, semantic contracts, independent review, findings, candidate evolution, and release gates.

For subsystem ownership and deep links, continue to **[Architecture Atlas](architecture-atlas.en.md)**.

---

## 02 · If you are integrating a fiction project ⚙️

Read **[Project SDK](project-sdk.en.md)** first. It defines what a complete consuming project must own: manifest, exact Framework lock, Project-owned Canon/state, plans, manuscripts, research, regressions, tests, and build outputs.

If the project already has a legacy directory layout, continue to **[Project Adapters](project-adapters.en.md)** and the exact **[Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md)**.

Important boundary: the generic Framework never becomes the database for one novel. Dependency direction remains Project → pinned NovelForge.

---

## 03 · If you are writing or revising fiction 📖

Use the fiction-mechanics layer in this order:

**[Story System](../core/STORY_SYSTEM.en.md)** — story units, pressure, causal movement, structural ownership.

**[Character & Relationship System](../core/CHARACTER_SYSTEM.en.md)** — agenda, beliefs, knowledge boundaries, independent action, relationship state.

**[Canon State](../core/CANON_STATE.en.md)** — what is locked, accepted, planned, under review, or merely proposed.

**[Surface Fundamentals](../surface/FUNDAMENTALS.en.md)** — recurring AI-prose failure mechanisms and their repair ownership.

**[Reader Engagement](../surface/READER_ENGAGEMENT.en.md)** — reader pressure, payoff, causality, grip, expectation, and chapter-level experience.

The production graph that combines them lives in **[Production Pipeline](production-pipeline.en.md)**.

---

## 04 · If you are working with context or memory 🧠

Read **[Context & Memory](context-and-memory.en.md)**.

The important idea is simple: persistent storage is not automatic prompt injection. Project authority, derived memory, runtime state, and model inference remain distinct.

Context inspection explains what entered the working set. Memory tiers and the editable memory bank provide explicit controls. Protected `accepted` / `locked` references cannot be silently rewritten through a memory editor.

When semantic relevance requires actual interpretation, the model owns that judgment. Deterministic memory code enforces hard budgets, provenance, lifecycle, authority class, and explicit controls.

---

## 05 · If you are operating the runtime 🔌

Read **[Runtime & Integrations](integrations.en.md)** for the practical entry point.

Then use the exact contracts as needed:

- **[Harness Agent](../harness/HARNESS_AGENT.en.md)** — manager ownership and run responsibilities;
- **[Orchestration Protocol](../harness/ORCHESTRATION_PROTOCOL.en.md)** — how one task run progresses;
- **[Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md)** — session/run/checkpoint identity and recovery;
- **[Runtime Capabilities](../harness/session_runtime/RUNTIME_CAPABILITIES.en.md)** — what the current host can actually do;
- **[Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.en.md)** — how an eligible execution path is selected;
- **[Control Plane](../harness/control_plane/CONTROL_PLANE.en.md)** — durable external work and consume-once result handling;
- **[Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md)** — bounded semantic jobs and results;
- **[Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md)** — transport, validation, receipts, and consumption.

Runtime capability never grants story authority by itself.

---

## 06 · If you are working with semantic model contracts ✦

The current development implementation uses a progressively disclosed contract system.

The deterministic index is:

`harness/semantic_workers/model_contract_catalog.json`

Concrete packs live under:

`harness/semantic_workers/contracts/`

The catalog is the only registry index. A run resolves an exact contract ID, loads only the necessary pack, packages bounded input/rubric/output contract, computes a semantic fingerprint, and validates the typed result.

This keeps literary intelligence in the model without letting model output bypass authority, permissions, or persistence rules.

---

## 07 · If you are auditing quality or revision ✅

Start with **[Quality & QA](quality-assurance.en.md)**, then continue to **[Quality Evolution](quality-evolution.en.md)** and **[Eval Reference](../evals/README.en.md)**.

Think in layers:

**Deterministic QA** proves machine-checkable invariants.

**Semantic contracts** answer questions requiring interpretation.

**Findings** make diagnosis explicit and traceable.

**Failure routing** returns a defect to the mechanism that owns it.

**Candidate evolution** tracks lineage and supports plateau stopping rather than endless rewriting.

**Independent review**, when mandatory, must come from a genuinely separate invocation/session and return a fingerprint-bound typed result.

---

## 08 · If you are working with learning or Corpus evidence 🔎

Read **[Adaptive Learning](adaptive-learning.en.md)** for preference/craft learning and **[Corpus Intelligence](../corpus/README.en.md)** for governed external evidence.

Deep policy references:

- [Corpus Policy](../corpus/CORPUS_POLICY.en.md)
- [Corpus Ingest Protocol](../corpus/CORPUS_INGEST_PROTOCOL.en.md)
- [Self-Improvement Protocol](../harness/SELF_IMPROVEMENT_PROTOCOL.en.md)
- [Continuous Maintenance](../harness/CONTINUOUS_MAINTENANCE.en.md)

Discovery, access, rights, storage, semantic analysis, learning, and promotion are separate gates. Corpus is not Canon. Model inference is not durable user taste. General Craft requires evidence, counterexamples/profile boundaries, eval coverage, versioning, rollback, and green deterministic validation.

---

## 09 · If you are comparing frameworks or runtimes 🧭

Use two different comparison layers.

**Product positioning:** [Why NovelForge](why-novelforge.en.md) compares NovelForge primarily with direct novel-writing agents/frameworks and distinguishes mature author products from engineering frameworks.

**Implementation influence:** [Agent Framework Adoption](../knowledge/AGENT_FRAMEWORK_ADOPTION.en.md) examines general runtimes and agent frameworks such as LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, coding-agent runtimes, MCP, and related engineering patterns.

Do not collapse these into one homepage comparison. They answer different questions.

---

## 10 · Documentation tiers 🌸

**Tier A · Product surfaces** — README, Docs Home, Why, Architecture, Pipeline, QA. These pages must be understandable without reading implementation files and must receive the strongest copy/visual QA.

**Tier B · Guides** — Project SDK, integrations, learning, Corpus, evals, context/memory, quality evolution. These pages optimize for practical understanding and happy-path use.

**Tier C · Contracts and records** — Harness, runtime, semantic worker, Story/Character/Canon, Surface/Reader, Corpus policy, historical specs. These optimize for exact boundaries and stable semantics rather than decorative presentation.

Historical specs and changelogs preserve their original meaning; documentation cleanup must not rewrite history into current-product claims.

The repository-wide authoring and QA rules live in **[Documentation Standard](DOCUMENTATION_STANDARD.en.md)** and **[Documentation QA](DOCUMENTATION_QA.en.md)**.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <br />
  <sub>Read only as deep as the task requires. 🌸</sub>
</div>