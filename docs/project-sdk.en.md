# Project SDK

A Quillframe Project is an independently versioned fiction project. The Framework supplies generic production mechanisms; the Project supplies concrete story authority.

<img src="assets/architecture/framework-vs-project.en.svg" alt="Project points to a pinned framework while concrete characters, Canon, plans, state, research, and manuscripts remain Project-owned" width="100%" />

## Project identity

A supported Project declares schema/version and logical paths in `quillframe.toml`. `quillframe.lock.json` stores the exact Framework identity, while `framework.attestation.json` records evidence for the same materialized Framework bundle identity.

Ordinary production must not silently replace the Project lock with current `main`, host session memory, or another local checkout. An explicit `quillframe pin` is a dependency/authority change, not a normal authoring side effect.

## Create a Project

From a clean Quillframe source checkout, install the local command surface:

```bash
python -m pip install -e .
quillframe doctor
```

Create the fiction Project outside the Framework repository:

```bash
quillframe init ../my-novel \
  --id MY-NOVEL \
  --title "My Novel" \
  --language en
```

`quillframe init` freezes the current clean checkout's exact git commit, computes a deterministic Framework bundle fingerprint, writes the matching attestation, then installs the generated Claude Code and Codex host scaffolds. A dirty Framework checkout is rejected: a commit identifier paired with uncommitted runtime bytes is not a reproducible authority identity.

## Claude Code and Codex bootstrap

Claude Code and Codex are optional hosts, not Quillframe workflow authority. Both adapters enter the same deterministic lifecycle:

`Project discovery → exact authority verification → typed manager session → exactly one task_mode → manager run → sparse Context execution`

At `SessionStart`, the host adapter creates or resumes a real `quillframe_agent_session_v1` and injects compact context containing `QF_SESSION_ID`. Exact Project authority may be verified at that point, but consequential work is still blocked until the model/user semantically chooses exactly one Quillframe task mode and starts the manager run with the exact command injected by the host, for example:

```bash
quillframe host-run begin \
  --session-id SES-CODEX-... \
  --mode DESIGN-BOOK \
  --project .
```

`quillframe host-run status --session-id ... --project .` reports the current deterministic state. Host bootstrap states are explicit: `blocked`, `awaiting_task_mode`, or `running`. Vocabulary injection alone is not considered a completed bootstrap.

Before `running`, consequential `Write` / `Edit` / `Bash` operations fail closed; Codex `apply_patch` is treated as an edit. The only pre-mode Bash exception is the strict Quillframe `host-run` bootstrap command bound to the exact injected session ID. A lookalike command with shell chaining is not allowed.

### Codex trust boundary

Codex reads Project `AGENTS.md` before work, so the generated file contains direct Quillframe bootstrap rules rather than merely linking to another document. Project-local `.codex/hooks.json` is also generated, but Codex intentionally requires project trust and review/trust of non-managed command hooks. If `QF_SESSION_ID` was not injected, open `/hooks`, review/trust the Quillframe hooks, then restart the Codex session before consequential Project work.

### Repair an existing Project

Older supported Projects can install or repair current host scaffolding explicitly:

```bash
quillframe host-install .
```

This operation is intentionally separate from `quillframe pin`. It does not change the Framework lock/attestation or any Project Canon, plans, profiles, manuscripts, or story state. Known generated files are upgraded idempotently; unknown user-authored `AGENTS.md` or host configuration is reported as `manual_merge_required` instead of being silently overwritten. Use `--force` only as an explicit replacement decision.

## Validate and explicitly repin

```bash
quillframe validate .
quillframe build .
```

`validate` reports both structural validity and `authority_ready`. For compatibility with older Projects, a missing exact commit/fingerprint/attestation is reported as an authority warning rather than silently repinning during validation.

Only when intentionally changing the Project's Framework dependency should you run:

```bash
quillframe pin .
```

The pin operation recomputes the current clean checkout's exact commit and bundle fingerprint, writes the attestation first, then writes the authority lock. A partial failure therefore becomes an observable mismatch/not-ready state instead of an assumed success.

## Ownership

Project-owned data includes concrete BOOK/VOL/ARC/UNIT/CH/SCN instances, characters and relationships, current state, claims, dependencies, active plans, profiles, research, regressions, manuscripts, and Accepted Canon.

Generic Framework source must never import those private story facts as built-in behavior. Claude Code, Codex, hooks, the CLI, SQLite, model results, and host capabilities also do not gain story authority merely because they can execute an operation.

## Standard and mapped layouts

The Project SDK supports a standard layout; Project Adapters can map mature/legacy repositories into the same logical contract. Mapping changes storage paths, not authority semantics.

Legacy lock migration remains an explicit engineering task. Ordinary fiction production does not rewrite an older lock to the currently checked-out Framework.

## Reproducibility

A Project should validate and build without chat memory. Exact commit identity, deterministic Framework bundle fingerprint, and attestation make materialized runtime bytes inspectable and repeatable. Framework current `main` is development authority for Framework maintenance; it is not silently substituted for a consumer's pin during ordinary production.

The Framework bundle includes the public `quillframe` Python package, `pyproject.toml`, and `VERSION`, so CLI/façade runtime bytes are covered by the consumer fingerprint. Engineering-process `specs/`, Git history, and local runtime state remain outside bundle authority.

## Change discipline

Structural changes may use spec → plan → tasks → implementation → verification → acceptance. Ordinary prose micro-edits do not need software-engineering ceremony. Canon mutation still requires explicit acceptance plus settlement regardless of repository layout.
