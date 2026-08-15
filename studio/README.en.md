# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio is the product-experience layer around NovelForge Core. **Phase 1 now exists on `main` as a contract-first, read-only product probe; it is not a released write-capable Studio application.** Development remains contract-first: validate product semantics and host boundaries against live Core contracts before choosing web, desktop, cloud, or agent-framework-specific stacks.

> **Authority boundary ✦** Studio consumes NovelForge Core state. UI state is not Canon, Memory, semantic truth, write authority, or a second workflow engine.

[简体中文](README.zh-CN.md)

## Product architecture

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) — machine-readable Phase 2A delivery-surface contract.

The product architecture records both the Core interfaces Studio can consume and the unresolved Core consumer gaps Studio must not patch around locally.

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency Run / Context Inspector; loads `novelforge_run_receipt_v1` JSON locally and exposes no write operation.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — clearly synthetic demo receipt for visual and interaction QA.

The first interaction principle is intentionally visible in the prototype:

**support identified by a semantic selection result ≠ evidence that actually entered the model context.**

## Phase 2A · One product, many hosts

Phase 2A treats Studio as a polished SaaS-like experience without making SaaS business infrastructure part of the product model. The same NovelForge semantics should be available through four first-class delivery surfaces:

- **CLI** — scriptable native automation and inspection.
- **Local app / local Web UI** — a creator workstation using local host capabilities through typed adapters.
- **Cloud-hosted UI** — the same product model behind a remote query/command boundary.
- **Agent skill / package** — a thin, versioned adapter for other agent frameworks that does not expose private NovelForge persistence or implementation internals.

Different hosts may have different capabilities and transports. Those differences never change Canon, Settlement, Context, semantic-result, or receipt semantics. **Host capability does not imply NovelForge story authority.**

### Portable Project Hub / Scene vertical slice

- [`project_hub_projection.py`](project_hub_projection.py) — deterministic read-only projection from `novelforge_project_adapter_resolution_v1`; rejects the wrong source schema, strips host absolute paths, and binds exact source/projection fingerprints.
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) — Project Hub + Scene workspace shell with Creator/Inspector progressive disclosure and delivery-surface switching.
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) — synthetic Project Adapter resolution containing deliberately private absolute paths for redaction validation.
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) — synthetic read-only Scene/Reader/Context/Runtime fixture.

The projection explicitly carries `authority=false`, `canon_authority=false`, `framework_write_authority=false`, and `settlement_authority=false`. It never infers current chapter, manuscript lifecycle, publication status, or quality status merely because a logical path exists.

The agent-package direction is intentionally generic: future adapters should expose capability discovery, typed queries, typed commands, resume references, and typed receipts. Mutating operations remain deferred until Core provides the command, precondition, and authority semantics.
