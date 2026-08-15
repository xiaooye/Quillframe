# 008 Tasks · State Integrity P0

## Stage A · #69
- [x] 对 current `state_graph`、Settlement、Canon/State、Project Adapter 做 evidence/overlap review。
- [x] 定义最小 mutation classes 与 deterministic route vocabulary。
- [x] resolver self-test 已在本地通过。
- [x] 发布 `property_write_policy.py` + schema。
- [x] 加入 Framework manifest discovery。
- [x] CI 增加 Project-path integration fixture。
- [x] 已跑首轮 public Actions 并检查实际执行 steps/artifact（`31891326122`，artifact `9248615828`）。
- [x] 将 resolver self-test 纳入 reusable release contracts。
- [ ] 跑 latest-head dedicated + full NovelForge CI，并检查所有相关 jobs。
- [ ] 做 compatibility + exact diff review。

## Stage B · #63
- [ ] Stage A 落地后重新读取 current-main dependency/state mechanisms。
- [ ] 定义 derived debt identity、lifecycle、required-action enum、discharge receipt。
- [ ] 证明只有 explicit dependency 才开 debt，并支持 idempotent resume。
- [ ] 增加 no-global-invalidation、supersession、discharge、waiver-with-evidence regressions。
- [ ] 跑 CI/evals并审 exact diff。
