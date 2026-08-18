# Specification · Zero-Setup Bootstrap and Claude Code Host Guard

Status: Draft

## Problem / Context

A fresh source checkout can be opened directly in Claude Code before the Quillframe Python package is installed or before a consuming fiction Project exists. Today the root `CLAUDE.md` is only a router, the Claude lifecycle hook records telemetry but does not inject verified Quillframe state, and `project_sdk.py init` writes a lock with null commit/fingerprint fields. As a result a third-party coding agent can fall back to its generic brainstorming workflow while merely knowing Quillframe vocabulary.

## Current-state Audit

- Quillframe Agent Runtime owns agent semantics; Claude Code is only an optional host/integration.
- `CLAUDE.md` does not import the detailed bootstrap contract with Claude Code's supported `@path` mechanism.
- `.claude/settings.json` invokes a telemetry-only lifecycle hook.
- New consumer Projects do not receive Claude Code hook configuration.
- New consumer locks are not exact pins.
- The installed package has no `quillframe` console entry point.

## User / Editorial Value

A normal local path should be predictable:

`clone → pip install -e . → quillframe doctor → quillframe init <project> → cd <project> → claude`

When Claude Code starts, it should immediately know whether it is inside the generic Framework or a verified consumer Project, which exact Framework bytes are authoritative, and that exactly one Quillframe task mode must govern fiction work.

## Requirements

1. Add a real `quillframe` CLI entry point for doctor/init/pin/validate/build and Claude host integration.
2. New Project initialization must pin a clean Framework checkout to an exact git commit and deterministic Framework bundle fingerprint.
3. New Project initialization must emit `framework.attestation.json` bound to the same exact identity.
4. Project validation must expose whether exact Framework authority is ready without silently migrating old Projects.
5. Root Claude Code instructions must load the actual Quillframe bootstrap rules using supported imports.
6. Claude `SessionStart` must inject compact, typed bootstrap state instead of telemetry only.
7. Consumer Projects must install project-local Claude hook settings that call the installed Quillframe host bridge.
8. If a consumer lock/attestation cannot be verified, consequential Claude tools must fail closed while read-only diagnosis remains possible.
9. Generic Framework work must remain possible; host guards must not convert Claude Code into Framework authority or hard-code Project facts.
10. Normal CI must remain model-free and deterministic.

## Non-goals

- Replacing the Quillframe-owned Agent Runtime with Claude Code.
- Inferring literary task mode with regex/heuristics.
- Automatically settling Canon or granting write authority from a hook.
- Migrating every existing consumer Project in this change.
- Studio UI/UX work.

## Authority / Canon Impact

No story Canon authority changes. The change hardens Framework/Project identity and host-side execution boundaries only.

## Reader / Prose Impact

Indirect: fiction tasks reach the intended Quillframe production workflow instead of an ungoverned generic coding-agent workflow.

## Compatibility Constraints

- Existing Projects with incomplete legacy locks remain inspectable and explicitly report `authority_ready=false`; they are not silently repinned.
- Source checkout / editable-install remains the primary local development path for exact pinning.
- The Framework bundle algorithm remains the existing deterministic bundle contract.

## Acceptance Scenarios

1. Fresh Framework checkout + editable install exposes `quillframe --help` and `quillframe doctor`.
2. `quillframe init` from a clean checkout writes non-null exact commit/fingerprint plus matching attestation.
3. Starting Claude in the Framework repo receives context that it is the generic Framework and must not store a fiction Project there.
4. Starting Claude in a newly initialized consumer Project receives verified Project/Framework authority context before the first user prompt.
5. Tampered/mismatched consumer lock or attestation causes Write/Edit/Bash tool calls to be denied by the host guard.
6. Existing deterministic unit tests and documentation quality gates stay green.

## Risks

- Computing a deterministic bundle fingerprint during init/pin costs local I/O; this is acceptable for explicit pin operations but must not run on every tool call.
- Claude hook output formats can evolve; tests must lock the supported JSON contract and fail safely.
- A globally installed non-editable package may not contain a source checkout; host discovery must report blocked state rather than inventing authority.