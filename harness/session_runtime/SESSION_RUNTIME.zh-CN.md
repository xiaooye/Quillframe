# Session Runtime · 给执行过程持久身份，但绝不把聊天记忆误当成正典

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>SESSION ≠ RUN ≠ CHECKPOINT</kbd>&nbsp;&nbsp;<kbd>可恢复</kbd></p>

Session Runtime 让 Quillframe 能跨聊天回合、本地 Agent、外部 worker、等待、重试与进程重启保持一个可恢复的执行身份。它记录的是**工作执行到哪里**，不是“小说里什么是真的”。

> **核心不变量 ✦** Session / provider history 可以帮助恢复工作，但不会因为被保存下来就自动成为 Project authority。

## 01 · 身份模型

这些身份必须始终分开：

```text
project / resource
≠ session / thread
≠ run / invocation
≠ checkpoint
≠ external attempt / handoff
```

**Project / resource**：正在处理的持久小说或框架资源。

**Session**：带角色、生命周期和 memory policy 的可恢复执行容器。

**Run**：同一个 session 内的一次具体 invocation / execution episode。

**Checkpoint**：已经验证的 workflow cursor，以及安全恢复所需要的 fingerprint / precondition。

Provider-native conversation / thread / session ID 可以作为执行 metadata，但不能建立故事事实。

## 02 · Session role

参考 role：

- `manager`：拥有一个 primary task mode 与用户交互；
- `writer`：与 manager 分离时的受限写作 worker；
- `specialist`：任务范围内的模拟、研究、分析或实现 worker；
- `semantic_reviewer`：需要独立 semantic invocation / session 时的 reviewer identity；
- `human_reviewer`：人工或 peer-relay reviewer；
- `other`：只有明确 extension 才使用。

Role 只描述执行职责，不等于 authority。一个 worker 就算叫 `semantic_reviewer`，只要没有真正独立的 invocation / session、没有 bounded blind job，就不具备 independent review 条件。

## 03 · Memory policy

参考 memory policy：

`none | bounded | session | external | checkpoint_only`

Memory policy 只描述 runtime 可以保留什么，不代表下一次 prompt 自动收到什么。

每次 invocation 仍然必须遵守显式 Context Manifest / context policy。

Independent semantic work 通常使用 `none` 或 `bounded`：不要把 writer private reasoning、无关项目状态、hidden expected verdict、旧 reviewer verdict、regression answer key 一起塞给 reviewer，除非当前 rubric 明确需要某一小块受限证据。

## 04 · 生命周期状态机

参考 lifecycle：

```text
created → running
running → idle | awaiting_user | awaiting_external | completed | failed | terminated | stale
idle → running | completed | terminated | stale
awaiting_user → running | failed | terminated | stale
awaiting_external → running | failed | terminated | stale
failed → running | terminated | stale
completed → stale
stale → terminated
```

非法 transition 是确定性错误。

`semantic_pending` 通常属于 run 内某个 workflow / gate 的状态，不应为了它发明一个不存在的 session transition。

## 05 · Run identity

一个 run 至少应能回答：

- 属于哪个 session；
- 正在执行哪个 task mode；
- 目标 resource / project 是什么；
- 当前 workflow step / cursor；
- 哪些 input / artifact 已经冻结；
- 哪些 external result 仍 pending；
- 本次 invocation 最终以什么状态结束。

中断后的下一次 invocation 可以是同一个 session 内的新 run。

## 06 · Checkpoint

在“重复执行或忘记执行都会造成风险”的边界 checkpoint：

- Context Freeze；
- fingerprint-bound review 前冻结 candidate；
- 等待 user / external；
- consequential Project / Framework write 前；
- valid external result 完成绑定后；
- Canon settlement 前；
- 长时间 handoff / discovery / learning work 前。

一个有效 checkpoint 通常记录：

- session ID 与 run ID；
- workflow step / cursor；
- 相关 artifact ID / fingerprint；
- 当前 authority / lock reference；
- pending gate / event / handoff；
- 必要时的 approval / write-intent reference；
- resume policy；
- timestamp / version。

Checkpoint 不是把整段聊天序列化一份存起来。

## 07 · Resume 算法

Resume 是一次新的验证动作，不是“凭聊天记忆继续写”。

Automatic feedback Learning 本身也可能成为 pending runtime work。semantic capability 不可用时，durable feedback event/intake 保持 `awaiting_semantic`；后续 run 必须重新验证 event hash、registered semantic-job fingerprint、当前 Project/Framework authority/capability，以及 Learning consumer receipt，再 exactly-once 应用。Provider/chat history 永远不是 preference authority。

```text
加载 durable session + checkpoint
→ 重新验证 Framework / Project compatibility
→ 重新验证当前 authority 与 exact lock / bundle
→ 按当前状态重建 sparse context
→ 验证 referenced artifact fingerprint
→ 验证 approval / write precondition
→ 重新解析 pending external work 所需 capability
→ 如果有返回结果，则完成 binding / validation
→ 验证 logical result / side effect 尚未被消费
→ 从保存的 workflow cursor 继续
```

只要任何关键 binding 发生实质变化，就应该停止或路由 repair，而不是在 stale assumption 下静默继续。

## 08 · Side-effect 安全

Session persistence 必须能面对现实中的 at-least-once delivery，而不造成逻辑副作用重复。

必须区分：

```text
worker / result delivery
≠ result validation
≠ logical result consumption
≠ downstream side effect
```

重复收到完全相同的 result，可以识别成 already consumed；同一个 logical identity 却收到不同 result hash，则必须硬停止。

Consequential write 仍然需要自己的 before-state、idempotency 与 post-condition 语义；session state 本身不能让一次写入自动安全。

## 09 · Chat 是一等 runtime

普通当前聊天可以直接担任 manager session。另一个独立 chat 可以承担 independent semantic review，只要它只收到 bounded blind packet，并返回绑定 exact semantic / artifact fingerprint 的 typed result。

当前 chat 没有 subprocess / API key，不代表整个 Harness 所有路径都不可用。进入 `semantic_pending` 前，Runtime Routing 应先检查当前真实连接 / 声明的其他 eligible route。

需要用户手工转发的 peer-chat relay 在等待期间可以进入 `awaiting_user`。

## 10 · 本地 Agent / Service session

Codex、Claude Code、本地模型、MCP worker、provider API、GitHub / service job 等，只要 capability 得到证明，都可以承载 manager 或 worker session。

Manager 与 reviewer 即使使用同一个 CLI 家族，只要 reviewer 是真正不同 invocation / session、上下文受限，而且没有泄漏 verdict / gold material，仍然可以满足 independence。

Runtime family 不是 session identity。

## 11 · Persistence 边界

`session_runtime.py` 负责确定性验证 session / run / checkpoint object 与 lifecycle。

Control Plane 负责共享 operational state，例如 event、handoff、lease、result hash 与 consume-once receipt。

Provider-native memory 可以作为 execution metadata 引用，但不能成为安全 resume 所依赖的唯一 durable record。

## 12 · 失败语义

以下情况应停止或进入明确失败状态：

- session / run / checkpoint identity 无法对齐；
- artifact fingerprint 非预期变化；
- approval / write precondition 已 stale；
- pending external result 无法绑定冻结 job；
- 无法证明某个 side effect 是否已经执行；
- 当前 capability 已不能满足 pending work；
- reviewer packet 无法维持所需 independence / context isolation。

不要从“聊天里好像说过”反推出缺失 truth。

## 13 · 不变量

1. `project/resource != session != run != checkpoint`。
2. Provider-native ID 是 metadata，不是 authority。
3. Persistent memory 不等于自动 prompt injection。
4. Resume 必须重新验证当前 authority 与 capability。
5. 已完成的 logical effect 不重复执行。
6. Checkpoint 保存受限恢复状态，不保存 private reasoning transcript。
7. Session state 永远不授予 Canon / Framework write authority。
8. Gate 要求 independent review 时，就必须有独立 execution identity。

## 14 · 相关契约

- [Harness Agent](../HARNESS_AGENT.zh-CN.md)：manager execution policy。
- [Orchestration Protocol](../ORCHESTRATION_PROTOCOL.zh-CN.md)：mode graph 与 checkpoint boundary。
- [Runtime Routing](RUNTIME_ROUTING.zh-CN.md)：基于 capability 的 backend selection。
- [Control Plane](../control_plane/CONTROL_PLANE.zh-CN.md)：共享 event、handoff、lease 与 receipt。
- [上下文与记忆](../../docs/context-and-memory.zh-CN.md)：context / memory authority boundary。
