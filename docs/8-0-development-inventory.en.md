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

### Same-fingerprint production-readiness gate

PR #31 added `novelforge_production_readiness_v1` and exposes it through `HARNESS_MANIFEST.yaml`.

The gate does not compute a composite literary score. It binds required gate evidence to **one exact candidate fingerprint** and applies a fail-closed conjunction policy:

- Surface and Reader Engagement are required;
- Continuity can be policy-required;
- independent semantic review can be policy-required;
- missing, `pending`, or `fail` required gates block `ready_for_user_visible_review`;
- `RG-15` SAFE-BUT-FLAT cannot simultaneously be a passing Reader Engagement gate;
- the readiness record has `authority=false` and grants no Canon / Framework-write / durable-user-taste permissions.

This makes the user-visible readiness boundary executable without pretending deterministic code can judge literary quality itself.

### Deterministic Publication core

PR #31 also added the first manifest-authoritative Publication implementation:

- `publication/publication_ir.schema.json` with schema `novelforge_publication_ir_v1`;
- `publication/compiler.py`;
- exact Accepted-text fingerprint checking and `text_preservation = exact-unicode-text`;
- derived output authority fixed to `false`;
- deterministic profiles: `clean_text`, `web_reflow`, `print_book`, `epub3`;
- deterministic EPUB generation and internal structural/text-roundtrip validation;
- W3C EPUB 3.3 as the target, with an explicitly supplied external EPUBCheck command required for release conformance.

`print_book` currently emits print-oriented HTML/CSS. It is **not** a finished paged-media → PDF engine. The current IR is intentionally minimal: book metadata plus chapter title/text/fingerprint. It does not yet implement all of the richer semantic structures and profile controls described by Issue #16.

### Release-complete Framework bundle

PR #18 fixed a release-substrate defect where a reproducible bundle could omit the `quality/` runtime. Bundle CI now checks the emitted package and runs `novelforge.py doctor` plus the model-free self-test after extraction.

PR #31 extends the bundle surface to include the new production-readiness and Publication runtime contracts and tests them in normal deterministic CI without fabricating semantic verdicts.

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

### Story Loom v2 + exact-pinned WeiUI zero-JS foundation

PR #32 upgraded `assets/brand/tokens.json` to `novelforge_brand_tokens_v2` and made the application design foundation executable.

`assets/brand/weiui.integration.json` now records the exact generic UI dependency contract:

- source repo: `xiaooye/weiui`;
- exact commit: `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`;
- license: MIT;
- allowed WeiUI packages: `@weiui/tokens`, `@weiui/css`;
- forbidden runtime packages: `@weiui/headless`, `@weiui/react`;
- WeiUI runtime JavaScript required: `false`;
- theme layer: `wui-theme`;
- import order: WeiUI tokens → WeiUI CSS → `assets/brand/story-loom.weiui.css`.

`story-loom.weiui.css` provides the actual light/dark `--wui-*` aliases plus NovelForge `--nf-*` product-semantic variables without forking WeiUI component selectors.

The machine token contract now includes application rules for mobile-first responsive behavior, 44px minimum touch targets, focus-ring geometry, `en-US` + `zh-CN`, logical properties, no fixed-width locale assumptions, reduced motion, no idle animation, no default polling, and no heavy default component import. `scripts/design_system_quality.py` deterministically checks those invariants, exact WeiUI pin/provenance, required variables, CSS layering, and light/dark contrast in CI.

### Phase 2C application stack decision

The product/runtime-overhead decision selects **SolidJS + TypeScript + Vite + `@solidjs/router`** for Phase 2C application code.

WeiUI is intentionally consumed as a **zero-JavaScript CSS/tokens foundation**, not through React or WeiUI runtime/headless packages. Local Web remains first-class and preferred where minimum incremental CPU/RAM matters. Tauri remains an optional/installable desktop host rather than the center of product architecture.

This stack decision preserves the one-product/many-host invariant: transport/host choice does not alter Canon, Settlement, Context, semantic-result, production-readiness, or receipt semantics.

### 0.8.0 version normalization and documentation truth

The machine manifest, Skill metadata, CLI, Project SDK default, exposed MCP server version, and documentation governance metadata now share one `0.8.0` development identity. Documentation also registers the current Studio authority sources and keeps `studio/` inside bilingual manifest-coverage QA.

## Active gaps and dependencies

These items are **not complete** and must not be described as shipped stable capabilities.

### Run Receipt / Control Plane read-surface gaps

Studio still depends on Core-owned consumer/read-surface work:

1. stable Run Receipt schema/tool discoverability through the Framework manifest surface;
2. consistent event-schema support for `run.receipt_recorded`;
3. a stable receipt/query projection instead of direct persistence access;
4. safe Session/Event/Handoff/Run Receipt reads and resume semantics before they can be added to the portable host bridge.

PR #25 deliberately defers those unsafe queries rather than inventing UI-side contracts. Core issue #23 owns the stable query/command boundary work.

### Publication / Typesetting Toolkit · minimum core merged, broader scope open

Publication is no longer merely an issue-level proposal: `novelforge_publication_ir_v1` and the deterministic compiler are real on `main`.

Issue #16 remains open because its larger target is broader than the current compiler. Still outstanding or not yet represented by the minimum implementation are, among other things:

- richer semantic IR structures such as parts, sections, scene breaks, epigraphs, notes, figures, front/back matter and in-world documents;
- a fuller versioned Typesetting Profile contract rather than only the current named compiler profiles;
- richer CJK/Latin typography, font-embedding and publication-style controls;
- print PDF through a paged-media engine such as a Vivliostyle-compatible backend;
- broader accessibility / visual-regression / asset-validation hooks;
- Studio publication preview and authoring UX.

Documentation must therefore describe the current compiler precisely: useful deterministic core, **not the completion of the whole Typesetting Toolkit**.

### Phase 2C application implementation

The Story Loom/WeiUI foundation and SolidJS stack decision are now concrete, but the Phase 2C product application is not implied to be complete.

Still requiring implementation evidence are the actual SolidJS route/workspace shell, host lifecycle, typed bridge consumption, optional Tauri packaging, and measured runtime behavior. Product acceptance should include actual idle CPU/RAM and first-interaction measurements rather than assuming that a lightweight stack is automatically lightweight in practice.

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

The Core now has an executable production-readiness conjunction gate and a minimum deterministic Publication compiler. The Product foundation now has an exact-pinned, zero-JS WeiUI token/CSS layer plus a SolidJS Phase 2C stack decision. Stronger stable-release claims still need explicit scope decisions and evidence around the Run Receipt/query surface, the remaining Issue #16 Publication scope, Studio write boundaries, actual Phase 2C application/runtime measurements, exact bundle/CI evidence, and synchronized customer-facing English/Simplified Chinese review.

Until then: **0.8.0 = active pre-1.0 development on latest `main`.**
