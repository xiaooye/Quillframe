# Specification · Unified Claude Code and Codex Project Bootstrap

Status: Draft

Primary task mode: `SYSTEM-IMPROVE`

## Problem / Context

The first zero-setup host change made Claude Code aware of Quillframe authority, but it did not complete the Quillframe bootstrap lifecycle and it did not add an equivalent Codex host path.

Current failures are structural rather than prompt-quality issues:

- root `AGENTS.md` is still a router, while Codex reads `AGENTS.md` directly and does not interpret Claude-style `@path` imports;
- consumer Projects scaffold Claude configuration but no Codex lifecycle hooks;
- the Claude hook persists an ad-hoc Control Plane session rather than `quillframe_agent_session_v1`;
- no manager run is created/resumed;
- `primary_task_mode` remains `UNRESOLVED` forever;
- consequential writes can currently occur after authority verification even while no Quillframe task mode/run is active;
- host-specific bootstrap code risks drifting into parallel Claude/Codex implementations;
- a Generic Framework host must also have a safe way to create a separate consumer Project for fiction intent without first pretending that fiction work belongs to a Framework task mode.

## User / Editorial Value

A user should be able to open the same initialized Project in Claude Code or Codex and receive the same Quillframe execution boundary before fiction work begins:

`Project discovery → exact authority verification → manager session → exactly one task_mode → manager run → sparse-context execution`

If the user starts in the Generic Framework checkout and asks to create fiction, the host should create a separate consumer Project through a narrow deterministic escape and then require restart from that Project; it must not store story data in the Framework or force a fake Framework task mode.

Host differences should be adapters, not workflow semantics.

## Current Research

Current official Codex behavior provides Project `AGENTS.md` discovery plus project-local lifecycle hooks (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `SessionEnd`). Project `.codex/` configuration/hooks require project trust, and non-managed command hooks require explicit hook trust. `PreToolUse` can observe/block Bash and `apply_patch` edits. Therefore static `AGENTS.md` must remain a correct fallback even before Codex hooks are trusted.

Claude Code loads `CLAUDE.md`, supports `@path` imports, and supports the same relevant lifecycle hook stages through project settings. The existing Quillframe Claude adapter should become a compatibility wrapper around one host-neutral bootstrap core.

## Requirements

1. Add one host-neutral bootstrap runtime used by both Claude Code and Codex.
2. Consumer Project bootstrap must verify `quillframe.toml`, exact lock, attestation, and materialized Framework identity before granting consequential host execution.
3. Host sessions must use the existing `quillframe_agent_session_v1` contract and be persisted through the Control Plane.
4. Session bootstrap must not invent a literary task mode. A model/user must explicitly resolve exactly one allowed Quillframe `task_mode` through a deterministic command.
5. Starting a task mode must create exactly one active manager run bound to the verified Project/session/authority snapshot.
6. Consequential writes must fail closed while authority is invalid, task mode is unresolved, or no matching active run exists.
7. The bootstrap command used to resolve mode/start a run must remain callable without creating a deadlock; deterministic validation may allow only the narrow Quillframe bootstrap command while the write gate is closed.
8. Root and consumer `AGENTS.md` must contain compact direct Quillframe bootstrap rules sufficient for Codex even if project hooks are not trusted.
9. New Projects must scaffold `.codex/hooks.json` as well as Claude host configuration.
10. Codex `apply_patch` must be treated as a consequential edit.
11. Add an explicit, idempotent host-install/repair command for existing supported Projects; it must not repin Framework identity, mutate Canon, or overwrite unknown user-authored host instructions without a safe precondition.
12. Host adapters must expose truthful states such as `blocked`, `awaiting_task_mode`, and `running`; vocabulary injection alone is not bootstrap completion.
13. Normal CI stays deterministic and model-free.
14. In Generic Framework scope, fiction intent must not select a fiction task mode. Before mode resolution the guard may permit only a strictly parsed `quillframe init` / `python -m quillframe.cli init` command that provides one outside-Framework target plus required project id/title, excludes `--force` and shell chaining, and leaves normal host permission/approval behavior intact. After creation, fiction work must restart from the consumer Project.

## Non-goals

- Making Claude Code or Codex the Quillframe Agent Runtime authority.
- Heuristic/regex inference of literary task mode.
- Canon settlement or acceptance from a host hook.
- Silent Framework repin or consumer schema migration.
- Studio UI/UX work.
- Materializing old pinned Framework bundles into `.quillframe/framework` in this workstream; exact bundle recovery/materialization remains a separate dependency-delivery problem if needed after host lifecycle correctness is fixed.

## Authority / Canon Impact

No story authority changes. The work only strengthens host entry, execution identity, and deterministic preconditions. Model output, host session state, and a successful hook never grant Canon or Framework promotion authority.

## Compatibility / Overreach Audit

- Claude project files remain supported; `claude_hook.py` becomes a thin compatibility entry.
- Codex hooks are additive and project-local; untrusted projects still rely on `AGENTS.md` and must explicitly trust hooks before lifecycle enforcement can run.
- Existing Projects are not automatically repinned.
- Existing custom `AGENTS.md`/host configuration must be preserved unless it is a known generated Quillframe scaffold or the user invokes a force/explicit replacement path.
- No provider/model assumptions enter generic Framework contracts.
- The Framework-to-consumer init escape is not a general pre-mode shell allowlist. It only lets the host's normal permission layer consider one deterministic Project creation command whose implementation already rejects targets inside the Framework and dirty exact-pinning state.

## Acceptance Scenarios

1. Fresh Framework repo opened in Codex sees direct Generic Framework boundaries from root `AGENTS.md` before any hook trust.
2. A newly initialized consumer Project contains working Claude and Codex host configuration.
3. Claude and Codex `SessionStart` produce equivalent verified Project bootstrap snapshots.
4. The persisted manager session validates as `quillframe_agent_session_v1`.
5. Before task-mode resolution, Write/Edit/Bash/apply_patch are denied but the narrow mode-start command is permitted through normal host permissions.
6. `quillframe host-run begin --mode DESIGN-BOOK` validates the mode, starts one run, persists it, and subsequent authorized Project writes can proceed.
7. Invalid/second conflicting mode starts fail closed rather than silently switching mode.
8. Tampered lock/attestation or changed Framework identity blocks both hosts.
9. `quillframe host-install` upgrades known generated host scaffolding idempotently without changing lock/attestation/Canon.
10. Existing deterministic tests, docs quality, Studio build, and normal no-live-model CI remain green.
11. From Generic Framework scope, a strict outside-target Project init command can proceed through normal host approval, while an inside-Framework target, `--force`, or shell-chained lookalike is denied before execution.

## Risks

- Hook schemas differ subtly by host; wrappers must normalize input/tool aliases without leaking host-specific semantics into the core.
- Overly broad Bash denial can deadlock bootstrap; the pre-mode allowlist must remain structurally parsed and limited to Quillframe's own run bootstrap plus the exact Framework-to-consumer Project-creation escape.
- Codex hook trust is a user security boundary and cannot be bypassed by Quillframe; static instructions and clear diagnostics must make that state explicit.
