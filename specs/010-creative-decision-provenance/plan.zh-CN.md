# 计划 · 创作决策来源

1. 冻结 NeuroBook 与 GitHub Spec Kit 的跨框架证据及 profile/counterexample。
2. 实现 provider-neutral JSON artifact validator/lifecycle tool；不新增数据库或第二套 plan store。
3. 实现 `open`、`resolve`、`supersede`、`drop` 与 audience projection，并使用 exact fingerprint/CAS guard。
4. deterministic code 不做语义选择，只验证 actor 权限与 provenance；具体选择由 user/authorized planner/manager semantic work 决定。
5. 仅输出 downstream revalidation candidates；需要 debt 时由 #63 在显式 dependency evidence 下单独处理。
6. 加 deterministic self-tests 与 dedicated CI。
7. dedicated CI 绿后，再接 HARNESS、normal/reusable contracts 与 documentation governance。
8. 补齐 Self-Improvement Protocol 要求的 capability/regression evidence 与 rollback review，再决定 merge/promotion。
