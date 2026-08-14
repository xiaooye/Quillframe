<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Architecture · models interpret fiction; deterministic systems bind authority and execution</strong></p>
  <p><kbd>PROJECT AUTHORITY</kbd>&nbsp;&nbsp;<kbd>SEMANTIC CONTRACTS</kbd>&nbsp;&nbsp;<kbd>RUNTIME SHELL</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd>&nbsp;&nbsp;<kbd>SETTLEMENT</kbd></p>
  <p><a href="architecture.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# NovelForge Architecture

NovelForge is built around a refusal to blur **story truth**, **model judgment**, **runtime state**, and **evidence** into one giant prompt or one opaque agent memory.

The Framework uses AI for the things that actually require interpretation, and deterministic machinery for the things that must remain exact.

<img src="../assets/ui/home-architecture.en.svg" alt="NovelForge architecture separating Project authority, semantic contracts, deterministic runtime shell, and evidence evolution" width="100%" />

---

## 01 · The architecture in one sentence

> **Projects own story truth. Models own semantic interpretation. Deterministic runtime owns execution invariants. Evidence may inform decisions, but it never gains authority by accident.**

That sentence explains most design decisions in the repository.

A session can remember something without making it Canon. A model can diagnose a character problem without gaining write permission. Corpus evidence can change a hypothesis without becoming character knowledge. A user-visible Review Draft can pass QA without automatically entering Accepted Canon.

---

## 02 · Project authority is the top boundary

NovelForge is generic. A consuming fiction Project is authoritative for its own instances and facts.

The Project owns, as applicable:

- project identity and manifest;
- exact pinned NovelForge dependency;
- project profile and prose profile;
- story bible and research decisions;
- Accepted Canon and current state;
- active plans and review artifacts;
- character / relationship instances;
- manuscripts;
- project regressions and tests;
- explicit acceptance and Canon-change evidence.

NovelForge owns the reusable mechanisms that operate on those structures. It must not absorb one consumer's plot, characters, or private taste into generic Framework truth.

The dependency direction is therefore always:

**consuming Project → exact NovelForge revision**

Never the reverse.

Deep references: [Project SDK](project-sdk.en.md) · [Project Adapters](project-adapters.en.md) · [Canon State](../core/CANON_STATE.en.md)

---

## 03 · Fiction mechanics define what must be represented

Generic Story, Character / Relationship, Canon / State, Surface, and Reader mechanisms define the fiction-native concepts the system must preserve.

The Story System owns structural units, causal pressure, open loops, and story-level failure ownership.

The Character / Relationship System owns agenda, beliefs, knowledge boundaries, independent action, relationship position, obligations, spatial state, and aftermath.

Canon / State owns the authority distinction among facts that are locked, accepted, planned, under review, or merely proposed.

Surface Fundamentals and Reader Engagement describe different quality layers: realization quality versus the actual reading experience.

These are **semantic and structural contracts**, not a claim that all of fiction can be computed deterministically.

Deep references: [Story](../core/STORY_SYSTEM.en.md) · [Character](../core/CHARACTER_SYSTEM.en.md) · [Canon](../core/CANON_STATE.en.md) · [Surface](../surface/FUNDAMENTALS.en.md) · [Reader](../surface/READER_ENGAGEMENT.en.md)

---

## 04 · Semantic intelligence is contract-first and progressively disclosed

NovelForge does not route literary work through one giant critic prompt or a monolithic semantic registry.

The small deterministic catalog lives at:

`harness/semantic_workers/model_contract_catalog.json`

The catalog lists high-level packs and when they are relevant. The manager / model selects the smallest relevant pack; deterministic runtime then resolves an **exact contract ID** to exactly one pack.

Current contract domains include:

**Quality** — reader reaction / comparison, character integrity, revision diagnosis.

**Narrative memory** — derived narrative-state interpretation, reader expectations, memory consolidation.

**Learning** — craft-mechanism analysis and blind evaluation.

**Context / research** — semantic context selection and Corpus discovery planning.

**Story simulation** — character action proposals and scene-level causal resolution.

**Long horizon** — active-plan reconciliation, relationship-memory reconciliation, narrative-commitment auditing.

**Creative evolution** — scenario divergence and evidence-based incumbent / challenger comparison.

The catalog stays small by design. The runtime must not keyword-route literary intent on the model's behalf, and it must not load every semantic pack by default.

Deep reference: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md)

---

## 05 · A semantic result is bounded evidence, not authority

Every semantic job is packaged with bounded input, rubric, output contract, permissions, and an exact semantic fingerprint.

The fingerprint identifies **what semantic question was asked of what evidence**. Execution lineage—such as which worker session, provider attempt, or handoff carried the work—is tracked separately.

This separation makes several guarantees possible:

- material artifact changes invalidate stale review bindings;
- transport retry does not silently change the semantic task;
- typed validation can reject malformed or misbound output;
- a result can be consumed once without becoming a hidden source of truth;
- model judgment can be useful without gaining Canon, Framework-write, or durable-user-taste authority.

When independence is mandatory, the semantic execution must additionally come from a genuinely separate invocation / session. Independence is a property of the gate, not a property automatically claimed by every semantic contract.

Deep reference: [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md)

---

## 06 · The deterministic shell owns execution invariants

The Harness and runtime code are intentionally less “creative.” They own the parts of the system that benefit from exact rules.

This includes:

- task-mode identity;
- Project / Framework compatibility;
- session, run, checkpoint, event, and handoff identity;
- runtime capability discovery;
- routing constraints;
- artifact and job fingerprints;
- permission checks;
- lifecycle and consume-once behavior;
- leases, idempotency, and resume safety;
- hard context / memory budgets;
- typed validation;
- durable Control Plane state;
- rights / provenance gates;
- reproducible project and Framework builds;
- settlement transactions and postconditions.

The shell transports and constrains intelligence. It does not replace it with fake literary heuristics.

Deep references: [Harness](../harness/HARNESS_AGENT.en.md) · [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md) · [Runtime Capabilities](../harness/session_runtime/RUNTIME_CAPABILITIES.en.md) · [Control Plane](../harness/control_plane/CONTROL_PLANE.en.md)

---

## 07 · Runtime identity is intentionally not Project identity

NovelForge separates four concepts that are often conflated:

**Resource / Project** — the durable thing being worked on.

**Session / Thread** — a continuing working relationship or execution context.

**Run / Invocation** — one bounded attempt to perform a task.

**Checkpoint** — a resumable record of before-state and pending work.

Provider conversation IDs, local process IDs, GitHub jobs, MCP handoffs, and human-review sessions can all participate in this model, but none of them is the Project and none grants story authority.

This is what makes external waits and interrupted work resumable without treating provider history as Canon.

---

## 08 · Capability is discovered; authority is granted separately

NovelForge can run across different hosts: current chat, peer chat, local Codex / Claude, provider APIs, MCP workers, GitHub jobs, local models, and humans.

But a runtime label is not proof that a capability exists. The current host must expose the required capability under the current permission and usage constraints.

Even then:

> **capability ≠ authority**

A tool that can technically write files does not thereby gain Canon-write permission. A model that can search the web does not gain permission to ingest copyrighted text. A reviewer capable of judging prose does not gain permission to settle the result.

Deep reference: [Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.en.md)

---

## 09 · Context is selected, not inherited

NovelForge uses **complete schema, sparse injection**.

Project storage may be rich and durable, but each invocation receives only the slice needed for its current contract.

Context can include Accepted state, active plans, relevant character / relationship state, research evidence, commitments, and derived memory—but only when current work needs them.

When relevance itself requires interpretation, `context.select` is model-owned semantic work. Deterministic context machinery still owns budget, provenance, authority class, and packaging constraints.

Persistent memory follows the same principle. Memory Bank and memory tiers are author-visible derived controls, not a new Canon database. Protected `accepted` / `locked` facts cannot be silently edited through memory tooling.

Deep guide: [Context & Memory](context-and-memory.en.md)

---

## 10 · Durable state is split by authority domain

Several kinds of state persist across runs, but they remain intentionally different.

**Project state** contains Canon, current state, plans, research decisions, manuscripts, and other Project-owned records.

**Runtime state** contains sessions, checkpoints, waits, events, handoffs, leases, and result receipts.

**Learning state** contains preference evidence, revisable hypotheses, Corpus gaps, learning candidates, evaluation evidence, promotion history, and rollback information.

**Derived narrative / memory state** can compact or reconcile evidence for future use, but remains non-authoritative unless Project rules explicitly promote something through an allowed boundary.

References may cross domains. Authority does not.

---

## 11 · Quality is evidence + repair ownership + evolution

Quality architecture is not “run more critics.”

Deterministic QA proves machine-checkable invariants.

Surface / Reader mechanisms define generic quality questions.

Model-readable quality contracts produce reader, character, and revision evidence.

Typed findings make problems traceable.

Repair ownership sends defects back to Story, Plan, Scene, Character, Reader Pressure, Surface, Continuity, Context / Memory, Research, Runtime, or Human escalation as appropriate.

Quality Evolution keeps candidate fingerprints and lineage so an incumbent can be compared against a challenger. Revision can admit ties and stop at a plateau rather than assuming every iteration improves the artifact.

Deep references: [Quality & QA](quality-assurance.en.md) · [Quality Evolution](quality-evolution.en.md)

---

## 12 · Long-horizon state is interpreted without becoming a second Canon

Serialized fiction needs memory beyond the current scene, but blindly persisting model summaries creates another authority problem.

NovelForge therefore treats long-horizon views as source-bound, derived evidence.

Semantic contracts can:

- reconcile an active plan after causal emergence;
- reconcile conflicting relationship memories against evidence;
- audit explicit narrative commitments;
- interpret reader expectations from reader-visible text;
- consolidate rebuildable memory.

Deterministic state graph / ledger layers may persist structure and provenance, but those derived views explicitly have no automatic Canon authority.

---

## 13 · Evidence, Corpus, and learning live outside story truth

Corpus Intelligence and Adaptive Learning form an evidence domain, not a hidden content domain.

Corpus work separates discovery, access, rights classification, storage, semantic analysis, learning, and promotion. Search success is not permission to store or redistribute a source.

Learning separates evidence from hypothesis and hypothesis from promotion. Model inference alone cannot become durable user taste or General Craft.

General Craft requires stronger evidence such as cross-work support, counterexamples or profile boundaries, eval coverage, provenance, versioning, rollback, and green deterministic validation.

Neither Corpus evidence nor learning output becomes Canon or character knowledge automatically.

Deep references: [Corpus Intelligence](../corpus/README.en.md) · [Adaptive Learning](adaptive-learning.en.md)

---

## 14 · Settlement is the only high-authority mutation path

Generation, semantic review, quality gates, and user acceptance do not themselves write Canon.

`SETTLE` uses a deterministic transaction runtime that requires explicit accepted-artifact evidence and explicit write authorization. It owns compare-and-swap before-state checks, exact write operations, rollback behavior, required projection receipts, postconditions, idempotency, and the distinction between complete and `settlement_incomplete`.

It explicitly does **not** infer literary meaning, acceptance, or State Delta.

That semantic / Project logic must already have produced an exact intended before→after transaction.

This architecture keeps:

**candidate generation → review → acceptance → Canon mutation**

as separate authority transitions.

---

## 15 · Release and documentation follow the same source-of-truth rule

Human-facing diagrams and prose are presentation / explanation layers. They are not allowed to become a second architecture authority.

Current product-facing visuals use the Story Loom design language, while exact machine contracts remain in JSON / YAML / Python and deep protocol docs.

When implementation, manifest, and human documentation disagree, that disagreement is a release-quality problem to surface—not something documentation should hide by inventing a new truth.

This is also why historical specs and changelogs preserve their historical meaning rather than being rewritten to sound current.

---

## 16 · Architectural invariants worth remembering

A small set of equations captures the whole system:

**Project → pinned Framework, never the reverse.**

**Storage ≠ prompt context.**

**Memory ≠ Canon.**

**Model judgment ≠ write authority.**

**Capability ≠ authority.**

**Review ≠ acceptance.**

**Acceptance ≠ completed settlement.**

**Corpus evidence ≠ story truth.**

**Learning hypothesis ≠ durable rule.**

**Deterministic runtime ≠ literary intelligence.**

For subsystem-by-subsystem ownership and exact links, continue to [Architecture Atlas](architecture-atlas.en.md).

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <br />
  <sub>Keep authority explicit, intelligence bounded, and fiction free to feel alive. ✦</sub>
</div>
