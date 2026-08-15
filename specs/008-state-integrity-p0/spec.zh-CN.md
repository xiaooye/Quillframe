# 008 · State Integrity P0 — Property Ownership 与 Propagation Debt

## 状态
Generic NovelForge 的 Draft implementation spec。此分支在形成正式 release 并被下游 Project 显式 pin 之前，**不具任何下游 Project authority**。

## 证据
- #69：外部 Codex 系统证明“可编辑字段 / 派生字段”边界有价值，也暴露了同一 property 同时允许人工编辑与 agent 推导写入时的 last-write-wins 双 writer 问题。
- #63：外部长篇系统会追踪上游变化后的 downstream propagation debt；NovelForge 当前已要求 dependency impact，但没有通用 durable debt lifecycle。

## 问题
NovelForge 已经区分 Canon、Accepted artifact、Settlement、derived memory、runtime state、plan 与 proposal，但还缺两个 deterministic contract：

1. Project 无法在 property 粒度机器声明：哪个 writer class 可以 direct mutation，哪个必须走 proposal / Settlement / reconcile。
2. authoritative upstream change 发生后，dependency impact 没有通用的 `open → discharged` 生命周期。

## 不变量
- 模型推断不会获得 write authority。
- capability/tool availability ≠ authority。
- policy resolver 是 deterministic 的；配置后的 Project policy 可以对 **write route** 作权威解析，但 resolver 永远不授予 Canon / Framework-write authority，也不判断 value 是否为真。
- 未配置 property policy 的旧 Project 保持现有 object-level behavior。
- 同一 property 不得静默拥有两个 authoritative writers。
- `settlement_only` 仍由 Settlement 提供 authority transition。
- derived state 始终 `authority=false` 且 source-bound。
- 后续 propagation debt 只是 derived work ledger，不是 Canon。
- 禁止 global invalidation 与自动重写正文。

## Stage A — #69 Property write-source policy
Project 可选地通过 `paths.property_write_policy` 指向 UTF-8 JSON policy，schema 为 `novelforge_property_write_policy_v1`。

解析优先级：

`global default → object-type default → exact property override`

Mutation classes：
- `user_declared`
- `settlement_only`
- `derived_only`
- `proposal_only`
- `runtime_only`
- `locked`
- `mixed_reconcile`

Deterministic resolver 只返回 route：

`allow_direct | proposal_required | settlement_required | reconcile_required | deny | legacy_unmanaged`

它不判断候选 value 是否为故事真相。

## Stage B — #63 Propagation debt
Stage A 稳定以后，再增加 non-authoritative debt ledger：把 upstream before/after fingerprint 与明确 dependent artifact、required action (`revalidate|rebuild|replan|resimulate|human_review`) 绑定。只允许 explicit dependency evidence 开 debt，只允许 fingerprint-bound result evidence discharge。

## 兼容性
Stage A 不升级 Project schema version。没有 `paths.property_write_policy` 时返回 `legacy_unmanaged`，保持旧行为；一旦显式配置，文件缺失或 invalid 则 policy resolver fail closed。

## 验收
- deterministic self-tests + public CI green；
- Framework manifest 可发现 schema/tool；
- host payload 不能自我提权；
- broad defaults 避免 per-field ACL forest；
- exact policy fingerprint 可观察；
- #69 语义稳定前不实现 #63。
