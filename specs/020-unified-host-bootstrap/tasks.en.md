# Tasks · Unified Claude Code and Codex Project Bootstrap

Format: `[ID] [P?] [Phase] exact target + completion criterion`

## Phase 1 · Authority / Research Freeze

- [x] T001 Freeze live `main` at `e353fd506ae047b22c43442ceba0fda0a73c032d` and create isolated implementation branch.
- [x] T002 Re-read HARNESS manifest, Skill, Harness Agent, Project SDK, host code, session runtime, and Control Plane contracts.
- [x] T003 Verify current official Claude Code and Codex instruction/hook behavior; record Codex trust constraint.
- [x] T004 Write bilingual spec/plan/tasks with explicit non-goals and overreach audit.

## Phase 2 · Unified Host Runtime

- [ ] T010 Add `harness/integrations/host_bootstrap.py` with host-neutral scope/authority/session state.
- [ ] T011 Persist full `quillframe_agent_session_v1` through Control Plane instead of ad-hoc host session payload.
- [ ] T012 Derive truthful `blocked | awaiting_task_mode | running` host states.
- [ ] T013 Make `claude_hook.py` a compatibility wrapper over the unified runtime.
- [ ] T014 Add Codex wrapper/dispatch with Codex tool alias normalization.

## Phase 3 · Task Mode / Run Gate

- [ ] T020 Add `quillframe host-run status|begin` deterministic CLI surface.
- [ ] T021 Validate exactly one allowed task mode and start exactly one manager run.
- [ ] T022 Deny consequential writes until valid authority + active task mode/run.
- [ ] T023 Permit only strict Quillframe bootstrap commands before mode resolution; reject lookalike shell commands.
- [ ] T024 Treat Codex `apply_patch` as consequential edit.

## Phase 4 · Host Scaffolding

- [ ] T030 Replace root router-only `AGENTS.md` with compact direct Quillframe bootstrap instructions.
- [ ] T031 Update generated consumer `AGENTS.md` to include direct exact-authority/session/run bootstrap.
- [ ] T032 Generate consumer `.codex/hooks.json` and keep Claude host scaffold compatible.
- [ ] T033 Add Framework `.codex/hooks.json` for trusted local Codex sessions without requiring package installation for static instruction correctness.
- [ ] T034 Add explicit idempotent `quillframe host-install` repair path for existing supported Projects with safe overwrite preconditions.

## Phase 5 · Verification

- [ ] T040 Add deterministic unified-host regression tests covering Claude/Codex parity, typed sessions, task modes, runs, write gates, stale authority, hook aliases, and retrofit behavior.
- [ ] T041 Verify existing Project SDK/bootstrap tests remain green.
- [ ] T042 Verify normal CI performs no live model/API execution.
- [ ] T043 Run docs/site/Studio CI and separate candidate-owned failures from unrelated debt.

## Phase 6 · Documentation / Acceptance

- [ ] T050 Synchronize bilingual Project SDK/integration docs including Codex hook trust instructions.
- [ ] T051 Review exact diff for Framework/Project/Canon/provider overreach.
- [ ] T052 Open review PR only after deterministic candidate checks are ready; merge only after CI and explicit acceptance.
