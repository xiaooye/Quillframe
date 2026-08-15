# Tasks · Story Workspace & Narrative Runtime

> The current `feature/008-story-workspace` branch has been rebuilt on current main and retains only the Core-safe slice that cannot overwrite shared registries. The earlier full-integration attempt is preserved on backup branches and is **not** a release candidate; the statuses below describe the current feature branch.

- [x] T1 · Create `spec / plan / tasks` and freeze authority / non-goal / acceptance boundaries.
- [x] T2 · Define `novelforge_story_workspace_v1` schema and Core projector; cover standard + mapped synthetic Projects.
- [x] T3 · Define `novelforge_context_trace_v1`, linking Inspector / `context.select` / memory-tier packing provenance.
- [x] T4 · Define `novelforge_event_ir_v1` schema, validator, and synthetic event fixtures.
- [x] T5 · Define `novelforge_scene_simulation_run_v1`, binding base state / semantic results / Event IR / branch fingerprints.
- [x] T6 · Define `novelforge_candidate_state_delta_v1`, representing candidate `before -> after + evidence` while remaining non-authoritative.
- [x] T7 · Define the `narrative.verify` semantic contract and `novelforge_narrative_verification_v1` layered report, keeping semantic issues distinct from transport failure.
- [x] T8 · Add deterministic guards for stale fingerprint, future knowledge, authority flattening, selected-branch-is-not-Canon, and semantic-reject-is-not-transport-failure; add three generic narrative eval fixtures.
- [ ] T9 · Incrementally merge the new schemas / tools / semantic contract into current-main `HARNESS_MANIFEST.yaml`, semantic catalog, top-level CLI, and model-free CI without replacing shared registries with stale feature blobs.
- [ ] T10 · Incrementally add read-only `story.workspace` / `context.trace` / `scene.simulation.inspect` / `state.candidate.inspect` / `continuity.verify` to the current-main Studio Host Bridge while preserving existing Publication/runtime operations.
- [ ] T11 · Wire the implemented `NarrativeWorkspace.tsx` into the current-main Studio routes/product shell while preserving Inspector / Control / Architecture / Publication and the prior execution playground, with no parallel Canon store.
- [ ] T12 · Incrementally register the completed bilingual `docs/story-workspace.*` and 008 spec/plan/tasks in the current-main documentation manifest and update architecture / context / pipeline / Studio references.
- [ ] T13 · After shared integration, run deterministic contract / syntax / schema / bundle / Studio typecheck/build / documentation-quality tests and repair regressions.
- [ ] T14 · Obtain independent semantic capability / regression evidence with the blind narrative fixtures; fixture existence alone is not semantic acceptance.
- [ ] T15 · Open a new Draft PR from current main and review the exact diff, authority boundary, rollback path, base drift, and CI status; old PR #80 was closed by the clean reset and is not the current acceptance target.
- [ ] T16 · After merge, produce a new exact Framework commit plus deterministic bundle fingerprint / attestation evidence.
- [ ] T17 · Only after release evidence is complete, migrate a consuming Project's `novelforge.lock.json` / attestation separately; old production sessions do not ordinary-resume across the dependency change.
