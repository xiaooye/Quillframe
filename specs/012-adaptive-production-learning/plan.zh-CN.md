# Plan 012 · 自适应生产学习与 Realization 边界

## 目标

把 NovelForge 已有 primitive 连接成 stateful co-creative production loop，同时避免重复造 subsystem，也不削弱 authority boundary。

## Workstream 1 · Author Model 与 Review feedback

1. 基于现有 Learning Store 增加 deterministic Author Model projection runtime。
2. 增加 semantic `learning.preference_interpret` contract，对明确 Review feedback 做受限解释。
3. 严格区分 observation、hypothesis、activation 与 production projection。
4. 支持 contradiction / supersession 与 scope-aware activation rule。
5. 把已有 `feedback.observed` Author Steering 接到 Review learning lifecycle；通过 contract/orchestration 连接，不静默切换 primary task mode。

## Workstream 2 · Adaptive Context Assembly

1. 扩展 Context stage，使人物私有 simulation state 可以给 simulation 看，但默认不能给 prose generation 看。
2. 增加 typed required-context obligation 与 deterministic satisfaction receipt。
3. 新增 context-assembly runtime，验证 selected IDs 的 stage、authority、invalidation、required class/purpose 与 provenance/fingerprint。
4. `context.select` 继续拥有 semantic relevance judgment。
5. Corpus retrieval 保持条件性；benchmark 只是可选 context class，不是每次必跑的固定节点。

## Workstream 3 · Simulation-before-Prose

1. 复用 `character.action_propose` 与 `scene.resolve_actions`。
2. 增加 semantic `scene.realization_project` contract，把 private simulation evidence 转成 writer-safe interaction/event projection。
3. 默认阻止 raw private-character / simulation context class 进入 `writer_pre_draft`。
4. 明确接口：private state 控制行为；realization projection 控制 Writer 可见的 event/dialogue opportunity。

## Workstream 4 · Reader → Editor closed loop

1. 增加结构化 Reader production audit，判断真实 reading experience、profile fit、paragraph rhythm 与 dialogue realization，同时不暴露 creator-private state。
2. 增加 `editor.repair_spec`，把 Reader evidence 转为 preserve/change priority 与 owning repair layer。
3. material repair 复用 `reader.compare` / `quality.compare` 做 incumbent/challenger comparison。
4. Production Readiness 只增加 deterministic runtime 真正能证明的 structural receipts；不为每个文学维度造一个 deterministic gate。

## Workstream 5 · Quality mechanism

1. 注册 HF-30：Agenda-to-Dialogue Leakage / Character-Sheet-to-Dialogue Serialization。
2. 增加 profile-sensitive prose telemetry，但仅作为 signal。
3. 增加 formal-completeness dialogue 与 legitimate selective-short-paragraph counterexample。
4. Surface / Character / Reader contract 同步 architecture 与 backstop diagnosis。

## Workstream 6 · Safety 与 integrity

1. 新增 write-intent/action guard，阻止 resource/operation/target mismatch。
2. 修复 stale `model_contracts.json` reference，并增加 deterministic semantic-reference integrity check。
3. Framework 能负责的 semantic-bridge failure classification 在 code 中改进；repo setting/configuration owner 单独报告，不假装修好了外部权限。

## Workstream 7 · Integration 与 verification

1. 在 `HARNESS_MANIFEST.yaml` 与 model contract catalog 注册新 tool/contract。
2. 双语更新 Harness / Orchestration / production / context / adaptive-learning docs。
3. 把 deterministic self-test 接入 reusable release contracts CI。
4. 增加 generic semantic fixture，reviewer queue 不泄露 hidden expected label。
5. 跑 exact-head CI，区分 candidate failure 与 pre-existing repo debt。
6. 只在存在 eligible independent transport 时，为 exact candidate fingerprint 获取 independent semantic capability/counterexample evidence。
7. 证据达到人工审核门槛以前 PR 保持 Draft；本 run 不 merge、不 release、不迁移 downstream lock。

## Compatibility strategy

优先 additive schema 与 optional policy requirement。未声明新 required context / structural receipt 的已有 Project 继续兼容。Material version/release identity 只在 exact diff 与 verification 后决定。

## Rollback

每个 workstream 形成 coherent commit，可独立 revert。Downstream consumer 整个 run 都继续 pinned 到 NovelForge 0.8.0，因此 candidate rollback 永远不会改变本书 runtime authority。
