<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Architecture Atlas · exact subsystem ownership without source-tree archaeology</strong></p>
  <p><kbd>PROJECT</kbd>&nbsp;&nbsp;<kbd>FICTION</kbd>&nbsp;&nbsp;<kbd>SEMANTIC</kbd>&nbsp;&nbsp;<kbd>RUNTIME</kbd>&nbsp;&nbsp;<kbd>QUALITY</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd></p>
  <p><a href="architecture-atlas.zh-CN.md">简体中文</a> · <a href="architecture.en.md">Architecture</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# Architecture Atlas

[Architecture](architecture.en.md) explains how NovelForge's major authority domains relate. This atlas answers the next question: **which subsystem owns a concrete problem, what is it forbidden to own, and where is the exact contract?**

<img src="../assets/ui/home-architecture.en.svg" alt="NovelForge system map separating Project authority, semantic contracts, deterministic runtime, and evidence" width="100%" />

---

## 01 · Project SDK and Project Adapter

**Owns:** the consuming-project contract: project identity, `novelforge.toml`, exact dependency lock, standard / mapped layouts, validation, deterministic project build, and resolution of logical Project paths.

**Refuses to own:** the Framework cannot become the database for one novel, and an adapter cannot silently change Project authority merely because it can resolve a file path.

Use the SDK when creating / validating a Project. Use the Adapter when an existing repository should preserve its mature layout while satisfying NovelForge's logical contract.

References: [Project SDK](project-sdk.en.md) · [Project Adapters](project-adapters.en.md) · [Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md)

---

## 02 · Canon / State and Settlement Runtime

**Owns:** authority classes and the high-authority transition from explicitly accepted artifact to authorized Project writes.

Canon / State distinguishes `locked`, `accepted`, `active_plan`, `review`, and `proposal`. The exact Project precedence remains Project-owned.

Settlement Runtime owns transaction mechanics only: explicit acceptance receipt, accepted-artifact fingerprint, checkpoint / write authorization, exact create / update / delete intent, compare-and-swap before-state, rollback behavior, required projection receipts, idempotency, and postcondition verification.

**Refuses to own:** settlement does not infer acceptance, State Delta, Canon meaning, or literary intent. Review output, memory, semantic verdicts, Corpus evidence, and scenario branches cannot write themselves into Canon.

References: [Canon State](../core/CANON_STATE.en.md) · `harness/settlement_runtime.py`

---

## 03 · Story System

**Owns:** structural hierarchy, story-level pressure, causal movement, open loops, dependencies, and story-level repair ownership.

NovelForge can represent `BOOK → VOLUME → ARC → UNIT → CHAPTER → SCENE` without pretending every project must use the same storytelling style.

**Refuses to own:** character-private knowledge, final prose realization, or automatic Canon settlement.

When a scene premise is causally broken, repair belongs here or in Plan—not in sentence polishing.

Reference: [Story System](../core/STORY_SYSTEM.en.md)

---

## 04 · Character & Relationship System

**Owns:** agenda, beliefs, knowledge boundary, independent action, voice ownership, spatial / task state, interests, obligations, relationship position, and emotional / event aftermath.

**Refuses to own:** manager knowledge, reader knowledge, author intent, or planned reactions merely because an outline contains them.

The system exists so important characters can resist, misunderstand, improvise, or pursue their own interests without becoming puppets of the plan.

Reference: [Character & Relationship System](../core/CHARACTER_SYSTEM.en.md)

---

## 05 · Story-Simulation semantic pack

**Owns semantic judgment for:** pre-draft character action and scene-level causal resolution.

The pack exposes:

- `character.action_propose` — proposes plausible character-owned action from typed character / relationship / scene evidence;
- `scene.resolve_actions` — resolves those actions against one another and world constraints into a causal event trajectory.

**Refuses to own:** deterministic routing, Project authority, or Canon mutation. The model proposes semantic outcomes; the manager / runtime package and validate the bounded job.

Source: `harness/semantic_workers/contracts/story-simulation.json`

---

## 06 · Context Inspector, Memory Tiers, and Memory Bank

**Owns deterministic control for:** context provenance, hard budgets, memory authority classes, explicit pin / reprioritize / invalidate controls, and protected-memory edit boundaries.

When relevance itself requires interpretation, semantic selection belongs to the `context-research` pack's `context.select` contract.

**Refuses to own:** pseudo-literary relevance scores, silent automatic prompt injection, or Canon mutation. A protected `accepted` / `locked` edit becomes a non-authoritative proposal rather than rewriting story truth.

Guide: [Context & Memory](context-and-memory.en.md)

Implementation: `harness/context_inspector.py` · `harness/memory_tiers.py` · `harness/memory_bank.py`

---

## 07 · Semantic Contract Catalog

**Owns:** the smallest deterministic index needed to discover semantic contract packs.

`harness/semantic_workers/model_contract_catalog.json` is the **only registry index**. It describes packs, contract IDs, and load conditions. The manager / model chooses the smallest relevant pack; runtime resolves an exact contract ID to exactly one pack.

Current pack families are:

- quality;
- narrative-memory;
- learning;
- context-research;
- story-simulation;
- long-horizon;
- creative-evolution.

**Refuses to own:** keyword-routing literary intent, loading every contract by default, or deciding semantic meaning on behalf of the model.

Reference: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md)

---

## 08 · Semantic Worker Router and Execution Runtime

**Owns deterministic packaging / transport:** exact contract resolution, bounded semantic job construction, permissions, semantic fingerprints, typed result validation, provider-neutral execution lineage, and consume-once result handling.

Adapters may route to local agents, provider APIs, peer-chat relay, MCP / service paths, or other eligible transports.

**Refuses to own:** literary judgment. The runtime validates the contract and result shape; the model performs the interpretation.

It also refuses to pretend every semantic call is independent. Independence is enforced only when the active gate requires a genuinely separate invocation / session.

References: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) · [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md)

---

## 09 · Harness Manager and Orchestration

**Owns:** one primary `task_mode`, Framework / Project bootstrap, sparse context, capability resolution, checkpoint timing, bounded specialist use, semantic-pack selection, external waits, failure routing, gate ordering, result validation, and truthful user-visible completion state.

**Refuses to own:** Project story facts or fake independent judgment. The manager coordinates the system; it does not become a second Canon database and cannot self-certify an independent gate inside the same invocation.

References: [Harness Agent](../harness/HARNESS_AGENT.en.md) · [Orchestration Protocol](../harness/ORCHESTRATION_PROTOCOL.en.md)

---

## 10 · Session Runtime

**Owns:** durable identity and recovery semantics for `resource / project`, `session / thread`, `run / invocation`, and `checkpoint`.

It records workflow cursor, waits, before-state, handoff bindings, and resume-relevant evidence so long-running work can survive process / provider boundaries.

**Refuses to own:** Canon. A provider conversation ID or persistent chat session remains runtime metadata.

Reference: [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md)

---

## 11 · Runtime Capabilities and Routing

**Owns:** evidence of what the current host can actually do, including permission, availability, user-interaction requirements, model-execution capability, and usage constraints.

Runtime Routing selects an eligible path only after those capabilities are known.

**Refuses to own:** authority. Provider name is not capability proof; capability is not Canon-write permission.

References: [Runtime Capabilities](../harness/session_runtime/RUNTIME_CAPABILITIES.en.md) · [Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.en.md)

---

## 12 · Durable Control Plane

**Owns:** operational state for external / parallel work: events, handoffs, bounded leases, result receipts, idempotency, lifecycle, provenance, and logical consume-once behavior.

**Refuses to own:** semantic validity, Project authority, or story direction. A worker result must still pass the semantic / authority contract that owns its use.

Reference: [Control Plane](../harness/control_plane/CONTROL_PLANE.en.md)

---

## 13 · Surface Fundamentals and Reader Engagement

These are two different generic quality layers.

**Surface Fundamentals owns:** recurring prose-realization failure mechanisms and the distinction between isolated repair and cluster-level regeneration.

**Reader Engagement owns:** pressure, payoff, causal movement, contrast, reader reward, relationship movement, forward pull, and SAFE-BUT-FLAT diagnosis.

**They refuse to own:** story authority and deterministic runtime invariants. A reader problem may route upstream into scene design; a surface-clean candidate can still be bad fiction.

References: [Surface Fundamentals](../surface/FUNDAMENTALS.en.md) · [Reader Engagement](../surface/READER_ENGAGEMENT.en.md)

---

## 14 · Quality semantic pack and Findings

The `quality` pack exposes model-owned interpretation for:

- `reader.reaction`;
- `reader.compare`;
- `character.integrity`;
- `revision.diagnose`.

Typed findings make semantic diagnosis traceable and attach it to an exact artifact / evidence context.

**Refuses to own:** automatic repair, automatic independent-gate status, or Canon authority. Reader simulation is diagnostic evidence unless a separate workflow explicitly requires independence.

References: [Quality & QA](quality-assurance.en.md) · `harness/semantic_workers/contracts/quality.json` · `quality/findings.py`

---

## 15 · Quality Evolution and Creative Evolution

**Quality Evolution ledger owns deterministically:** candidate fingerprints, parent lineage, repair owner, comparison identity, result binding, current incumbent, and plateau counters.

**Creative Evolution semantic pack owns interpretation for:**

- `scene.diverge` — materially different causal scenario exploration;
- `quality.compare` — incumbent / challenger comparison that may select either candidate or return a tie.

**Refuses to own:** the deterministic ledger never decides literary quality, and a comparison winner never gains Canon authority.

Guide: [Quality Evolution](quality-evolution.en.md)

Implementation: `quality/quality_evolution.py` · `harness/semantic_workers/contracts/creative-evolution.json`

---

## 16 · Narrative Memory and Long-Horizon semantic packs

These packs interpret durable narrative evidence without creating a second Canon.

**Narrative Memory** can handle source-bound narrative interpretation, `reader.expectations`, and rebuildable memory consolidation.

**Long Horizon** can handle `plan.reconcile`, `relationship.memory_reconcile`, and `continuity.commitment_audit`.

**Refuses to own:** derived narrative state, reader expectations, relationship memory, scenario branches, and state-graph results remain non-authoritative unless Project rules explicitly promote a fact through an authorized boundary.

Sources: `harness/semantic_workers/contracts/narrative-memory.json` · `harness/semantic_workers/contracts/long-horizon.json`

---

## 17 · Adaptive Learning

**Owns:** durable evidence, revisable preference hypotheses, contradictions, applicability boundaries, Corpus gaps, learning candidates, evaluation evidence, promotion history, and rollback.

Semantic learning work lives in the `learning` pack. Deterministic learning stores / cycles own state transitions and promotion preconditions.

**Refuses to own:** model inference alone cannot become durable user taste; promotion evidence does not itself grant Framework-write authority.

References: [Adaptive Learning](adaptive-learning.en.md) · [Self-Improvement Protocol](../harness/SELF_IMPROVEMENT_PROTOCOL.en.md)

---

## 18 · Corpus Intelligence

**Owns:** evidence discovery planning, source provenance, rights classification, bounded storage / analysis, mechanism observations, counterexamples, and cross-work benchmarks.

The `context-research` pack's `corpus.discovery_plan` can propose a semantic discovery plan; deterministic capability / rights layers decide whether and how that plan may actually execute.

**Refuses to own:** search success is not ingestion permission; Corpus is not Canon; external truth is not automatic character knowledge; named-author imitation profiles are out of bounds.

References: [Corpus Intelligence](../corpus/README.en.md) · [Corpus Policy](../corpus/CORPUS_POLICY.en.md) · [Corpus Ingest Protocol](../corpus/CORPUS_INGEST_PROTOCOL.en.md)

---

## 19 · Evals

**Owns:** deterministic, rubric, and hybrid evaluation cases; blind semantic queue construction; scoring; baseline / release logic; and the distinction between actual judgment and `PENDING_MODEL`.

**Refuses to own:** normal CI may not fabricate semantic PASS and may not silently spend paid / login-bound model usage.

References: [Eval Reference](../evals/README.en.md) · [Quality & QA](quality-assurance.en.md)

---

## 20 · Framework Bundle and Release Engineering

**Owns:** deterministic Framework materialization, exact bundle fingerprint, compatibility evidence, reproducible artifacts, and downstream pinning.

**Refuses to own:** a bundle does not create a second story database and does not make derived output authoritative.

Reference: [Framework Bundle](../release/FRAMEWORK_BUNDLE.en.md)

---

## 21 · The atlas test: where should a failure go?

If you cannot answer “which subsystem owns this failure?” the architecture is becoming too blurry.

A few examples:

**The character knows future-plan information** → Character / Context, possibly upstream Story / Plan.

**The scene is polished but inert** → Reader Pressure + Scene Simulation.

**The reviewer judged an old fingerprint** → Semantic Runtime / validation.

**The repair candidate is merely different** → Quality Evolution / `quality.compare`.

**A relationship memory conflicts with Accepted evidence** → Long Horizon reconciliation; do not overwrite Canon from memory.

**A source is discoverable but rights are unclear** → Corpus rights / provenance gate.

**The user accepted prose but a before-state changed before write** → Settlement Runtime → `settlement_incomplete`.

That routing discipline is the architecture's real value.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="52" />
  <br />
  <sub>Narrow owners. Explicit boundaries. Deep links only when you need them. ✦</sub>
</div>
