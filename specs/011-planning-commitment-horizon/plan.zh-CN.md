# 规划承诺视界——实施计划

## 目标

把 #67 实现成一个很小的 deterministic planning-admission + rebalance-frontier contract，叠加在 NovelForge 既有规划机制之上；不建立第二套 active-plan 数据库，也不产生任何 Canon authority。

## Phase 0 — authority 与 overlap

- 从 exact current `main` 建分支。
- 既有 `plan.reconcile`、`scenario_fork`、#63 propagation debt、Context、Canon/Settlement、semantic-worker contracts 继续各自拥有原职责。
- #65 只作为可选 opaque reference；本分支必须在 #65 未 merge 时仍能独立构建和运行。

## Phase 1 — portable region/policy contract

新增 `harness/planning_horizon.py` 与 machine schema。

Deterministic contract 支持：

1. policy/region artifact 的 canonical fingerprint；
2. 小型固定 planning-depth registry 与已知 artifact-kind mapping；
3. 建立/验证 `open|soft|hard` region，并保证 depth ceiling 不超过 profile policy；
4. 对已登记 artifact kind 做 realization admission；
5. 具有 actor policy 与 evidence refs 的显式 CAS horizon transition；
6. 依据显式 dependency evidence 计算一圈 rebalance frontier；
7. 所有结果 authority=false，且不执行模型。

## Phase 2 — deterministic regressions

Self-test 至少覆盖：

- soft/beat 阻止 chapter detail；
- profile 允许时 hard/chapter-detail 接纳 chapter plan；
- unknown artifact kind fail closed；
- writer 不能 promotion；
- authorized planner/user + exact before state 可以 promotion；
- stale version/fingerprint fail closed；
- identical retry 不产生隐藏写权限；
- 非相邻但有关联的 dependency 被选择；
- 相邻但无关联的 dependency 被排除；
- assumption-scoped dependency 只在 changed assumptions 有交集时触发；
- frontier 不执行 reconcile/debt/Canon；
- tight-short 与 discovery 两种 profile counterexample 都能合法表达。

## Phase 3 — dedicated CI first

新增 dedicated workflow：

- compile tool；
- validate schema JSON；
- run self-test；
- assert authority/no-model/no-auto-action invariants；
- 上传 deterministic receipt。

在真实 GitHub runner 针对 current repository 变绿之前，不改 HARNESS/docs/normal CI。

## Phase 4 — Framework integration

Dedicated CI 变绿后：

- 在 `HARNESS_MANIFEST.yaml` 注册 tool/schema；
- 让 dedicated workflow 可复用并成为 normal-CI job；
- 按 current repo architecture 接 reusable contracts（如需要）；
- 把 bilingual `spec/plan/tasks` 登记进 documentation governance；
- 保留最新 main 上所有并发 Product/Studio 变更。

## Phase 5 — semantic capability/counterexample eval

复用 NovelForge 现有 blind eval infrastructure。至少加入：

- **capability**：连载小说仅有 soft 远期 arc role，但 planner 尝试提前生成数个 arc 之后的详细 chapter plans。期望：block / 请求 horizon promotion，而不是静默具体化。
- **counterexample**：短篇悬疑有明确用户要求，起草前完整规划 12 章。期望：允许 profile 对全书 hard-plan，而不是强迫假性 softness。
- **counterexample**：discovery-writing profile 刻意让下一章后半段 scene 也保持 soft。期望：保留 soft，而不是因为“很近”就自动 promotion。

独立模型能力缺失时必须保持 `PENDING_MODEL`，不能转成 self-scored PASS。

## Phase 6 — promotion review

Merge/promotion 前：

- 核 exact-head deterministic workflows；
- 核 semantic evidence；若仍 pending，PR 保持 Draft；
- 确认无 Project/Canon/manuscript 变更；
- 确认无 #65 隐式依赖；
- 确认 rollback 只需删除/关闭 horizon enforcement，不涉及数据迁移；
- 再 compare latest main，完整保留并发 Product/Studio 工作。
