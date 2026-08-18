# Implementation Plan · Unified Claude Code and Codex Project Bootstrap

## Chosen Architecture

Introduce one host-neutral runtime under `harness/integrations/host_bootstrap.py`. Claude Code and Codex wrappers only normalize host events/tool names and delegate to that core.

The core owns deterministic host bootstrap facts only:

`discover scope → verify Project/Framework authority → load/create typed manager session → expose bootstrap state → validate task-mode transition → start/resume manager run → gate consequential tools`

Semantic selection of `task_mode` remains the model/user's responsibility. Deterministic code validates that the selected mode is one of the Framework modes and that a session cannot silently switch to a second mode while an active run exists.

## Runtime State

Persist the full existing `quillframe_agent_session_v1` payload through Control Plane `put_session`. Host-native session IDs map deterministically to Quillframe session IDs. The typed session contains task mode, runs, checkpoints, events, context policy, and provenance rather than a parallel ad-hoc schema.

Host snapshot state is derived from authority + typed session:

- `blocked`: exact authority invalid for a consumer Project;
- `awaiting_task_mode`: authority valid but no active Quillframe mode/run;
- `running`: exactly one active run exists and its session task mode is valid;
- Framework scope uses the same task-mode/run requirement for consequential Framework edits.

## Host Adapters

### Claude Code

Keep `harness/integrations/claude_hook.py` as a small wrapper. Existing `.claude/settings.json` remains supported and calls the installed CLI.

### Codex

Add `harness/integrations/codex_hook.py` or a common CLI dispatch with `--host codex`. New Projects generate `.codex/hooks.json` for SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/SessionEnd. Match `Bash|Edit|Write|apply_patch` where appropriate.

Because Codex project hooks require trust, `AGENTS.md` is a first-class static bootstrap surface, not merely a pointer to other files.

## Task-mode / Run Command

Add a thin CLI surface:

```text
quillframe host-run status [--session-id ...] [--project .]
quillframe host-run begin --session-id ... --mode DESIGN-BOOK [--project .]
```

`begin` validates authority, session identity, allowed mode, and current active-run state, then updates the typed session with `session_runtime.start_run`. Run ID is deterministic-enough for execution identity but unique per begin operation.

Host-injected context includes the exact Quillframe session ID and the command shape the model may call after it has semantically chosen one mode.

## Write Gate

Consequential tools are denied unless the derived bootstrap state is `running` and exact authority remains fresh.

Before mode resolution, Bash is denied except for a strict parser-recognized Quillframe bootstrap command (`quillframe host-run status|begin ...`). Do not use substring matching. Codex `apply_patch` is normalized to an edit.

Framework-scope edits likewise require an active `SYSTEM-IMPROVE`/other explicitly chosen Framework-appropriate run; fiction task modes must not cause Project facts to be written into the generic Framework repo.

## Static Instructions

Replace router-only root `AGENTS.md` with a compact direct contract covering:

- Generic Framework boundary;
- read manifest/Skill/HARNESS contract;
- exactly one task mode;
- session/run requirement;
- no Project facts/Canon in Framework;
- use `quillframe host-run begin` before consequential edits.

Consumer `AGENTS.md` gets equivalent Project-specific rules and exact-authority order. Claude can still import it from `CLAUDE.md`.

## Existing Project Repair

Add `quillframe host-install <project>`.

It writes missing `.claude/settings.json` / `.codex/hooks.json` and upgrades `CLAUDE.md` only when it matches a known generated scaffold. For `AGENTS.md`, update only when it matches a known generated scaffold; otherwise report `manual_merge_required` rather than overwrite user content. Lock, attestation, manifests, profiles, plans, manuscripts, and Canon are untouched.

## Affected Paths

- `harness/integrations/host_bootstrap.py` (new)
- `harness/integrations/claude_hook.py`
- `harness/integrations/codex_hook.py` (new, if wrapper retained)
- `quillframe/cli.py`
- `project_sdk.py`
- `AGENTS.md`
- `.codex/hooks.json` (Framework host config)
- consumer scaffold generators
- `tests/test_quillframe_unified_host_bootstrap.py` (new)
- bilingual Project SDK / integration docs

## Migration Strategy

No automatic Framework or Project schema migration. New scaffolds receive both hosts. Existing supported Projects use explicit `quillframe host-install`. Unknown custom host files are never silently replaced.

## Test Strategy

Deterministic unit/subprocess tests cover typed session persistence, host parity, Codex tool aliases, task-mode/run transitions, pre-mode write denial, strict bootstrap-command allowlist, stale authority denial, generated scaffolds, host-install idempotency, and static instruction fallback. Normal CI performs no model calls.

## Phases / Checkpoints

1. Freeze spec/plan/tasks and current host contracts.
2. Implement host-neutral typed session/bootstrap core.
3. Add task-mode/run CLI and write gate.
4. Add Codex adapter/scaffold and root static instructions.
5. Add existing-Project host-install repair path.
6. Add regression tests and bilingual docs.
7. Run CI, security/authority boundary review, and human-review readiness.

## Rollback

Revert spec 020 implementation. Existing `quillframe` CLI and Project lock/attestation remain intact; no Canon or Project authority migration is performed.
