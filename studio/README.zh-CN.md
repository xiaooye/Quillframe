# NovelForge Studio

<p><kbd>产品体验</kbd>&nbsp;&nbsp;<kbd>创作工作台</kbd>&nbsp;&nbsp;<kbd>可检查运行</kbd></p>

NovelForge Studio 是 NovelForge Core 之上的产品体验层。**只读 Phase 1、Phase 2A、Phase 2B 已经真实合并到 `main`；它们是产品契约与宿主边界实现，但还不是已经发布、可以写入项目状态的完整 Studio 应用。** 未来可安装 Shell 的方向已经选定为 **Tauri + React + WeiUI**；具体实现仍待落地，而且 Core 的权威边界不会因此改变。

> **权威边界 ✦** Studio 只消费 NovelForge Core 状态。UI 状态不是正典（Canon）、记忆（Memory）、语义真相、写入权威，也不是第二套工作流引擎。

[English](README.en.md)

## 产品架构

- [English](PRODUCT_ARCHITECTURE.en.md)
- [简体中文](PRODUCT_ARCHITECTURE.zh-CN.md)
- [`portable_product_contract.json`](portable_product_contract.json) —— machine-readable 的 portable delivery-surface contract。

产品架构文档同时记录 Studio 已经可以消费的 Core interfaces，以及仍需由 Core workstream 解决、Studio 不得自行打补丁掩盖的 consumer gaps。它也记录已经选定的 Tauri + WeiUI 可安装 Shell 方向、token ownership、性能约束、responsive/i18n 要求，以及未来应用什么时候才能从“方向”晋升为“已交付能力”的 acceptance evidence。

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

## Phase 2B · Portable read-only host bridge

Phase 2B 把“一个产品，多种宿主”的边界真正做成可执行接口，同时不把 Studio 变成第二套 runtime。[`host_bridge.py`](host_bridge.py) 接收 versioned `novelforge_studio_host_bridge_request_v1` envelope，并返回绑定 fingerprint 的 `novelforge_studio_host_bridge_result_v1`。[`host_bridge_contract.json`](host_bridge_contract.json) 是 CLI、本地应用、云托管 UI 与 Agent Package 共同使用的 machine-readable allowlist。

当前支持的 read operations 刻意保持很小：`bridge.describe`、`framework.doctor`、`project.inspect`、`capabilities.inspect`、`context.inspect` 与 `semantic.catalog`。结果采用 default-deny 路线清除宿主私有路径，并明确携带 `authority=false`、Canon 无权威、Framework-write 无权威和 Settlement 无权威标记。

有些操作会明确返回 **unsupported**，而不是被 UI 或 Agent 偷偷模拟。Runtime session/event/handoff 查询暂缓，是因为当前 Control Plane CLI 即使执行名义上的读取命令，也会先初始化 persistence。`run.receipt.get` 继续暂缓，是因为 Core 尚未提供稳定的 Run Receipt retrieval projection，而且 event discoverability 仍不一致。通用 invoke/write 与 resume 也必须等 Core 明确定义公开 command、precondition、CAS/idempotency 与 receipt contract 后才能开放。这些 Core-owned dependency 统一记录在 #23。

### Agent Skill package

[`../agent-skills/novelforge/SKILL.md`](../agent-skills/novelforge/SKILL.md) 是 portable Agent Skills package。它附带的 [`novelforge_bridge.py`](../agent-skills/novelforge/scripts/novelforge_bridge.py) client 只负责发现并调用共享 Studio host bridge；不会 import 私有 Core runtime module，也不需要知道 persistence layout。

在 skill 目录中，先运行 discovery：

```bash
python scripts/novelforge_bridge.py describe
```

随后可以通过 request envelope 调用：

```bash
python scripts/novelforge_bridge.py invoke --request /path/to/request.json
```

宿主必须原样保留 `unsupported` / `unavailable` 状态，不能绕过 bridge 直接读 SQLite、import 私有实现，或拿一个 mutating Core primitive 来代替缺失的公开 contract。Phase 2B 仍然是 read-only：**这里不会加入 acceptance、settlement、Canon mutation、通用写入 API 或隐藏的 authority shortcut。**

## 未来可安装 Shell · Tauri + WeiUI

可安装版 Studio 的方向已经确定，但目前还没有 Tauri 应用实现合并到 `main`：

- **Tauri** 负责桌面应用宿主；
- **React 19** 提供 `@weiui/react` 所要求的 application shell；
- **WeiUI** 提供可复用 components、zero-JavaScript CSS 与 W3C-style token infrastructure；
- **NovelForge Story Loom** 继续通过确定性的 WeiUI-compatible token adapter 保持产品视觉/语义权威；
- Tauri / React / WeiUI 不会变成 Generic Core runtime correctness、CLI、Framework bundle 或 Agent Skill 的默认依赖。

Token ownership、tree-shaking、runtime overhead、responsive/i18n、accessibility、reduced motion 和 acceptance gate 的细则统一记录在 [产品架构](PRODUCT_ARCHITECTURE.zh-CN.md)。在对应实现 artifact 与测量证据真正进入 `main` 之前，Tauri + WeiUI 只是**已选定产品方向**，不能写成已经发布的 Studio capability。
