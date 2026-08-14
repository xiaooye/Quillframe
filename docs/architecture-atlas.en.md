<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Architecture Atlas · subsystem-by-subsystem</strong></p>
  <p><kbd>STORY</kbd>&nbsp;&nbsp;<kbd>RUNTIME</kbd>&nbsp;&nbsp;<kbd>QUALITY</kbd>&nbsp;&nbsp;<kbd>LEARNING</kbd>&nbsp;&nbsp;<kbd>PROJECT ENGINEERING</kbd></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# Architecture Atlas

> 🌸 **The top-level architecture tells you how domains relate. This atlas tells you what each subsystem actually owns, what it refuses to own, and where its exact contract lives.**

<img src="../assets/ui/home-architecture.en.svg" alt="NovelForge five-domain architecture" width="100%" />

---

## 01 · Project Boundary & Context Broker

**Purpose.** Bind one consumer project to one exact NovelForge framework revision and build task-scoped context without dumping the whole project into every model invocation.

**Owns.** Project manifest, exact lock resolution, adapter mapping, authority-path resolution, sparse Context Manifest construction, artifact fingerprints.

**Does not own.** Story truth itself, semantic review verdicts, user preferences, or runtime session history.

```text
Project manifest + lock
→ Project Adapter
→ authority/profile/state resolution
→ task-scoped Context Manifest
→ manager / specialist invocation
```

**Important boundary.** Storage presence ≠ prompt inclusion. Future plans, irrelevant Canon, regression gold, and manager history do not enter context unless the active task genuinely requires them.

References: [Project SDK](project-sdk.en.md) · [Project Adapters](project-adapters.en.md) · [Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md)

---

## 02 · Story System

**Purpose.** Model the structural hierarchy and causal progression of fiction rather than treating a novel as an undifferentiated stream of text.

**Owns.** `BOOK → VOLUME → ARC → UNIT → CHAPTER → SCENE` hierarchy, structural objectives, causal movement, open loops, story dependencies, and story-level failure ownership.

**Does not own.** Character-private knowledge, final prose surface, runtime sessions, or automatic Canon settlement.

```text
accepted prior state
+ active plan
+ current scene problem
→ Story Preflight
→ Scene Simulation
→ state-changing event trajectory
```

Reference: [Story System](../core/STORY_SYSTEM.en.md)

---

## 03 · Character & Relationship System

**Purpose.** Keep important characters behaviorally and epistemically independent instead of allowing the manager/outline to speak through everyone.

**Owns.** Character agenda, knowledge boundary, voice ownership, location/presence, interests, relationship state, obligations, tasks, emotional aftermath, and character-owned decisions.

**Does not own.** Omniscient manager knowledge or planned reactions merely because they appear in an outline.

```text
character state + relationship state + scene pressure
→ Character Simulation
→ plausible action / refusal / mistake / reaction
→ scene-state update proposal
```

Reference: [Character System](../core/CHARACTER_SYSTEM.en.md)

---

## 04 · Canon State & Settlement

**Purpose.** Prevent plans, reviews, memories, corpus evidence, or model guesses from silently becoming story truth.

**Owns.** Authority lifecycle such as `locked > accepted > active_plan > review > proposal`, accepted-state evidence, before/after settlement, dependency impact, post-condition checks, and settlement traces.

**Does not own.** Automatic acceptance. A Review Draft is not Canon merely because it passed QA.

```text
explicit user acceptance
→ freeze accepted artifact
→ state delta
→ exact before-state validation
→ dependency impact
→ authorized write
→ derived-view rebuild
→ post-condition + trace
```

Reference: [Canon State](../core/CANON_STATE.en.md)

---

## 05 · Harness Manager

**Purpose.** Coordinate a task-aware production run without turning “multi-agent” into a goal by itself.

**Owns.** Exactly one task mode, capability resolution, sparse context, checkpointing, bounded specialist dispatch, gate ordering, external wait/resume, result validation, and user-visible completion truth.

**Does not own.** Independent semantic judgment when independence is mandatory, or project-specific story facts.

```text
user request
→ resolve task mode
→ capability + authority preflight
→ context freeze
→ production / audit / research / learning graph
→ required gates
→ truthful user-visible status
```

Reference: [Harness Agent](../harness/HARNESS_AGENT.en.md) · [Orchestration Protocol](../harness/ORCHESTRATION_PROTOCOL.en.md)

---

## 06 · Session Runtime

**Purpose.** Make long-running work resumable across waits, tool calls, provider changes, process restarts, and external workers.

**Owns.** Session/run/checkpoint/event identity, workflow cursor, pending waits, handoff/result binding, resume validation, and consume-once behavior.

**Does not own.** Canon. Provider-native conversation IDs remain metadata.

```text
project/resource
→ session
→ run
→ checkpoint
→ event / handoff
→ result
→ validate / consume once
→ resume
```

Reference: [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md) · [Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.en.md)

---

## 07 · Runtime Capability Broker

**Purpose.** Route work only through capabilities that are actually available and permitted in the current host.

**Owns.** Capability discovery/normalization, permission constraints, model-execution availability, usage constraints, and eligible transport selection.

**Does not own.** Authority. A connector or runtime that can perform a write does not gain permission to mutate Canon.

Examples of eligible transports can include current chat, separate peer chat, local Codex/Claude, provider APIs, MCP, GitHub jobs, local models, and humans.

Reference: [Runtime Capabilities](../harness/session_runtime/RUNTIME_CAPABILITIES.en.md)

---

## 08 · Durable Control Plane

**Purpose.** Track external/parallel operational work without letting asynchronous infrastructure become a hidden source of story truth.

**Owns.** Events, handoffs, leases, result receipts, lifecycle state, idempotency, consume-once semantics, and operational provenance.

**Does not own.** Semantic validity or Canon authority.

```text
manager dispatch
→ handoff / lease
→ external work
→ typed result receipt
→ fingerprint/provenance validation
→ consume once
```

Reference: [Control Plane](../harness/control_plane/CONTROL_PLANE.en.md)

---

## 09 · Semantic Worker Runtime

**Purpose.** Provide real independent judgment when a task requires semantic evaluation that the manager cannot validly self-produce.

**Owns.** Independent session/invocation identity, bounded review packets, artifact fingerprint binding, typed verdicts, reviewer freshness policy, and result validation.

**Does not own.** Automatic repair or authority promotion. A reviewer says what failed; the owning mechanism decides how to repair it.

```text
frozen candidate
→ bounded blind packet
→ independent invocation/session
→ typed fingerprint-bound result
→ manager validates
→ owning repair layer
```

Reference: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) · [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md)

---

## 10 · Surface Fundamentals

**Purpose.** Enforce generic anti-AI realization rules at the prose surface without confusing surface cleanliness with reader quality.

**Owns.** Known malformed/AI-ish surface mechanisms and the distinction between local surface repair and cluster-level regeneration.

**Does not own.** Story design, character motivation, or reader pressure.

Reference: [Surface Fundamentals](../surface/FUNDAMENTALS.en.md)

---

## 11 · Reader Engagement

**Purpose.** Judge whether the text actually creates reading pressure, payoff, causal movement, contrast, and forward pull.

**Owns.** Reader-facing quality dimensions and SAFE-BUT-FLAT detection.

**Does not own.** Grammar-only correctness or deterministic lifecycle invariants.

```text
surface-safe candidate
→ reader pressure / reward / causality / contrast review
→ PASS
or
→ upstream Scene Simulation + Reader Pressure repair
```

Reference: [Reader Engagement](../surface/READER_ENGAGEMENT.en.md)

---

## 12 · Adaptive Learning

**Purpose.** Learn from user evidence without turning model guesses into permanent preference rules.

**Owns.** Evidence records, preference hypotheses, confidence/contradictions, applicability boundaries, corpus gaps, promotion candidates, versions, and rollback.

**Does not own.** Automatic project Canon or automatic General Craft promotion.

```text
feedback evidence
→ hypothesis
→ contradiction / scope analysis
→ corpus gap
→ evidence / eval
→ candidate
→ activation or rollback
```

Reference: [Adaptive Learning](adaptive-learning.en.md) · [Self-improvement Protocol](../harness/SELF_IMPROVEMENT_PROTOCOL.en.md)

---

## 13 · Corpus Intelligence

**Purpose.** Acquire lawful evidence and extract mechanism-level observations without confusing external text with project truth or author-imitation templates.

**Owns.** Discovery requests, source/provenance checks, rights classification, ingestion boundaries, mechanism observations, counterexamples, and cross-work benchmarks.

**Does not own.** Canon, character knowledge, or durable user taste merely because a source was found.

```text
corpus gap
→ discovery
→ source verification + rights
→ bounded ingest / observation
→ mechanism analysis
→ benchmark / eval evidence
```

Reference: [Corpus Intelligence](../corpus/README.en.md) · [Corpus Policy](../corpus/CORPUS_POLICY.en.md)

---

## 14 · Evals

**Purpose.** Separate deterministic release invariants from blind semantic quality judgments.

**Owns.** Regression/capability/infrastructure cases, deterministic/rubric/hybrid judge modes, blind queue construction, result scoring, and release-blocking logic.

**Does not own.** Fake semantic PASS when no reviewer ran.

Reference: [Quality & QA](quality-assurance.en.md) · [Eval Reference](../evals/README.en.md)

---

## 15 · Project SDK & Release Bundle

**Purpose.** Make both Framework and consuming novels reproducible engineering artifacts.

**Owns.** Manifests, exact locks, validation, build bundles, compatibility checks, migration workflow, release fingerprints, and deterministic build outputs.

**Does not own.** A second copy of project truth. Build bundles and derived views remain rebuildable artifacts.

Reference: [Project SDK](project-sdk.en.md) · [Framework Bundle](../release/FRAMEWORK_BUNDLE.en.md)

---

## 16 · Dependency rule ✦

The complete system obeys one direction:

```text
Novel Project → pinned NovelForge Framework
NovelForge Framework -X→ consumer-specific story facts
```

And one authority principle:

```text
capability ≠ authority
memory ≠ Canon
review ≠ acceptance
corpus ≠ story truth
learning hypothesis ≠ durable rule
```

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="52" />
  <br />
  <sub>Every subsystem gets a narrow job. Most safety comes from refusing to let those jobs blur together. ✦</sub>
</div>
