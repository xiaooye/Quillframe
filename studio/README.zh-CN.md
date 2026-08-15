# NovelForge Studio

<p><kbd>PRODUCT EXPERIENCE</kbd>&nbsp;&nbsp;<kbd>CREATOR WORKBENCH</kbd>&nbsp;&nbsp;<kbd>INSPECTABLE RUNTIME</kbd></p>

NovelForge Studio 是 NovelForge fiction operating substrate 之上的产品体验层。开发继续采用 contract-first 路线：先验证产品语义和宿主边界，再决定正式应用、桌面、云端或 Agent Framework 专用技术栈。

> **权威边界 ✦** Studio 只消费 NovelForge Core state。UI state 不是 Canon、Memory、semantic truth，也不是第二套 workflow engine。

[English](README.en.md)

## 产品架构

- [Phase 1 产品架构 · English](PRODUCT_ARCHITECTURE.en.md)
- [Phase 1 产品架构 · 简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [Phase 2A 可移植产品契约 · English](PORTABLE_PRODUCT_CONTRACT.en.md)
- [Phase 2A 可移植产品契约 · 简体中文](PORTABLE_PRODUCT_CONTRACT.zh-CN.md)

Phase 2A 的方向是 **一个产品，多种宿主**：CLI、本地应用/本地 Web UI、云托管 UI、Agent Skill/Package Adapter 全部消费稳定 NovelForge contracts，不创建彼此独立的 truth model。

## Phase 1 · Run / Context Inspector

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— zero-dependency Run / Context Inspector；在本地加载 `novelforge_run_receipt_v1` JSON，不暴露 write operation。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 明确标记为 synthetic 的 demo receipt，用于 visual / interaction QA。

第一条交互原则会直接显示在 prototype 中：

**semantic selection 识别为 support 的 evidence ≠ 最终真正进入 model context 的 evidence。**

## Phase 2A · Portable Project Hub / Scene workspace

- [`project_hub_projection.py`](project_hub_projection.py) —— 从 `novelforge_project_adapter_resolution_v1` 生成 deterministic read-only projection；删除 host absolute paths，并绑定 exact source/projection fingerprints。
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) —— Project Hub + Scene workspace shell，包含 Creator/Inspector progressive disclosure 与 delivery-surface switching。
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) —— synthetic Project Adapter resolution；故意包含 host-private path，用于验证 redaction。
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) —— synthetic read-only Scene/Reader/Context/Runtime fixture。

可移植边界保持第二条交互原则：

**delivery surface 和 host capability 永远不能推导出 NovelForge story authority。**
