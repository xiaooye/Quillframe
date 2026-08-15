# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio is the product-experience layer around NovelForge Core. **Phase 1 now exists on `main` as a contract-first, read-only product probe; it is not a released write-capable Studio application.** Its purpose is to validate the product architecture and observability UX against live Core contracts before choosing a web or desktop stack.

> **Authority boundary ✦** Studio consumes NovelForge Core state. UI state is not Canon, Memory, semantic truth, write authority, or a second workflow engine.

[简体中文](README.zh-CN.md)

## Product architecture

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)

The product architecture records both the Core interfaces that Phase 1 can consume and the unresolved Core consumer gaps that Studio must not patch around locally.

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency Run / Context Inspector; loads `novelforge_run_receipt_v1` JSON locally and exposes no write operation.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — clearly synthetic demo receipt for visual and interaction QA.

The first interaction principle is intentionally visible in the prototype:

**support identified by a semantic selection result ≠ evidence that actually entered the model context.**
