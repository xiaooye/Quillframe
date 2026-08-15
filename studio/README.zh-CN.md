# NovelForge Studio

<p><kbd>产品体验</kbd>&nbsp;&nbsp;<kbd>创作工作台</kbd>&nbsp;&nbsp;<kbd>可检查运行</kbd></p>

NovelForge Studio 是 NovelForge Core 之上的产品体验层。**只读 Phase 1、Phase 2A、Phase 2B 已经存在于 `main`；Story Loom v2 + exact-pinned 的 zero-JS WeiUI CSS/token foundation 也已经合并。** Phase 2C application stack 现已确定为 **SolidJS + TypeScript + Vite + `@solidjs/router`**。Local Web 保持一等产品面；Tauri 是 optional/installable host。当前仍然不是已经发布、可写项目状态的完整 Studio 应用。

> **权威边界 ✦** Studio 只消费 NovelForge Core 状态。UI 状态不是 Canon、Memory、semantic truth、write authority，也不是第二套 workflow engine。

[English](README.en.md)

## 产品架构

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) —— machine-readable portable delivery-surface contract。
- [`../assets/brand/weiui.integration.json`](../assets/brand/weiui.integration.json) —— exact WeiUI pin 与 zero-JS consumption contract。
- [`../assets/brand/story-loom.weiui.css`](../assets/brand/story-loom.weiui.css) —— 当前 live Story Loom `wui-theme` layer。

产品架构文档同时记录 Studio 已经可以消费的 Core interfaces，以及仍需由 Core workstream 解决、Studio 不得自行绕过的 consumer gaps。它也记录 low-overhead Phase 2C stack、Local Web / optional Tauri host 分工、mobile/i18n/accessibility/runtime rules，以及 Core 现在真正已经暴露的 Publication / production-readiness surfaces。

## 第一阶段纵向切片

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— 零依赖的 Run / Context Inspector；只在本地加载 `novelforge_run_receipt_v1` JSON，不暴露任何写入操作。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 明确标记为 synthetic 的演示回执，仅用于视觉与交互质量检查。

第一版原型会把下面这个区别直接呈现在界面中：

**语义选择结果判断为支撑材料的证据 ≠ 最终真正进入模型上下文的证据。**

## Phase 2A · 一个产品，多种宿主

同一套 NovelForge semantics 继续通过四个一等交付面使用：

- **CLI** —— 可脚本化的原生自动化与 inspection。
- **Local Web / 本地应用** —— low-overhead creator workstation，通过 typed adapter 使用本地 host capability。
- **云托管 UI** —— 在远程 query/command boundary 后使用相同产品模型。
- **Agent Skill / Package** —— 面向其他 Agent Framework 的薄、versioned adapter，不暴露 NovelForge 私有 persistence 或 implementation internals。

不同宿主可以拥有不同 capability 与 transport，但这些差异不能改变 Canon、Settlement、Context、semantic-result、readiness、publication 或 receipt semantics。**Host capability 不会推导出 NovelForge story authority。**

### Portable Project Hub / Scene 纵向切片

- [`project_hub_projection.py`](project_hub_projection.py) —— 从 `novelforge_project_adapter_resolution_v1` 生成 deterministic read-only projection；拒绝错误 source schema，删除 host absolute paths，并绑定 exact source/projection fingerprints。
- [`prototypes/project-hub-scene.html`](prototypes/project-hub-scene.html) —— Project Hub + Scene workspace shell，包含 Creator/Inspector progressive disclosure 与 delivery-surface switching。
- [`fixtures/project-adapter-resolution.synthetic.json`](fixtures/project-adapter-resolution.synthetic.json) —— synthetic Project Adapter resolution；故意包含 private absolute paths，用于验证 redaction。
- [`fixtures/scene-workspace.synthetic.json`](fixtures/scene-workspace.synthetic.json) —— synthetic read-only Scene/Reader/Context/Runtime fixture。

Projection 明确携带 `authority=false`、`canon_authority=false`、`framework_write_authority=false` 与 `settlement_authority=false`。它不会因为 logical path 存在就推断 current chapter、manuscript lifecycle、publication status 或 quality status。

## Phase 2B · Portable read-only host bridge

[`host_bridge.py`](host_bridge.py) 接收 versioned `novelforge_studio_host_bridge_request_v1` envelope，并返回绑定 fingerprint 的 `novelforge_studio_host_bridge_result_v1`。[`host_bridge_contract.json`](host_bridge_contract.json) 是 CLI、Local Web/app、Hosted UI 与 Agent Package 共同使用的 machine-readable allowlist。

当前支持的 read operations 刻意保持很小：`bridge.describe`、`framework.doctor`、`project.inspect`、`capabilities.inspect`、`context.inspect` 与 `semantic.catalog`。结果采用 default-deny 路线清除宿主私有路径，并明确携带 `authority=false`、Canon 无权威、Framework-write 无权威和 Settlement 无权威标记。

有些操作继续明确返回 **unsupported**，而不是被 UI 或 Agent 偷偷模拟。Runtime session/event/handoff 查询与 Run Receipt retrieval 仍依赖 Core Issue #23。Generic invoke/write 与 resume 也继续等待 Core 暴露正式的 precondition/CAS/idempotency/receipt contract。

### Agent Skill package

[`../agent-skills/novelforge/SKILL.md`](../agent-skills/novelforge/SKILL.md) 是 portable Agent Skills package。它附带的 [`novelforge_bridge.py`](../agent-skills/novelforge/scripts/novelforge_bridge.py) client 只负责发现并调用共享 Studio host bridge；不会 import 私有 Core runtime module，也不需要知道 persistence layout。

## Story Loom v2 · WeiUI zero-JS foundation

Design-system integration 已经不再只是未来方向：

- Story Loom token schema：`novelforge_brand_tokens_v2`；
- exact WeiUI source pin：`d84d1cd365fb5f90cbbab794d2358f7a13b29b79`；
- allowed WeiUI packages：`@weiui/tokens`、`@weiui/css`；
- forbidden Phase 2C runtime packages：`@weiui/react`、`@weiui/headless`；
- WeiUI runtime JavaScript：**不需要**；
- Story Loom theme：`assets/brand/story-loom.weiui.css`，位于 `wui-theme`；
- baseline locales：`en-US`、`zh-CN`；
- mobile-first、44px minimum touch target、reduced motion、no idle decorative animation、no default polling；
- `scripts/design_system_quality.py` 提供 deterministic design-system CI。

## Phase 2C · SolidJS product shell

选定的 application shape 是：

```text
Core public boundary
→ Studio view models
→ SolidJS + TypeScript + Vite + @solidjs/router
→ WeiUI tokens/CSS + Story Loom theme
→ Local Web（first-class）
→ optional Tauri package
```

当前 Phase 2C 计划**不包含 React runtime**。Tauri 仍适合做 installable desktop build，但产品必须在完全不依赖 desktop-host overhead 的 Local Web 形态下保持完整一致。

App 本身仍需要真实实现和测量。Phase 2C production-ready 前必须测量 idle CPU/RAM、first-interaction latency、route cost 与 Core-process lifetime，并继续满足 no-default-polling 与 explicit host lifecycle 规则。

## 当前与 Studio 直接相关的 Core 新能力

`novelforge_production_readiness_v1` 现在让 Review 拥有真实的 same-fingerprint conjunction gate，而不是一个虚构的质量百分比。

`novelforge_publication_ir_v1` + `publication/compiler.py` 现在给 Publish 提供真实的 deterministic minimum Core：Accepted text → clean text、Web HTML、print-oriented HTML/CSS、EPUB 3.3。它不表示更大的 Typesetting Toolkit 或 Studio Publish UX 已完成；Issue #16 的 richer scope 继续 open。
