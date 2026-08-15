# NovelForge 8.0 Development Change Inventory

> Development status document. This is **not** a released migration guide and does not define a stable compatibility boundary. During active 8.0 development, the latest `main` branch is the working baseline. Formal release notes and upgrade instructions should be generated only after the release contract is frozen.

[简体中文](8-0-development-inventory.zh-CN.md)

## Purpose

This page keeps release communication aligned with what actually exists on `main` while NovelForge 8.0 is still under construction. It separates merged implementation from active dependencies and deferred product work so documentation does not promote plans into shipped features.

The inventory is intentionally narrower than a roadmap: it records externally relevant changes and compatibility implications, not every internal refactor.

## Merged on `main`

### NovelForge machine namespace migration

PR #11 migrated live machine-facing names away from the old Novel OS namespace without adding compatibility aliases:

- `NOVEL_OS_*` → `NOVELFORGE_*`;
- live `novel_os_*` schema IDs → `novelforge_*`;
- `.novel-os/runtime.db` → `.novelforge/runtime.db`;
- MCP tool/server names → `novelforge_*`;
- peer packet and Session / Control Plane machine schemas aligned to NovelForge naming.

The separate permission field `os_behavior_write` was deliberately not renamed in that PR.

### Task-aware, perspective-safe context grounding

PR #12 upgraded context selection so active grounding questions are explicit, visibility is enforced before semantic selection, perspective-incompatible evidence cannot enter the model packet, and selected support can be distinguished from support later dropped by the hard budget.

This preserves the architectural boundary: the model owns semantic relevance; deterministic code owns visibility, budgets, provenance, authority class, and packet construction.

### Metadata-only Run Receipts

PR #13 added `novelforge_run_receipt_v1` and a deterministic recording boundary for execution evidence. Receipts can record artifact/context identities, semantic jobs, guard outcomes, and selected-versus-loaded support without storing candidate prose or gaining Canon authority.

Run Receipts are observability evidence, not a second state database.

### Release-complete Framework bundle

PR #18 fixed a release-substrate defect where the deterministic bundle could be reproducible but omit the `quality/` runtime. Bundle CI now checks that the emitted package contains the quality runtime and can execute `novelforge.py doctor` plus the model-free self-test after extraction.

### Studio Phase 1 read-only product probe

PR #19 merged the first Studio product architecture and a zero-dependency Run / Context Inspector prototype driven by `novelforge_run_receipt_v1`.

Phase 1 is intentionally read-only. It validates information architecture and observability UX; it is not a released write-capable Studio application and does not own Canon, Memory, semantic truth, or workflow authority.

### Documentation release-truth cleanup

Current documentation now distinguishes development architecture from release metadata, tracks unreleased changes explicitly, registers Studio documentation in the repository documentation manifest, and checks `studio/` for unregistered bilingual human-facing documents.

## Active gaps and dependencies

These items are **not complete** and must not be described as shipped 8.0 capabilities.

### Framework-write permission rename

The intended rename of `os_behavior_write` remains unresolved. PRs #14 and #15 were closed without merge after the attempted migration was found invalid/stale. Until a valid Core-owned migration lands, documentation must preserve the current machine field exactly where a normative contract requires it.

### Run Receipt consumer contract gaps

Studio Phase 1 identified three Core-owned gaps:

1. Run Receipt schema/tool discoverability is not yet fully exposed through `HARNESS_MANIFEST.yaml`;
2. `run_receipt.py` emits `run.receipt_recorded`, while the current Control Plane event schema does not yet advertise that event type;
3. Studio needs a stable receipt/query projection instead of reading Control Plane persistence internals.

Documentation should describe these as dependencies, not invent UI-side substitute contracts.

### Version metadata drift

The repository still contains development-version drift between release metadata and implementation metadata. During active development, this page treats latest `main` as the working implementation baseline rather than using that drift as a compatibility gate. A formal release must still normalize release/version metadata before publication.

### Studio Phase 2A

Issue #20 defines the next read-only Studio slice: portable Project Hub + Scene workspace across CLI, local UI, hosted UI, and agent-skill/package adapters. It remains an active product target, not a shipped capability.

The core invariant remains one truth model behind multiple delivery surfaces; no delivery surface gains Canon or workflow authority.

### Publication / Typesetting Toolkit

Issue #16 defines the desired deterministic publication pipeline:

`Accepted manuscript → Publication IR → Typesetting Profile → Renderer → Validator → derived outputs`

No official `novelforge_publication_ir_v1` implementation is assumed complete by this document. Publication preview, EPUB/Web/print rendering, and publication validation remain future work until the owning Core implementation lands.

### MCP ecosystem and broader Studio work

Issue #8 remains the umbrella for MCP registry/management, richer runtime observability, and later Studio surfaces. Capability discovery must remain separate from authority; UI/MCP availability must never become a prerequisite for Core runtime correctness.

## Compatibility policy during active 8.0 development

Because 8.0 is still under active development:

- latest `main` is the development baseline;
- breaking machine-contract cleanup is allowed when justified by the architecture;
- compatibility aliases are not added automatically;
- historical changelog/spec records keep their original meaning;
- project/user data never becomes Generic Framework source;
- documentation must distinguish merged implementation, active dependency, and proposal;
- no issue, design document, prototype, or candidate schema becomes release truth merely by existing.

When 8.0 is frozen, this inventory should be converted into a real migration guide with exact old→new identifiers, compatibility notes, removed behavior, upgrade steps, and final release metadata.

## Release-readiness checklist

Before documentation can call 8.0 released, at minimum:

- Framework release/version metadata is internally consistent;
- machine schema/tool names in `HARNESS_MANIFEST.yaml` match live implementation;
- known Run Receipt event/discoverability gaps are resolved or explicitly excluded from the release contract;
- any intended permission rename is either completed or formally deferred;
- Framework bundle extraction/self-test is green;
- deterministic CI is green on the exact release commit;
- customer-facing English and Simplified Chinese docs are synchronized against that commit;
- release notes distinguish Core, Studio, Publication, and deferred work without promoting prototypes into released product capabilities.

Until then, refer to NovelForge 8.0 as **development work on `main`**, not as a released compatibility target.
