# Spec 015 — Candidate Lineage

## 目标

让 prose candidate 的派生关系可检查、可按 fingerprint 追溯，同时不替换 NovelForge 现有 quality evolution、authority、Canon、semantic comparison 或 settlement 机制。

## 必须行为

1. `quality_evolution` 继续作为唯一 incumbent/challenger ledger，`quality.compare` 继续拥有 semantic winner 判断。
2. 区分 comparison ancestry 与 prose derivation ancestry。
3. 支持 `draft | repair | fresh_regeneration | user_edit`。
4. repair 的 prose parent 必须是 direct comparison parent。
5. fresh regeneration 必须保留 comparison parent，但 prose parent 必须为空。
6. semantic review receipt 必须绑定单一 exact candidate fingerprint，stale/cross-candidate reuse 必须拒绝。
7. 只允许保存 opaque external acceptance-evidence reference；lineage 层不得认证 user acceptance，也不得授权 SETTLE。
8. Resume 必须从 durable state 精确重建 lineage。
9. 不新增 Writer context，不新增 mandatory semantic call。
10. 所有 lineage/evidence 记录保持 `authority=false`。

## 非目标

- 不为 prose candidate 创建 Git branch。
- 不自动选 winner。
- 不从 latest/incumbent/review pass 推断 Accepted。
- 不写 Canon/Settlement。
- 不创建第二套 objective-preservation system。
- 不新增第二个 ColdRead agent。

## 兼容性

Migration 对现有 quality-evolution SQLite DB 只做 additive extension。现有 caller 保持有效；历史 provenance 不猜测。Consumer 不自动 repin，也无需被静默迁移。

## 验收标准

`docs/CANDIDATE_LINEAGE_V1.zh-CN.md` 中 A-H deterministic tests 通过；legacy-vs-lineage ablation 证明 representation gap 被消除且 incumbent selection 不变；repository hygiene 与相关 CI 通过；任何 authority boundary 均不得变弱。
