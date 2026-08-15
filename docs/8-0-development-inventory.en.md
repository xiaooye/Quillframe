# NovelForge 0.8.0 / 8.0-line Development Change Inventory

> Development status document. `0.8.0` is the pre-1.0 SemVer identity for the architecture previously discussed as the “8.0” development line. It is **not** a frozen 1.0 compatibility promise or a final migration guide. During active development, latest `main` remains the working baseline.

[简体中文](8-0-development-inventory.zh-CN.md)

## Purpose

This page keeps release communication aligned with what actually exists on `main`. It separates merged implementation from active Core dependencies and deferred product work so issues, designs, and prototypes are never promoted into capabilities they do not yet provide.

The inventory is intentionally narrower than a roadmap: it records externally relevant changes, authority boundaries, and compatibility implications rather than every internal refactor.

## Version identity

NovelForge now uses **0.8.0** consistently across the current machine manifest, Skill metadata, CLI, Project SDK default, exposed MCP server metadata, and documentation governance metadata.

This is a pre-1.0 reset of development numbering. It replaces the previous fragmented 7.2 release-metadata / 7.3 implementation-metadata convention without rewriting historical 7.x records.

During active development:

- latest `main` is the implementation baseline;
- `0.8.0` identifies the current development line rather than promising API freeze;
- justified breaking machine-contract cleanup may still land before 1.0;
- existing projects that intentionally pin an older Framework revision remain on that revision until explicitly upgraded.

## Merged on `main`

### Machine namespace + final machine-contract cleanup

PR #11 migrated live machine-facing names away from the old Novel OS namespace without compatibility aliases: `NOVEL_OS_*` → `NOVELFORGE_*`, live `novel_os_*` schema IDs → `novelforge_*`, `.novel-os/runtime.db` → `.novelforge/runtime.db`, MCP tool/server names → `novelforge_*`, and related Session / Control Plane identifiers.

PR #24 completed the remaining machine-contract cleanup: `os_behavior_write` → `framework_behavior_write`, semantic job/result IDs moved from `novel-os-*` to `novelforge-*`, the live `.novel-os/` ignore surface was removed, and namespace hygiene prevents those old machine identifiers from returning. No compatibility aliases were added.

### Task-aware, perspective-safe, story-ordered context grounding

PR #12 upgraded context selection so active grounding questions are explicit, visibility is enforced before semantic selection, perspective-incompatible evidence cannot enter the model packet, and selected support can be distinguished from support later dropped by the hard budget.

PR #27 tightened that contract with deterministic temporal story-order eligibility and per-question evidence checks. Future/incompatible pinned context now fails closed, and the grounding result explicitly reports when hard budgets prevent required evidence from entering the packet.

The model owns semantic relevance; deterministic code owns visibility, story-order eligibility, budgets, provenance, authority class, and packet construction.

### Evidence-bound character and long-horizon reasoning

PR #28 separates a character's epistemic status from acquisition mode and binds proposed actions to story-ordered, character-visible evidence. Future, unknown, or otherwise invalid evidence cannot be cited as positive support for an action merely because it exists somewhere in Framework state.

PR #29 requires story-ordered evidence and complete requirement coverage for long-horizon continuity reconciliation, preserves uncertainty as a legitimate typed state, and separates shared relationship state from each character's individual perception of that relationship.

These changes strengthen evidence discipline inside the existing semantic-contract architecture; they do not add another agent or create a new authority layer.

### Metadata-only Run Receipts

PR #13 added `novelforge_run_receipt_v1` and a deterministic recording boundary for execution evidence. Receipts can record artifact/context identities, semantic jobs, guard outcomes, and selected-versus-loaded support without storing candidate prose or gaining Canon authority.

Run Receipts are observability evidence, not a second state database.

### Release-complete Framework bundle

PR #18 fixed a release-substrate defect where a reproducible bundle could omit the `quality/` runtime. Bundle CI now checks the emitted package and runs `novelforge.py doctor` plus the model-free self-test after extraction.

### Studio Phase 1 · read-only Run / Context Inspector

PR #19 merged the first Studio product architecture and a zero-dependency Run / Context Inspector prototype driven by `novelforge_run_receipt_v1`. It remains read-only and has no Canon, Memory, semantic, settlement, or workflow authority.

### Studio Phase 2A · portable Project Hub + Scene workspace

PR #21 merged the next read-only vertical slice: one portable product contract shared by CLI/local/hosted/agent-package surfaces, deterministic Project Hub projection, browser-safe path handling, source-fingerprint binding with `authority=false`, synthetic project/scene fixtures, and a read-only Project Hub + Scene workspace prototype.

### Studio Phase 2B · read-only Host Bridge + Agent Skill

PR #25 merged a versioned read-only host bridge and standards-compatible NovelForge Agent Skill package.

The bridge currently allowlists only:

- `bridge.describe`;
- `framework.doctor`;
- `project.inspect`;
- `capabilities.inspect`;
- `context.inspect`;
- `semantic.catalog`.

Unsupported operations fail closed. Browser/remote-safe projections do not expose host-private absolute paths by default. The external Agent Skill uses the bridge rather than importing private Core persistence or implementation internals. The entire surface remains `authority=false` and explicitly has no Canon/Framework-write/Settlement authority.

### 0.8.0 version normalization and documentation truth

The machine manifest, Skill metadata, CLI, Project SDK default, exposed MCP server version, and documentation governance metadata now share one `0.8.0` development identity. Documentation also registers the current Studio authority sources and keeps `studio/` inside bilingual manifest-coverage QA.

The Studio product documentation now records **Tauri + React + WeiUI** as the selected future installable-shell direction while keeping that decision separate from implementation status. `assets/brand/tokens.json` remains the current NovelForge token source; no generated WeiUI theme/converter artifact is claimed until one actually lands on `main`.

## Active gaps and dependencies

These items are **not complete** and must not be described as shipped stable capabilities.

### Run Receipt / Control Plane read-surface gaps

Studio still depends on Core-owned consumer/read-surface work:

1. stable Run Receipt schema/tool discoverability through the Framework manifest surface;
2. consistent event-schema support for `run.receipt_recorded`;
3. a stable receipt/query projection instead of direct persistence access;
4. safe Session/Event/Handoff/Run Receipt reads and resume semantics before they can be added to the portable host bridge.

PR #25 deliberately defers those unsafe queries rather than inventing UI-side contracts. Core issue #23 owns the stable query/command boundary work.

### Publication / Typesetting Toolkit

Issue #16 defines the desired deterministic publication pipeline: `Accepted manuscript → Publication IR → Typesetting Profile → Renderer → Validator → derived outputs`.

No official `novelforge_publication_ir_v1` implementation is assumed complete by this document. Publication preview, EPUB/Web/print rendering, and publication validation remain future work until the owning Core implementation lands.

### Installable Studio shell · selected, implementation pending

The product direction is Tauri + React 19 + WeiUI. The intended visual dependency is NovelForge Story Loom tokens → deterministic WeiUI-compatible W3C token representation → WeiUI token/CSS/React substrate → Tauri shell.

No Tauri application, app lockfile, NovelForge→WeiUI converter, or generated theme artifact is treated as merged merely because this direction is documented. When implementation lands, release truth must bind to the exact dependency pins, generated/source relationship, responsive/i18n/accessibility checks, tree-shaking evidence, and idle CPU/memory/process-lifecycle measurements.

Tauri, React, and WeiUI remain Product dependencies, not prerequisites for Generic Core correctness, CLI, the Framework bundle, or the Agent Skill.

### Write-capable / production-hosted Studio

The merged Studio slices remain read-only. Generic invoke/write, project mutation, settlement commands, production cloud hosting, authentication, collaboration, and vendor-specific write adapters are not part of the current product contract.

### Broader MCP ecosystem

Issue #8 remains the umbrella for MCP registry/management and later product surfaces. Capability discovery remains separate from authority, and UI/MCP availability must never become a prerequisite for Core runtime correctness.

## Compatibility policy during pre-1.0 development

- latest `main` is the Framework-development baseline;
- breaking machine-contract cleanup is allowed when justified by architecture and validated by deterministic CI;
- compatibility aliases are not added automatically;
- historical changelog/spec records preserve their original meaning;
- project/user data never becomes Generic Framework source;
- documentation must distinguish merged implementation, selected product direction, active dependency, and proposal;
- no issue, design document, prototype, or candidate schema becomes authority merely by existing;
- current machine version surfaces should stay aligned rather than accumulating parallel development version labels.

A future stable migration guide should be generated only after a release contract is intentionally frozen, with exact old→new identifiers, compatibility notes, removed behavior, upgrade steps, and final bundle evidence.

## Current readiness boundary

`0.8.0` means the active pre-1.0 development identity is normalized. It does **not** mean every 8.0-line product goal is finished or that APIs are frozen.

Before NovelForge makes a stronger stable-release claim, the relevant scope still needs explicit decisions and evidence around the Run Receipt/query surface, Publication inclusion/exclusion, Studio write boundaries, installable-shell implementation/performance evidence, exact bundle/CI evidence, and synchronized customer-facing English/Simplified Chinese review.

Until then: **0.8.0 = active pre-1.0 development on latest `main`.**
