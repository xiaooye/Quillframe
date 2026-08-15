# NovelForge Studio

<p><kbd>产品体验</kbd>&nbsp;&nbsp;<kbd>创作工作台</kbd>&nbsp;&nbsp;<kbd>可检查运行</kbd></p>

NovelForge Studio 是 NovelForge Core 之上的产品体验层。**第一阶段（Phase 1）已经合并到 `main`，目前是一套契约优先、只读的产品验证原型；它不是已经发布、可以写入项目状态的完整 Studio 应用。** 开发继续采用 contract-first 路线：先基于 live Core contracts 验证产品语义和宿主边界，再决定正式 Web、Desktop、Cloud 或 Agent Framework 专用技术栈。

> **权威边界 ✦** Studio 只消费 NovelForge Core 状态。UI 状态不是正典（Canon）、记忆（Memory）、语义真相、写入权威，也不是第二套工作流引擎。

[English](README.en.md)

## 产品架构

- [Phase 1 产品架构 · English](PRODUCT_ARCHITECTURE.en.md)
- [Phase 1 产品架构 · 简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [Phase 2A 可移植产品契约 · English](PORTABLE_PRODUCT_CONTRACT.en.md)
- [Phase 2A 可移植产品契约 · 简体中文](PORTABLE_PRODUCT_CONTRACT.zh-CN.md)

产品架构文档同时记录 Studio 已经可以消费的 Core interfaces，以及仍需由 Core workstream 解决、Studio 不得自行打补丁掩盖的 consumer gaps。Phase 2A 将这个原则扩展为 **一个产品，多种宿主**：CLI、本地应用/本地 Web UI、云托管 UI、Agent Skill/Package Adapter 全部消费稳定 NovelForge contracts，不创建彼此独立的 truth model。

## 第一阶段纵向切片

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— 零依赖的 Run / Context Inspector；只在本地加载 `novelforge_run_receipt_v1` JSON，不暴露任何写入操作。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 明确标记为 synthetic 的演示回执，仅用于视觉与交互质量检查。

第一版原型会把下面这个区别直接呈现在界面中：

**语义选择结果判断为支撑材料的证据 ≠ 最终真正进入模型上下文的证据。**

## Phase 2A 可移植纵向切片

- [`project_hub_projection.py`](project_hub_projection.py) —— 从 `novelforge_project_adapter_resolution_v1` 生成 deterministic read-only projection；删除 host absolute paths，并绑定 exact source/projection fingerprints。
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) —— Project Hub + Scene workspace shell，包含 Creator/Inspector progressive disclosure 与 delivery-surface switching。
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) —— synthetic Project Adapter resolution；故意包含 host-private path，用于验证 redaction。
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) —— synthetic read-only Scene/Reader/Context/Runtime fixture。

可移植边界增加第二条交互原则：

**delivery surface 和 host capability 永远不能推导出 NovelForge story authority。**
