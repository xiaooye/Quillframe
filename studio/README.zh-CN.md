# Quillframe Studio

<p><kbd>产品体验</kbd>&nbsp;&nbsp;<kbd>创作工作台</kbd>&nbsp;&nbsp;<kbd>低运行开销</kbd></p>

Quillframe Studio 是 Quillframe Core 之上的产品体验层。Phase 1、Phase 2A、Phase 2B 已经建立产品模型、安全投影和 portable Host Bridge。**Phase 2C 现在已经包含一个真实可构建的只读 SolidJS application shell**：TypeScript + Vite + `@solidjs/router`，消费 Story Loom v2 和通过 config 按需生成的 zero-runtime-JavaScript WeiUI CSS foundation。

Local Web 是一等产品面；当目标是最低增量 CPU/RAM 时，它也是首选宿主。Tauri 继续作为未来 optional/installable host，而不是产品语义中心。

> **权威边界 ✦** Studio 只消费 Quillframe Core 状态。UI state 不是 Canon、Memory、semantic truth、write authority，也不是第二套 workflow engine。

[English](README.en.md)

## 产品架构

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) —— one-product/many-hosts delivery contract。
- [`host_bridge_contract.json`](host_bridge_contract.json) —— public read-only Host Bridge allowlist。
- [`../assets/brand/weiui.integration.json`](../assets/brand/weiui.integration.json) —— exact WeiUI source pin 与 generated-bundle contract。
- [`../assets/brand/story-loom.weiui.css`](../assets/brand/story-loom.weiui.css) —— live Story Loom `wui-theme` layer。

规则保持简单：**Core 拥有 truth；Studio 拥有 presentation 与 transport。** Core 尚未提供的公共 primitive 会明确保持 unavailable，而不是在 UI 中重造一套。

## Phase 1 · Run / Context Inspector prototype

- [`prototypes/run-context-inspector.html`](prototypes/run-context-inspector.html) —— 零依赖只读 Inspector prototype。
- [`fixtures/run-receipt.synthetic.json`](fixtures/run-receipt.synthetic.json) —— 仅用于 visual / interaction QA 的 synthetic receipt。

第一版原型建立了一个关键 observability 区分：语义选择认为能支撑问题的 evidence，不等于最终真正进入模型上下文的 evidence。

## Phase 2A · 一个产品，多种宿主

Quillframe 产品语义面向四种一等交付方式：

- **CLI** —— 可脚本化的原生 inspection / automation。
- **Local Web / local app** —— low-overhead creator workstation。
- **Cloud-hosted UI** —— 相同产品模型置于远程 transport 后。
- **Agent Skill / package** —— 面向其他 Agent Framework 的 portable adapter。

不同宿主可以拥有不同 capability，但这些差异不能改变 Canon、Settlement、Context、semantic-result、readiness、publication 或 receipt semantics。**Capability 不等于 authority。**

Phase 2A Project Hub safe projection 位于 [`project_hub_projection.py`](project_hub_projection.py)，会清除 absolute host paths 并携带明确的 non-authority markers。

## Host Bridge v11 · Portable read-only Agent Package

[`host_bridge.py`](host_bridge.py) 接收 `quillframe_host_bridge_request_v11`，返回带 fingerprint 的 `quillframe_host_bridge_result_v11`。`bridge.describe` 返回 `quillframe_host_bridge_description_v11`，并暴露 live `operation_contracts` metadata（`kind`、`required_args` 以及声明过的 `allowed_surfaces`）。

Portable [`../agent-skills/quillframe/SKILL.md`](../agent-skills/quillframe/SKILL.md) 会在转发前校验这些 metadata。`agent_package` 只允许 query：任何 command、semantic command、authority command、secret command、external query 或 handoff operation 都会在调用前 fail closed。`database.doctor` 同样是 side-effect-free；repair 不是 Bridge operation。Package 不会打开 private SQLite，也不会 import 私有 Core module。

[`portable_product_contract.json`](portable_product_contract.json) 与 [`host_bridge_contract.json`](host_bridge_contract.json) 是 checked-in v11 contract reference；live `bridge.describe` response 仍然是 operation source of truth。

## Story Loom v2 · WeiUI config-generated foundation

Story Loom 继续拥有 Quillframe visual/product-semantic authority；WeiUI 拥有 generic CSS/token primitives。

Reviewed upstream exact pin 记录在 [`../assets/brand/weiui.integration.json`](../assets/brand/weiui.integration.json)。Phase 2C 只消费 `@weiui/tokens` 与 `@weiui/css`；`@weiui/react` 和 `@weiui/headless` 继续禁止成为 Studio runtime dependency。

WeiUI 现在拥有正式的 **build-time config layer**。Studio 在 [`app/weiui.config.json`](app/weiui.config.json) 中声明实际需要的 generic UI surface：

```text
weiui.config.json
→ exact-pinned @weiui/css config/bundle manifest
→ dependency-closed minimal CSS
→ checked-in vendor CSS + token CSS
→ Story Loom wui-theme
→ SolidJS product surface
```

Generated files 会直接 checked in，因此普通 Studio runtime 不需要 Node、WeiUI checkout 或 bundler。[`sync_weiui.py`](sync_weiui.py) 在 CI 中基于 exact upstream pin 做 byte-for-byte regeneration verification。

Baseline design/runtime constraints 继续由 machine gate 强制：

- `en-US` + `zh-CN`；
- mobile-first、phone focus-first composition；
- minimum 44px touch target；
- logical CSS properties 与 text-expansion-safe layout；
- reduced-motion support；
- no idle decorative animation；
- no default polling；
- zero WeiUI browser JavaScript。

## Phase 2C · 真实 SolidJS product shell

Application source 位于 [`app/`](app/)。

```text
Core public boundary
→ studio/host_bridge.py
→ studio/local_server.py
→ typed /api/bridge/invoke transport
→ SolidJS + TypeScript + Vite + @solidjs/router
→ config-generated WeiUI CSS + Story Loom theme
```

当前只读 shell 已经包含：

- **Desk** —— live `bridge.describe`、supported/deferred operation counts 与 current project summary。
- **Project Hub** —— 真实 `project.inspect` safe projection。
- **Scene Workspace** —— 在 Core 暴露可信 current-scene/content projection 前明确 unavailable；不使用 fixture 或 filesystem inference 冒充当前场景。
- **Context Inspector** —— 使用 live contract 暴露的 `inspector.context.runtime` 与 typed inspector projection。
- **Host Capabilities** —— capability metadata 来自 live `bridge.describe`；UI 不自行发明 capability list。
- **Semantic evidence** —— 只提供 live v11 description 中存在的 operation，不保留 stale catalog alias。
- **Framework Diagnostics** —— 显式 `database.doctor` query；repair 有意不通过 Bridge 暴露。
- **Command palette** —— operation vocabulary 来自 live `bridge.describe`；deferred Core operations 会显示依赖原因，而不会表现成可执行命令。

App 默认没有 interval polling、WebSocket heartbeat、Redux-like second state store，也不把 project truth 持久化到 browser storage。Project root 只是当前页面 session 的 presentation state。

### Local server

[`local_server.py`](local_server.py) 是 stdlib-only transport。它：

- 只 bind `127.0.0.1`；
- 启动时生成 ephemeral token 并注入 served app；
- 检查 Host / Origin / `Sec-Fetch-Site`；
- API 只暴露 `POST /api/bridge/invoke`；
- 拒绝 CORS preflight；
- request body 上限 128 KiB；
- 没有 write / Canon / Settlement authority；
- 没有 polling 或 background refresh。

`local_server.py` 是 canonical launcher 管理的内部 transport。从仓库 workspace 完成构建后，只通过唯一受支持的用户入口打开 Project：

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm --filter @quillframe/studio-app build
quillframe launch PROJECT
```

`quillframe launch` 统一负责 Project 解析、loopback 生命周期、无 secret 的 launch receipt 与浏览器打开。内部 server 不是第二套 CLI 或用户流程。

## 性能纪律

Phase 2C 把性能当成 acceptance condition，而不是后期优化项。CI 会检查 raw JS/CSS budget；产品 routes 使用 lazy loading；初始 shell 不引入 heavy editor/runtime libraries。

首轮 production build 的 main Solid/router JS chunk 只有几十 KB raw，各 route chunk 为低个位数 KB。真正的 target-host idle CPU/RAM 仍必须实测后，才能称 desktop wrapper production-ready；bundle size 不能冒充 runtime measurement。

## 当前与 Studio 直接相关的 Core 能力

`quillframe_production_readiness_v1` 让 Review 拥有真实 same-fingerprint conjunction gate，而不是虚构的 quality percentage。

`quillframe_publication_ir_v1` + `publication/compiler.py` 提供 Accepted text → clean text、Web HTML、print-oriented HTML/CSS、EPUB 3.3 的 deterministic compilation。更丰富的 Publication Studio 仍然只能建立在 Core 实际存在的 contract 上。
