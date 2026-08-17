# Plan 015 — Candidate Lineage

1. 冻结 current `main`、consumer pin 与 authority boundaries。
2. 复用现有 `quality_evolution` schema 与 semantic comparison contract，不创建平行 candidate system。
3. 在同一个 SQLite DB 中增加 lineage、review-receipt、opaque acceptance-evidence companion tables。
4. 实现 immutable lineage registration 与 exact fingerprint validation。
5. 实现 review receipt binding、typed semantic-result validation 与 stale-result rejection。
6. 实现 acceptance-evidence reference consistency，同时明确拒绝 authority verification 与 SETTLE authorization。
7. 增加 A-H deterministic tests、legacy-vs-lineage ablation、migration/rollback docs 与 CI。
8. 运行 repository-wide compatibility/hygiene gates；遇到结构集成失败时修复集成，不削弱 gate。
9. 在 acceptance conditions 全绿前保持 draft PR；不得自动 repin consumer。
