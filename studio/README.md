# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio is the product surface around the NovelForge fiction operating substrate. Phase 1 is deliberately contract-first and read-only: validate the product architecture and observability UX before choosing an application or desktop stack.

> **Authority boundary ✦** Studio consumes NovelForge Core state. UI state is not Canon, Memory, semantic truth, or a second workflow engine.

## Product architecture

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) — zero-dependency Run / Context Inspector; loads `novelforge_run_receipt_v1` JSON locally and exposes no write operation.
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) — clearly synthetic demo receipt for visual/interaction QA.

The first interaction principle is intentionally visible in the prototype:

**support identified by a semantic selection result ≠ evidence that actually entered the model context.**
