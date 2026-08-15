# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio 是 NovelForge fiction operating substrate 之上的产品体验层。Phase 1 刻意采用 contract-first、read-only 路线：先验证产品架构与 observability UX，再决定正式 Web / Desktop 技术栈。

> **权威边界 ✦** Studio 只消费 NovelForge Core state。UI state 不是 Canon、Memory、semantic truth，也不是第二套 workflow engine。

[English](README.en.md)

## 产品架构

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)

## Phase 1 vertical slice

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— zero-dependency Run / Context Inspector；在本地加载 `novelforge_run_receipt_v1` JSON，不暴露任何 write operation。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 明确标记为 synthetic 的 demo receipt，只用于 visual / interaction QA。

第一版 prototype 会把下面这个区别直接做成 UI：

**semantic selection 识别为 support 的 evidence ≠ 最终真正进入 model context 的 evidence。**
