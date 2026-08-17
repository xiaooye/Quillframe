# Plan 015 — Candidate Lineage

1. 冻结 current `main`、consumer pin 与 authority boundaries。
2. 复用现有 `quality_evolution` schema 与 semantic comparison contract，不创建平行 candidate system。
3. 在同一个 SQLite DB 中增加 lineage、review-receipt、opaque acceptance-evidence companion tables。
4. 实现 immutable lineage registration 与 exact fingerprint validation。
5. 实现 review receipt binding、typed semantic-result validation 与 stale-result rejection。
6. 实现 acceptance-evidence reference consistency，同时明确拒绝 authority verification 与 SETTLE authorization。
7. 在现有 evolution ledger 上增加 lineage-aware runtime facade；new candidate 必须显式提供 provenance，只要 run 中存在缺失/无效 lineage，就在 comparison 前 fail closed，同时保留 legacy v2 ledger API 的 compatibility。
8. 增加 versioned machine-readable schema、A-H deterministic tests、runtime bypass/recovery tests、legacy-vs-lineage ablation、migration/rollback docs 与 CI。
9. 运行 repository-wide compatibility/hygiene gates；遇到结构集成失败时修复集成，不削弱 gate。
10. 在 acceptance conditions 全绿前保持 draft PR；不得自动 repin consumer。
