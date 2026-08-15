# NovelForge Studio · 可移植产品契约

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>PHASE 2A</kbd>&nbsp;&nbsp;<kbd>一个产品 · 多种宿主</kbd></p>

NovelForge Studio 可以拥有成熟 SaaS 产品一样的体验，但不需要把订阅、计费之类 SaaS 商业基础设施变成产品架构核心。产品契约应同时服务 CLI、本地应用、云托管 UI，以及供其他 Agent Framework 使用的 Skill / Package Adapter。

> **不变量 ✦ `DELIVERY SURFACE != SOURCE OF TRUTH.`**

## 01 · 四个一等交付面

### CLI

CLI 是原生自动化与脚本入口。它应暴露稳定、typed 的 query / command contracts 与 receipts，而不是要求调用方 import NovelForge 私有 Python 实现。

### 本地应用 / 本地 Web UI

本地 Creator Workstation 可以利用 filesystem-local adapter 与本地 runtime capability，但浏览器/UI 仍然只消费 projection 与 command，不拥有 Canon，也不直接读取 persistence internals。

### 云托管 UI

云 UI 在远程 API/query boundary 后消费与本地相同的 Studio projection 和 Core command semantics。Auth、隔离、存储拓扑、部署方式属于 hosting concerns，不重新定义 NovelForge story authority。

### Agent Skill / Package

其他 Agent Framework 应通过薄、versioned adapter package 使用 NovelForge。Adapter 只负责把宿主的 invocation convention 映射为 NovelForge capability/query/command contract，并返回 typed receipts。宿主不需要理解 NovelForge 的私有实现或数据库结构。

## 02 · 共享产品边界

```text
NovelForge Core contracts
        ↓
stable query / command / projection boundary
        ↓
┌────────────┬───────────────┬─────────────────┬──────────────────────┐
│ CLI        │ local app     │ cloud-hosted UI │ agent skill/package  │
└────────────┴───────────────┴─────────────────┴──────────────────────┘
```

不同交付面可以在 transport、host capability、latency、interaction density 上不同；它们不能在 Canon semantics、settlement semantics、Context authority、semantic-result meaning 或 receipt truth 上出现分叉。

## 03 · Capability 是宿主证据，不是故事权限

宿主可以报告：

- 本地文件系统；
- Git；
- subprocess / CLI；
- Web/search；
- 外部模型/provider；
- MCP 或其他 tool transport；
- publication renderer。

这些 capability 只说明当前宿主技术上能做什么，不会自动授予 Canon-write、Framework-write、Settlement 或 independent semantic authority。

Studio 因此必须分开显示：

1. **Host capability** —— 当前环境能执行什么。
2. **NovelForge authority** —— 某个 Core command/result 被允许修改或声明什么。

不能把二者压成一个“权限”徽章。

## 04 · Project Hub projection boundary

`novelforge_project_adapter_resolution_v1` 含有 Core 很需要、但不适合直接暴露给浏览器或远程客户端的 host-local 信息，尤其是 absolute filesystem path。

Phase 2A 引入一个 derived Studio projection，规则是：

- unknown source schema 直接拒绝；
- 对收到的 exact source object 计算 deterministic fingerprint；
- 只暴露 project identity、layout、framework lock identity、logical paths 和安全的 policy metadata；
- 默认删除 `project_root` 和所有 `paths.*.absolute`；
- 明确携带 `authority=false`、`canon_authority=false`、`framework_write_authority=false`、`settlement_authority=false`；
- 不能因为某目录存在就推断 manuscript state、current chapter、publication status 或 quality status；
- derived projection 自己再独立 fingerprint。

它是 presentation/query projection，不是新 Project schema。

## 05 · Scene / Chapter workspace 契约

Scene workspace 在所有宿主里仍然是同一个产品。不同宿主可以富 UI 或纯文本呈现，但概念模式保持一致：

- **Focus** —— manuscript first；
- **Analysis** —— manuscript + Reader / Character / Context evidence；
- **Compare** —— incumbent/challenger evidence 与 regressions；
- **Review** —— user-visible gate 与 unresolved findings。

Workspace 必须把这些轴分开：

- manuscript lifecycle / authority；
- runtime execution state；
- semantic findings；
- provenance；
- host capability。

一个 semantic job 正在 running，不会让 draft 更接近 Canon；一个 accepted manuscript 也不能证明当前宿主有 Settlement 能力。

## 06 · Agent Package 方向

Generic NovelForge Agent Adapter 应尽量小。稳定公共面可以抽象为 capability discovery、typed query、typed command 和 receipts。

建议的概念 API：

```text
inspect_capabilities()
inspect_project()
inspect_context(...)
inspect_run(...)
invoke(command, input, preconditions)
resume(session_or_run_ref)
```

Phase 2A prototype 不暴露 mutation。以后只有 Core 已定义 typed command + precondition semantics 时，adapter 才可映射写操作。

Adapter package 应发布：

- adapter/package schema version；
- compatible NovelForge contract versions；
- supported operations；
- required host capabilities；
- permission/authority notes；
- typed result/receipt schemas；
- provider/framework-specific glue 与 generic contract 分离。

未来可以适配 Agent Skill、MCP-style host、framework plugin、CLI bridge；这些都只是 adapter，不是另一套 NovelForge runtime。

## 07 · 当前故意不决定的技术

Phase 2A 不选：

- React/Vue/Svelte；
- Electron/Tauri/PWA；
- cloud provider；
- auth provider；
- database topology；
- 某一个外部 Agent Framework；
- billing/subscription system。

稳定 boundary 形成后，再由真实需求决定这些实现选择。

## 08 · 产品质量底线

无论在哪个宿主，NovelForge 都要保持：

- 有视觉 UI 时沿用 Story Loom semantic language；
- 缺失数据明确显示 unavailable/unsupported，不猜；
- Creator Mode → Inspector detail progressive disclosure；
- 能提供时保留 exact provenance 与 fingerprint；
- 不展示 chain-of-thought；
- 不制造 fake engagement / consistency 百分比；
- 浏览器不直接修改 Core persistence；
- 不创建第二套 Canon、Memory、Quality、Session 或 Semantic Truth store。

## 09 · Phase 2A 输出

本阶段新增：

1. deterministic Project Hub projection；
2. browser/remote-safe path redaction；
3. exact source + projection fingerprints；
4. CLI/local/cloud/agent-package 共用的一份产品契约；
5. read-only Project Hub + Scene workspace prototype；
6. 用于 interaction QA 的 synthetic fixtures。

下一个真正的架构 gate 不是“选哪套 SaaS stack”，而是：**什么稳定的 Core query/command boundary 能让所有宿主消费，同时不耦合私有实现？**
