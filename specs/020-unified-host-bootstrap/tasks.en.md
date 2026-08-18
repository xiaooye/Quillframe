# Tasks · Unified Claude Code and Codex Project Bootstrap

Format: `[ID] [P?] [Phase] exact target + completion criterion`

## Phase 1 · Authority / Research Freeze

- [x] T001 Freeze live `main` at `e353fd506ae047b22c43442ceba0fda0a73c032d` and create isolated implementation branch.
- [x] T002 Re-read HARNESS manifest, Skill, Harness Agent, Project SDK, host code, session runtime, and Control Plane contracts.
- [x] T003 Verify current official Claude Code and Codex instruction/hook behavior; record Codex trust constraint.
- [x] T004 Write bilingual spec/plan/tasks with explicit non-goals and overreach audit.

## Phase 2 · Unified Host Runtime

- [x] T010 Add `harness/integrations/host_bootstrap.py` with host-neutral scope/authority/session state.
- [x] T011 Persist full `quillframe_agent_session_v1` through Control Plane instead of ad-hoc host session payload.
- [x] T012 Derive truthful `blocked | awaiting_task_mode | running` host states.
- [x] T013 Make `claude_hook.py` a compatibility wrapper over the unified runtime.
- [x] T014 Add Codex wrapper/dispatch with Codex tool alias normalization.

## Phase 3 · Task Mode / Run Gate

- [x] T020 Add `quillframe host-run status|begin` deterministic CLI surface.
- [x] T021 Validate exactly one allowed task mode and start exactly one manager run.
- [x] T022 Deny consequential writes until valid authority + active task mode/run.
- [x] T023 Permit only strict Quillframe bootstrap commands before mode resolution; reject lookalike shell commands.
- [x] T024 Treat Codex `apply_patch` as consequential edit.

## Phase 4 · Host Scaffolding

- [x] T030 Replace root router-only `AGENTS.md` with compact direct Quillframe bootstrap instructions.
- [x] T031 Make official `quillframe init` / `host-install` install the generated consumer `AGENTS.md` with direct exact-authority/session/run bootstrap.
- [x] T032 Generate consumer `.codex/hooks.json` through the official CLI scaffold path and keep Claude host scaffold compatible.
- [x] T033 Add Framework `.codex/hooks.json` for trusted local Codex sessions without requiring package installation for static instruction correctness.
- [x] T034 Add explicit idempotent `quillframe host-install` repair path for existing supported Projects with safe overwrite preconditions.

## Phase 5 · Verification

- [x] T040 Add deterministic unified-host regression tests covering Claude/Codex parity, typed sessions, task modes, runs, write gates, stale authority, hook aliases, and retrofit behavior.
- [x] T041 Verify existing Project SDK/bootstrap tests remain green after compatibility repairs.
- [x] T042 Verify normal CI performs no live model/API execution.
- [x] T043 Run Core/SQLite/authority, docs/site, and Studio CI; run 705 is fully green.

## Phase 6 · Documentation / Acceptance

- [x] T050 Synchronize bilingual Project SDK/integration docs including Codex hook trust instructions.
- [x] T051 Review exact changed-file set for Framework/Project/Canon/provider overreach: changes are limited to host/runtime/CLI/tests/docs/spec surfaces; no Project Canon, settlement, provider secret, or Studio UI path is modified.
- [x] T052 Open draft review PR #141 with the candidate isolated from `main`.
- [ ] T053 Mark ready/merge only after explicit user acceptance; until then keep the candidate reviewable and do not mutate `main`.
