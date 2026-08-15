# 010 · 创作决策来源与未决选择权

## 状态

NovelForge General Craft 的实现候选。外部系统只作为机制证据，不具有权威。

## 问题

NovelForge 已能维护 active plan、探索 scenario fork、在因果证据变化后 `plan.reconcile`，以及通过 propagation debt 追踪下游待重核工作；但还没有一个一等 artifact 表达：

> “这个重要选择目前故意未决；谁有权决定；有哪些有限候选；最终为什么选了某项；旧决定后来如何被替代。”

缺少该边界时，writer/revision run 可能为了完成正文而擅自把作者拥有的选择写死。之后系统即使知道“计划现在是什么”，也可能丢失重要选择的可见理由、被拒绝方案、已接受风险与 supersession 历史。

## 外部机制证据

- `notnotype/neuro-book@306e563ad7a4d4a58354fa8d582ad9aa9b886e8c`：open/decided 决策、候选、理由、风险、依赖引用与 supersession 历史。
- `github/spec-kit@bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`：持久 `[NEEDS CLARIFICATION]`、planning 前显式澄清、带理由/open questions 的 decision record，以及重要未知未解决时阻止继续。

反例：普通局部措辞与低成本 prose choice 不应 ADR 化，不得强迫所有创作动作登记 decision artifact。

## 必须机制

portable `creative_decision` artifact 必须：

1. 具有稳定 `decision_id`、scope、有限问题、resolver policy、候选、dependency/served refs 与 source fingerprints；
2. 生命周期为 `open | decided | superseded | dropped`；
3. writer 可以发现并登记 open question，但不能因此获得 resolution authority；
4. `open -> decided` 仅允许 resolver policy 明确授权的 actor，且必须匹配 exact before-version/fingerprint；
5. decided 状态只保存简短、用户可见的 outcome / rationale / rejected alternatives reasons / accepted risks；禁止保存模型私有 chain-of-thought；
6. supersession 必须显式链接 successor，保留旧决定与旧 rationale，不做破坏性覆盖；
7. 决策变化只输出 downstream revalidation candidates，不自动修改 active plan，也不自动创建 propagation debt；
8. artifact 永远不是 Canon/Settlement：自身不能写 Project state、Canon、Framework behavior 或 Settlement。

## Context 隔离

- `writer` 看到 open decision 时只获得 unresolved question + `DO_NOT_RESOLVE` 警告，默认隐藏 alternatives；
- `planner` 可以查看 alternatives 与 decision provenance；
- `reader` / `character` projection 完全隐藏 planning decision；
- `decided` 结果不重复注入 writer decision context；正常执行仍由 active plan 承载。

## 兼容性

该机制是 provider-neutral JSON artifact，不新建 session store、plan store、scenario store 或 Canon DB。持久化位置由 consuming Project/host 决定。未启用的既有 Project 行为不变。

## 评估

deterministic regressions 必须证明：

- writer 无法擅自 resolve author-owned open decision；
- authorized resolution 绑定 CAS/fingerprint；
- future alternatives 不泄漏给 writer/reader/character；
- resolution 后保留简短 provenance；
- supersession 保留旧 resolution，并要求明确 successor lineage；
- scope mismatch/tamper fail closed；
- decision change 只输出 revalidation candidates，不自动创建 #63 debt 或改 plan；
- rollback 不重解释任何 Canon/Settlement 状态。

正式 promotion 前仍需 General Craft capability/regression eval 与 exact-head Framework CI 全绿。
