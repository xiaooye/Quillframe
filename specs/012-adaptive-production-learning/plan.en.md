# Plan 012 · Adaptive Production Learning and Realization Boundary

## Goal

Connect existing NovelForge primitives into a stateful co-creative production loop without creating duplicate subsystems or weakening authority boundaries.

## Workstream 1 · Author Model and review feedback

1. Add a deterministic Author Model projection runtime backed by the existing Learning Store.
2. Add a semantic `learning.preference_interpret` contract for bounded interpretation of explicit review feedback.
3. Separate observation, hypothesis, activation, and production projection.
4. Support contradiction/supersession and scope-aware activation rules.
5. Connect existing `feedback.observed` Author Steering to the review-learning lifecycle by contract/documentation, not by automatic mode switching.

## Workstream 2 · Adaptive Context Assembly

1. Extend context stages so private simulation state can be visible to simulation but not to prose generation.
2. Add typed required-context obligations and deterministic satisfaction receipts.
3. Add a context-assembly runtime that validates selected IDs against stage, authority, invalidation state, required class/purpose, and provenance/fingerprint requirements.
4. Preserve semantic relevance ownership in `context.select`.
5. Keep Corpus retrieval conditional; benchmarks are one possible context class, not a universal pipeline stage.

## Workstream 3 · Simulation-before-Prose

1. Reuse `character.action_propose` and `scene.resolve_actions`.
2. Add a semantic `scene.realization_project` contract that converts private simulation evidence into a writer-safe interaction/event projection.
3. Block raw private-character/simulation classes from `writer_pre_draft` by default.
4. Document the interface: private state controls behavior; realization projection controls writer-visible event/dialogue opportunity.

## Workstream 4 · Reader → Editor closed loop

1. Add a structured Reader production audit focused on actual reading experience, profile fit, paragraph rhythm and dialogue realization without exposing creator-private state.
2. Add an `editor.repair_spec` contract that translates Reader evidence into preserve/change priorities and owning repair layers.
3. Reuse `reader.compare` / `quality.compare` for material incumbent/challenger comparison.
4. Extend Production Readiness only for structural receipts that deterministic runtime can actually prove; do not create one deterministic gate per literary dimension.

## Workstream 5 · Quality mechanisms

1. Register HF-30: Agenda-to-Dialogue Leakage / Character-Sheet-to-Dialogue Serialization.
2. Add profile-sensitive prose telemetry as signals only.
3. Add semantic counterexamples for formal-completeness dialogue and legitimate selective short paragraphs.
4. Extend surface/character/reader contracts so the architecture and backstop diagnosis agree.

## Workstream 6 · Safety and integrity

1. Add a write-intent/action guard for resource/operation/target mismatch.
2. Fix stale `model_contracts.json` references and add deterministic semantic-reference integrity checking.
3. Improve semantic-bridge failure classification where Framework code owns the distinction; report repository-setting/configuration owners separately.

## Workstream 7 · Integration and verification

1. Register new tools/contracts in `HARNESS_MANIFEST.yaml` and model contract catalog.
2. Update Harness/Orchestration/production/context/adaptive-learning docs in both languages.
3. Add deterministic self-tests to reusable release contracts CI.
4. Add generic semantic fixtures without hidden expected labels in reviewer queues.
5. Run exact-head CI; distinguish candidate failures from pre-existing repository debt.
6. Obtain independent semantic capability/counterexample evidence for the exact candidate fingerprint when an eligible independent transport is available.
7. Keep PR Draft until evidence is complete enough for human review; no merge, release, or downstream lock migration in this run.

## Compatibility strategy

Prefer additive schemas and optional policy requirements. Existing projects that do not declare new required context/structural receipts remain compatible. Material release identity/version changes are decided only after exact diff and verification.

## Rollback

Each workstream should land in a coherent commit. Any workstream can be reverted independently. The downstream consumer remains pinned to NovelForge 0.8.0 throughout this run, so candidate rollback never changes the book's runtime authority.
