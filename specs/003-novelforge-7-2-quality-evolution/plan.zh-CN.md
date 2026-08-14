# 计划 · NovelForge 7.2 Author Control + Quality Evolution

## 总策略

7.2 延续 7.1 的 `deterministic shell + optional semantic capability`。任何新功能都不得静默调用模型。Reader Panel、Character Integrity 与 revision quality pass 只负责 typed packaging / validation / aggregation；实际 semantic execution 继续服从 Host Capability + Runtime Routing + independent-session contract。

质量升级主循环：

`observe → classify → repair owning mechanism → compare → keep/discard → regression → stop/continue`

不是“多叫几个 Agent 打分”。

按用户明确指示，本轮实现直接进入 `main`，取消 feature-branch / PR release gate；替代它的是更严格的 **exact final HEAD + deterministic CI + deterministic bundle**。

## Phase 0 · Baseline Audit

- 冻结 7.1 + Story Loom 合并后的开发基线；
- 核对 7.1 spec 与已实现 module；
- 把 7.1 stale checkbox 修成 historical completion ledger；
- customer-facing Story Loom docs 不重做。

## Phase 1 · Common Quality Finding Contract

新增 `quality/findings.py`：normalized severity/category/repair owner、candidate evidence、authority evidence、source refs、confidence、stable fingerprint 与 self-test。所有新 audit 尽量输出统一 finding。

## Phase 2 · Reader Simulation Panel

新增 `quality/reader_panel.py`：reading-behavior persona、single-candidate + A/B builder、per-persona order swap、result aggregation、disagreement / templating / first-shown-bias diagnostics，并明确 `independent_gate=false`。复用 semantic kind `external_review`。

## Phase 3 · Durable Quality Evolution

新增 `quality/quality_evolution.py`：SQLite runs/candidates/comparisons、exact candidate fingerprint、comparison result consume-once、exact replay idempotency、repair-owner、no-gain plateau、illegal winner rejection、crash/resume self-test。

## Phase 4 · Context Inspector

新增 `harness/context_inspector.py`：authority/stage/relevance/pin visibility；pin/unpin/priority/hide/invalidate-derived overlay；protected edit → proposal；pre-draft/post-draft/reviewer isolation。此模块永不写 Project Canon。

## Phase 5 · Tiered + Durable Editable Memory

1. 新增 `harness/memory_tiers.py`：`hot | working | archival`、provenance validation、hard budget、whole-item-or-skip、current-event/participant relevance、pin-first、derived `authority=false`。
2. 新增 `harness/memory_bank.py`：durable SQLite entry、明确 authority taxonomy、exact before-fingerprint edit guard、accepted/locked protected edit→proposal、pin/priority、Context Manifest export。
3. proposal memory 默认 `never` injection stage，future/contested state 不得静默进入 writer pre-draft。
4. deterministic memory module 不做自由文本 Canon “自动总结”；semantic consolidation 必须另走 bounded semantic job + derived provenance。

## Phase 6 · Character Integrity

新增 `quality/character_integrity.py`：bounded scene excerpt + character snapshot（agenda/knowledge/voice/relationship/spatial-task）、`artifact_audit` packaging、forbidden-context scan、result → common evidence-chained finding。

## Phase 7 · State Graph Audit

新增 `quality/state_graph.py`：scene snapshot nodes/edges/transitions、stable-attribute diff、transition evidence binding、unexplained-change finding、before/after evidence chain、derived `authority=false`。复杂剧情合理性继续属于 semantic layer。

## Phase 8 · Multi-pass Revision Orchestration

新增 `quality/revision_orchestrator.py`：

- narrow continuity / character / reader / surface / research pass planning；
- missing/failing pass isolation；
- normalized finding aggregation + dedupe；
- evidence/diagnostic preservation；
- owning-mechanism repair queue；
- surface cluster → scene regeneration；
- SAFE-BUT-FLAT / reader-grip → Reader Pressure + Scene Simulation；
- reviewer/panel result 永不获得 Canon authority。

## Phase 9 · CLI / Manifest / Project SDK / CI

- `novelforge.py` → 7.2.0，并 route reader-panel / quality-evolution / revision-orchestrator / context-inspect / memory-tiers / memory-bank / character-integrity / state-graph；
- doctor + top-level self-test 覆盖全部 7.2 module；
- `HARNESS_MANIFEST.yaml`、`SKILL*` 更新 7.2 authority contract；
- `project_sdk.py` 新 scaffold 默认 7.2.0，并声明 quality-control capability；
- reusable CI 接入全部新 deterministic self-test，同时保留全部 7.1 regression；
- normal CI 继续 `model_execution=false`，bundle 继续 deterministic。

## Phase 10 · Verification

1. exact HEAD compile + repository hygiene；
2. 全部旧 7.1 contract 保持 green；
3. 全部 7.2 self-test（含 Memory Bank / Revision Orchestrator）green；
4. `novelforge.py self-test` green；
5. Framework bundle 连续两次 build bytes/fingerprint 一致，tamper detection 仍生效；
6. normal CI 无 model execution；
7. fail 必须修 owning module，不降低 gate；
8. 只有 final exact HEAD 所有 required workflow green 才称 release-ready。

## Release Follow-up

- final green 后记录 exact 7.2 commit + deterministic bundle fingerprint；
- 本 run 不迁移已停止的 legacy consumer repo；
- 未来若有仍维护的 consumer，再另开 dependency migration，且 Framework migration 不得修改 story Canon/state。

## Rollback

Framework rollback base：`5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`。7.2 各机制还有独立 introducing commit + deterministic self-test，因此某一机制失败时可以精确 rollback，而不需要制造任何替代 story state。
