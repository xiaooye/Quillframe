# NovelForge · Story Workspace & Narrative Runtime

## Problem

NovelForge already has sparse Context, character / scene semantic simulation, scenario forks, state graphs, reader expectations, quality comparison, sessions / checkpoints, and settlement as separate mechanisms. They still exist primarily as low-level contracts and tools, without a unified, explainable, replayable story-workspace semantic layer.

The main gaps are:

1. There is no unified Story Workspace projection that presents structure, characters, relationships, world state, plans, reader commitments, current Context, and exploration branches in one read-only view while preserving authority class.
2. Context Inspector can determine eligibility and stage isolation, but an author still cannot easily inspect why an item was selected, why another was excluded, and what was actually packed into a concrete run budget.
3. Scene simulation already has `character.action_propose` and `scene.resolve_actions`, but there is no shared Event IR or simulation-run envelope that can carry character collisions into planning, drafting, state verification, and Studio.
4. `state_graph.py` can detect stable-field contradictions and unexplained state changes, but there is no formal candidate-prose → candidate-state-delta → narrative-verification boundary.
5. Studio currently behaves more like a Framework developer console; without a Core-owned story projection, adding timelines or character boards directly would create a second story model.

## Goals

- Add `novelforge_story_workspace_v1`: a project-agnostic, read-only, source-bound Story Workspace projection exposing structure / timeline / characters / relationships / world state / active plans / reader expectations / current context / scenario branches without copying Project Canon authority.
- Add `novelforge_context_trace_v1`: evidence for candidate eligibility, author controls, semantic selection, budget packing, exclusion reasons, stage visibility, source fingerprints, and the final loaded working set for one bounded context build.
- Add `novelforge_event_ir_v1`: a causal intermediate representation between Scene Simulation and prose realization covering actors, preconditions, intent, action, obstacle, response, consequence, state changes, knowledge changes, relationship changes, resource changes, and reader-question evolution.
- Add `novelforge_scene_simulation_run_v1`: bind character action proposals, scene resolution, Event IR candidates, scenario branches, and comparison evidence to the same subject / state fingerprint without introducing permanently stateful character agents.
- Add `novelforge_candidate_state_delta_v1`: represent state / knowledge / relationship / resource / obligation / location changes derived from a candidate artifact; candidate deltas remain non-authoritative.
- Add `novelforge_narrative_verification_v1`: combine deterministic state contradictions with model-owned narrative plausibility / knowledge-boundary judgments into typed findings without asking deterministic runtime to make literary judgments.
- Provide stable read/query contracts for Studio so UI consumes Core projections rather than reparsing a Novel Bible or creating another Canon store.

## Core Invariants

1. Workspace / Context Trace / Event IR / Simulation Run / Candidate State Delta / Verification Report default to `authority=false`.
2. `locked / accepted / active_plan / review / proposal / derived / scenario` remain distinct lifecycle / authority classes and must not be flattened by Workspace.
3. Project authority remains owned by the consuming Project manifest / adapter / database; Framework never embeds concrete BOOK/VOL/CHAR/Canon data.
4. Context Trace may explain the selection process, but semantic relevance remains model-owned; deterministic runtime owns eligibility, stage boundaries, hard budgets, author controls, fingerprints, and typed validation.
5. Event IR is a pre-prose causal intermediate representation, not Canon. Actual realization may diverge from Event IR; post-generation evidence must update candidate delta rather than forcing prose to restate the outline.
6. Scene Simulation remains `one manager + bounded semantic invocations`; it must not create a shared-mutable-memory persistent agent society for character realism.
7. Candidate state extraction / verification never auto-settles. Canon changes still require explicit Project acceptance plus a settlement transaction.
8. Studio does not gain direct Canon-write authority. Editing protected facts must create a proposal or use an explicit Project write contract.

## Minimum Event IR Semantics

At minimum support:

- `event_id` / `scene_id` / `story_order`;
- `actors` and `preconditions`;
- `intent` / `action` / `obstacle` / `response` / `consequence`;
- `state_delta` / `knowledge_delta` / `relationship_delta` / `resource_delta`;
- `reader_question_before` / `reader_question_after` / `reader_reward`;
- `source_refs` / `evidence_refs` / `subject_fingerprint`;
- `authority=false` / `canon_write=false`.

Profiles and genres may extend fields, but Generic Framework must not hard-code one project's database tables.

## Minimum Context Trace Semantics

For every candidate item, the trace must be able to answer:

- source / source fingerprint;
- authority class;
- inclusion reason;
- stage visibility;
- author pin / priority / hidden / invalidated state;
- eligibility verdict;
- semantic-selection verdict / order when executed;
- loaded / skipped;
- budget impact;
- exclusion reason;
- semantic result fingerprint / provenance when executed.

Arbitrary numeric relevance heuristics must not become durable literary truth.

## Narrative Verification Layering

Deterministic runtime owns:

- stable-field contradictions;
- unexplained typed state transitions;
- invalid / stale source fingerprints;
- provable future-knowledge / stage-visibility / lifecycle violations;
- candidate-delta schema and before-state binding.

Model semantic contracts own:

- whether an action is adequately supported by known character agenda / relationship / pressure;
- whether a character makes an implausible knowledge leap relative to visible evidence;
- whether a relationship change lacks sufficient narrative evidence;
- whether an event consequence is causally detached from the scene trajectory.

Both layers use the shared finding contract while preserving owner and provenance.

## Non-goals

- Do not replace Project Canon databases with a knowledge graph or vector store.
- Do not turn Event IR into a rigid checklist that prose must mechanically fulfill.
- Do not make deterministic code score tension, character realism, or reader grip.
- Do not create a default multi-character round-table or autonomous agent society.
- Do not promote a selected scenario branch automatically into active plan or Canon.
- Do not upgrade a consuming Project's `novelforge.lock.json` in this slice.
- The first Studio slice does not need Canon mutation; read-only exploration / trace / simulation projections are sufficient.

## Acceptance

1. Story Workspace projection returns a stable schema for synthetic standard and mapped Projects, with source / authority / lifecycle on every object, and does not create a second authoritative state store.
2. Context Trace can reconstruct include / exclude / loaded explanations from Context Inspector + `context.select` + memory-tier packing evidence while preserving semantic relevance owner = model.
3. Event IR validates a synthetic multi-character conflict event containing at least one knowledge change and one resource or relationship change.
4. Scene Simulation Run binds exact base-state fingerprint, character proposal results, scene resolution, Event IR candidates, and branch fingerprints; stale or mismatched results fail closed.
5. Candidate State Delta exposes exact `before -> after + evidence` while returning `authority=false` and `settlement_authority=false`.
6. Narrative Verification can return deterministic contradiction findings and semantic narrative findings in one report while retaining distinct repair owners / provenance; semantic reject is not treated as transport failure.
7. Scenario selection, simulation results, and verification PASS never gain Canon / Settlement / Framework-write authority.
8. Initial Studio / bridge read operations consume Core contracts and do not directly parse consuming-project private schema to create parallel truth.
9. Generic tests use synthetic fixtures only and do not import concrete prose, Canon, identifiers, or private schemas from any consuming Project.
10. New contracts / docs / schemas are covered by deterministic CI, bundle-content inclusion, and bilingual documentation integrity checks.
