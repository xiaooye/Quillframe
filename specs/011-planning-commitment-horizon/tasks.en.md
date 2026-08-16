# Planning Commitment Horizon — Tasks

## Before-state / evidence

- [x] Record AI-Novel-Writing-Assistant exact implementation evidence and its soft-label counterexample in #67.
- [x] Record Stanford Generative Agents exact implementation evidence for progressive near-term decomposition and bounded schedule rewrite.
- [x] Audit overlap with `plan.reconcile`, `scenario_fork`, and #63 propagation debt.
- [x] Define profile boundary: no universal chapter/volume/time horizon.

## Design

- [x] Write bilingual specification before implementation.
- [x] Write bilingual implementation plan before implementation.
- [x] Keep #67 independent of unmerged #65; creative-decision refs are opaque only.
- [x] Preserve plan-vs-Canon and Settlement authority boundaries.

## Stage 1 — executable contract

- [ ] Implement `harness/planning_horizon.py`.
- [ ] Add `harness/planning_horizon.schema.json`.
- [ ] Implement portable profile policy and region artifact validation/fingerprinting.
- [ ] Implement registered artifact-kind -> planning-depth admission.
- [ ] Fail closed on unknown artifact kinds.
- [ ] Implement exact-before CAS horizon transition with allowed actor classes.
- [ ] Implement one-wave dependency-evidence rebalance frontier.
- [ ] Ensure no automatic `plan.reconcile`, propagation-debt creation, active-plan mutation, Canon, Framework, Project, or Settlement write.

## Stage 1 regressions

- [ ] soft/beat blocks `chapter_plan`.
- [ ] hard/chapter-detail permits `chapter_plan` when profile allows.
- [ ] writer cannot promote/deepen horizon.
- [ ] authorized actor can promote with exact before version/fingerprint.
- [ ] stale transition fails closed.
- [ ] unknown artifact kind fails closed.
- [ ] non-adjacent dependency with matching evidence is selected.
- [ ] adjacent region without dependency evidence is excluded.
- [ ] assumption-scoped dependency triggers only on changed-assumption intersection.
- [ ] frontier is one wave and performs no follow-up action.
- [ ] tightly plotted short-work profile can allow deep hard planning.
- [ ] discovery profile can preserve soft near-future planning.
- [ ] all artifacts/results report authority=false and model_execution=false.

## Stage 2 — real runner

- [ ] Add dedicated `novelforge-planning-horizon.yml`.
- [ ] Compile tool and validate schema on GitHub-hosted Python 3.11.
- [ ] Run deterministic self-test and invariant assertions.
- [ ] Upload exact-head deterministic receipt artifact.
- [ ] Do not start Framework integration until dedicated workflow is green.

## Stage 3 — Framework integration

- [ ] Register tool/schema/policy semantics in `HARNESS_MANIFEST.yaml`.
- [ ] Make dedicated workflow reusable and required by top-level normal CI.
- [ ] Integrate reusable contract checks where the latest repo architecture requires them.
- [ ] Register 011 bilingual spec/plan/tasks in documentation manifest.
- [ ] Run exact-head full NovelForge deterministic CI.
- [ ] Attribute concurrent Product/Studio baseline failures separately; do not fix them from this Core branch.

## Stage 4 — semantic evaluation

- [ ] Add blind semantic capability case for meaningful far-future over-concretization.
- [ ] Add tightly plotted short-work counterexample.
- [ ] Add discovery-writing near-future-soft counterexample.
- [ ] Use a genuinely independent fingerprint-bound reviewer/model.
- [ ] If independent reviewer capability is unavailable, emit/retain `PENDING_MODEL`; never self-score PASS.

## Promotion / rollback

- [ ] Recompare latest `main` before merge and preserve concurrent product work.
- [ ] Verify no Project lock, manuscript, Canon, user taste, or Settlement state changed.
- [ ] Verify #67 does not depend on #65 merge order.
- [ ] Verify disabling/removing horizon enforcement leaves existing active plans unchanged and falls back to existing planning contracts.
- [ ] Keep PR Draft until required General Craft semantic evidence is complete.
