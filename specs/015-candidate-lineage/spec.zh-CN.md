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
11. 通过 `quality/candidate_lineage.schema.json` 暴露 machine-readable projection；schema 使用 JSON Schema draft 2020-12，版本 identity 为 `novelforge_candidate_lineage_v1`。
12. 新的 lineage-aware evolution 必须通过 `quality/candidate_lineage_runtime.py` 执行；只要 run 中存在缺失或无效显式 lineage 的 candidate，就必须在 comparison/consumption 前 fail closed。Legacy `quality_evolution.py` 继续保留用于兼容，但不能静默满足 lineage-aware runtime contract。

## 非目标

- 不为 prose candidate 创建 Git branch。
- 不自动选 winner。
- 不从 latest/incumbent/review pass 推断 Accepted。
- 不写 Canon/Settlement。
- 不创建第二套 objective-preservation system。
- 不新增第二个 ColdRead agent。
- 不为 legacy 或 crash-partial candidate 猜测 lineage。

## 兼容性

Migration 对现有 quality-evolution SQLite DB 只做 additive extension。现有 caller 保持有效；历史 provenance 不猜测。Consumer 不自动 repin，也无需被静默迁移。

Machine-readable schema 只描述 lineage candidate view、durable graph projection 与 SETTLE reference-consistency receipt；它本身不授予任何 authority。

Lineage-aware runtime 是现有 core ledger/comparator 上的 facade。如果 legacy caller 创建了没有 lineage 的 candidate，core row 仍保持兼容，但 lineage-aware runtime 会报告 `MISSING_LINEAGE`，并在 exact provenance 被显式补齐之前拒绝 comparison。这样可以同时保留 compatibility 与 fail-closed provenance semantics。

## 验收标准

`docs/CANDIDATE_LINEAGE_V1.zh-CN.md` 中 A-H deterministic tests 通过；legacy-vs-lineage ablation 证明 representation gap 被消除且 incumbent selection 不变；lineage-aware runtime test 证明 direct legacy/bypass insertion 会被检测并阻断 comparison，直到显式恢复；`quality/candidate_lineage.schema.json` 可解析且 identity 为 `novelforge_candidate_lineage_v1`；repository hygiene 与相关 CI 通过；任何 authority boundary 均不得变弱。
