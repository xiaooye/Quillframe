<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><kbd>MODEL-OWNED SEMANTICS</kbd>&nbsp;&nbsp;<kbd>EVIDENCE-BOUND REPAIR</kbd>&nbsp;&nbsp;<kbd>PLATEAU STOPPING</kbd></p>
</div>

# Quality Evolution · Improve candidates without pretending revision always helps

NovelForge separates **literary judgment** from **quality-state machinery**. Models perform bounded semantic work through model-readable contracts. Deterministic code enforces visibility, authority, fingerprints, budgets, typed validation, persistence, consume-once behavior, and revision state.

> **Core invariant ✦** Python may constrain, persist, route, validate, and transact. It does not become a literary critic merely because a quality workflow needs one.

---

## 01 · Quality is a stack, not one score

NovelForge keeps several questions distinct:

- **deterministic correctness** — schema, lifecycle, permission, authority, fingerprints, idempotency;
- **context grounding** — whether the active task received relevant evidence without crossing perspective boundaries;
- **surface realization** — whether prose exhibits known structural/model failure mechanisms;
- **reader engagement** — pressure, reward, causality, character investment, clarity, forward pull;
- **character integrity** — agenda, knowledge, voice, relationship position, task and spatial coherence;
- **continuity / long-horizon integrity** — whether the candidate respects authoritative state and live commitments;
- **independent judgment** — a genuinely separate invocation/session only when the workflow explicitly requires independence.

No absolute score collapses these dimensions into objective literary truth.

---

## 02 · Semantic intelligence lives in contract packs

The catalog at [`harness/semantic_workers/model_contract_catalog.json`](../harness/semantic_workers/model_contract_catalog.json) resolves progressively disclosed semantic packs. The runtime exposes only the bounded input, rubric, permissions, fingerprint and typed output contract needed for the active step.

Quality-facing contracts include:

- `reader.reaction` — one reading-behavior persona's immediate experience;
- `reader.compare` — pairwise comparison, including swapped-order bias checks;
- `character.integrity` — agenda, knowledge, voice, relationship and task/spatial integrity;
- `revision.diagnose` — evidence-backed diagnosis and repair ownership;
- `reader.expectations` — current reader questions, promises, setups and obligations;
- `context.select` — task-aware semantic selection among already visibility-safe evidence blocks.

A semantic result is evidence. It does not receive Canon write, Framework behavior write or durable user-taste write authority merely because it is persuasive.

---

## 03 · Grounding is part of quality

A quality judgment is weak if the model saw the wrong evidence. Current context selection therefore separates **semantic relevance** from **deterministic visibility**.

[`harness/memory_tiers.py`](../harness/memory_tiers.py) requires the active task to state:

- `task_mode` and `task_goal`;
- current story point when applicable;
- perspective scope and perspective identity;
- explicit active questions.

Before the model sees candidate memory blocks, deterministic code removes perspective-incompatible material. A character-perspective task cannot receive another character's private knowledge merely because the block is relevant. Even a pinned block fails closed when it violates the active perspective boundary.

Only then does `context.select` decide which visible blocks support the active questions. The deterministic packer owns hard budgets and whole-block packing; it does not invent literary relevance scores.

This creates a clean responsibility split:

```text
visibility / authority / budget  → deterministic runtime
semantic relevance / support    → model contract
story truth                     → project authority
```

Context support is still observation, not Canon.

---

## 04 · Reader diagnostics are evidence, not automatic gates

Reader personas describe **reading behavior**, not demographic stereotypes. Useful signals include continue desire, tension, pacing, confusion, emotional response, favorite/stumble beats and drop-off reasons.

`reader.compare` is preferable to pretending one scalar score is universal. When positional bias matters, compare again with A/B order swapped.

Important boundaries:

- reader diagnostics are not Canon;
- a single score never decides keep/discard by itself;
- persona disagreement is useful evidence rather than noise to average away;
- reader diagnostics do not automatically satisfy a mandatory independent gate.

---

## 05 · Character integrity remains epistemically bounded

`character.integrity` receives only the supplied candidate and typed established state. It checks agenda, knowledge, voice, relationship position, spatial/task state and surprise-within-consistency.

Manager, narrator, reader, research and model knowledge are not automatically character knowledge. Intentional change is valid when transition evidence supports it.

The result is a finding, not a state mutation.

---

## 06 · Diagnose before rewriting

`revision.diagnose` exists to stop generic “polish passes.” It identifies the failure and routes it to the mechanism that actually owns repair.

Typical ownership:

- isolated surface defect → local surface rewrite;
- repeated surface cluster → larger Surface Realization regeneration;
- SAFE-BUT-FLAT / weak reader pressure → Reader Pressure + Scene Simulation;
- character failure → Character Simulation / character-state reasoning;
- story or plan failure → Story / Plan layer;
- continuity/state failure → continuity or authoritative-state repair;
- context failure → rebuild sparse, question-grounded context;
- memory failure → invalidate or rebuild derived memory;
- research failure → research resolution;
- runtime/capability failure → transport or capability layer;
- unresolved artistic direction → user/human decision.

Repair the cause, not the symptom.

---

## 07 · Typed findings create a common evidence language

[`quality/findings.py`](../quality/findings.py) normalizes evidence-backed findings without deciding literary quality itself.

A useful finding identifies:

- category and severity;
- subject and candidate;
- repair owner;
- candidate-side evidence;
- authoritative/state-side evidence when relevant;
- source references;
- confidence;
- a repair proposal that does not directly mutate authoritative state.

Surface, reader, character, continuity, context, memory and research failures can therefore share transport semantics without being collapsed into one kind of defect.

---

## 08 · Candidate evolution is durable and non-monotonic

[`quality/quality_evolution.py`](../quality/quality_evolution.py) owns revision-state persistence, not literary judgment.

A typical loop is:

```text
incumbent
→ targeted repair
→ challenger
→ semantic comparison
→ validate + consume once
→ promote challenger or record no-gain
→ repeat only while useful
```

Every candidate has a content fingerprint and parent lineage. Every comparison result is fingerprint-bound and logically consume-once. A challenger must descend from the current incumbent, and a declared winner must be one of the candidates that was actually compared.

A genuine win resets the no-gain counter. Repeated no-gain reaches the configured plateau limit and stops the loop.

**Revision is not monotonically beneficial. Stopping is part of quality control.**

---

## 09 · Reader expectations preserve long-horizon pressure

[`quality/reader_expectation.py`](../quality/reader_expectation.py) stores durable, non-authoritative reader-facing expectations. Semantic interpretation comes from `reader.expectations`; deterministic code owns identity, persistence, transitions and evidence references.

An expectation may represent a live:

- question;
- promise;
- setup/payoff expectation;
- relationship expectation;
- goal;
- mystery or unresolved reader-facing obligation.

A future planned payoff is not evidence that the reader already holds that expectation. The ledger must distinguish current reader experience from future intent.

---

## 10 · Quality work is resumable and observable

[`quality/state_graph.py`](../quality/state_graph.py) records non-authoritative quality workflow progress so interrupted work can resume without guessing which steps already ran.

The Control Plane also supports **metadata-only run receipts** through [`harness/control_plane/run_receipt.py`](../harness/control_plane/run_receipt.py). A receipt may record:

- artifact fingerprints;
- context-selection fingerprints;
- which evidence blocks were loaded or excluded;
- question → evidence loading status;
- semantic job IDs, contract IDs and result fingerprints;
- deterministic guard outcomes.

It deliberately does **not** store candidate prose, private reasoning or hidden gold, and it carries no Canon or memory authority.

This makes quality work inspectable without creating a second story database or a surveillance copy of the manuscript.

---

## 11 · Independent review remains conditional and real

Internal semantic contracts may run inside the manager's workflow. They become an **independent gate** only when the active rubric requires independence.

When independence is mandatory, judgment must come from a genuinely separate eligible invocation/session/runtime and return a typed result bound to the exact artifact fingerprint.

A valid `semantic_reject` routes repair. It is not a transport failure and is not permission to keep switching reviewers until one says PASS.

---

## 12 · Relationship to the production pipeline

Evidence preparation can happen before drafting: authority resolution, visibility filtering, active-question definition and sparse context selection all affect whether the later candidate is grounded.

**Candidate evolution itself begins only after a candidate exists.** Regression bad examples and critic-only evidence stay post-generation. Semantic contracts inspect bounded packets; deterministic infrastructure validates and persists their results; repair returns to the owning mechanism; comparison determines whether the repair actually improved the incumbent.

A user-visible artifact still requires the active workflow's required gates. User acceptance remains separate from Canon settlement.

---

## 13 · Why this architecture matters

The split avoids two common failures:

**Fake determinism** — heuristics pretending to decide literary quality that actually requires interpretation.

**Unbounded model authority** — a model being allowed to write durable truth because its judgment sounds convincing.

NovelForge instead keeps the boundary explicit:

```text
model       → semantic interpretation
runtime     → visibility + packet + permissions + fingerprint + budget
validator   → typed-result and binding checks
ledgers     → durable non-authoritative evidence/state
project     → Canon authority and settlement
```

---

## 14 · Related contracts

- [Quality & QA](quality-assurance.en.md) — full quality stack and release gates.
- [Production Pipeline](production-pipeline.en.md) — where diagnosis, repair and evolution occur.
- [Context & Memory](context-and-memory.en.md) — sparse selection, visibility and editable derived memory.
- [Reader Engagement](../surface/READER_ENGAGEMENT.en.md) — positive reader-quality model.
- [Character & Relationship System](../core/CHARACTER_SYSTEM.en.md) — character state and knowledge boundaries.
- [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) — provider-neutral semantic job/result contract.
- [Control Plane](../harness/control_plane/CONTROL_PLANE.en.md) — durable runtime coordination and receipts.
