# Implementation Plan · Zero-Setup Bootstrap and Claude Code Host Guard

## Chosen Architecture

Keep Quillframe runtime authority provider-neutral. Add a thin Claude Code host integration that consumes existing Project/Framework contracts instead of creating a second agent runtime.

1. `quillframe` console entry point delegates Project SDK and doctor operations and exposes Claude hook dispatch.
2. Project SDK explicit init/pin computes exact Framework identity from a clean source checkout: git commit + existing deterministic bundle fingerprint; writes lock + attestation together.
3. `CLAUDE.md` uses supported `@path` imports for concise static host instructions.
4. Claude lifecycle hook builds a compact bootstrap snapshot. Framework mode injects Framework-only boundaries. Project mode loads manifest, lock and attestation and verifies them against the materialized Framework during `SessionStart`.
5. The verified bootstrap snapshot is cached under `.quillframe/` for the session. `PreToolUse` reuses it and denies consequential tools when consumer authority is invalid instead of recomputing a bundle fingerprint for every tool call.
6. New Project scaffold writes `.claude/settings.json` invoking `quillframe claude-hook`; this remains a host adapter, not Project authority.

## Alternatives Considered

- Put all instructions into a huge `CLAUDE.md`: rejected because instruction context is guidance, not an authority guard, and large files reduce adherence.
- Make Claude Code the Quillframe Agent Runtime: rejected; violates provider-neutral architecture.
- Recompute full bundle fingerprint before every tool: rejected for unnecessary I/O.
- Automatically repin legacy Projects on validate: rejected because migration must be explicit.

## Affected Objects / Paths

- `pyproject.toml`
- `quillframe/cli.py` (new)
- `project_sdk.py`
- `harness/integrations/claude_hook.py`
- `.claude/settings.json`
- `CLAUDE.md`
- `tests/test_quillframe_bootstrap_host.py` (new)
- `README.en.md`, `README.zh-CN.md`, `docs/project-sdk.en.md`, `docs/project-sdk.zh-CN.md`

## Dependency Graph

`CLI → Project SDK / persistence doctor / Claude hook`

`Project SDK pin → git identity + release/build_framework_bundle.py → lock + attestation`

`Claude SessionStart → Project/Framework discovery → exact authority verification → cached bootstrap snapshot → additionalContext`

`Claude PreToolUse → cached authority snapshot → allow or deny consequential tool`

## Migration Strategy

No automatic migration. Existing Projects with incomplete locks remain readable and validate structurally, but expose `authority_ready=false`. `quillframe pin <project>` is the explicit upgrade operation.

## Test / Eval Strategy

Deterministic tests cover exact pin creation, dirty-checkout rejection helper behavior, attestation mismatch, hook JSON context, fail-closed consequential tools, root instruction imports, and console entry point metadata. Existing CI remains model-free.

## Phases / Checkpoints

1. Spec/plan/tasks freeze.
2. CLI + exact Project pin/attestation.
3. Claude static bootstrap + lifecycle guard.
4. Tests.
5. Docs synchronization.
6. CI and review readiness.

## Rollback

Revert spec 019 implementation commits. Legacy Python entry points remain available; no Project Canon or schema migration is performed.