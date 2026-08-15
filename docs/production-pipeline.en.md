<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="560" />
  <p><strong>Production Pipeline · simulate causality, evolve candidates, release through explicit gates</strong></p>
  <p><kbd>FREEZE</kbd>&nbsp;&nbsp;<kbd>SIMULATE</kbd>&nbsp;&nbsp;<kbd>DRAFT</kbd>&nbsp;&nbsp;<kbd>DIAGNOSE</kbd>&nbsp;&nbsp;<kbd>EVOLVE</kbd>&nbsp;&nbsp;<kbd>GATE</kbd></p>
  <p><a href="production-pipeline.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# Production Pipeline

A NovelForge chapter is a **recoverable production run**, not a single completion and not a fixed chain of critic agents.

The manager chooses the smallest semantic contract pack needed for each judgment. Models own story, character, reader, continuity, and revision interpretation. Deterministic runtime code owns authority, fingerprints, permissions, persistence, checkpoints, typed validation, budgets, and settlement transactions.

<img src="../assets/ui/home-pipeline.en.svg" alt="NovelForge production run: freeze and simulate, create an internal candidate, diagnose and evolve, then cross the release gate" width="100%" />

---

## 01 · The four responsibilities

Every `DRAFT` or `REVISE` run has four high-level responsibilities.

**Freeze + simulate** establishes the legal story state, sparse working context, character-owned action, scene causality, and reader pressure before prose generation.

**Create an internal candidate** produces event-first Raw Draft material and realizes the prose surface. Raw Draft remains private to the production run.

**Diagnose + evolve** uses exact semantic contracts and deterministic evidence to identify the owning failure mechanism, repair at the correct layer, and verify that a challenger candidate actually improves the incumbent.

**Release gate** checks the reader experience, long-horizon commitments, state/authority integrity, and any task-specific independent judgment before exposing review-ready prose.

The graph is adaptive: a failure can return upstream. It is not a conveyor belt that must always execute every possible contract.

---

## 02 · Bootstrap the run before touching prose

A run begins by resolving the consuming Project and its exact Framework dependency, then restoring or creating manager `session`, `run`, and checkpoint identity.

Before generation, the manager must know:

- the single active `task_mode`;
- Project authority and Canon cutoff;
- the exact candidate / plan / accepted-state fingerprints involved;
- the host capabilities available for semantic or external work;
- whether any consequential side effect requires a checkpoint first.

Chat history may help the runtime continue a conversation, but it is not a substitute for Project authority or durable state.

**Failure route:** runtime / Project bootstrap. Do not begin creative generation on ambiguous authority.

---

## 03 · Freeze sparse context

NovelForge treats context as a budgeted working set, not a whole-project dump.

The manager loads only the current task's relevant slices, such as:

- Project profile and active prose constraints;
- Accepted Canon and directly relevant current state;
- the active chapter / unit plan and scene intent;
- participating characters and relationships;
- unresolved commitments or dependencies;
- research claims the current scene actually needs;
- selected derived memory when it is useful and allowed.

When relevance itself requires interpretation, the manager may use the `context-research` pack, including `context.select`. Deterministic code still owns the hard budget, provenance, authority classes, and final packaging constraints.

Do not inject unrelated future plans, the entire Corpus, the manager's full history, hidden eval labels, or regression bad examples by default.

**Failure route:** Context / Memory.

---

## 04 · Preflight Story and Canon

Before simulating the scene, verify that the requested work is legal relative to current Project state.

Typical questions include:

- Is this event merely planned, already Accepted, or currently under review?
- Does the scene require knowledge, resources, relationships, or locations that do not yet exist?
- Is a proposed change compatible with current Canon and dependency obligations?
- Is a stale plan being followed after causal emergence already invalidated it?
- Is the user actually asking for another mode such as `PLAN-*` or `SETTLE`?

If active plans must adapt to newly emerged story facts, the `long-horizon` pack can use `plan.reconcile`. Reconciliation proposes an updated plan relationship; it does not retroactively rewrite Accepted Canon.

**Failure route:** Story / Plan / Project authority.

---

## 05 · Simulate character action, then resolve the scene

The current development architecture makes the pre-draft causal step explicit through the `story-simulation` pack.

`character.action_propose` asks what an important character would plausibly attempt given that character's:

- agenda and immediate goal;
- beliefs and knowledge boundary;
- incentives and risks;
- relationship state;
- spatial situation;
- emotional and event aftermath.

`scene.resolve_actions` then resolves collisions among those proposed actions and the world state into a causal event trajectory.

This ordering matters. The framework does not first invent a convenient scene outcome and then force every character to cooperate with it.

**Output:** character-owned action proposals + a scene-level causal trajectory.

**Failure route:** Character Simulation or Scene Simulation; if the scene only works through character distortion, return to Story / Plan.

---

## 06 · Establish reader pressure before drafting

A causally legal scene can still be dull. Reader Pressure asks what makes the current unit matter **to the reader now**.

Useful pressure may come from:

- a live desire, threat, dilemma, or promise;
- uncertainty with meaningful consequences;
- relationship tension;
- a choice with cost;
- a reveal, reversal, failure, or earned payoff;
- contrast that prevents monotonous escalation;
- an explicit reader expectation that the chapter should advance or complicate.

Reader pressure is a design target, not a demand for mechanical cliffhangers.

If a scene is later diagnosed as SAFE-BUT-FLAT, repair returns here and to scene simulation rather than decorating sentences.

---

## 07 · Generate an event-first Raw Draft

Only after the current causal problem is sufficiently resolved does prose generation begin.

“Event-first” means the Raw Draft prioritizes:

- choices and mistakes;
- conflict and response;
- information movement;
- state change;
- consequence and cost;
- relationship movement;
- earned reader reward.

Routine procedure should be compressed unless it carries conflict, character, information, or consequence.

Raw Draft is **internal**. It is not the Review Draft and is never automatically user-visible.

Negative regression examples remain excluded until Raw Draft freeze. This prevents known failures from becoming first-pass stylistic priming.

---

## 08 · Realize the prose surface

Surface Realization converts event-first material into the Project's prose profile while respecting Framework Surface Fundamentals.

This stage owns prose realization problems such as recurring AI-text rhythms, narrator hype, mechanical micro-actions, voice leakage, process-report narration, fake significance, or malformed compression / expansion.

Repair scale matters:

- isolated surface defect → local rewrite;
- clustered realization failures → regenerate the scene realization;
- clean but inert prose → do **not** stay at the sentence layer.

Surface cleanliness is a floor, not the release criterion.

---

## 09 · Freeze the candidate before post-generation regression

Once the first realized candidate exists, freeze its artifact fingerprint before introducing post-generation regression evidence.

Only now should the manager load relevant negative regressions or known failure exemplars.

The purpose is twofold:

1. prevent first-pass generation from being primed by bad examples;
2. make every downstream diagnosis refer to an exact candidate rather than a moving target.

Material candidate changes create a new fingerprint and invalidate review results that were bound to the old artifact.

---

## 10 · Diagnose through exact semantic contracts

There is no single universal critic prompt.

The manager chooses the smallest relevant contract pack from `model_contract_catalog.json`; deterministic runtime resolves the exact contract ID to exactly one pack.

For candidate quality work, the `quality` pack currently exposes:

- `reader.reaction` — reader experience evidence;
- `reader.compare` — bounded pairwise reader comparison;
- `character.integrity` — character-behavior integrity;
- `revision.diagnose` — diagnosis plus repair-owner routing.

Other packs may be selected when the problem requires them:

- `narrative-memory` for derived narrative state or reader expectations;
- `long-horizon` for plan, relationship, or commitment reconciliation;
- `creative-evolution` for materially divergent scene alternatives or incumbent/challenger comparison.

A semantic result is evidence. It does not gain Canon or write authority merely because a model produced it.

---

## 11 · Convert diagnosis into findings and repair ownership

Diagnosis should become explicit evidence rather than a vague instruction to “make it better.”

Quality findings record the problem and evidence in a form that can be traced across candidate evolution. `revision.diagnose` can identify which mechanism actually owns the defect.

Typical routing:

**Surface defect** → local rewrite or scene realization regeneration.

**SAFE-BUT-FLAT / reader-grip failure** → Reader Pressure + Scene Simulation.

**Character integrity failure** → Character Simulation; possibly Story / Plan if the scene premise itself requires distortion.

**Story / causal failure** → Story / Plan.

**Context / memory failure** → Context / Memory.

**Long-horizon commitment failure** → continuity / plan / relationship reconciliation, not sentence polishing.

**Valid independent semantic reject** → the owning repair layer, never reviewer-shopping.

---

## 12 · Evolve candidates instead of assuming every rewrite is better

Revision is not automatically progress.

NovelForge keeps candidate lineage and can compare an incumbent with a challenger. The `creative-evolution` pack exposes `quality.compare` for evidence-driven comparison, and `scene.diverge` when the workflow needs a genuinely different causal alternative rather than another local paraphrase.

The comparison is allowed to conclude:

- challenger is better;
- incumbent remains better;
- neither has a meaningful advantage / tie.

Quality evolution therefore supports **plateau stopping**. If revision no longer creates real evidence of improvement, the system may stop instead of entering endless rewrite churn.

Deep guide: [Quality Evolution](quality-evolution.en.md).

---

## 13 · Audit reader experience and long-horizon commitments

Before release, the candidate must survive the gates relevant to the current task.

Reader Engagement asks whether the chapter has pressure, causality, payoff, contrast, meaningful movement, and forward pull.

Long-horizon work can use the `long-horizon` pack's `continuity.commitment_audit` to check the candidate against explicit commitments and established facts. Relationship memories can be reconciled through `relationship.memory_reconcile` when long-lived evidence conflicts.

Continuity includes more than trivia. It may cover:

- character knowledge and presence;
- location and movement;
- promises, obligations, deadlines, resources, injuries, and debts;
- relationship movement;
- open loops and setup / payoff obligations;
- chronology;
- emotional and event aftermath.

A contradiction is not repaired by declaring the new version Canon.

---

## 14 · Use independent review only when independence is required

Independent semantic review is a **specific gate**, not a synonym for all model judgment.

When the active rubric or workflow requires independence, the result must come from a genuinely different invocation / session and be bound to the exact artifact fingerprint. The review packet is bounded; hidden gold and the manager's entire history are excluded.

A transport failure may justify an eligible fallback. A valid semantic rejection is a real result and must route to repair.

If independence is not required for a particular semantic contract, normal model-owned semantic work may execute through another eligible route without pretending to be an independent reviewer.

Deep references: [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md) and [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md).

---

## 15 · Cross the user-visible gate truthfully

Raw Draft never crosses this gate.

A candidate may be presented as review-ready only when the gates required by the active task are resolved. Honest unresolved states include:

`awaiting_user` · `awaiting_external` · `semantic_pending` · `failed_gate` · `settlement_incomplete`

A missing required judgment is not PASS. A stale fingerprint is not PASS. A continuity defect hidden by fluent prose is not PASS.

The goal is not maximal ceremony; it is a truthful boundary between internal production candidates and user-visible artifacts.

---

## 16 · Acceptance starts a different transaction: SETTLE

User-visible Review Draft and Accepted Canon are different authority classes.

Only explicit acceptance or an explicit authorized Canon-change request may enter settlement. The deterministic settlement runtime does **not** infer acceptance, State Delta, Canon meaning, or literary intent.

A settlement transaction requires exact accepted-artifact evidence and explicit write intent, including:

- accepted artifact reference + fingerprint;
- acceptance receipt;
- checkpoint reference;
- write-authorization reference;
- exact create / update / delete operations;
- before-state fingerprints for compare-and-swap where required;
- required derived projections and their receipts;
- authoritative postcondition verification.

Required projection failure yields `settlement_incomplete`; completed projection receipts are not silently replayed as new work.

This keeps generation, review, acceptance, and Canon mutation as four distinct events.

---

## 17 · What this pipeline is optimizing for

The pipeline is strict backstage so the fiction can remain natural on the page.

It is designed to prevent recurring long-form failure modes:

- future plans leaking into current truth;
- characters acting with manager-only knowledge;
- flat scenes being cosmetically polished instead of causally repaired;
- regression examples contaminating first-pass generation;
- reviewers judging different candidate fingerprints;
- repeated rewrites continuing after improvement plateaus;
- derived memory or semantic output quietly gaining story authority;
- resume paths repeating consequential writes;
- user-visible approval being confused with completed settlement.

The intended result is not prose that looks engineered. It is **engineering that disappears behind fiction that feels alive**.

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="52" />
  <br />
  <sub>Simulate causality. Draft internally. Diagnose precisely. Evolve with evidence. Settle only after acceptance. 🌸</sub>
</div>
