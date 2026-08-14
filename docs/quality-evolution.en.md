<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><kbd>MODEL-OWNED SEMANTICS</kbd>&nbsp;&nbsp;<kbd>TYPED EVIDENCE</kbd>&nbsp;&nbsp;<kbd>PLATEAU STOPPING</kbd></p>
</div>

# Quality Evolution · Semantic judgment by models, durable quality state by deterministic code

NovelForge separates **literary judgment** from **quality-state machinery**. A model reads fiction and makes semantic judgments through bounded, model-readable contracts. Deterministic code packages context and permissions, validates typed outputs, stores evidence and candidate lineage, enforces fingerprints, and stops revision loops when they stop producing gains.

> **Core invariant ✦** Python may persist, route, fingerprint, budget, validate, and transact. It does not become a literary critic merely because a quality workflow needs one.

## 01 · Quality is a stack, not one score

NovelForge keeps several questions distinct:

- **deterministic correctness** — schema, lifecycle, fingerprint, authority, permission, consume-once, idempotency;
- **surface realization** — whether prose exhibits known structural/model failure mechanisms;
- **reader engagement** — attention, pressure, reward, causality, character investment, forward pull;
- **character integrity** — agenda, knowledge, voice, relationship position, task/spatial coherence;
- **continuity/state integrity** — whether the candidate agrees with relevant authoritative state;
- **independent semantic judgment** — a genuinely separate invocation/session when the workflow explicitly requires an independent gate.

No absolute score collapses these dimensions into objective literary truth.

## 02 · Semantic intelligence lives in model contracts

The catalog at [`harness/semantic_workers/model_contract_catalog.json`](../harness/semantic_workers/model_contract_catalog.json) indexes progressively disclosed semantic contract packs. The runtime supplies only the candidate, allowed context, rubric, permissions, fingerprint, and typed output contract.

Current quality-facing contracts include:

- `reader.reaction` — one reading-behavior persona's immediate experience of one candidate;
- `reader.compare` — pairwise reader-experience comparison, suitable for swapped-order bias checks;
- `character.integrity` — agenda, knowledge, voice, relationship, task/spatial state, and surprise-within-consistency;
- `revision.diagnose` — diagnosis across requested dimensions and routing to the mechanism that owns repair;
- `reader.expectations` — interpretation of live reader questions, promises, setups, relationship expectations, goals, and mysteries.

These contracts explicitly prohibit Canon write, framework-behavior write, and durable user-taste write.

## 03 · Reader diagnostics are evidence, not a gate by themselves

Reader simulation personas describe **reading behavior**, not demographic stereotypes. Default behaviors include binge/forward-pull sensitivity, genre familiarity, mobile attention, character investment, and reward sensitivity.

A `reader.reaction` judgment may report continue desire, tension, pacing, confusion, emotional response, favorite/stumble beats, drop-off point, and a concrete reason.

A `reader.compare` judgment compares A/B candidates across overall preference, forward pull, character investment, and reward. When bias detection matters, repeat with candidate order swapped rather than trusting first-position advantage.

Important boundaries:

- reader diagnostics are not Canon;
- an absolute score alone does not decide keep/discard;
- persona disagreement is useful evidence rather than noise to average away;
- reader diagnostics do not automatically satisfy a mandatory independent semantic gate.

## 04 · Character Integrity stays bounded

The `character.integrity` contract receives only the supplied scene excerpt and typed established character state. Its rubric explicitly checks:

`agenda alignment · knowledge boundary · voice · relationship position · spatial/task state · surprise within consistency`

It must not assume that manager, narrator, reader, research, or model knowledge is character knowledge.

Intentional character change is valid when the candidate supplies transition evidence. Findings must cite candidate-side and established-state evidence.

The result is an observation. It does not mutate character state.

## 05 · Revision diagnosis before rewriting

The `revision.diagnose` contract exists to stop generic “polish passes.” It first identifies the failure and then assigns repair ownership.

The model may distinguish failures in:

- story;
- plan;
- scene;
- character;
- reader pressure / engagement;
- surface realization;
- continuity/state;
- context or memory;
- research/fact support.

The contract explicitly states that SAFE-BUT-FLAT is not a line-edit problem and that a cluster of surface failures may require scene-level regeneration.

Its typed output contains evidence-chained findings plus a repair sequence. It still cannot mutate Canon.

## 06 · Typed findings create a common evidence language

[`quality/findings.py`](../quality/findings.py) is deterministic infrastructure for normalizing evidence-backed quality findings. A useful finding identifies:

- category and severity;
- subject/candidate;
- repair owner;
- candidate-side evidence;
- authoritative/state-side evidence when relevant;
- source references;
- confidence;
- a proposal for repair that does not directly mutate authoritative state.

This lets surface, reader, character, continuity, context, memory, and research diagnostics share a transport format without pretending they are the same kind of failure.

## 07 · Repair the owning mechanism

Quality findings should route repair to the smallest layer that actually owns the cause:

- isolated surface issue → local surface rewrite;
- repeated surface cluster → paragraph/block or whole-scene Surface Realization;
- SAFE-BUT-FLAT / reader-grip failure → Reader Pressure + Scene Simulation;
- character failure → Character Simulation / character-state reasoning;
- story or plan failure → Story / Plan layer;
- continuity/state failure → continuity or authoritative-state repair;
- context failure → rebuild sparse Context Manifest;
- memory failure → invalidate/rebuild derived memory;
- research failure → research resolution;
- runtime/capability failure → transport/capability layer;
- unresolved artistic direction → human/user decision.

Repair the cause, not the symptom.

## 08 · Durable candidate evolution

[`quality/quality_evolution.py`](../quality/quality_evolution.py) owns deterministic revision-state persistence, not literary judgment.

A typical evolution is:

```text
baseline candidate
→ challenger
→ model/semantic comparison result
→ validate + consume result once
→ incumbent update or no-gain
→ next challenger
→ plateau / complete
```

Every candidate has a content fingerprint and parent lineage. Every comparison result is fingerprinted and logically consume-once; exact replay is idempotent.

A challenger must descend from the current incumbent. A declared winner must be one of the actual compared candidates, or a tie/no-decision. The ledger cannot quietly swap candidates after judgment.

When a challenger genuinely wins, it becomes the incumbent and the no-gain counter resets. Repeated no-gain reaches the configured plateau limit and stops the loop.

**Revision is not monotonically beneficial. Plateau stopping is a quality feature.**

## 09 · Reader Expectation Ledger preserves long-horizon reader state

[`quality/reader_expectation.py`](../quality/reader_expectation.py) stores durable, non-authoritative reader-facing expectations. Semantic interpretation comes from the `reader.expectations` model contract; deterministic code owns identity, persistence, state transitions, and evidence references.

An expectation may represent a live:

- question;
- promise;
- setup/payoff expectation;
- relationship expectation;
- goal;
- mystery or unresolved reader-facing obligation.

The semantic contract distinguishes an expectation that currently exists in the reader experience from a **future planned payoff**. The ledger therefore must not turn an active plan into a reader fact merely because the plan exists.

Expectation state may be reinforced, partially rewarded, paid off, abandoned, or made dormant when evidence supports that interpretation. The ledger has no Canon authority.

## 10 · State graph makes quality work resumable

[`quality/state_graph.py`](../quality/state_graph.py) persists the non-authoritative state of quality work so an interrupted run can resume without inventing which analysis or revision steps already happened.

It records workflow progress. It does not grant Canon write authority and does not replace the consuming project's acceptance/settlement rules.

## 11 · Independent review remains a separate contract

Internal semantic contracts such as reader simulation, character integrity, and revision diagnosis can be valuable while still running inside the manager's workflow.

When the Harness requires a **mandatory independent semantic gate**, the judgment must still come from a genuinely separate eligible invocation/session/runtime and return a typed result bound to the exact artifact fingerprint.

A semantic rejection is a valid result. It routes repair. It is not a reason to switch reviewers until somebody says PASS.

## 12 · Relationship to the production pipeline

Quality Evolution begins only after a candidate exists.

Regression bad examples and critic-only evidence remain post-generation inputs. Semantic contracts inspect bounded candidate/context packets and return typed judgments. Deterministic infrastructure validates and persists those results. Repair returns to the owning mechanism. Candidate evolution records whether the repair actually defeats the current incumbent.

Only after required surface, reader, continuity, and independent gates resolve may the artifact cross the user-visible gate. User acceptance is still separate from Canon settlement.

## 13 · Why this architecture matters

Keeping semantic intelligence in model-readable contracts avoids two common failure modes:

**Fake determinism** — Python heuristics pretending to decide literary quality that actually needs interpretation.

**Unbounded model authority** — a model being allowed to write durable truth merely because it produced a convincing judgment.

NovelForge instead makes the boundary explicit:

```text
model      → semantic judgment
runtime    → bounded packet + permissions + fingerprint
validator  → typed-result checks
ledgers    → durable non-authoritative state
project    → Canon authority and settlement
```

## 14 · Related contracts

- [Quality & QA](quality-assurance.en.md) — full quality stack and release gates.
- [Production Pipeline](production-pipeline.en.md) — where diagnostics and repair occur.
- [Reader Engagement](../surface/READER_ENGAGEMENT.en.md) — generic positive reader-quality model.
- [Character & Relationship System](../core/CHARACTER_SYSTEM.en.md) — state and knowledge boundaries used by character integrity judgments.
- [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) — provider-neutral semantic job/result contract.
- [`model_contract_catalog.json`](../harness/semantic_workers/model_contract_catalog.json) — model-readable catalog for progressively disclosed semantic contract packs.
