# Semantic Execution Runtime · 让同一个语义契约跨 Chat、本地 Agent、API、MCP、Service 与人工保持不变

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>TRANSPORT-NEUTRAL</kbd>&nbsp;&nbsp;<kbd>PROVENANCE</kbd>&nbsp;&nbsp;<kbd>VALIDATE BEFORE CONSUME</kbd></p>

Semantic Execution Runtime 是冻结 semantic job 与合格 model / human invocation 之间的 transport layer。它的目的，是让 Quillframe 可以改变**判断在哪里执行、怎么传输**，却不改变**原来到底请求了什么判断**。

> **核心不变量 ✦** Transport 可以变；semantic identity、bounded input、rubric、output contract、permission 与 fingerprint 不能跟着 transport 静默改变。

## 01 · 输入契约

Execution 从一份已经由 generic semantic boundary 构建并验证过的 semantic job 开始。

Executor 收到：

- job / contract identity；
- exact semantic fingerprint；
- bounded input / context；
- rubric；
- output contract；
- permissions；
- independent requirement 等 execution constraint；
- source / session provenance reference。

Executor 即使技术上能看到更多 project context，也不能因此私自把它加进 prompt。

## 02 · Eligible execution family

Semantic job 可以通过以下方式执行：

- 独立 chat / peer relay；
- local Codex / Claude / 其他 agent invocation；
- provider API；
- local model endpoint；
- MCP / Control Plane worker；
- GitHub / service job；
- human reviewer。

Eligibility 来自当前 capability evidence 与 job constraint。

无论换什么 transport，同一 semantic contract 都应该保持可识别的同一问题。

## 03 · Direct execution 与 relay execution

### Direct execution

Runtime 可以直接调用 model / human endpoint，并在当前 orchestration path 中收到 typed result。

### Relayed execution

Manager 也可以把 semantic packet 发给另一个 chat、人或 external system，之后再收回 typed result。

Relay work 更需要 durable identity，因为 manager 不能靠“聊天上下文好像还记得”去证明返回结果到底属于哪个 frozen job。

## 04 · Independent gate execution

当 `independent_gate=true`，或者 owning workflow 另外要求 independence，execution 必须证明 separate invocation / session / worker identity。

以下做法不能满足 independence：

- 在同一个 manager invocation 里只换 system prompt；
- 让同一隐藏 reasoning process “扮演 critic”；
- 把 manager 全部 private context 原样复制给 reviewer；
- 不提供 execution provenance。

同一个 provider / model family 仍然可能合法，只要 invocation / session 真的独立，而且 packet 保持 bounded / blind。

## 05 · Execution provenance

Result 应保存真实 execution metadata，例如：

```yaml
source_session_id:
worker_session_id:
handoff_id:
attempt_id:
provider:
model:
transport:
```

具体字段取决于 runtime。Provenance 应足够验证 isolation / independence，但不能因此泄漏 credential 或 private reasoning。

## 06 · Typed-output boundary

Executor 请求的是 contract 指定的输出形状，不是任意长篇 prose。

模型内部可以按照 provider / runtime 支持的方式完成 reasoning，但 durable result 只保存 typed contract，以及 contract 明确要求、可观察、可审计的 concise evidence。

不要请求或持久化 private chain-of-thought。

如果模型把 JSON 包在额外 prose 里，adapter 只有在能够**确定性、且不改变语义**地归一化时才可以处理；否则 result 应判 invalid，并作为 execution issue 重试 / 修复。

## 07 · Binding validation

Owning workflow 把 result 当作 valid 之前，确定性验证至少检查：

- result schema / output contract；
- exact job / subject identity；
- exact semantic fingerprint；
- required worker / session / attempt provenance；
- permission / result-scope boundary；
- required evidence fields；
- 必要时的 forbidden leakage。

一个文学判断即使“看起来非常好”，只要回答的是错误 fingerprint，也必须判 invalid。

## 08 · Control Plane integration

分布式 / 长时间 execution：

```text
manager checkpoint
→ semantic handoff stored
→ eligible worker claims lease
→ worker executes frozen job
→ result + hash stored
→ manager validates semantic binding
→ named gate consumes once
→ workflow resumes
```

Lease / retry / idempotency 属于 infrastructure concern，不能改变 semantic verdict。

## 09 · Transport fallback

当 infrastructure failure，而 frozen semantic question 没变时，允许 fallback：

```text
adapter unavailable / crash / timeout / expired lease
→ preserve semantic fingerprint
→ 重新解析 eligible transport
→ 在别处执行同一个 frozen job
```

如果 bounded input、rubric、candidate 或 output contract 发生变化，就不能继续复用旧 fingerprint。

## 10 · Semantic rejection 不是 fallback 理由

合格 worker 返回的 valid typed reject / fail，本身就是一次**成功完成的 semantic execution**。

Owning gate 应消费该结果并路由 repair。

不能把“reviewer 不喜欢 artifact”谎称成 provider failure，然后不停换 route / reviewer 直到拿到 PASS。

## 11 · Human / Peer-chat execution

Human 和 peer-chat reviewer 遵守同一种概念契约：

- 收到 frozen subject + bounded context；
- 收到 rubric / output format；
- 不收到 hidden expected verdict / gold material；
- 返回带 required identity / fingerprint 的 typed result；
- 保存足够 provenance 证明 separate reviewer identity。

如果用户手工 relay packet，typed result 回来之前 manager 可以保持 `awaiting_user`。

## 12 · Provider adapter rule

Provider-specific adapter 应保持 thin。它可以把 generic semantic job 翻译成 provider request syntax，也可以归一化 provider response metadata。

它不能：

- 私自改 rubric；
- 静默扩大 context；
- 追加 permission；
- 改变 fingerprint 意义；
- 把 provider confidence 当 authority；
- 隐藏实际执行 judgment 的 model / runtime。

## 13 · Failure taxonomy

### `execution_unavailable`
当前没有 route 满足 job 的 capability / independence constraint。

### `execution_failed`
Eligible transport 在产生 valid result 前 crash / timeout / failure。

### `semantic_invalid`
返回结果没通过 schema / fingerprint / provenance / leakage validation。

### valid semantic outcome
满足 contract 的 typed PASS / FAIL / REJECT / diagnosis 等。

只有前三种属于 infrastructure retry / fallback 范畴。有效 negative semantic outcome 应进入 semantic repair。

## 14 · 不变量

1. Transport neutrality 必须保持 semantic identity。
2. Execution 不静默扩大 context 或 permission。
3. Independent gate 必须证明 separate execution identity。
4. Provider adapter 保持 thin。
5. Result 在 workflow consume 前先做 deterministic binding validation。
6. 只有 semantic question 未变时，infrastructure fallback 才能保持原 fingerprint。
7. Valid rejection 不是 provider failure。
8. Private chain-of-thought 不属于 durable contract。

## 15 · 相关契约

- [Semantic Worker Protocol](SEMANTIC_WORKER_PROTOCOL.zh-CN.md)：semantic job / result identity 与 permission。
- [Runtime Routing](../session_runtime/RUNTIME_ROUTING.zh-CN.md)：eligible route selection。
- [Runtime Capabilities](../session_runtime/RUNTIME_CAPABILITIES.zh-CN.md)：capability evidence。
- [Control Plane](../control_plane/CONTROL_PLANE.zh-CN.md)：handoff / lease / result persistence。
- [`semantic_worker_runner.py`](semantic_worker_runner.py)：确定性 execution / adapter boundary。
