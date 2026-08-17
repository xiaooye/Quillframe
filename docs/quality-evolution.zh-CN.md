# 质量演进

Quillframe Quality Evolution 是 revision 的 durable comparison ledger，不是 automatic rewriting authority。它记录 exact incumbent、challenger、comparison 时使用的 objective envelope，以及继续改写是否还在产生真实 gain。

## Incumbent / Challenger

Candidate 带 exact content fingerprint 进入；challenger 记录 direct comparison parent。Registered `quality.compare` 获得 incumbent、challenger、objective envelope 与 bounded evidence，再由 semantic judgment 选择 challenger / incumbent / tie。Deterministic layer 先验证 result 绑定 exact pair，再 consume-once。

## Objective Envelope

<img src="assets/concepts/objective-preserving-repair.zh-CN.svg" alt="Repair target 的改善受到稳定 objective envelope 约束" width="100%" />

Objective envelope 在 repair 前从 authorized Project/request evidence 中选择，防止局部润色把真正的 story/readership/character/pressure/reward 目标优化掉。它不能从 rejected realization text 重新推导。

## Candidate Lineage

Comparison ancestry 与 prose derivation 是两种关系。Repair 通常把 comparison parent 同时作为 prose parent；fresh regeneration 为了 evaluation 仍有 comparison parent，但 prose parent 必须为空，从而守住 contamination boundary。User edit 也显式记录 lineage，而不是当成无法追踪的 overwrite。

<img src="assets/concepts/candidate-lineage.zh-CN.svg" alt="Candidate lineage tree 分开 comparison ancestry 与 prose derivation，并显示 fresh regeneration 没有 prose parent" width="100%" />

## Regression Evidence

Repair-induced objective regression 记录“目标 defect 改好但 collateral harm 出现”；known-regression escape 记录已知 mechanism 没有在 expected stage 被发现。这些都是 diagnostic provenance，不是 Canon，也不授予 autonomous repair authority。

## Stopping

No-gain comparison 会累积 plateau state；challenger 胜出就成为新 incumbent。重复无收益可以终止 revision，避免无限 rewrite churn。Stopping rule 属于 execution policy，不会把未评审 artifact 自动变成 Accepted。
