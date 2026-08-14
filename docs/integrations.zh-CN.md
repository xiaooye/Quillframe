<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><strong>运行时与集成 · 先证明当前环境具备什么能力，再把结果绑定回同一个任务契约</strong></p>
  <p><kbd>能力确认</kbd>&nbsp;&nbsp;<kbd>路由</kbd>&nbsp;&nbsp;<kbd>检查点</kbd>&nbsp;&nbsp;<kbd>执行回执</kbd>&nbsp;&nbsp;<kbd>结果校验</kbd></p>
  <p><a href="integrations.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 运行时与集成

NovelForge 不绑定某一家模型或执行平台，但“提供商无关”并不意味着系统可以假设任何运行时都具备同样能力。

一条执行路径只有在当前宿主真实满足任务需要的**权限、可用性、用户交互要求、模型执行能力与额度 / 使用限制**时，才算可用。

Harness 允许执行路径在当前聊天、本地 Codex / Claude、模型 API、MCP、GitHub job、本地模型或人工之间变化，但语义任务本身的身份与项目权威边界不能跟着漂移。

> **运行时名称不是能力证明；能力也不是权威。重试 transport，不等于换了一个语义问题。**

---

## 01 · 所有集成共享同一套执行模型

大多数外部任务或语义任务都遵守相同顺序。

**先分类任务。** 当前步骤到底需要文件读写、Git、Web / GitHub 搜索、语义模型、独立审查、持久外部工作，还是其他明确能力？

**再确认 capability。** 没有声明的能力按不可用处理。仅凭“这是某某模型 / 某某平台”不能推断能力存在。

**有外部等待或 consequential write 前先 checkpoint。** 保存 Project authority、artifact fingerprint、pending work 与已完成 side effect 状态。

**选择满足契约的最简单执行路径。** 路由需要同时考虑 independence、用户约束与 usage policy。

**封装精确任务契约。** Semantic work 的 subject、bounded input、rubric、output contract、permissions 与 fingerprint 不依赖某一家 transport。

**执行并记录来源。** Provider、worker、session、attempt 属于 execution lineage，不改变 semantic identity。

**校验返回结果。** Stale fingerprint、错误 contract binding、malformed output 或越权 side effect 都应被拒绝。

**结果只消费一次。** 有效结果进入真正拥有它的 workflow；有效语义拒绝进入 repair；基础设施失败才允许换另一条 eligible route。

---

## 02 · 当前聊天

当前 chat 可以承担 manager，也可以执行普通的 bounded semantic work——前提是当前契约并不要求独立性。

同一个 invocation 里由自己生成候选稿，再换一个“reviewer 角色”自审，不能满足 mandatory independent gate。

聊天历史可以帮助继续对话，但不会自动变成 Canon、Project state 或持久 semantic receipt。

---

## 03 · 独立 peer chat

当用户希望得到真正不同的模型调用，或者当前 rubric 明确要求 independence，但又不想额外走 provider API 时，独立 peer chat 是一种合法路径。

Peer 只接收有界 packet，并通过 relay protocol 返回绑定精确 fingerprint 的类型化证据。

### Issue / relay 必须属于消费项目仓库

这条边界尤其重要：**某一本小说的 peer-review issue / relay surface 应放在消费 NovelForge 的 Project repo，而不是 generic Framework repo。**

NovelForge 只提供可复用 workflow、composite action 与 bridge runtime：

- review issue / relay state 由消费项目仓库拥有；
- Framework repo 监听具体 Project review issue 是禁止的；
- caller 必须绑定自己正在使用的 exact Framework commit；
- provenance 同时绑定 Project repo 与 Framework revision。

这样，一个项目的独立审查队列不会变成 Framework 仓库里的共享可变状态。

参考实现：`.github/workflows/novelforge-chat-semantic-bridge.yml`、`.github/actions/project-peer-semantic/`、`harness/semantic_workers/peer_chat_relay.py`。

---

## 04 · 本地 Codex 与 Claude Code

本地 coding agent 可以执行完整 Harness，也可以只承担 bounded specialist / semantic worker，只要当前宿主确实开放了对应能力。

常见用途包括：

- 需要 repo 上下文的 Project / Framework 工程任务；
- 需要真正独立 invocation 的本地语义判断；
- semantic result 前后的 deterministic validation；
- 不适合通过 provider API 隧道执行的本地文件 / Git 操作。

如果本地 Codex / Claude 已经通过其支持的方式完成认证，NovelForge 不要求仅为了使用 Framework 再额外配置同一家 provider 的第二份 API credential。

需要 independent gate 时，仍然必须使用真正独立的 invocation / session，并保持同一 bounded packet 与 fingerprint contract。

Repo hooks 可以记录生命周期或文件变化 telemetry，但这些 deterministic telemetry 不是语义审查。

---

## 05 · 模型提供商 API

Provider API 只是可选的 semantic execution transport。

Adapter 仍然必须保持 NovelForge 的统一契约：

- exact contract ID 与 pack；
- bounded input；
- rubric 与 output contract；
- semantic fingerprint；
- authority / permission boundary；
- typed result validation；
- execution provenance；
- consume-once semantics。

模型提供商不会因为“结果是它生成的”就获得 Project authority。

普通 CI 只跑 contract / dry-run test，不会静默消耗 provider inference usage。真正的 live semantic execution 需要显式选择执行路径并配置相应 secret。

---

## 06 · MCP 与 service worker

本地参考 transport 是 stdio MCP。远程 service 可以使用 Streamable HTTP，但必须正常处理 authentication、Origin、session 与 transport security。

Control Plane 暴露的是**运行能力**：external event、handoff、lease、result receipt 与 durable work lifecycle。

它故意不提供一个通用的“把这条结果写进 Canon”工具。

Worker 可以返回结果；Harness 仍然要判断它是否满足 semantic contract；真正的高权威 mutation 仍然属于 Project / Settlement。

---

## 07 · GitHub Actions 与 service job

GitHub 可以承担很多不同工作，但这些工作不能混成一个“万能自动化”。

**Deterministic CI** —— 检查代码、Schema、Project / Framework contract、文档、bundle 与 eval queue hygiene，不执行 live model。

**Reusable contract workflow** —— 让消费 Project 对一个精确锁定的 Framework revision 运行确定性契约检查。

**Typed event ingress** —— 把外部事件规范化成共享生命周期，而不是为每一家 provider 发明一套 retry / resume 语义。

**Project-hosted peer-chat bridge** —— 运输独立 semantic packet，但 review state 留在消费 Project repo。

**Optional live semantic workflow** —— 只有显式手工 dispatch、且存在所需 secret / usage policy 时才执行 model-backed eval。

**Scheduled maintenance** —— 可以推进确定性维护状态或准备队列，但不会因为“时间到了”就自动获得模型执行、Web 访问或 Framework promotion 权限。

当前主要 workflow 包括：

- `.github/workflows/novelforge-ci.yml`
- `.github/workflows/novelforge-contracts.yml`
- `.github/workflows/novelforge-semantic-contract-packs.yml`
- `.github/workflows/novelforge-release-bundle.yml`
- `.github/workflows/novelforge-event-router.yml`
- `.github/workflows/novelforge-chat-semantic-bridge.yml`
- `.github/workflows/novelforge-semantic-live.yml`
- `.github/workflows/novelforge-weekly-maintenance.yml`

GitHub workflow event 是 trigger / transport evidence，不会自动提升 authority。

---

## 08 · Provider-neutral semantic run receipt

较长的 semantic workflow 可以产生 `novelforge_semantic_run_receipt_v1`。

Receipt 是**无权威的执行追踪记录**，不是 Session / Control Plane 的替代品，也不是 private reasoning dump。

它可以绑定：

- run / session / task identity；
- Context Manifest reference、fingerprint 与 authority snapshot；
- capture policy；
- 激活了哪些 contract pack、为什么激活；
- 每个 semantic step 的 input / result fingerprint；
- worker execution lineage；
- artifact / finding references；
- 无权威 decision；
- workflow status。

Capture policy 明确禁止保存 private reasoning 与 hidden gold。Semantic payload 可以只保存 fingerprint，也可以保存 bounded typed result。

Receipt 里的 step / decision 均保持 `authority=false`；permissions 也明确禁止 Canon、Framework 与 durable-user-taste write。

精确 Schema：`harness/semantic_workers/semantic_run_receipt.schema.json`。

---

## 09 · Web / GitHub / Corpus discovery

不能因为“模型看起来能上网”就推断网络能力存在。

真正执行 discovery 之前，需要当前 host 明确提供 web search、GitHub search、authorized connector 或其他 source capability。

像 `corpus.discovery_plan` 这样的 semantic contract 可以判断**应该搜什么、为什么搜**；能不能实际执行、可以保存什么，则仍然由 capability / rights layer 决定。

Scheduled job 或本地 runtime 在没有授权 source tool 时，不得伪造“已经搜索过”。

Discovery 也不等于 ingestion；source provenance 与 rights classification 仍然是另一道门槛。

---

## 10 · 人工审阅

Human reviewer 是一等 runtime。

用于 independent gate 时，人工审阅者应该收到和模型 reviewer 同样受限的 artifact / rubric contract、精确 fingerprint 与必要 provenance。

返回结果最好保持 typed evidence 或等价的结构化格式，方便 manager 校验对方实际审的是哪一份 artifact。

人工判断本身同样不会自动获得 Canon-write authority。

---

## 11 · Webhook 与外部事件

Provider-specific webhook 应先 normalize 成统一 typed event，再交给 Harness 分类。

推荐路径是：

**provider event → NovelForge typed event → provenance / idempotency validation → Harness classification → owning workflow**

不要为每一个 provider 分别发明 resume、retry 与 authority semantics。

Webhook、connector event、schedule 或 MCP message 可以触发工作，但不能单独授权 Canon mutation。

---

## 12 · Fallback 只针对基础设施失败

只有 **infrastructure failure** 才能切换执行路径。

例如：

- worker 不可用；
- provider outage；
- lease 过期；
- 本地 binary 缺失；
- 已声明 capability 消失；
- 尚未形成有效 semantic result 前 transport response 损坏。

一个已经有效返回的 semantic result——尤其 `semantic_reject`——不是 transport failure。它必须进入真正的 repair mechanism。

如果修复导致 artifact / rubric / output contract 实质变化，就形成新的 semantic fingerprint，通常也需要新的 review job。

---

## 13 · Secret 与 credential 边界

Provider credential 属于 host / runtime configuration。

不要把 secret 写进：

- Project Canon；
- semantic job payload；
- Corpus record；
- commit 到仓库的 runtime SQLite；
- Framework source；
- review issue / relay packet；
- learning evidence。

Capability record 可以说明某个 provider / API 当前可用，但不应把真正 secret 嵌进去。

---

## 14 · 怎么选执行路径

选择**满足契约的最简单路径**。

**当前聊天** —— manager 或普通 semantic work；不要求 independence 时成本最低。

**Peer chat** —— 用户中继的独立模型判断，尤其适合不想走 API model execution 的场景。

**本地 Codex / Claude** —— 已认证、能直接读仓库的本地执行。

**Provider API** —— 显式的程序化 semantic execution 与自动化。

**MCP / service worker** —— 跨进程 / 主机的 durable operational delegation。

**GitHub job** —— deterministic CI、事件驱动 integration 或明确配置的 service workflow。

**本地模型** —— 在能力足够时换取 privacy / cost / offline 优势。

**人工** —— 高价值判断、policy 或需要人类证据的 acceptance / review。

执行路径可以变；任务契约和 authority boundary 不能跟着变。

---

## 15 · 精确参考

- [运行时能力](../harness/session_runtime/RUNTIME_CAPABILITIES.zh-CN.md)
- [运行时路由](../harness/session_runtime/RUNTIME_ROUTING.zh-CN.md)
- [会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md)
- [控制平面](../harness/control_plane/CONTROL_PLANE.zh-CN.md)
- [语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)
- [语义执行运行时](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)
- [项目 SDK](project-sdk.zh-CN.md)
- [语料智能](../corpus/README.zh-CN.md)

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="48" />
  <br />
  <sub>执行路径可以切换，权威边界不能跟着漂移。✦</sub>
</div>
