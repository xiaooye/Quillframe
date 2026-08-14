# 计划 · NovelForge 7.2 Author Control + Quality Evolution

## 总策略

7.2 延续 7.1 的 `deterministic shell + optional semantic capability`。本 release 不新增隐式模型调用；Reader Panel、Character Integrity 等只负责 typed packaging / validation / aggregation，实际 semantic execution 继续服从 Host Capability + Runtime Routing + independent-session contract。

质量升级的主原则：

`observe → classify → repair owning mechanism → compare → keep/discard → regression → stop/continue`

不是“多叫几个 Agent 打分”。

## Phase 0 · Baseline Audit

- 冻结 `main@5e8f586b...`；
- 核对 7.1 spec/implementation/consumer lock；
- 将 7.1 stale task checklist 标记为 historical completion ledger；
- customer docs/Story Loom 本 phase 不重做。

## Phase 1 · Common Quality Finding Contract

新增 `quality/findings.py`：

- normalized finding schema；
- severity/category/repair_owner；
- candidate evidence + authority evidence；
- source refs + confidence；
- stable fingerprint；
- self-test。

所有新 audit 模块尽量输出统一 finding，而不是各自发明不可组合的格式。

## Phase 2 · Reader Simulation Panel

新增 `quality/reader_panel.py`：

- default reading-behavior personas；
- single-candidate review job builder；
- A/B pairwise job builder；
- per-persona order swap metadata；
- validated-result aggregation；
- disagreement / templating / first-shown-bias diagnostics；
- no independent-gate claim；
- self-test。

Reader panel 使用现有 semantic kind `external_review`，避免扩张 worker transport taxonomy。

## Phase 3 · Durable Quality Evolution

新增 `quality/quality_evolution.py`：

- SQLite schema：runs / candidates / comparisons；
- start/add-candidate/record-comparison/status；
- exact candidate fingerprint；
- result fingerprint consume-once；
- repair owner；
- no-gain counter + plateau；
- illegal transition / illegal winner rejection；
- self-test crash/resume/idempotency。

## Phase 4 · Context Inspector

新增 `harness/context_inspector.py`：

- inspect typed context items；
- authority/stage/relevance/pin visibility；
- overlay controls：pin/unpin/priority/hide/invalidate-derived；
- protected-authority edit → proposal；
- pre-draft/post-draft/reviewer isolation validation；
- self-test。

此模块只管理 context control overlay，不写 Project Canon。

## Phase 5 · Tiered Derived Memory

新增 `harness/memory_tiers.py`：

- `hot | working | archival`；
- input item provenance validation；
- hard budgets + whole-item-or-skip；
- current-event overlap / participant match boost；
- pin-first ordering；
- derived authority=false；
- invalidation metadata；
- self-test。

不在 deterministic module 里做自由文本“自动总结”；semantic consolidation 必须另走 bounded semantic job + derived provenance。

## Phase 6 · Character Integrity

新增 `quality/character_integrity.py`：

- bounded character snapshot；
- scene excerpt + agenda/knowledge/voice/relationship/spatial-task state；
- `artifact_audit` semantic job packaging；
- forbidden-context scan；
- result → normalized findings；
- self-test。

## Phase 7 · State Graph Audit

新增 `quality/state_graph.py`：

- scene snapshot node/edge normalization；
- stable attribute diff；
- transition evidence binding；
- unexplained-change candidate finding；
- before/after evidence chain；
- derived authority=false；
- self-test。

Deterministic graph audit 不判断复杂剧情合理性；复杂性仍交 semantic layer。

## Phase 8 · CLI / Manifest / CI

升级 `novelforge.py`：

- version → 7.2.0；
- route reader-panel / quality-evolution / context-inspect / memory-tiers / character-integrity / state-graph；
- doctor + self-test 覆盖新模块。

升级：

- `HARNESS_MANIFEST.yaml`；
- `.github/workflows/novelforge-contracts.yml`；
- `SKILL*` / Harness machine-facing bootstrap 仅做必要 contract/version 更新；
- bundle builder 继续自动收录 runtime files并做 reproducibility test。

## Phase 9 · Verification

1. branch push 触发 CI；
2. compile / hygiene / old 7.1 self-tests 全绿；
3. 新 7.2 self-tests 全绿；
4. bundle double-build fingerprint 一致；
5. normal CI 无 model execution；
6. 若失败，按 owning module 修复；
7. 开 draft PR，保持 user-visible review surface；
8. CI green 后才称 `release candidate`，不自动 merge。

## Phase 10 · Release Follow-up（本 run 不执行）

- merge/acceptance 后确定 exact 7.2 commit；
- build new immutable bundle + fingerprint；
- consumer 项目另开 dependency migration；
- consumer validation green 后再更新 lock/attestation；
- Canon/story state 不随 Framework dependency migration 改变。

## Rollback

- Framework branch rollback base：`5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`。
- 7.1 consumer 保持 `d9126b...`，因此 7.2 branch 失败不会污染当前小说 runtime。
