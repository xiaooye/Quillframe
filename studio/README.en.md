# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio is the product-experience layer around NovelForge Core. **Phase 1 now exists on `main` as a contract-first, read-only product probe; it is not a released write-capable Studio application.** Development remains contract-first: validate product semantics and host boundaries against live Core contracts before choosing web, desktop, cloud, or agent-framework-specific stacks.

> **Authority boundary ✦** Studio consumes NovelForge Core state. UI state is not Canon, Memory, semantic truth, write authority, or a second workflow engine.

[简体中文](README.zh-CN.md)

## Product architecture

- [Phase 1 product architecture · English](PRODUCT_ARCHITECTURE.en.md)
- [Phase 1 product architecture · 简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [Phase 2A portable product contract · English](PORTABLE_PRODUCT_CONTRACT.en.md)
- [Phase 2A portable product contract · 简体中文](PORTABLE_PRODUCT_CONTRACT.zh-CN.md)

The product architecture records both the Core interfaces Studio can consume and the unresolved Core consumer gaps Studio must not patch around locally. Phase 2A extends that principle into **one product, many hosts**: CLI, local app/local Web UI, cloud-hosted UI, and agent-skill/package adapters all consume stable NovelForge contracts rather than creating separate truth models.

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency Run / Context Inspector; loads `novelforge_run_receipt_v1` JSON locally and exposes no write operation.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — clearly synthetic demo receipt for visual and interaction QA.

The first interaction principle is intentionally visible in the prototype:

**support identified by a semantic selection result ≠ evidence that actually entered the model context.**

## Phase 2A portable vertical slice

- [`project_hub_projection.py`](project_hub_projection.py) — deterministic read-only projection from `novelforge_project_adapter_resolution_v1`; strips host absolute paths and binds exact source/projection fingerprints.
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) — Project Hub + Scene workspace shell with Creator/Inspector progressive disclosure and delivery-surface switching.
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) — synthetic Project Adapter resolution including host-private paths used to verify redaction.
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) — synthetic read-only Scene/Reader/Context/Runtime fixture.

The portable boundary adds a second interaction principle:

**delivery surface and host capability never imply NovelForge story authority.**
