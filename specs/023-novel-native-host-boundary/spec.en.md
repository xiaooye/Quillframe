# Spec 023 · Quillframe Novel-Native Host Boundary

Status: proposed for the v0.9.1 release line

## Decision

Quillframe is a novel-contract kernel, not a general-purpose agent harness.
The product boundary is:

> The host runs the agent. Quillframe governs the novel.

Codex, Claude Code, Cursor, and other hosts own sessions, model/tool loops,
sandboxing, generic subagents, and host transport. Quillframe owns Project
resolution, story/character/relationship/Canon contracts, POV and knowledge
boundaries, planning horizons, bounded Context, candidate lifecycle, quality
gates, exact independent review, Review Draft visibility, and the separate
Acceptance/Settlement state transitions. A Project owns concrete story facts,
documents, research, plans, and Accepted Canon.

The embedded model/agent runtime remains available as a Studio implementation,
local adapter, deterministic test implementation, or fallback when a complete
host is unavailable. It is not Quillframe's product identity and does not gain
host-level authority.

## Surface partition

The default novelist-facing surface reuses existing typed operation names and
schemas and exposes only contract work:

- Project resolution and safe inspection;
- Canon/context query and bounded Context preview/freeze;
- `author.run` and planning/draft/revision lifecycle;
- candidate review, reject, revision, and `candidate.visible.get`;
- state-delta proposal and continuity/consistency inspection.

Internal/ops operations remain available behind an explicit internal namespace
or capability manifest: session/event/checkpoint/handoff, lease and
consume-once state, provider/runtime diagnostics, and transport receipts.
These operations are implementation plumbing and do not become novelist
authority.

`candidate.accept` and `settlement.apply` are privileged author-control
operations. They require an explicit human/authorized-human receipt, the exact
candidate fingerprint, exact before-state, and separate acceptance and
settlement transactions. A model result, reviewer result, host, MCP discovery,
or Studio view cannot self-grant either authority. Existing compatibility
operations may remain, but their privilege boundary must be machine-visible.

## Version and truthfulness

v0.9.1 has one release identity. `VERSION`, `pyproject.toml`,
`HARNESS_MANIFEST.yaml`, CLI/doctor output, Host Bridge metadata, MCP/skill
capability manifests, Studio packages, site/docs manifests, Tauri metadata,
and release artifacts must agree on `0.9.1`. Historical changelog entries are
preserved; current descriptions must not claim a future or deferred feature is
released.

Documentation must describe the dependency direction as Host → agent loop,
Quillframe → novel contract, Project → story authority. The phrase
“Quillframe runs the agent” is retired; embedded runtime documentation must
identify its optional/reference role instead.

## Compatibility and non-goals

Existing Host Bridge operation names and embedded runtime adapters remain
compatible where their authority and visibility contracts are unchanged.
This spec does not delete the embedded runtime, create a second API family, or
change candidate acceptance/settlement semantics.

The following are post-v0.9.1 backlog and must not block this release: full
Studio UI/UX redesign, hosted multi-user/cloud deployment, a complete
author-control profile product, full ConStory-Bench integration, every
discovery/arc/web-serial profile, a reference novel, book-scale empirical
benchmarks, a plugin ecosystem, a model-provider catalogue, collaboration and
billing, and a full typesetting suite.

## Acceptance invariants

- A host can run a generic agent without receiving Canon or Settlement authority.
- A novelist-facing discovery surface cannot enumerate raw pre-release text.
- Only `candidate.visible.get` returns released Review Draft content.
- Every independent review binds exact packet/candidate/result evidence.
- `accepted=false` and `settled=false` remain visible until two explicit human
  transitions occur.
- Version and capability manifests agree with the implementation and release
  artifact.
- Standard Projects and local adapters continue to work without a runtime
  manifest; mapped Projects fail closed on missing/stale projection inputs.
