# Tasks · Zero-Setup Bootstrap and Claude Code Host Guard

Format: `[ID] [P?] [Phase/Story] exact target + completion criterion`

## Phase 1 · Foundation

- [x] T001 Freeze current `main`, inspect open PRs/branches, and record current Claude/Project SDK gaps.
- [x] T002 Research current official Claude Code CLAUDE import and hook contracts.
- [x] T003 Write spec/plan/tasks with explicit non-goals and rollback.

## Phase 2 · Project Authority

- [x] T010 Add exact clean-checkout Framework identity helper to `project_sdk.py`.
- [x] T011 Make new Project init write exact lock + matching `framework.attestation.json`.
- [x] T012 Add explicit `pin` operation and `authority_ready` validation without silent legacy migration.

## Phase 3 · Host Entry

- [x] T020 Add `quillframe` console entry point and CLI delegation.
- [x] T021 Replace root Claude router-only behavior with supported static imports.
- [x] T022 Upgrade Claude hook from telemetry-only to bootstrap context + cached authority snapshot.
- [x] T023 Add fail-closed consumer guard for consequential tools when authority verification fails.
- [x] T024 Scaffold consumer `.claude/settings.json` using the installed host bridge.

## Phase 4 · Verification

- [x] T030 Add deterministic bootstrap/host regression tests.
- [x] T031 Run core/unit/docs quality CI and repair candidate-owned failures.
- [x] T032 Verify no model/live API execution was introduced into normal CI.

## Phase 5 · Documentation / Acceptance

- [x] T040 Synchronize English/Chinese Quick Start and Project SDK docs.
- [x] T041 Review exact diff for Framework/Project/Canon boundary overreach.
- [ ] T042 Merge only after CI is green; delete the temporary branch after merge.
