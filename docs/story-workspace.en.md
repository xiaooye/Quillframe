# Story Workspace and Narrative Runtime

NovelForge Story Workspace is not another Story Bible and it is not a giant JSON copy of an entire novel. It is a set of **read-only, source-bound, authority-preserving projections and runtime evidence** that lets authors and Studio inspect the current story model, the context a run actually received, how characters proposed actions, how scenes became causal events, what a candidate would change, and where narrative verification found problems.

It connects the existing Story / Character / Canon, Context, Scenario Fork, State Graph, and Quality systems without creating a second Canon.

## 1 · Story Workspace is a view, not an authority database

`harness/story_workspace.py` produces `novelforge_story_workspace_v1`.

A Workspace can present together:

- Book / Volume / Arc / Unit / Chapter / Scene structure;
- timeline / story order;
- characters and relationships;
- current world / resource / obligation state;
- active plans;
- reader expectations;
- current Context;
- scenario branches.

Every object still retains its own `source_ref`, `source_fingerprint`, `authority_class`, and `lifecycle`. `locked`, `accepted`, `active_plan`, `review`, `proposal`, `derived`, and `scenario` do not become equivalent merely because one UI can display them together.

Workspace itself always remains:

`authority=false · canon_write=false · settlement_authority=false`

The Project Adapter / SDK normalizes Project-owned objects first; Workspace then projects them. The Generic Framework should not guess a consuming project's private Markdown or database schema merely to draw a timeline or character board.

## 2 · Context Trace answers “why did this run see this?”

Context Inspector owns eligibility, stage isolation, and author overlays. `context.select` owns model semantic relevance. Memory Tiers owns deterministic budget packing.

`harness/context_trace.py` combines evidence from those stages into `novelforge_context_trace_v1`, so one concrete context build can explain:

- where a candidate item came from and its authority class;
- which stage may see it;
- whether the author pinned, hid, or invalidated it;
- whether Inspector marked it eligible;
- whether `context.select` selected it, for which tier, and why;
- whether hard-budget packing actually loaded it;
- whether exclusion came from future story order, perspective visibility, author controls, invalidation, or budget constraints.

Ownership stays explicit:

- semantic relevance: model;
- eligibility / stage / authority: deterministic runtime;
- hard budget: deterministic runtime.

Context Trace does not create a durable “literary relevance = 0.83” score, and model selection never upgrades an item's authority.

## 3 · Event IR is the causal intermediate between Scene Simulation and prose

`core/event_ir.py` defines `novelforge_event_ir_v1`.

An Event candidate can represent:

- actors and preconditions;
- intent, action, obstacle, response, consequence;
- state / knowledge / relationship / resource deltas;
- reader-question movement;
- reader reward;
- source / evidence refs;
- exact subject fingerprint.

Event IR is not an attempt to turn fiction into code, and prose is not required to mechanically restate it. It lets Scene Simulation answer the more fundamental question first: **who acts for what reason, what collision follows, and which options, costs, relationships, knowledge, or world state actually change?**

Actual prose realization may diverge from Event IR. Once prose is frozen, the system should derive candidate evidence / state change from what was actually written rather than forcing a living scene back into its earlier causal proposal.

Event IR is never Canon.

## 4 · Scene Simulation remains one manager plus bounded invocations

`harness/scene_simulation_run.py` produces `novelforge_scene_simulation_run_v1`.

A simulation run binds:

1. the exact base checkpoint / state fingerprint;
2. one or more completed `character.action_propose` results;
3. a completed `scene.resolve_actions` result;
4. Event IR candidates;
5. optional scenario branches;
6. optional pairwise comparison evidence.

NovelForge does not therefore create a persistent society of character agents. Character realism comes from perspective-bounded state, agenda, relationships, pressure, and bounded semantic invocations—not from multiple long-lived agents sharing mutable memory and chatting indefinitely.

Stale Event / branch / semantic bindings fail closed. Even a branch marked selected remains a scenario; it does not automatically become an active plan or Canon.

## 5 · Candidate State Delta describes what a candidate would change

`quality/candidate_state_delta.py` produces `novelforge_candidate_state_delta_v1`.

It aggregates candidate events or prose evidence into source-bound transitions:

`before → after + evidence`

Current domains include state, knowledge, relationship, resource, plus supplemental obligation / location changes. When consecutive events modify the same field, one transition's `after` must line up with the next transition's `before`; a broken chain is an explicit candidate-state inconsistency.

Candidate State Delta is only verification / review evidence:

`authority=false · settlement_authority=false`

Only after explicit user acceptance may Project Settlement reread the live before-state and create a real Canon transaction under the Project's authoritative schema.

## 6 · Narrative Verification separates provable errors from interpretive errors

NovelForge should not ask Python to decide whether a character feels real, and it should not ask a model to own an exact before-state mismatch that deterministic code can prove.

`quality/narrative_verification.py` therefore combines two evidence layers into `novelforge_narrative_verification_v1`.

The **deterministic layer** can check stable-state contradictions, unexplained typed transitions, stale fingerprints, provable future-knowledge / lifecycle / stage violations, and candidate-delta binding.

The **semantic layer** uses the progressively disclosed `narrative.verify` contract to judge whether:

- an important action is supported by supplied agenda / pressure / relationship / visible evidence;
- a character uses information they cannot currently possess;
- a relationship change lacks sufficient narrative evidence;
- a consequence is causally detached from the supplied event trajectory.

Both layers produce the shared finding contract while retaining repair owner and provenance. A valid `issues_found` judgment is semantic evidence, not a transport failure and not something to erase through reviewer shopping.

`narrative.verify` is diagnostic. It does not replace an independent production gate such as `quality.production_review` when a Project requires one.

## 7 · Studio consumes Core projections only

The first Story Workspace Host Bridge operations are read-only:

- `story.workspace`
- `context.trace`
- `scene.simulation.inspect`
- `state.candidate.inspect`
- `continuity.verify`

These operations accept only project-relative normalized evidence files inside the current `project_root`. The Host Bridge rejects path escape and does not return host-private absolute paths to the product surface.

`/workspace` presents Story, Context, Simulation, and Verification in author-facing language, with raw Core JSON relegated to expandable evidence. The earlier execution preview remains available at `/playground` for inspecting contract / execution boundaries rather than pretending to be a real novel workspace.

Studio does not parse private consuming-project databases into a second Canon and does not receive Canon / Settlement write authority.

## 8 · Position in DRAFT / REVISE

Story Workspace does not replace the production graph. It makes the boundaries among existing mechanisms inspectable.

After Context Freeze, Context Trace can explain the working set. Scene / Character Simulation can form causal Event candidates. The Writer still creates Raw Draft under isolated first-pass context. After Raw Draft is frozen, actual prose evidence can produce Candidate State Delta, followed by deterministic + semantic Narrative Verification and the existing Reader / Character / Surface / Continuity mechanisms.

A SAFE-BUT-FLAT failure still belongs upstream in Reader Pressure / Scene Simulation. It should not be “fixed” by adding more Event IR fields or patching sentences. Event IR is a causal carrier, not a substitute for story quality.

## 9 · Authority mental model

A useful model is:

**Project authority supplies facts → Workspace supplies a readable projection → Context Trace explains a working set → Simulation proposes causal possibilities → Event IR expresses candidate events → prose realizes them → Candidate Delta describes candidate changes → Verification produces evidence → the user decides whether to accept → Settlement alone changes Canon.**

No intermediate artifact gains write authority merely because it appears coherent or useful.

## 10 · Exact implementation entry points

- `harness/story_workspace.py` / `harness/story_workspace.schema.json`
- `harness/context_trace.py` / `harness/context_trace.schema.json`
- `core/event_ir.py` / `core/event_ir.schema.json`
- `harness/scene_simulation_run.py` / `harness/scene_simulation_run.schema.json`
- `quality/candidate_state_delta.py` / `quality/candidate_state_delta.schema.json`
- `quality/narrative_verification.py` / `quality/narrative_verification.schema.json`
- `harness/semantic_workers/contracts/story-simulation.json`
- `harness/semantic_workers/contracts/narrative-verification.json`
- `harness/semantic_workers/model_contract_catalog.json`
- `studio/host_bridge.py`
- `studio/app/src/routes/NarrativeWorkspace.tsx`

Story Workspace is meant to make **causality, context, character knowledge, state transitions, and authority boundaries inspectable while keeping genuine literary judgment with models and authors**—not to engineer the life out of fiction.
