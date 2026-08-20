# Superseded pre-1.0 endurance plan

> Review record only. This document is not an execution plan, release authority,
> or current implementation checklist. The native 1.0 contract and current
> tests outrank this historical record.

## Scope retained for review

The record concerned the host boundary: the host runs the agent, while
Quillframe governs novel authority. The current native owners are
`project_resolution.py`, `core_operations.py`, `studio/project_hub_projection.py`,
`studio/host_bridge.py`, and their contract tests.

The current Project contract is exact: `quillframe.toml` has five root keys
(`schema`, `id`, `title`, `language`, `chapter_scope`), the schema is
`quillframe_project_v1_0`, the run boundary is CH001, the manifest fingerprint
is deterministic `sha256:` evidence, durable data is `.quillframe/data`, and
UI/projection authority is `false`.

## Historical review outcome

The earlier endurance work was superseded by the native 1.0 hard cut. Any
remaining release, external-host, or human-review work was not executed in
this record and must not be inferred from the old checklist. Deterministic
verification consists of native resolver/bridge tests, exact fingerprint
checks, CH001 rejection tests, bundle byte/fingerprint checks, and explicit
authority-boundary checks.

This record intentionally does not prescribe any superseded alternate identity,
layout, or execution behavior. Historical specifications and changelogs retain
their original wording in their separate historical roots.

## Status

Superseded; no pending checklist is authoritative. Consult the current native
contract, implementation, tests, and release evidence for any future work.
