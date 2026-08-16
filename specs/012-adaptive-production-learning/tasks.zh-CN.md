# Tasks 012 · 自适应生产学习与 Realization 边界

## Design

- [x] 冻结真实 production failure evidence，并严格区分 historical pinned authority 与当前 engineering target。
- [x] Benchmark 成熟写作/agent system，依据 persistent intent、sparse context、simulation-before-prose、evaluator/editor loop、bounded learning 重构设计。
- [x] 复用现有 Author Steering、Learning Store、Context Inspector、story simulation、readiness、quality evolution owner，不重复造 subsystem。

## Author Model / feedback

- [ ] 增加 `learning.preference_interpret` semantic contract。
- [ ] 基于现有 Learning Store 增加 deterministic Author Model projection/runtime。
- [ ] 强制 one_off、project、user_taste、general_craft 的 scope/authority boundary。
- [ ] 增加 contradiction / supersession tests。
- [ ] 把实质性 Review feedback 接成 typed evidence / proposed preference delta，不改变 primary task mode。

## Context assembly

- [ ] 增加 simulation/private-state stage 与 pre-draft isolation。
- [ ] 增加 required context obligation 与 satisfaction receipt。
- [ ] 增加 deterministic Context Assembly validator/self-test。
- [ ] 保持 semantic relevance selection 归模型所有。

## Simulation / realization

- [ ] 增加 writer-safe `scene.realization_project` semantic contract。
- [ ] 保证 private character state 只做 causal state，不直接成为 prose payload。
- [ ] 增加 formal-completeness counterexample boundary。

## Reader / Editor / quality

- [ ] 在 quality taxonomy 注册 HF-30。
- [ ] 增加 profile-sensitive prose telemetry，明确只是 non-authoritative signal。
- [ ] Reader production assessment 增加 paragraph/profile/dialogue realization 的结构化维度。
- [ ] 增加 `editor.repair_spec` contract。
- [ ] material repair 复用 pairwise incumbent/challenger comparison。
- [ ] 只在确有 deterministic structural receipt 时扩展 readiness。

## Safety / integrity

- [ ] 增加 typed write-intent/action mismatch guard。
- [ ] 修复 stale semantic registry reference。
- [ ] 增加 semantic-reference integrity self-test/CI。
- [ ] 保持 semantic reject 与 transport/configuration/result-validation failure 的类型区分。

## Integration

- [ ] 在 manifest/catalog 注册新 tool/contract。
- [ ] 双语更新 Harness/Orchestration 与 production/context/learning 用户文档。
- [ ] 把本 spec 注册到 documentation governance。
- [ ] 把 deterministic tests 接入 normal reusable contracts CI。
- [ ] 增加 hidden-gold isolation 的 semantic/regression eval fixture。

## Verification

- [ ] Compile 所有 Python module。
- [ ] 跑完所有新增 deterministic self-test。
- [ ] 跑与本改动相关的 existing deterministic regression。
- [ ] 构建/验证 semantic contract catalog。
- [ ] 构建 blind semantic judge queue。
- [ ] 最终文件集合确定后验证 Framework bundle reproducibility。
- [ ] 跑 exact-head CI，并区分 pre-existing 与 introduced failure。
- [ ] 若存在 eligible transport，为 exact candidate 获取 independent semantic capability/counterexample evidence。
- [ ] 形成 rollback point 与 human-review handoff summary。

## Release boundary

- [ ] 本 SYSTEM-IMPROVE run 不 merge PR #90、不 promote Framework behavior、不迁移 consuming Project lock；除非之后另有单独 authority。
