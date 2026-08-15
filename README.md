<div align="center">
  <img src="assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="640" />
  <p><strong>AI-native fiction production with explicit story authority, recoverable runtime state, and model-readable semantic contracts.</strong></p>
  <p><kbd>CANON BOUNDARIES</kbd>&nbsp;&nbsp;<kbd>CONTRACT PACKS</kbd>&nbsp;&nbsp;<kbd>RECOVERABLE RUNS</kbd>&nbsp;&nbsp;<kbd>QUALITY EVOLUTION</kbd>&nbsp;&nbsp;<kbd>EVIDENCE LEARNING</kbd></p>
  <p><a href="README.en.md"><strong>English</strong></a> · <a href="README.zh-CN.md"><strong>简体中文</strong></a> · <a href="docs/README.en.md"><strong>Documentation</strong></a></p>
</div>

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge · Adaptive Fiction Agent Framework

NovelForge is a project-agnostic framework for long-form and serialized fiction. It does not try to turn literary judgment into a pile of Python heuristics, and it does not treat one model completion as a finished chapter.

Its architecture is deliberately split:

> **Models own semantic fiction judgment. Deterministic code owns authority, permissions, fingerprints, persistence, routing, typed validation, hard budgets, transactions, and reproducibility.**

A consuming Project owns the facts of its story. NovelForge owns the generic production machinery around those facts.

**Development version:** NovelForge now uses pre-1.0 SemVer for the active development line. The machine manifest, CLI, Project SDK default, Skill metadata, and exposed MCP server metadata are aligned on **0.8.0**. During active development, the latest `main` branch remains the working implementation baseline; `0.8.0` is a development identity, not a frozen 1.0 compatibility promise. See the [8.0 Development Change Inventory](docs/8-0-development-inventory.en.md) and [Changelog](CHANGELOG.en.md).

<p align="center"><a href="docs/why-novelforge.en.md"><strong>Why NovelForge?</strong></a> · <a href="docs/production-pipeline.en.md"><strong>Production Pipeline</strong></a> · <a href="docs/quality-assurance.en.md"><strong>Quality & QA</strong></a> · <a href="docs/architecture-atlas.en.md"><strong>Architecture Atlas</strong></a></p>

---

## 01 · What problem is NovelForge solving? ✦

Long-running fiction fails in ways that short prompt workflows do not:

- a plan silently becomes “what already happened”;
- a character suddenly knows something they were never told;
- session memory outranks Accepted Canon;
- the model keeps polishing sentences when the actual failure is story structure;
- every reviewer sees a slightly different candidate;
- “memory” becomes an uncontrolled prompt dump;
- an eval, Corpus note, or learning hypothesis quietly acquires authority it never earned;
- a interrupted run cannot be resumed without guessing what already happened.

NovelForge treats those as system problems rather than prompt-writing problems.

Its distinctive mechanisms are **authority separation, sparse context, independent character state, explicit semantic contracts, recoverable sessions/runs, failure routing, transactional settlement, and evidence-backed learning**.

<img src="assets/ui/home-comparison.en.svg" alt="Evidence-led comparison of NovelForge, NovelClaw, Novel OS, AuthorAgent, and autonovel across long-form state, quality evolution, and publishing mechanisms" width="100%" />

For direct novel-agent/product positioning, tradeoffs, and source-backed comparison, read [Why NovelForge](docs/why-novelforge.en.md). General agent frameworks belong in the deeper [implementation-influence guide](knowledge/AGENT_FRAMEWORK_ADOPTION.en.md).

---

## 02 · The development mental model 🪄

<img src="assets/ui/home-architecture.en.svg" alt="NovelForge Story Loom architecture separating project authority, semantic model contracts, deterministic runtime shell, and evidence evolution" width="100%" />

NovelForge keeps four concerns separate even when they collaborate closely.

### Story authority

Project truth follows explicit authority classes such as `locked`, `accepted`, `active_plan`, `review`, and `proposal`. Plans, memories, semantic judgments, Corpus evidence, and runtime state do not become Canon merely because the system can see them.

### Semantic intelligence

Literary understanding is exposed through exact model-readable contracts. The runtime resolves a contract from `harness/semantic_workers/model_contract_catalog.json`, loads only the required pack from `harness/semantic_workers/contracts/`, packages bounded context and rubric, fingerprints the semantic job, and validates the typed result.

There is no monolithic semantic registry and no deterministic “literary score engine” pretending to understand prose.

### Deterministic shell

Python and workflow code own the parts that should actually be deterministic: permissions, persistence, fingerprints, session/run identity, checkpointing, consume-once semantics, authority boundaries, hard budgets, rights/provenance gates, release invariants, and reproducible project/framework builds.

### Project engineering

A novel is a versioned project with its own manifest, exact Framework lock, profiles, bible, Accepted Canon, state, plans, manuscripts, research, regressions, tests, and build artifacts. Chat history is never the project database.

Read [Architecture](docs/architecture.en.md) for the system view and [Architecture Atlas](docs/architecture-atlas.en.md) for subsystem ownership.

---

## 03 · A chapter is a production run, not one model call 📖

<img src="assets/ui/home-pipeline.en.svg" alt="NovelForge four-stage production run with freeze and simulation, internal candidate generation, diagnosis and evolution, release gate, and failure routing" width="100%" />

A DRAFT/REVISE run is organized around four responsibilities rather than one giant prompt.

### Prepare the run

Freeze only the context the current work actually needs. Reconfirm Project authority and Canon cutoff. Simulate the scene, character agendas/knowledge, and reader pressure before asking for prose.

### Create an internal candidate

Generate event-first Raw Draft material, then realize the prose surface. Raw Draft is internal and is never automatically promoted to the user-visible chapter.

### Diagnose the real failure

Post-generation checks may include Surface/Reader mechanisms, regression evidence, character integrity, reader reaction or comparison, revision diagnosis, continuity/state evidence, and other exact semantic contracts. Semantic work is bounded and fingerprinted; deterministic checks verify everything that does not require literary judgment.

### Repair the owning mechanism, then release

A sentence-level defect can be rewritten locally. A clustered realization failure may require scene regeneration. SAFE-BUT-FLAT goes back to Reader Pressure and Scene Simulation. Character failure returns to Character Simulation. Story failure returns to Story/Plan. Context failure returns to Context/Memory.

A candidate crosses the user-visible gate only after the applicable quality and continuity gates resolve.

Read [Production Pipeline](docs/production-pipeline.en.md).

---

## 04 · Quality means diagnosis, not one score ✅

<img src="assets/ui/home-quality.en.svg" alt="NovelForge quality system separating deterministic QA, semantic QA, quality evolution, and independent fingerprint-bound review" width="100%" />

NovelForge intentionally separates different kinds of evidence.

**Deterministic QA** catches things machines can prove: invalid schema, broken authority boundaries, hidden-gold leaks, lifecycle violations, stale fingerprints, duplicate consumption, bad project mapping, rights/provenance failures, missing capabilities, and release invariant failures.

**Semantic QA** asks the model questions that require understanding: does this character choice follow from the character's agenda and beliefs, what is a reader likely to feel or expect, why is a scene flat, what mechanism owns a revision problem, and which of two candidates better serves the supplied rubric.

When independence is mandatory, the judgment must come from a genuinely separate invocation/session and return a typed fingerprint-bound result. A valid `semantic_reject` is evidence to repair, not an excuse to shop for another reviewer.

Quality evolution tracks findings and candidate lineage so revision can stop when it plateaus instead of becoming endless rewrite churn.

Read [Quality & QA](docs/quality-assurance.en.md), [Quality Evolution](docs/quality-evolution.en.md), and [Eval Reference](evals/README.en.md).

---

## 05 · Context and memory are controllable, not magical 🧠

NovelForge treats persistent memory as a governed derived view, not as automatic prompt injection.

Context inspection can explain what entered the current working set and why. Memory tiers and the editable memory bank support author-visible control, but protected `accepted` / `locked` references cannot be silently rewritten through a memory editor. Editing protected truth produces a proposal or another explicitly non-authoritative artifact.

Semantic relevance belongs to model judgment when genuine interpretation is required; deterministic memory code enforces hard budgets, lifecycle, provenance, authority classes, and explicit controls instead of inventing pseudo-literary scalar relevance.

Read [Context & Memory](docs/context-and-memory.en.md).

---

## 06 · Runtime without confusing capability and authority 🔌

NovelForge can operate through a current chat, separate peer chat, local Codex/Claude invocation, provider API, MCP/service worker, GitHub job, local model, or human reviewer when the current host actually exposes the required capability.

A runtime name is not capability proof. A capability is not write authority.

The runtime model keeps `project/resource`, `session/thread`, `run/invocation`, and `checkpoint` separate so interrupted or external work can be resumed and validated without pretending provider history is Canon.

Read [Runtime & Integrations](docs/integrations.en.md), [Session Runtime](harness/session_runtime/SESSION_RUNTIME.en.md), and [Semantic Execution](harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md).

---

## 07 · Evidence-driven learning and Corpus intelligence 🔎

NovelForge can learn from direct edits, accepts/rejects, repeated correction patterns, project conventions, Corpus evidence, and evals—but learning never receives authority for free.

Preference and craft hypotheses remain scoped, contradictable, versioned, and rollbackable. Corpus discovery, rights classification, storage, semantic analysis, learning, and promotion are separate gates. Search success is not permission to mirror copyrighted text, and Corpus evidence is not Canon or automatic character knowledge.

Read [Adaptive Learning](docs/adaptive-learning.en.md) and [Corpus Intelligence](corpus/README.en.md).

---

## 08 · Project engineering ⚙️

```bash
python project_sdk.py init <path> --id PROJECT-X --title "Novel"
python project_sdk.py validate <path>
python project_sdk.py build <path>
python project_sdk.py self-test
```

Projects pin an exact NovelForge revision and can map legacy storage through a Project Adapter. Structural changes can use `spec → plan → tasks → implementation → verification → acceptance`; ordinary prose micro-edits do not need fake ceremony.

Read [Project SDK](docs/project-sdk.en.md), [Project Adapters](docs/project-adapters.en.md), and [Framework Bundle](release/FRAMEWORK_BUNDLE.en.md).

---

## 09 · Honest fit ⚖️

<img src="assets/ui/home-fit.en.svg" alt="NovelForge honest-fit guide showing strong-fit scenarios, lighter-tool scenarios, and explicit tradeoffs" width="100%" />

NovelForge is strongest when a fiction project is long-lived enough that authority, continuity, context control, resumability, model/runtime choice, QA provenance, and learning discipline genuinely matter.

It is deliberately heavier than a one-shot writing assistant. If the main goal is fast ideation, light rewriting, or a polished consumer editor, a simpler product may be the better choice.

The framework also does not pretend every semantic judgment is deterministic. Model or human review adds latency and cost; the point is to make those judgments explicit, bounded, inspectable, and unable to mutate story truth by accident.

---

<img src="assets/brand/story-thread.svg" alt="" width="100%" />

## 10 · Documentation 🌸

<p align="center"><a href="docs/README.en.md"><strong>Docs Home</strong></a> · <a href="docs/why-novelforge.en.md"><strong>Positioning</strong></a> · <a href="docs/architecture-atlas.en.md"><strong>Architecture Atlas</strong></a> · <a href="docs/production-pipeline.en.md"><strong>Production Pipeline</strong></a> · <a href="docs/quality-assurance.en.md"><strong>Quality & QA</strong></a> · <a href="assets/DESIGN_SYSTEM.en.md"><strong>Story Loom Design</strong></a></p>

<div align="center">
  <img src="assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="58" />
  <br />
  <sub><strong>Strict backstage. Vivid fiction.</strong> 🌸</sub>
</div>