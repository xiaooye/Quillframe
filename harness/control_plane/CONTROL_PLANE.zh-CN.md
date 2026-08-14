# Control Plane · 让跨 invocation 的工作可以可靠持久化、重试和恢复

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>EVENT</kbd>&nbsp;&nbsp;<kbd>LEASE</kbd>&nbsp;&nbsp;<kbd>CONSUME-ONCE</kbd></p>

NovelForge Control Plane 是跨 invocation / process 工作的持久 operational substrate。它保存 session、typed event、bounded handoff、worker lease、result hash 与 logical consume-once receipt，让外部工作即使遇到重试、中断和进程重启，也不会靠猜测判断“之前到底做没做完”。

> **边界 ✦** Control Plane 回答的是：**工作现在在哪里、哪个 attempt 正在拥有它、某个 result 是否已经被逻辑消费。** 它不判断故事事实，也不判断文学质量。

## 01 · Operational graph

一个 distributed work item 通常经过：

```text
project / resource
→ manager session + checkpoint
→ typed event / bounded handoff
→ worker claim / lease
→ attempt executes
→ result stored + hashed
→ manager validates binding
→ named consumer records receipt
→ owning workflow resumes
```

这些记录是 execution evidence，不是 Canon evidence。

## 02 · Control Plane 负责什么

Control Plane 可以持久保存：

- session 与 operational version；
- typed internal / external event；
- handoff / job；
- worker attempt identity；
- lease 与 expiry；
- result payload hash；
- consume-once receipt；
- timestamp 与 trace metadata；
- retry / reclaim bookkeeping。

它不拥有：

- story direction；
- Accepted Canon；
- Canon settlement decision；
- literary verdict；
- durable user taste；
- Framework promotion authority；
- model reasoning。

## 03 · Typed event

Event class 应保持窄而无权威，例如：

- resume request；
- semantic job / result arrival；
- eval request / result；
- maintenance request；
- research refresh；
- feedback observation；
- acceptance observation。

Generic event 不能意味着“静默写 Canon”“自动继续下一章”“自动把某条规则晋升进 Framework”。这些行为都需要独立 authority、precondition 与 user-visible workflow semantics。

### Idempotency

现实中的 event delivery 应按 at-least-once 考虑：

- 同一 idempotency key + 同一 payload → 安全重复；
- 同一 idempotency key + 不同 payload → hard conflict。

不要假装网络天然提供 exactly-once delivery。

## 04 · Bounded handoff

Handoff 只传 worker 真正需要的东西：

```yaml
handoff_id:
source_session_id:
target_worker_class:
resource_id:
task_or_gate:
artifact_refs: []
input_fingerprints: []
instructions:
context_policy:
permissions:
return_contract:
relay_or_native_refs:
```

默认规则：**不要复制整个 manager conversation。**

Canon write、Framework promotion、durable-taste write 等高权威 permission 默认保持 false，除非另有明确 authority path。绝大多数 semantic / research worker 都不应该拿到这些权限。

## 05 · Lease 与 Attempt

Queued worker 通过原子操作 claim 一段有时限的 lease。

Lease 至少建立：

- current attempt identity；
- current owner；
- claim time；
- expiry / recovery semantics。

只有 active lease owner 可以完成当前 attempt。如果 lease 过期、任务被另一个 worker reclaim，旧 worker 之后不能再覆盖新 owner 的有效 result。

Lease expiry 是 infrastructure state，不是 semantic judgment。

## 06 · Completion 与 Consumption 不是同一步

Worker 完成工作，不等于 result 已经被应用。

```text
worker completes
→ result payload stored
→ deterministic payload hash recorded
→ manager / gate validates job + fingerprint + provenance
→ named logical consumer records receipt
→ downstream workflow effect occurs once
```

这层区别决定了 retry / resume 能不能安全。

完全相同的 duplicate 可以返回“already consumed”；同一个 logical source / consumer 却出现不同 result hash，必须 hard stop，而不是 last-write-wins。

## 07 · Exactly-once 指“逻辑应用一次”

NovelForge 的 consume-once 语义针对的是**下游逻辑应用**，不是宣称 transport message 一定只送达一次。

这样才能正确容忍：

- webhook / event 重复送达；
- worker 在 acknowledgement 不确定时重试；
- process restart；
- manager resume；
- lease expiry 后 queue reclaim。

安全条件是：一个已经验证的 logical result / side effect 不会被应用两次。

## 08 · Semantic job 经过 Control Plane

Semantic handoff 携带冻结的 semantic job / fingerprint。Worker 返回 typed result，manager 再验证：

- job identity；
- semantic fingerprint；
- worker / session / attempt provenance；
- output schema；
- permission boundary。

Control Plane 负责保存与运输这些 evidence，但不负责判断正文好不好。

有效 `semantic_reject` 应作为有效 semantic result 保存，并送回 owning repair mechanism。

## 09 · MCP / Service transport

本地 reference MCP transport 可以使用 stdio。Remote service transport 则应正常实施 authentication、origin / session isolation 与 network-security requirement。

MCP tool 暴露的是受限 operational capability。即使 MCP 里存在某个“write” tool，也不会自动制造 Canon authority。

切换 transport 时，应保持相同 job / handoff / result identity，避免“换传输方式”变成“换了语义问题”。

## 10 · Chat、本地 Agent、CI 与 Service

不同 host 可以参与同一 operational model：

- chat manager 可以打包 peer relay；
- local Codex / Claude 可以执行 bounded job 或连接 stdio MCP；
- GitHub / service worker 可以把外部事件归一成 typed handoff；
- remote worker 可以 claim lease；
- normal CI 可以测试 lifecycle / idempotency / contract，而不调用付费模型。

Host 多样性不会改变 authority semantics。

## 11 · Failure 与 Recovery

Infrastructure failure 可能导致：

- attempt failure；
- lease expiry；
- handoff reclaim；
- transport fallback；
- 没有 eligible route 时进入 `awaiting_external` / `semantic_pending`。

恢复时，必须先重新验证冻结 identity / fingerprint，再消费返回结果。

禁止：

- 旧 lease owner 覆盖新 owner；
- result binding 不匹配却因为“看着像正确答案”就消费；
- 没有 precondition / receipt 证据时重复 consequential side effect；
- 把 timeout 当 semantic reject。

## 12 · Authority boundary

Control-plane arrival 永远不会抬高 authority。

以下内容单独到达时仍然无权威：

- webhook；
- scheduled task；
- MCP request / result；
- worker handoff / result；
- GitHub / service event；
- CI status；
- semantic verdict；
- learning candidate；
- acceptance observation。

观察到“用户已经 acceptance”可以触发 settlement workflow，但不会绕过项目正常 authority / precondition 自动执行 settlement。

## 13 · 不变量

1. Operational persistence 与 story authority 分离。
2. Event 有类型、有 idempotency。
3. Handoff 保持 bounded，默认不复制 manager 全部上下文。
4. Lease 建立 attempt ownership 与安全 reclaim 语义。
5. Completion 与 logical consumption 分离。
6. Exactly-once 指 logical application，不指 transport delivery。
7. Result 在消费前验证 identity / fingerprint / provenance。
8. Control-plane data 本身绝不授予 Canon / Framework / taste-write authority。

## 14 · 相关契约

- [Session Runtime](../session_runtime/SESSION_RUNTIME.zh-CN.md)：session / run / checkpoint identity。
- [Runtime Routing](../session_runtime/RUNTIME_ROUTING.zh-CN.md)：选择 eligible execution path。
- [Semantic Worker Protocol](../semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)：typed semantic job / result。
- [正典与状态模型](../../core/CANON_STATE.zh-CN.md)：独立的 settlement transaction 与 authority。
