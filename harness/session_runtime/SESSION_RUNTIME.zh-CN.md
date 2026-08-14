# Session Runtime · v7 中文版

## Identity

NovelForge 严格区分：

`project/resource != session/thread != run/invocation != checkpoint`

Session 是可恢复执行身份；Run 是 session 内的一次 invocation；Checkpoint 是经过验证的 workflow cursor。

Provider-native chat/thread/session ID 只是可选 metadata，永远不是 Project authority。

## Session Roles

- `manager`：协调一个 task mode 与用户交互；
- `writer`：需要独立时的 bounded production worker；
- `specialist`：task-scoped analysis/simulation/research；
- `semantic_reviewer`：独立审计，默认 fresh-per-fingerprint；
- `human_reviewer`：human/peer relay identity；
- `other`：显式 extension。

## Memory Policies

`none | bounded | session | external | checkpoint_only`

Persistent memory 不等于自动 prompt context。每次 invocation 仍需要明确 Context Manifest / worker context policy。

Independent reviewer 使用 `none|bounded`；hidden gold、writer private reasoning、prior expected verdict 与无关 project state 不得进入。

## State Machine

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

非法 transition 是 deterministic error。

## Checkpoints

这些稳定边界应 checkpoint：
- Context Freeze；
- independent review 前冻结 candidate；
- external/user wait；
- consequential write 前；
- valid external result bind 后；
- Canon settlement 前。

Checkpoint 至少记录 run ID、workflow step、relevant fingerprints、pending gate/handoff、resume policy 与 timestamp。

## Resume

Resume 时：
1. load durable session/checkpoint；
2. 验证 framework/project compatibility；
3. 根据当前 project authority 重建 sparse context；
4. 验证 referenced artifact fingerprints；
5. 验证 approval/write preconditions；
6. 如有 pending result，完成 binding；
7. 确保 logical result / side effect 不被重复应用；
8. 从保存步骤继续。

## Chat Sessions

普通 Chat 是一等 runtime。当前 chat 可以是 manager；独立 chat 只有在收到 bounded blind packet 并返回 typed fingerprint-bound evidence 时，才能作为 independent reviewer。

当前 chat 没有 subprocess/API key，不等于整个 Harness 自动 blocked。

## Local Agent Sessions

Codex/Claude/local agent 可以跑完整 manager 或 bounded worker。即使使用同一 CLI/provider，mandatory independent review 也需要 separate invocation/session。

## Durable Persistence

`session_runtime.py` 负责 session object/lifecycle deterministic validation；Control Plane 负责共享 operational state、events、handoffs、leases 与 consumption receipts。

Session state 永远不会授予 Canon authority。
