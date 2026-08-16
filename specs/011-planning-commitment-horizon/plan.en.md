# Planning Commitment Horizon — Implementation Plan

## Objective

Implement #67 as a small deterministic planning-admission and rebalance-frontier contract layered on existing NovelForge planning primitives. Do not introduce a second active-plan database or any Canon authority.

## Phase 0 — authority and overlap

- Base the branch on an exact current `main` commit.
- Treat current `plan.reconcile`, `scenario_fork`, #63 propagation debt, Context, Canon/Settlement, and semantic-worker contracts as existing owners.
- Keep #65 an optional opaque-reference integration only; this branch must build and run if #65 is not merged.

## Phase 1 — portable region/policy contract

Create `harness/planning_horizon.py` and a machine schema.

The deterministic contract should support:

1. canonical fingerprinting of policy/region artifacts;
2. small fixed planning-depth registry and known artifact-kind mapping;
3. region creation/validation with `open|soft|hard` strength and a depth ceiling no greater than the selected profile policy allows;
4. realization admission for a registered artifact kind;
5. explicit CAS horizon transition with allowed actor classes and evidence refs;
6. one-wave rebalance-frontier selection from explicit dependency evidence;
7. authority=false on every artifact/result and no model execution.

## Phase 2 — deterministic regressions

Self-test at minimum:

- soft/beat blocks chapter detail;
- hard/chapter-detail permits chapter plan when profile permits;
- unknown artifact kind fails closed;
- writer cannot promote;
- authorized planner/user can promote with exact before state;
- stale version/fingerprint fails;
- identical retry is deterministic and does not create hidden write authority;
- non-adjacent linked dependency is selected;
- adjacent unlinked dependency is excluded;
- assumption-scoped dependency only triggers when changed assumptions intersect;
- frontier result performs no reconcile/debt/Canon operation;
- tight-short and discovery profile counterexamples are both representable.

## Phase 3 — dedicated CI first

Add a dedicated workflow that:

- compiles the tool;
- validates schema JSON;
- runs self-test;
- asserts authority/no-model/no-auto-action invariants;
- uploads the deterministic receipt.

Do not modify HARNESS/docs/normal CI until this workflow passes on the real GitHub runner against the current repository.

## Phase 4 — Framework integration

After dedicated CI is green:

- register the tool/schema in `HARNESS_MANIFEST.yaml`;
- make the dedicated workflow reusable and a normal-CI job;
- add any reusable-contract invocation needed by the current repository architecture;
- register bilingual `spec/plan/tasks` in documentation governance;
- preserve all concurrently developed Product/Studio files from current main.

## Phase 5 — semantic capability/counterexample eval

Use existing NovelForge blind eval infrastructure. Add profile-boundary cases such as:

- **capability:** a serialized novel has only a soft far-future arc role, but a planner tries to generate detailed chapter plans several arcs ahead. Expected route: block/escalate for horizon promotion rather than silently concretize.
- **counterexample:** a short mystery has an explicit user requirement for a fully plotted 12-chapter structure before drafting. Expected route: allow a profile that hard-plans the whole work rather than forcing artificial softness.
- **counterexample:** a discovery-writing profile deliberately keeps even the next chapter's later scenes soft. Expected route: preserve soft planning rather than automatically promoting because the material is near-term.

Missing independent model capability must remain `PENDING_MODEL`, not be converted into self-scored PASS.

## Phase 6 — promotion review

Before merge/promotion:

- verify exact-head deterministic workflows;
- verify semantic evidence or leave PR Draft if semantic evidence remains pending;
- confirm no Project/Canon/manuscript changes;
- confirm no hidden dependency on #65;
- confirm rollback is deletion/disable of horizon enforcement without data migration;
- compare latest main again and preserve concurrent Product/Studio work.
