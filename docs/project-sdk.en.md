# Project SDK

A Quillframe Project is an independently versioned fiction project. The Framework supplies generic production mechanisms; the Project supplies concrete story authority.

<img src="assets/architecture/framework-vs-project.en.svg" alt="Project points to a pinned framework while concrete characters, Canon, plans, state, research, and manuscripts remain Project-owned" width="100%" />

## Project identity

A supported Project declares schema/version and logical paths in `quillframe.toml`. `quillframe.lock.json` stores the exact Framework identity, while `framework.attestation.json` records evidence for the same materialized Framework bundle identity.

Ordinary production must not silently replace the Project lock with current `main`, Claude session memory, or another local checkout. An explicit `quillframe pin` is a dependency/authority change, not a normal authoring side effect.

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

`init` freezes the current clean checkout's exact git commit and computes a `sha256:` fingerprint with the deterministic Framework bundle contract. A dirty checkout is rejected: a commit identifier paired with uncommitted runtime bytes is not a reproducible authority identity.

The scaffold also includes a project-local `CLAUDE.md` and `.claude/settings.json`. Claude Code remains an optional host. On SessionStart the host adapter verifies the Project lock/attestation against the materialized Framework and injects compact bootstrap state. If consumer authority is invalid, consequential host tools such as `Write`, `Edit`, and `Bash` fail closed. The hook does not gain Canon, Framework-promotion, or settlement authority.

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

Generic Framework source must never import those private story facts as built-in behavior. Claude Code, hooks, the CLI, SQLite, model results, and host capabilities also do not gain story authority merely because they can execute an operation.

## Standard and mapped layouts

The Project SDK supports a standard layout; Project Adapters can map mature/legacy repositories into the same logical contract. Mapping changes storage paths, not authority semantics.

Legacy lock migration remains an explicit engineering task. Ordinary fiction production does not rewrite an older lock to the currently checked-out Framework.

## Reproducibility

A Project should validate and build without chat memory. Exact commit identity, deterministic Framework bundle fingerprint, and attestation make materialized runtime bytes inspectable and repeatable. Framework current `main` is development authority for Framework maintenance; it is not silently substituted for a consumer's pin during ordinary production.

The Framework bundle includes the public `quillframe` Python package, `pyproject.toml`, and `VERSION`, so CLI/façade runtime bytes are covered by the consumer fingerprint. Engineering-process `specs/`, Git history, and local runtime state remain outside bundle authority.

## Change discipline

Structural changes may use spec → plan → tasks → implementation → verification → acceptance. Ordinary prose micro-edits do not need software-engineering ceremony. Canon mutation still requires explicit acceptance plus settlement regardless of repository layout.
