# NovelForge Studio

<p><kbd>产品体验</kbd>&nbsp;&nbsp;<kbd>创作工作台</kbd>&nbsp;&nbsp;<kbd>可检查运行</kbd></p>

NovelForge Studio 是 NovelForge Core 之上的产品体验层。**第一阶段（Phase 1）已经合并到 `main`，目前是一套契约优先、只读的产品验证原型；它不是已经发布、可以写入项目状态的完整 Studio 应用。** 这一阶段先用 live Core contracts 验证产品架构与可观察性体验，再决定正式 Web / Desktop 技术栈。

> **权威边界 ✦** Studio 只消费 NovelForge Core 状态。UI 状态不是正典（Canon）、记忆（Memory）、语义真相、写入权威，也不是第二套工作流引擎。

[English](README.en.md)

## 产品架构

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)

产品架构文档同时记录第一阶段已经可以消费的 Core 接口，以及仍需由 Core workstream 解决、Studio 不得自行打补丁掩盖的 consumer gaps。

## 第一阶段纵向切片

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— 零依赖的 Run / Context Inspector；只在本地加载 `novelforge_run_receipt_v1` JSON，不暴露任何写入操作。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 明确标记为 synthetic 的演示回执，仅用于视觉与交互质量检查。

第一版原型会把下面这个区别直接呈现在界面中：

**语义选择结果判断为支撑材料的证据 ≠ 最终真正进入模型上下文的证据。**
