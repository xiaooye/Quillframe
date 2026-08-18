# Tasks 014 — 语义上下文运行时

- [x] 冻结 Quillframe main `0d211675fd9f545b83d02ab4102563f0c67e11b9` 与 Shujuku main `12fec85bae325cacd8370b4dd0f4aff0dfd6da0e`。
- [x] 读取当前 Harness、Context、Story、Character、Canon、Agent/Model Runtime、Persistence、Host Bridge contracts。
- [x] 实现 fingerprint-bound Semantic Context Profile、regeneration/stale 语义与 manual override preservation。
- [x] 实现 relevance 之前的 deterministic lifecycle/visibility/stage eligibility gate。
- [x] 实现 Agent selection 的 exact candidate-universe validation。
- [x] 实现 stage-specific greenlights 与 deterministic hard-budget packing，包含 incomplete grounding 状态。
- [x] 实现可复现 Context Freeze、stale/conflict validation、显式 refresh/extension fingerprint。
- [x] 实现 typed Context Query、mandatory/adaptive graph validation。
- [x] 实现不暴露 private reasoning 的 public Inspector projection。
- [x] 新增 SQLite migration + typed ContextRepository，保持 backup/restore/doctor compatibility。
- [x] 新增 `context.profile_derive`、`context.stage_select` semantic worker contracts，并保留 `context.select`。
- [x] Studio Host Bridge 增加 read-only Context projection；不改 UI。
- [x] 双语记录 Shujuku 吸收/拒绝项与 architecture difference。
- [x] 新增 required deterministic/integration tests。
- [ ] GitHub CI + aggregate release/bundle verification（commit 后验证回填）。
- [ ] 全部 green 后生成 acceptance report。
