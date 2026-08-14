# Runtime Control Plane · v7 中文版

## 目的

Control Plane 是 NovelForge 面向 session、event、handoff、worker lease、result hash 与 logical consume-once receipt 的 durable operational substrate。

它回答的是：**工作做到哪里、queued attempt 当前由谁拥有**。它不决定故事事实。

```text
project/resource
→ session/run/checkpoint
→ typed event / bounded handoff
→ lease / worker attempt
→ result
→ validation
→ consume-once receipt
→ resume
```

## Authority Boundary

Control-plane data 只属于 operational evidence。它本身不能：
- 建立 Accepted Canon；
- settle project state mutation；
- promote framework behavior；
- 覆盖 durable user taste；
- 授权 story direction。

Webhook、MCP、CI、schedule、connector、queue arrival 都不会提升 authority。

## Durable Semantics

Reference backend 使用 stdlib SQLite。

必须具备：
- transactional writes；
- 需要时 optimistic session version；
- event idempotency key；
- atomic handoff claim；
- bounded lease + expiry recovery；
- result payload hash；
- exactly-once **logical consumption** receipt。

Exactly-once 指 downstream application bookkeeping，不是假装网络 delivery 天然 exactly once。

## Typed Events

允许的 event class 刻意保持窄：resume request、semantic request/result、eval request、maintenance request、research refresh、feedback observation、acceptance observation。

Unattended Canon write、settlement apply、自动下一章 drafting、framework promotion 不是 generic event type。

相同 idempotency key + 相同 payload 的重复 delivery 是安全的；同 key 不同 payload 是 hard conflict。

## Handoffs

Handoff 只携带 bounded identity/context：
- source session；
- target worker/session class；
- resource/task identity；
- artifact refs/fingerprints；
- bounded instructions；
- context policy；
- permissions；
- return contract；
- optional native/relay refs。

默认不得复制 manager 整段 conversation。

Canon/framework-promotion/durable-taste write 等高 authority 权限在 generic worker handoff 中必须保持 false。

## Leases

Worker 原子 claim 一个 bounded lease。只有当前 lease owner 可以 complete。过期任务可以被重新 claim；旧 owner 失去 lease 后不能再覆盖新 owner 结果。

## Result Consumption

Completion 与 application 分开：

```text
worker completes
→ result stored + hashed
→ manager/gate validates binding
→ named consumer records receipt
→ downstream side effect occurs once
```

相同 result 重复投递返回 already-consumed；同 logical source/consumer 却出现不同 hash 时 hard stop。

## MCP

本地 reference transport 是 stdio MCP。未来 remote service 使用 Streamable HTTP，并执行正常 auth/origin/session protection。

Control-plane MCP tools 暴露 operational capability，不暴露无条件 Canon-write tool。

## Chat / Local / CI

- Chat session 可通过 connected/relay transport 接入；
- Local Codex/Claude 可用 CLI 或 stdio MCP；
- GitHub/service job 可以把外部 event normalize 成同一 event/handoff contract；
- Normal CI 只验证 infrastructure，不调用付费模型。

> 大胆持久化 execution state，保守授予 authority。
