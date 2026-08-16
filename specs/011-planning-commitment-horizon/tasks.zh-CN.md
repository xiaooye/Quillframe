# 规划承诺视界——任务

## Before-state / 证据

- [x] 在 #67 记录 AI-Novel-Writing-Assistant 的 exact implementation evidence 以及 soft-label 反例。
- [x] 记录 Stanford Generative Agents 关于渐进近端分解与 bounded schedule rewrite 的 exact implementation evidence。
- [x] 审计与 `plan.reconcile`、`scenario_fork`、#63 propagation debt 的 overlap。
- [x] 明确 profile boundary：不存在通用 chapter/volume/time horizon 常数。

## 设计

- [x] 在实现前完成 bilingual specification。
- [x] 在实现前完成 bilingual implementation plan。
- [x] #67 不依赖未 merge 的 #65；creative-decision refs 只能是 opaque refs。
- [x] 保持 plan-vs-Canon 与 Settlement authority boundary。

## Stage 1 — executable contract

- [ ] 实现 `harness/planning_horizon.py`。
- [ ] 新增 `harness/planning_horizon.schema.json`。
- [ ] 实现 portable profile policy 与 region artifact validation/fingerprinting。
- [ ] 实现 registered artifact-kind -> planning-depth admission。
- [ ] unknown artifact kind fail closed。
- [ ] 实现 allowed actor classes + exact-before CAS horizon transition。
- [ ] 实现一圈 dependency-evidence rebalance frontier。
- [ ] 保证不自动运行 `plan.reconcile`、不自动创建 propagation debt、不修改 active plan，也无 Canon/Framework/Project/Settlement write。

## Stage 1 regressions

- [ ] soft/beat 阻止 `chapter_plan`。
- [ ] profile 允许时 hard/chapter-detail 接纳 `chapter_plan`。
- [ ] writer 不能 promotion/deepen horizon。
- [ ] authorized actor + exact before version/fingerprint 可以 promotion。
- [ ] stale transition fail closed。
- [ ] unknown artifact kind fail closed。
- [ ] 非相邻但有匹配 evidence 的 dependency 被选择。
- [ ] 相邻但没有 dependency evidence 的 region 被排除。
- [ ] assumption-scoped dependency 只在 changed assumptions 有交集时触发。
- [ ] frontier 只是一圈，并且不执行 follow-up action。
- [ ] 严密短篇 profile 可以允许深度 hard planning。
- [ ] discovery profile 可以让近端保持 soft。
- [ ] 所有 artifact/result 均 authority=false、model_execution=false。

## Stage 2 — real runner

- [ ] 新增 dedicated `novelforge-planning-horizon.yml`。
- [ ] 在 GitHub-hosted Python 3.11 compile tool + validate schema。
- [ ] 跑 deterministic self-test + invariant assertions。
- [ ] 上传 exact-head deterministic receipt artifact。
- [ ] Dedicated workflow 变绿前不开始 Framework integration。

## Stage 3 — Framework integration

- [ ] 在 `HARNESS_MANIFEST.yaml` 注册 tool/schema/policy semantics。
- [ ] 让 dedicated workflow 可复用并成为 top-level normal CI required job。
- [ ] 按 latest repo architecture 接 reusable contract checks。
- [ ] 在 documentation manifest 登记 011 bilingual spec/plan/tasks。
- [ ] 跑 exact-head full NovelForge deterministic CI。
- [ ] 并发 Product/Studio baseline failures 单独归因；本 Core branch 不修产品线。

## Stage 4 — semantic evaluation

- [ ] 新增 meaningful far-future over-concretization 的 blind semantic capability case。
- [ ] 新增 tightly plotted short-work counterexample。
- [ ] 新增 discovery-writing near-future-soft counterexample。
- [ ] 使用真正独立且 fingerprint-bound 的 reviewer/model。
- [ ] 独立 reviewer capability 不可用时保持 `PENDING_MODEL`，绝不 self-score PASS。

## Promotion / rollback

- [ ] merge 前重新 compare latest `main` 并保留所有并发 product work。
- [ ] 确认没有 Project lock、manuscript、Canon、user taste 或 Settlement state 变化。
- [ ] 确认 #67 不依赖 #65 的 merge 顺序。
- [ ] 确认关闭/删除 horizon enforcement 后，现有 active plans 不变，并退回既有 planning contracts。
- [ ] 所需 General Craft semantic evidence 完成前 PR 保持 Draft。
