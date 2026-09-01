# Durable Model Pending 规格

2026-08-31 · 已实现的 `SYSTEM-IMPROVE` 契约 · 确定性工程证据已完成；CH001 的真实 REVISE 与全新独立审稿仍是分开的生产关卡。

本规格仅对新的本地 keyed 生产请求前向取代规格 027 中的同步生命周期规则。它不改变 Quillframe Project 1.0、语义契约、文学 rubric、候选指纹、独立审稿边界或 Core release 权限。

## 01 · 已观察问题

旧传输把 HTTP 等待、队列准入、worker 寿命、结果发布和生产阶段确认共用一个绝对截止时间。API 只是慢、进程仍活着，也可能因为交互等待结束而被杀死并记成终态失败。重新派发又不安全，因为旧进程可能稍后返回；完全不继续则会让正常的慢调用堵死生产。

现在必须区分：

- HTTP waiter 已结束，但同一个 worker 仍在运行；
- worker 心跳正常；
- 心跳陈旧，执行结果未知；
- worker 已退出且没有有效结果；
- 结果存在但身份、schema 或语义校验失败；
- 有效语义判断拒绝候选。

只有后三种对本次 attempt 是终态。HTTP 等待结束本身不是模型失败。

## 02 · 固定决策与不变量

1. Durable request 使用从冻结 `AgentJob` 与调用序号导出的稳定幂等键。
2. 该键只绑定一个不可变 relay packet、一个已计费 stage intent，最多启动一个 CLI 进程。
3. HTTP 短暂等待后可返回 `202 model_pending`；worker 继续，生产 run 进入 `semantic_pending`。
4. Resume 只能轮询原请求。轮询不得新增 stage-call 行，也不得再次扣预算。
5. 初始 deadline 仍限制格式错误、请求准备和启动前准入；一旦已留下启动证据，API 慢不再形成任意 worker 寿命上限。
6. 同一请求的精确终态输出可在原 HTTP／准入时间窗之后消费；错误身份、变更字节、已确认取消或终态 worker failure 仍然阻断。
7. 心跳丢失或陈旧代表未知，不代表可以重派。
8. 传输变化不得改写 prompt、语义指纹、输出 schema、文学关卡、独立性或 authority。

## 03 · 目标与非目标

目标是为慢速本地生产调用提供可恢复、只消费一次的执行，同时杜绝重复派发和重复计费。

非目标：

- 语义自动重试、JSON 修补或绕过质量关卡；
- 增加模型调用授权；
- 把确定性测试当作文学审稿；
- 改变 Canon、接受、结算或用户品味权限；
- 把历史 v2 失败伪装成仍存活的 v3 worker；
- 声称陈旧心跳能够证明成功或失败。

## 04 · 身份与权限

以下身份有关联，但绝不等价：

```text
逻辑 AgentJob request
≠ production stage-call intent
≠ relay request packet
≠ 已计费 CLI attempt
≠ worker process / heartbeat
≠ HTTP waiter
≠ response bytes
≠ confirmed stage result
≠ independent review
≠ Core release
```

生产 journal 管理调用意图与只消费一次确认；relay 管理不可变传输 packet；CLI driver 管理启动证据与 worker 状态；Semantic Runtime 校验返回结果；Core 单独负责释放 Review Draft。任何一项都不授予 Canon 或 Settlement 权限。

## 05 · 当前 v3 契约

新的前向执行路线使用：

- relay packet/result：`quillframe_chat_host_relay_v3`；
- CLI attempt ledger：`quillframe_codex_cli_relay_v3`；
- worker state：`quillframe_codex_cli_worker_state_v1`；
- AgentJob/AgentResult v1，其中 `model_pending` 是类型化非终态结果；
- `quillframe_production_execution_journal_v1`，以 `error_code=idempotent_model_request|model_pending` 表示可轮询的 dispatched 行。

请求键 header 为 `X-Quillframe-Model-Request-Key`。只有字面 loopback POST 携带它的 SHA-256；message body 不变。v3 durable packet 包含精确请求、请求键指纹、初始 timing、`durable_pending=true`、仅 manager 的 provenance，以及 `authority=false`。

本功能不改写原生 1.0 数据库 schema。pollable 是现有 stage journal 内的显式兼容编码；投影分别暴露 `pending_call_ids`、`hard_unconfirmed_call_ids` 和 `safe_to_poll_pending`。

## 06 · 生命周期

```text
冻结 stage intent
→ 持久化 pollable intent
→ 发布不可变 packet
→ CLI attempt 只计费一次
→ worker running + heartbeat
→ 发布结果或终态 worker state
→ 校验精确结果
→ stage 只确认一次
→ 继续生产图
```

HTTP waiter 可在 packet 发布后暂时退出：

```text
waiter 结束 → 202 model_pending → semantic_pending → 同请求轮询
```

它不会改变 worker 状态。packet 已发出但首个 202 尚未返回时进程崩溃，也能恢复，因为 transport 派发前 stage 已被标记为 pollable。

## 07 · 准入、worker 与心跳

调用方、relay 和 packet 仍保存有限 timing，因此 DNS、请求解析、队列准备和启动前准入不能永远挂住，也不能启动已无效的请求。CLI driver 必须先于新 packet 启动，并在真正拉起进程前记录一次已计费 `cli_started`。

对 keyed durable packet，默认 CLI 路线没有任意 `worker_seconds` 超时。操作者仍可显式设置有限的紧急上限；这只是运维策略，不是语义重试授权。进程运行时 driver 原子刷新心跳；正常退出后依次发布 `finalizing` 与 `completed`／`failed`。

准入后心跳丢失或陈旧属于 `execution_unconfirmed`，禁止二次启动。恢复只能依赖同一 worker／result 证据、显式取消或人工 reconciliation。

## 08 · HTTP pending 与结果绑定

relay 只做很短的交互等待。没有终态证据时返回：

```json
{"status":"model_pending","same_request_poll_only":true}
```

后续相同 POST 加入既有 packet；同 key 但 body 不同则返回幂等冲突。并发首次发布者加入精确胜出 packet，不会制造两个请求。

relay 先检查 response，再检查终态 worker state，并校验 request/response 身份。只有 worker 明确 `failed`，或 `completed` 却无 response，才返回终态 worker failure。轮询时的网络中断无法证明 worker 结束，因此仍保持 pending。

## 09 · 预算与只消费一次

生产 stage 行在外部派发前创建，只占一次 `max_model_calls`；CLI ledger 对实际启动 attempt 只记一次。重复 HTTP 等待、生产 resume、心跳刷新和结果读取都不是模型调用。

生产 journal 只接受与原 job、session、run、input fingerprint 和 Model Service 全部一致的结果。confirmed result 不可替换。pending 行即使跨过旧 waiter deadline 仍可轮询；过期不能凭空创建替代行。

独立审稿仍是一笔分开预留的调用与全新 invocation。延长等待不会增加任何预算。

## 10 · 取消与晚到结果

Core cancellation 把 run 与未决 stage 行标记为 cancelled，但不会谎称外部进程一定已被杀死。稍后到达的 response 可保留为传输证据，却不能被已取消 run 消费。在 Core 确认取消之前，请求保持 pending／unknown，不能重派。

只有已实际启动、身份精确且字节未变的 durable request 才能接受晚到发布。已确认取消、终态失败、attempt 冲突、格式错误或指纹不符的结果必须拒绝。

## 11 · 生产与审稿隔离

Durable pending 只属于 manager transport。Writer 与 registered semantic stage 的契约和输入不变；Blind Reader 与独立审稿人仍看不到 style selection 或旧判断。REVISE 候选仍需通过全新的 Reader、continuity、self-audit、comparison 与独立审稿，Core 才能将它暴露为未接受的 Review Draft。

## 12 · 兼容与前向取代

规格 027 继续作为 v2 同步请求的历史证据。本规格仅对新的 keyed v3 执行前向取代：

- 把 600 秒 Model/Agent cap 当作 worker 寿命；
- 把 170/590 秒 relay cap 当作 worker 寿命；
- 把 150/570 秒 CLI cap 当作生产 worker 默认寿命；
- 把 HTTP timeout 当作终态模型失败；
- 一律拒绝首个 waiter deadline 之后发布的结果；
- “异步 durable execution 不在目标内”的旧声明。

仍保留 027 的普通同步有限默认值、启动前校验、禁止自动重试、单次计费、历史证据不可变、指纹绑定、普通 CI 不跑模型，以及独立审稿单独计费。

历史 v2 packet 和 receipt 只读保留，不升级、不 replay，也不转成 v3 pending job。已确认终止的旧失败必须走新的授权 run。

## 13 · 回滚

回滚时停止为新 run 启用 keyed durable 路线，先 drain 或 reconcile 所有活动 v3 worker，再恢复同步默认值。不得删除 packet、worker state、stage row、ledger、候选或预算证据；同一 request 可能存在两个 writer 时禁止回滚切换。

## 14 · 规范要求

- `DMP-001`：派发前持久化 keyed stage intent。
- `DMP-002`：每个 request key 与精确 body 最多发布一个不可变 packet。
- `DMP-003`：该 packet 最多计费启动一次。
- `DMP-004`：只有 HTTP waiter 结束时返回 pending，不得报失败。
- `DMP-005`：worker 结果未知时不得重派。
- `DMP-006`：轮询必须保持同一 AgentJob input fingerprint 与 stage-call ID。
- `DMP-007`：只接受身份精确绑定的终态输出。
- `DMP-008`：终态失败、取消和无效输出继续作为阻断证据。
- `DMP-009`：manager transport、独立审稿与 Core release 必须分开。
- `DMP-010`：普通 CI 不得运行真实模型。

## 15 · 验收与完成真实性

确定性验收必须覆盖 pending/result 轮询、派发崩溃恢复、并发发布、瞬时轮询故障、终态 worker state、keyed 无默认超时、过期 waiter 后收取结果、稳定 stage 身份和无重复计费。

真实验收还需要一次真实慢调用、精确预算对账、完整 REVISE、全新独立审稿，以及 Core 可见的未接受候选。工程完成不等于文学成功，也不等于生产稿已释放。
