<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><kbd>READER EVIDENCE</kbd>&nbsp;&nbsp;<kbd>OWNING-MECHANISM REPAIR</kbd>&nbsp;&nbsp;<kbd>PLATEAU STOPPING</kbd></p>
</div>

# Quality Evolution · Improve candidates without turning revision into an infinite loop

NovelForge 7.2 turns revision from a loose sequence of “critic prompts” into an inspectable quality-evolution system. Diagnostics may come from different mechanisms, but findings share a typed evidence contract, repairs return to the mechanism that owns the failure, candidate comparisons are durable, and repeated no-gain can stop the loop.

> **Core invariant ✦** A quality signal may diagnose or reject a candidate. It does not gain Canon authority, and it does not become “independent review” merely because it came from another persona prompt.

## 01 · Quality is a stack, not one score

NovelForge keeps several questions separate:

- **deterministic correctness** — schema, lifecycle, fingerprints, authority, idempotency;
- **surface realization** — whether prose exhibits known structural/AI failure mechanisms;
- **reader engagement** — pressure, reward, causality, investment, forward pull;
- **character integrity** — agenda, knowledge, voice, relationship and spatial/task consistency;
- **continuity/state integrity** — whether the candidate agrees with relevant accepted/current state;
- **independent semantic judgment** — a genuinely separate invocation/session when the workflow requires an independent gate.

No single “8.4/10” number is allowed to collapse these dimensions into a fake objective truth.

## 02 · Reader Simulation Panel is diagnostic evidence

`quality/reader_panel.py` packages bounded reader-simulation jobs. Default personas describe **reading behavior**, not demographic stereotypes, for example binge, genre-native, casual-mobile, investment, and reward-sensitive readers.

The panel can inspect one candidate or compare A/B candidates. Signals include continue desire, tension, pacing, confusion, emotional response, favorite/stumble beats, forward pull, character investment, reward, and drop-off points.

Pairwise comparison uses swapped visible order so first-position bias can be detected rather than silently rewarded.

The aggregator also looks for disagreement and suspiciously templated reasons. Consensus can be useful evidence; disagreement can be even more useful because it tells the revision system *where different reading goals diverge*.

**Important:** Reader Panel results are diagnostic. They set neither Canon nor the mandatory independent semantic gate.

## 03 · Typed findings create a common language

Quality mechanisms normalize their observations into evidence-chained findings. A finding identifies:

- category and severity;
- subject;
- repair owner;
- candidate-side evidence;
- authority/state-side evidence when relevant;
- source references;
- confidence;
- a proposal or repair suggestion that does not directly mutate authoritative state.

This shared contract means the revision layer can combine continuity, character, reader, surface, research, context, or memory problems without pretending they are the same kind of failure.

## 04 · Character Integrity uses bounded context

`quality/character_integrity.py` packages only the scene excerpt and typed character state needed for the audit. It explicitly rejects private reasoning, chain-of-thought, hidden gold, writer scratchpads, and regression bad examples.

The audit dimensions are:

`agenda alignment · knowledge boundary · voice drift · relationship position · spatial/task state · surprise consistency`

The result is evidence, not a direct character-state mutation and not automatically an independent gate.

## 05 · Revision Orchestrator plans narrow passes

`quality/revision_orchestrator.py` is deterministic orchestration, not a literary judge. It plans bounded passes only when the required evidence exists:

`continuity · character · reader · surface · research/fact`

A missing prerequisite skips that pass rather than poisoning unrelated passes.

Completed findings are deduplicated and grouped by **repair owner**. That is the key failure-routing rule:

- isolated surface issue → local surface rewrite;
- surface cluster → whole-scene regeneration;
- reader-grip / SAFE-BUT-FLAT → Reader Pressure + Scene Simulation;
- character failure → Character Simulation;
- story/plan failure → Story or Plan layer;
- continuity/state failure → continuity/state repair;
- context failure → rebuild sparse context;
- memory failure → invalidate/rebuild derived memory;
- research failure → research resolution;
- runtime failure → transport/capability repair;
- unresolved direction → human decision.

The system repairs the cause rather than polishing the symptom.

## 06 · Durable candidate evolution

`quality/quality_evolution.py` stores revision progress in a deterministic SQLite ledger:

**baseline candidate → challenger → comparison → incumbent → next challenger → plateau / complete**

Every candidate has a content fingerprint and parent lineage. Every comparison result is fingerprinted and logically consume-once. Exact replay is idempotent.

A challenger must descend from the current incumbent; a winner must be one of the compared candidates or a no-decision/tie. This prevents a quality loop from quietly changing what was compared after the fact.

When a challenger genuinely wins, it becomes the new incumbent and the no-gain counter resets. Repeated no-gain reaches the configured plateau limit and stops evolution.

Plateau stopping matters because revision is not monotonically beneficial. “Keep rewriting until the model feels done” is not a quality strategy.

## 07 · Independent review remains independent

Reader personas, a Character Integrity audit, and internal critic passes can all be valuable while still sharing the manager's workflow.

When the Harness requires a mandatory independent semantic gate, that judgment must still come from a genuinely separate eligible invocation/session/runtime and return a typed result bound to the exact artifact fingerprint.

A semantic reject is a valid result. It routes repair. It is not an excuse to switch reviewers until somebody says PASS.

## 08 · State graph and resumability

`quality/state_graph.py` gives the quality workflow an explicit non-authoritative state graph so interrupted work can resume without inventing what already happened.

Durable state records what analysis/revision step was completed. It does **not** grant Canon write authority and it does not substitute for the consuming project's acceptance/settlement rules.

## 09 · Relationship to the production pipeline

Quality Evolution starts only after a candidate exists. Regression bad examples and critic-only evidence remain post-generation inputs. Reader diagnostics and bounded integrity checks can then produce findings; the Revision Orchestrator routes repair; candidate evolution records whether the repair actually improved the incumbent.

Only after required quality/continuity/independent gates resolve may the artifact cross the user-visible gate. User acceptance is still separate from Canon settlement.

## 10 · Related contracts

- [Quality & QA](quality-assurance.en.md) — the full quality stack and release gates.
- [Production Pipeline](production-pipeline.en.md) — where diagnostics and revision occur.
- [Reader Engagement](../surface/READER_ENGAGEMENT.en.md) — generic reader-quality mechanism.
- [`quality/reader_panel.py`](../quality/reader_panel.py) — reader diagnostic packaging.
- [`quality/revision_orchestrator.py`](../quality/revision_orchestrator.py) — finding aggregation and repair routing.
- [`quality/quality_evolution.py`](../quality/quality_evolution.py) — durable candidate ledger.
- [`quality/character_integrity.py`](../quality/character_integrity.py) — bounded character audit.
