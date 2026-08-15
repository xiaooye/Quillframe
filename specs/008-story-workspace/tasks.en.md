# Tasks · Story Workspace & Narrative Runtime

> The current `feature/008-story-workspace` branch is integrated on current main. Shared registries, CLI, Host Bridge, Studio routes, and documentation were merged incrementally so current-main Publication, Inspector, runtime-control, and authorized local `session.resume` behavior remain intact. Earlier integration attempts remain on backup branches for forensic rollback only and are **not** release candidates.

- [x] T1 · Create `spec / plan / tasks` and freeze authority / non-goal / acceptance boundaries.
- [x] T2 · Define `novelforge_story_workspace_v1` schema and Core projector; cover standard + mapped synthetic Projects.
- [x] T3 · Define `novelforge_context_trace_v1`, linking Inspector / `context.select` / memory-tier packing provenance.
- [x] T4 · Define `novelforge_event_ir_v1` schema, validator, and synthetic event fixtures.
- [x] T5 · Define `novelforge_scene_simulation_run_v1`, binding base state / semantic results / Event IR / branch fingerprints.
- [x] T6 · Define `novelforge_candidate_state_delta_v1`, representing candidate `before -> after + evidence` while remaining non-authoritative.
- [x] T7 · Define the `narrative.verify` semantic contract and `novelforge_narrative_verification_v1` layered report, keeping semantic issues distinct from transport failure.
- [x] T8 · Add deterministic guards for stale fingerprint, future knowledge, authority flattening, selected-branch-is-not-Canon, and semantic-reject-is-not-transport-failure; add three generic narrative eval fixtures.
- [x] T9 · Incrementally merge the new schemas / tools / semantic contract into current-main `HARNESS_MANIFEST.yaml`, semantic catalog, top-level CLI, and model-free CI without replacing shared registries with stale feature blobs.
- [x] T10 · Incrementally add read-only `story.workspace` / `context.trace` / `scene.simulation.inspect` / `state.candidate.inspect` / `continuity.verify` to the current-main Studio Host Bridge while preserving existing Publication/runtime operations and the authorized local runtime-command surface.
- [x] T11 · Wire `NarrativeWorkspace.tsx` into the current-main Studio routes/product shell while preserving Inspector / Control / Architecture / Publication and the prior execution playground, with no parallel Canon store.
- [x] T12 · Register the bilingual `docs/story-workspace.*` and 008 spec/plan/tasks in the current-main documentation manifest and update architecture / context / pipeline / Studio references.
- [ ] T13 · Run deterministic contract / syntax / schema / bundle / Studio typecheck/build / documentation-quality tests and repair feature regressions; distinguish any unrelated current-main hygiene blocker from 008 failures.
- [ ] T14 · Obtain independent semantic capability / regression evidence with the blind narrative fixtures; fixture existence and hidden-label isolation alone are not semantic acceptance.
- [ ] T15 · Review Draft PR #81 exact diff, authority boundary, rollback path, base drift, and final CI status; old PR #80 remains closed and is not the acceptance target.
- [ ] T16 · After merge, produce a new exact Framework commit plus deterministic bundle fingerprint / attestation evidence.
- [ ] T17 · Only after release evidence is complete, migrate a consuming Project's `novelforge.lock.json` / attestation separately; old production sessions do not ordinary-resume across the dependency change.
