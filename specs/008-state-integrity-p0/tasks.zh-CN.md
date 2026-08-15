# 008 Tasks · State Integrity P0

## Stage A · #69
- [x] 对 state graph、Settlement、Canon/State、Project Adapter 完成 evidence/overlap review。
- [x] 定义最小 mutation classes 与 deterministic route vocabulary。
- [x] 发布 resolver/schema + Project-path integration。
- [x] 加入 Framework manifest discovery 与 release/full-CI coverage。
- [x] Public dedicated run `31891941126` 全绿；artifact `9248769203`。
- [x] Full NovelForge CI `31891941404` 全绿；Studio Host Bridge / Product Site 同样 green。
- [x] 与同步后的 main 比较，exact diff 只有 P0 Core/spec/docs/workflow 文件。

## Stage B · #63
- [x] 重新读取 current-main state graph、Settlement、memory invalidation、quality evolution 与 resume preflight。
- [x] 定义 debt identity、lifecycle、required-action enum、explicit dependency evidence 与 closure receipts。
- [x] Deterministic self-test 已覆盖 no-global-invalidation、open/discharge/supersede 幂等、evidence-bound waiver 与 restart。
- [x] 发布 propagation-debt runtime/schema/self-test，并把 state-integrity workflow 接进 full CI。
- [x] Executable full CI `31892576274` 全绿；state-integrity job `95030952320`；artifact `9248929531`（`sha256:dbfa58b243426980c5687b54c5ba56c54ba6dfd10453f6dfc52b6ffcd04045c5`）。
- [x] 在 `HARNESS_MANIFEST.yaml` 注册 property-policy / propagation-debt tool/schema boundary，并把两个 deterministic test 纳入 normal CI。
- [x] 同步到 `221cc423f24e17eaf0da74f0d3e67a378aad5509` 时完整保留 latest-main public resume-preflight query 语义。
- [ ] Manifest/latest-main synchronization 后跑 final exact-head full NovelForge CI，并检查 artifacts/jobs。
- [ ] 再核 latest main、final exact diff / compatibility，并保持所有 downstream Project lock 不变。
