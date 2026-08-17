# Candidate Lineage v1

状态：Framework 结构扩展；仅属于 derived/provenance 层，不拥有权威写入权限。

## 问题

`quality/quality_evolution.py` 已经拥有 incumbent/challenger 比较语义。现有 `parent_candidate_id` 表示**比较血缘**：challenger 与当前 incumbent 比较。但这不总等于**正文派生血缘**。repair 通常复用 parent prose；fresh regeneration 则必须避免消费被拒/incumbent 正文，即使它仍然需要与该 incumbent 比较。

## 决策

Candidate Lineage 是现有 quality-evolution ledger 上的 additive projection。它不创建第二套 comparator、objective system、Canon system、settlement system，也不为每个正文 candidate 创建 Git branch。

记录：
- `origin = draft | repair | fresh_regeneration | user_edit`；
- `comparison_parent_candidate_id`，镜像现有 evolution parent；
- `prose_parent_candidate_id`，fresh regeneration 必须为 null；
- creator run/session provenance；
- 可选 authority-snapshot/diff fingerprint；
- 与单一 candidate exact fingerprint 绑定的 semantic review receipts；
- 与单一 candidate exact fingerprint 绑定的 opaque external acceptance-evidence reference。

所有记录均保持 `authority=false`。

## Authority 边界

Candidate Lineage 不能接受 candidate、不能认证外部事件确实构成 authoritative user acceptance、不能写 Canon/Settlement、不能从 comparison victory/latest status/review pass/user silence 推断 Accepted，也不能改变 `quality.compare` 的 winner semantics。

`bind_acceptance_evidence()` 只保存 opaque reference。它要求 exact candidate fingerprint、authority source reference、receipt fingerprint 与 timestamp，但始终保留 `authority_verified=false`、`settlement_authorized=false`。

`check_settlement_reference_consistency()` 只返回 `REFERENCE_MATCH` 或 `REFERENCE_MISMATCH`；始终 `settlement_authorized=false`，并要求外部 authority verification。真正 authority 仍由 Project/User Gate + SETTLE 拥有。

## Migration 与 rollback

迁移在同一个 quality-evolution SQLite DB 中 additive + lazy 创建：
1. `evolution_candidate_lineage`
2. `evolution_review_receipts`
3. `evolution_acceptance_evidence`

不重写现有 core tables。历史 derivation 或 Accepted state 不得在 backfill 时猜测。Rollback 是停止调用该 projection，并可选删除三个 companion tables；核心 candidate/comparison state 与 Canon 均不受影响。

## Runtime 语义

| Origin | Comparison parent | Prose parent |
|---|---|---|
| draft | null | null |
| repair | current incumbent | same parent |
| fresh_regeneration | current incumbent | null |
| user_edit | current incumbent | exact source when known |

这样 fresh realization 可以挑战 incumbent，同时不继承被拒正文。

## 必须验证

A. Draft A -> repair A1 的 prose parent 精确为 A。  
B. A1 -> fresh A2 保留 comparison ancestry，但 prose parent 为 null。  
C. A 的 review 不能验证 A1。  
D. A1 的 acceptance evidence 不意味着 A2 Accepted，也不能自行认证 A1。  
E. stale review 被失效。  
F. challenger 输掉现有 `quality.compare` 时 incumbent 保留。  
G. Resume 可从 durable state 精确重建 lineage。  
H. Settlement reference 必须匹配外部引用的 exact fingerprint，但 lineage 层永不授权 SETTLE。

`quality/candidate_lineage.py self-test` 覆盖 A-H。`evals/candidate_lineage_ablation.py` 验证 legacy representation 的歧义被消除，同时新增 semantic calls = 0，且 incumbent selection 不变。这是 architecture/provenance ablation，不是文学质量提升证明。

## 同一研究中的 Cold Read 决策

本次不增加第二个 mandatory ColdRead agent。当前 NovelForge 已有隔离 creator-private context 的 production Blind Reader，以及 fresh independent holistic production review。外部 OSS evidence 支持 cold read 有价值，但再增加一个 always-on reviewer 会重叠 semantic ownership 并提高成本。只有当 ablation 证明存在当前 Blind Reader + continuity + independent production review 捕捉不到的独立 miss class，例如 repair seams 或 book-level accumulated-state failure，才重新评估。
