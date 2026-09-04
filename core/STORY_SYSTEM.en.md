# Story System · Planning scale without pretending the future already happened

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>STORY HIERARCHY</kbd>&nbsp;&nbsp;<kbd>PLAN ≠ CANON</kbd></p>

Quillframe models long-form fiction as **persistent story objects at different planning scales** plus transient scene beats. The system exists to keep a serial coherent across chapters without requiring the distant future to be specified at scene-level detail.

> **Boundary ✦** The Story System owns planning structure, dramatic objectives, dependencies, and expected state movement. It does **not** decide what has already happened. Current truth belongs to the consuming project's Canon/state system.

## 01 · What this system owns

The Story System defines generic mechanics for:

- book-, volume-, arc-, unit-, chapter-, and scene-level planning;
- rolling elaboration: high resolution near the writing frontier, lower resolution farther away;
- scene simulation inputs such as participant agendas, knowledge, leverage, and constraints;
- reader-pressure requirements such as active questions, consequential choices, payoff, and forward pull;
- cross-object dependencies that invalidate future plans when their premises change.

It does not own:

- project-specific plot facts;
- Accepted Canon;
- character or relationship current state;
- research truth;
- runtime/session state;
- model memory;
- semantic-review authority.

Those domains may supply inputs to planning, but they do not become Story-System authority.

## 02 · Planning hierarchy

```text
BOOK
└─ VOLUME
   ├─ ARC      long-running dramatic line; may cross units or volumes
   └─ UNIT     contiguous production/consumption block
      └─ CHAPTER
         └─ SCENE
            └─ beat   usually transient; persist only when the project needs it
```

`ARC` and `UNIT` are intentionally different.

**Arc** answers: *what long-running question, relationship, investigation, struggle, or transformation is moving?*

**Unit** answers: *what contiguous block of chapters creates a concrete objective, pressure sequence, payoff, cost, and exit state?*

A volume may contain several units while multiple arcs pass through them.

## 03 · BOOK contract

A book-level design establishes the long-form promise and outer constraints.

```yaml
id:
title:
genre:
audience:
premise:
core_fantasy:
reader_promise:
protagonist_long_desire:
central_conflict:
expansion_ladder: []
core_progression: []
major_themes: []
relationship_promise:
end_state:
hard_limits: []
status:
```

A useful book design can answer:

- Why should the reader stay for a very long work?
- What kind of pleasure or fantasy is repeatedly renewed?
- How does scope expand without repeating the same conflict with larger numbers?
- What long desire keeps the protagonist moving?
- What relationship/world/end-state promises must eventually be paid?
- What is intentionally out of scope?

Book design fixes the ending, every volume spine, cross-volume plot/relationship/character arcs, and the climax chain. It is not a chapter-by-chapter prophecy. Chapter count, scene order, local obstacles, dialogue, and realization are elaborated by the rolling plan; changing the approved macro spine requires a new fingerprint and explicit author approval.

## 04 · VOLUME contract

A volume should represent a **state transformation**, not a bag of episodes.

```yaml
id:
book_id:
title:
timeframe:
primary_stage:
start_state:
end_state:
volume_desire:
volume_question:
reader_promise:
primary_opposition:
major_arcs: []
major_events: []
resource_delta:
status_delta:
relationship_delta:
character_arc_delta:
world_expansion:
midpoint_shift:
low_point:
climax:
final_payoff:
exit_condition_to_next_volume:
status:
```

A valid volume makes the `start_state → end_state` difference legible. If the same characters, permissions, resources, relationships, world access, and unresolved questions could be copied unchanged into the next volume, the design is probably episodic rather than transformational.

## 05 · ARC contract

An arc is a long-running line of pressure and change. It may belong to a protagonist, antagonist, supporting character, relationship, institution, investigation, family, romance, or social movement.

```yaml
id:
volume_ids: []
name:
type:
central_question:
participants: []
start_state:
desired_end_state:
owner_goal:
opposing_forces: []
stakes:
turning_points: []
planned_payoff:
dependencies: []
crosslinks: []
status:
```

An arc can cross units and volumes. Its turning points are plans until Accepted evidence establishes them.

## 06 · UNIT contract

A unit keeps a serial from dissolving into unrelated chapters.

```yaml
id:
volume_id:
title:
chapter_window:
primary_arcs: []
concrete_objective:
entry_state:
pressure_sequence: []
major_choices: []
payoff:
cost:
exit_state:
new_open_loops: []
status:
```

A strong unit has a recognizable entry condition, escalating pressure, at least one meaningful choice or reorientation, and a payoff/cost that changes what the next unit can be.

## 07 · CHAPTER contract

A chapter is both a production unit and a reader-experience contract.

```yaml
id:
unit_id:
title:
time_range:
locations: []
pov:
chapter_task:
entry_state:
main_problem:
reader_question:
scenes: []
must_happen: []
may_change: []
forbidden: []
payoff:
cost_or_counterpressure:
exit_state:
new_open_loops: []
state_delta_expected:
status:
```

The chapter plan should be specific enough to simulate and draft, but not so prescriptive that it scripts every sentence.

**A chapter plan is future intent. It is never evidence that the planned events occurred.**

## 08 · SCENE contract

A Scene Card constrains simulation. It is not a miniature screenplay.

```yaml
id:
chapter_id:
time:
location:
pov:
participants: []
entry_state:
scene_problem:
agenda_by_character: {}
knowledge_by_character: {}
misread_by_character: {}
leverage_by_character: {}
constraints: []
trigger:
action_reaction_sequence: []
pivot:
result:
relationship_delta:
resource_delta:
permission_delta:
information_delta:
emotional_aftereffect:
exit_state:
physical_anchors: []
voice_constraints: []
forbidden_forms: []
```

Before prose, a meaningful scene should make the following legible:

- what each important participant wants **now**;
- what each participant thinks is happening;
- what they know, suspect, misread, or cannot know;
- what leverage and constraints are actually available;
- what changes tactic or forces a choice;
- what concrete state may be different at the end.

Simulation produces plausible action/response possibilities. It should not pre-write polished interior monologues or dialogue for the prose model to copy.

## 09 · Rolling elaboration

Do not plan a thousand chapters at one resolution.

A useful default gradient is:

```text
BOOK / fixed ending and arcs     explicit and locked
all VOLUME spines and climaxes   explicit and locked
current VOLUME + active ARCS     detailed
next UNIT                         production-ready
next 1–3 CHAPTERS                 scene-ready
farther chapters                  sparse directional placeholders
```

The exact horizon is profile- and project-sensitive. The invariant is that **what happens, why it happens, and its irreversible macro consequence are fixed at Setup; detail increases near execution to decide how it happens**. Distant chapter realization remains revisable, but the approved ending, volume plots, arc terminal states, and climax chain do not silently move.

When Accepted Canon changes an upstream assumption, dependent future plans are re-evaluated instead of being preserved merely because they were expensive to generate.

## 10 · Reader pressure belongs in planning

A plan must model not only event order, but the evolution of reader attention.

A useful chapter/unit pattern is:

```text
live question
→ pressure changes the available options
→ partial reward / useful information
→ a sharper or different question
→ consequential choice
→ changed state
→ reason to continue
```

This is not a mandatory formula. It is a check against chapters that merely report correct procedure.

Routine process should usually be compressed. Expand the places where action changes because of conflict, error, cost, choice, relationship, surprise, or consequence.

## 11 · Dependency-aware planning

A plan may depend on:

- character state;
- relationship state;
- information ownership;
- resources, permissions, or obligations;
- a prior Accepted event;
- foreshadow/reveal state;
- a research claim;
- an open loop or promise;
- a runtime-visible project constraint.

Dependencies should be explicit enough that an upstream change can invalidate or re-evaluate downstream plans.

**Do not repair continuity by silently rewriting current truth to fit an old plan. Repair or replace the plan.**

## 12 · Inputs and outputs

Typical inputs:

- authoritative project/current state;
- Accepted Canon evidence;
- character/relationship state;
- active plans and dependencies;
- verified research claims;
- project/profile constraints;
- reader-engagement targets.

Typical outputs:

- proposal or `active_plan` story objects;
- Scene Cards;
- dependency references;
- expected but unsettled state deltas;
- reader questions, pressure, payoff, and open-loop expectations.

Outputs remain planning artifacts until another authority class explicitly changes them.

## 13 · Failure semantics

Route failures to the mechanism that owns them:

- no meaningful state transformation at volume/unit scale → redesign Story/Volume/Unit;
- chapter is correct but flat → Reader Pressure + chapter/scene planning;
- scene depends on impossible character knowledge → Character Simulation / information ownership;
- future plan conflicts with Accepted state → invalidate or re-plan the future;
- scene card over-scripts prose → reduce to constraints, agendas, state, and pivots;
- distant chapter realization becomes brittle → lower unit/chapter/scene resolution while preserving the approved ending and causal volume spine.

Do not use prose revision to hide a planning failure.

## 14 · Authority invariants

1. `proposal` and `active_plan` are future intent, not occurrence.
2. Review Draft is not Accepted Canon.
3. A Scene Card never proves that a scene happened.
4. A semantic/eval result may criticize a plan; it does not become story truth.
5. Accepted evidence and explicit project authority may invalidate plans.
6. Planning never writes Canon by side effect.

## 15 · Related contracts

- [Canon & State Model](CANON_STATE.en.md) — what is true, accepted, and settled.
- [Character & Relationship System](CHARACTER_SYSTEM.en.md) — agenda, knowledge, voice, relationship and presence state.
- [Reader Engagement](../surface/READER_ENGAGEMENT.en.md) — the positive reader-quality model used to pressure-test plans.
- [Production Pipeline](../docs/production-pipeline.en.md) — where planning, simulation, drafting, and revision interact.
