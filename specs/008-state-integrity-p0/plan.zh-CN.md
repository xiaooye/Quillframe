# 008 Plan · State Integrity P0

1. 冻结当前 Framework `main` exact base；不修改任何下游 Project lock。
2. 将 #69 实现为 stdlib-only deterministic resolver + JSON schema。
3. Project policy 只通过现有安全 `paths` map 可选发现。
4. 为 writer escalation、Settlement routing、derived authority、mixed reconcile、UI editability、legacy compatibility 建 regression fixtures。
5. 在 `HARNESS_MANIFEST.yaml` 暴露 contract，并接 public CI。
6. 审 exact diff；deterministic CI 全绿后才允许 merge。
7. #69 边界稳定后，才在同一 P0 方向实现 #63 propagation debt。

Rollback：移除 optional path/tool 并 revert Framework commit；未配置该 path 的 Project 行为不变。
