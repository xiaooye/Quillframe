# Tasks 015 — Candidate Lineage

- [x] Bootstrap pinned consumer authority，并冻结 current Framework base。
- [x] 研究外部 lineage/version/revision design 与 NovelForge current equivalent。
- [x] 定义 comparison-parent 与 prose-parent 语义。
- [x] 实现 additive companion schema 与 immutable lineage registration。
- [x] 绑定 exact semantic review receipts，并实现 stale invalidation。
- [x] 将 acceptance handling 收紧为 opaque、non-authoritative evidence reference。
- [x] 增加只读 SETTLE reference-consistency check，始终 `settlement_authorized=false`。
- [x] 增加 versioned machine-readable `quality/candidate_lineage.schema.json`。
- [x] 增加必须的 A-H deterministic tests。
- [x] 增加 legacy-vs-lineage architecture ablation。
- [x] 增加 migration、rollback、authority 与 Cold Read 决策文档。
- [x] 增加独立 CI workflow，并验证 typed-schema identity。
- [x] 在本次 checklist-only 文档更新之前，head `e4ffe009e4ced8e5a65047cec055c3642f5c7090` 已通过全部相关 repository-wide CI/host contracts。
- [ ] 完成 acceptance review；在此之前保持 draft PR。
- [ ] 仅在 merge/acceptance 后建议 consumer repin；永不自动执行。
