# Quillframe · Coding Agent Bootstrap

This repository is the **Generic Quillframe Framework**, not a fiction Project. Do not write concrete novel characters, plot, manuscripts, Canon, or private user taste into this repository.

Before consequential work:

1. Read `HARNESS_MANIFEST.yaml`, `SKILL.md` (plus the applicable language edition), and `harness/HARNESS_AGENT.md`.
2. Require Quillframe host bootstrap context containing `QF_SESSION_ID`. If it is absent, do not edit yet. In Codex, review/trust the repository hooks with `/hooks` and restart. In Claude Code, confirm the repository `.claude/settings.json` hooks loaded.
3. If the user intent is **fiction creation**, do not select a fiction task mode inside this Generic Framework. Create a separate consumer Project outside this checkout with the strict command shape `python -m quillframe.cli init <OUTSIDE_PATH> --id <PROJECT_ID> --title <TITLE> [--language zh-CN]`, then tell the user to restart Claude Code/Codex from that Project. The pre-mode host guard permits only this narrow Project-creation escape; it does not permit `--force`, shell chaining, or a target inside the Framework checkout.
4. If the work genuinely belongs to the Framework, determine exactly one primary Quillframe `task_mode`. Framework engineering normally uses `SYSTEM-IMPROVE`; do not silently combine modes.
5. After semantically choosing one Framework mode, execute the exact `host-run begin` command injected by Quillframe. In this source checkout the command form is `python -m quillframe.cli host-run begin --session-id <QF_SESSION_ID> --mode <ONE_TASK_MODE>`.
6. Confirm bootstrap state is `running` with one active manager run before Write/Edit/Bash/apply_patch operations.
7. Re-read current branch/HEAD and exact before-state before consequential writes. Use `spec → plan → tasks → implementation → verification → acceptance` for material Framework changes.

Authority boundaries remain mandatory: model judgment does not grant write authority; runtime/session/telemetry are not Canon; Project facts belong only to consuming Projects; normal CI must remain deterministic and model-free.

Authoritative bilingual repository guidance remains in `AGENTS.en.md` and `AGENTS.zh-CN.md`. Machine release authority is `HARNESS_MANIFEST.yaml`.
