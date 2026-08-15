# NovelForge Studio

<p><kbd>产品体验</kbd>&nbsp;&nbsp;<kbd>创作工作台</kbd>&nbsp;&nbsp;<kbd>可检查运行</kbd></p>

NovelForge Studio 是 NovelForge Core 之上的产品体验层。**第一阶段（Phase 1）已经合并到 `main`，目前是一套契约优先、只读的产品验证原型；它不是已经发布、可以写入项目状态的完整 Studio 应用。** 开发继续采用 contract-first 路线：先基于 live Core contracts 验证产品语义和宿主边界，再决定正式 Web、Desktop、Cloud 或 Agent Framework 专用技术栈。

> **权威边界 ✦** Studio 只消费 NovelForge Core 状态。UI 状态不是正典（Canon）、记忆（Memory）、语义真相、写入权威，也不是第二套工作流引擎。

[English](README.en.md)

## 产品架构

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) —— machine-readable 的 Phase 2A delivery-surface contract。

产品架构文档同时记录 Studio 已经可以消费的 Core interfaces，以及仍需由 Core workstream 解决、Studio 不得自行打补丁掩盖的 consumer gaps。

## 第一阶段纵向切片

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— 零依赖的 Run / Context Inspector；只在本地加载 `novelforge_run_receipt_v1` JSON，不暴露任何写入操作。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 明确标记为 synthetic 的演示回执，仅用于视觉与交互质量检查。

第一版原型会把下面这个区别直接呈现在界面中：

**语义选择结果判断为支撑材料的证据 ≠ 最终真正进入模型上下文的证据。**

## Phase 2A · 一个产品，多种宿主

Phase 2A 把 Studio 定位为具有成熟 SaaS-like 体验的产品，但不把 SaaS 商业基础设施变成产品模型的一部分。同一套 NovelForge semantics 应通过四个一等交付面使用：

- **CLI** —— 可脚本化的原生自动化与 inspection。
- **本地应用 / 本地 Web UI** —— 通过 typed adapter 使用本地 host capability 的 Creator Workstation。
- **云托管 UI** —— 在远程 query/command boundary 后使用相同产品模型。
- **Agent Skill / Package** —— 面向其他 Agent Framework 的薄、versioned adapter，不暴露 NovelForge 私有 persistence 或 implementation internals。

不同宿主可以拥有不同 capability 与 transport，但这些差异不能改变 Canon、Settlement、Context、semantic-result 或 receipt semantics。**Host capability 不会推导出 NovelForge story authority。**

### Portable Project Hub / Scene 纵向切片

- [`project_hub_projection.py`](project_hub_projection.py) —— 从 `novelforge_project_adapter_resolution_v1` 生成 deterministic read-only projection；拒绝错误 source schema，删除 host absolute paths，并绑定 exact source/projection fingerprints。
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) —— Project Hub + Scene workspace shell，包含 Creator/Inspector progressive disclosure 与 delivery-surface switching。
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) —— synthetic Project Adapter resolution；故意包含 private absolute paths，用于验证 redaction。
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) —— synthetic read-only Scene/Reader/Context/Runtime fixture。

Projection 明确携带 `authority=false`、`canon_authority=false`、`framework_write_authority=false` 与 `settlement_authority=false`。它不会因为 logical path 存在就推断 current chapter、manuscript lifecycle、publication status 或 quality status。

Agent-package 方向保持 generic：未来 adapter 应暴露 capability discovery、typed query、typed command、resume reference 与 typed receipts。Mutation 必须等 Core 已经定义 command、precondition 与 authority semantics 后才进入公开 adapter。
