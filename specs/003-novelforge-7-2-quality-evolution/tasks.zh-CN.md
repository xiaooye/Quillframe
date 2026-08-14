# 任务 · NovelForge 7.2 Author Control + Quality Evolution

## Phase 0 · Baseline
- [x] T001 冻结 `main@5e8f586b...`。
- [x] T002 读取 7.1 spec/plan/tasks 与 Self-Improvement Protocol。
- [x] T003 建立 7.2 feature branch 与 spec/plan/tasks。
- [ ] T004 把 7.1 stale checklist 更新为 historical completion ledger。

## Phase 1 · Common Findings
- [ ] T101 新增 `quality/__init__.py`。
- [ ] T102 新增 `quality/findings.py` + self-test。

## Phase 2 · Reader Panel
- [ ] T201 新增 `quality/reader_panel.py` single-candidate job builder。
- [ ] T202 增加 A/B pairwise + per-persona order swap。
- [ ] T203 增加 disagreement / templating / first-shown-bias diagnostics。
- [ ] T204 明确 panel diagnostic ≠ mandatory independent semantic gate。

## Phase 3 · Quality Evolution
- [ ] T301 新增 `quality/quality_evolution.py` SQLite lifecycle。
- [ ] T302 candidate/comparison fingerprint + result consume-once。
- [ ] T303 repair-owner + plateau stopping。
- [ ] T304 resume/idempotency/illegal-winner self-test。

## Phase 4 · Context Inspector
- [ ] T401 新增 `harness/context_inspector.py`。
- [ ] T402 authority/stage/relevance/pin inspector。
- [ ] T403 protected edit → proposal；direct Canon mutation forbidden。
- [ ] T404 regression/hidden-gold stage isolation self-test。

## Phase 5 · Tiered Memory
- [ ] T501 新增 `harness/memory_tiers.py`。
- [ ] T502 hard budget + whole-item-or-skip。
- [ ] T503 event/participant relevance + pin-first promotion。
- [ ] T504 provenance + derived authority=false self-test。

## Phase 6 · Character Integrity
- [ ] T601 新增 `quality/character_integrity.py`。
- [ ] T602 bounded `artifact_audit` packaging。
- [ ] T603 forbidden-context scan。
- [ ] T604 result → evidence-chained normalized findings。

## Phase 7 · State Graph
- [ ] T701 新增 `quality/state_graph.py`。
- [ ] T702 node/edge normalization + stable-field diff。
- [ ] T703 transition evidence binding。
- [ ] T704 before/after finding + derived authority self-test。

## Phase 8 · CLI / Release Contracts
- [ ] T801 `novelforge.py` → 7.2.0 + 新 routers/doctor/self-test。
- [ ] T802 `HARNESS_MANIFEST.yaml` 声明 7.2 quality/control modules。
- [ ] T803 reusable CI 增加全部 7.2 deterministic self-tests。
- [ ] T804 必要 machine/Harness version contract 更新；不重做 customer docs。

## Phase 9 · Verification
- [ ] T901 branch compile/hygiene green。
- [ ] T902 旧 7.1 deterministic contracts 全绿。
- [ ] T903 7.2 self-tests 全绿。
- [ ] T904 bundle double-build reproducible。
- [ ] T905 normal CI `model_execution=false`。
- [ ] T906 draft PR created。
- [ ] T907 exact candidate commit CI green。

## Release Follow-up（本 run 不执行）
- [ ] F001 Merge/acceptance 后确定 exact 7.2 commit。
- [ ] F002 构建并记录新 immutable bundle fingerprint。
- [ ] F003 consuming projects 另开 dependency migration。
- [ ] F004 consumer migration 验证 Canon/story state unchanged。
