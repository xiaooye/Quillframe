# 008 · State Integrity P0 — Property Ownership 与 Propagation Debt

## 状态
Generic NovelForge 的 Draft implementation。只有未来正式 merge、bundle、attest，并被下游 Project 显式 pin 后，才可能成为该 Project authority。

## Evidence / overlap
- #69：外部 editable Codex 证明字段 ownership 有价值，也暴露同一 property 多 writer 的 last-write-wins 问题。
- #63：外部长篇系统会追踪上游变化后的 downstream propagation debt。
- NovelForge 当前已经拥有 object/fact authority、Settlement、derived memory invalidation、state-graph contradiction detection、quality-evolution ledger 与 resume preflight；P0 只能扩展这些边界，不能复制第二套。

## Stage A · Property write-source policy (#69)
Project 可选地通过 `paths.property_write_policy` 使用 `novelforge_property_write_policy_v1`。

解析：`global default → object-type default → exact property override`

Mutation classes：
`user_declared | settlement_only | derived_only | proposal_only | runtime_only | locked | mixed_reconcile`

Routes：
`allow_direct | proposal_required | settlement_required | reconcile_required | deny | legacy_unmanaged`

Resolver 可以权威解析 write route，但不判断故事真相，也不授予 Canon / Framework-write authority。未配置 policy 的旧 Project 保持原有 object-level behavior。

## Stage B · Propagation debt (#63)
`harness/propagation_debt.py` 是 deterministic SQLite work ledger，schema 为 `novelforge_propagation_debt_v1`。

开 debt 必须由 caller 提供：
- upstream source exact before/after fingerprint；
- source-change evidence ref + fingerprint；
- source authority（`locked|accepted|settled|active_plan`）；
- 一个明确 dependency edge ref + fingerprint；
- dependent artifact ref + 当前 fingerprint；
- required action：`revalidate|rebuild|replan|resimulate|human_review`；
- bounded reason。

没有 dependency edge 就不开 debt；source fingerprint 没变也不开。Runtime 不会扫描整个 Project 猜 dependent，更不会自动执行 repair。

Debt identity 由 source change + exact dependency/dependent fingerprint + required action deterministic 生成。相同 identity retry 幂等；同 identity 却换 evidence/reason 则 fail closed。

Lifecycle：
`open → discharged | superseded | waived_with_evidence`

Discharge 必须绑定 debt 最新 source fingerprint、exact required action、result ref/fingerprint 和 resulting dependent fingerprint。Supersede 必须显式发生，且新 debt 的 source-before 必须连续接上旧 debt 的 source-after。Waive 必须有 evidence，不允许静默 dismiss。

Ledger 始终 `authority=false`，不是 Canon、不是第二 dependency graph、也不是 repair executor。Open debt 默认不成为全局 resume blocker；只有具体 workflow 明确声明 debt-free precondition 时才阻断，普通 resume 仍由 `resume_preflight.py` 管理。

## Stage A / B 关系
授权的 state/plan mutation 完成后，caller 可以根据 Project 显式 dependency evidence 开 downstream debt。Property policy 回答 **谁/哪条 route 可以写**；propagation debt 回答 **哪些已知 dependent work 因此 stale**。两者互不授予 authority，也都不能绕过 Settlement。

## Compatibility / rollback
- 不升级 Project schema version。
- 未配置 property policy → 保持 `legacy_unmanaged`。
- Propagation debt 默认存于新的 derived runtime DB `.novelforge/propagation-debt.db`；删除/重建它不会改 Canon。
- Revert P0 不会重解释既有 Project/Settlement 数据。

## 验收
- dedicated public CI + full NovelForge CI 全绿；
- promotion 前 Framework manifest 可发现 exact schema/tool；
- no global invalidation、no automatic prose regeneration；
- restart/retry 幂等；
- exact diff 不夹带无关 Studio/site；
- 下游 Project 在未来显式 migration 前继续使用旧 lock。
