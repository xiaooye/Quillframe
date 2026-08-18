# 任务 · NovelForge 7.2 Author Control + Quality Evolution

> 状态：implementation 已直接进入 `main`（用户明确取消 feature-branch/PR 要求）。最终 release gate 仍以 **exact final HEAD 的 CI + bundle** 为准。

## Phase 0 · Baseline
- [x] T001 冻结 7.1 + Story Loom 合并后的开发基线。
- [x] T002 读取 7.1 spec/plan/tasks 与 Self-Improvement Protocol。
- [x] T003 建立 7.2 spec/plan/tasks；后按用户指示直接在 `main` 实施。
- [x] T004 识别 7.1 stale checklist；历史 ledger 单独修正。

## Phase 1 · Common Findings
- [x] T101 新增 `quality/__init__.py`。
- [x] T102 新增 `quality/findings.py` + fingerprint/tamper self-test。

## Phase 2 · Reader Panel
- [x] T201 新增 `quality/reader_panel.py` single-candidate job builder。
- [x] T202 增加 A/B pairwise + per-persona order swap。
- [x] T203 增加 disagreement / templating / first-shown-bias diagnostics。
- [x] T204 明确 panel diagnostic ≠ mandatory independent semantic gate。

## Phase 3 · Quality Evolution
- [x] T301 新增 `quality/quality_evolution.py` SQLite lifecycle。
- [x] T302 candidate/comparison fingerprint + result consume-once。
- [x] T303 repair-owner + plateau stopping。
- [x] T304 resume/idempotency/illegal-winner self-test，并修复 comparison replay 顺序问题。

## Phase 4 · Context Inspector
- [x] T401 新增 `harness/context_inspector.py`。
- [x] T402 authority/stage/relevance/pin inspector。
- [x] T403 protected edit → proposal；direct Canon mutation forbidden。
- [x] T404 regression/hidden-gold stage isolation self-test。

## Phase 5 · Tiered + Editable Memory
- [x] T501 新增 `harness/memory_tiers.py`。
- [x] T502 hard budget + whole-item-or-skip。
- [x] T503 event/participant relevance + pin-first promotion。
- [x] T504 provenance + derived authority=false self-test。
- [x] T505 新增 durable `harness/memory_bank.py`。
- [x] T506 accepted/locked edit → proposal；editable entry 使用 exact before-fingerprint。
- [x] T507 proposal 默认 `never` stage，禁止 future/proposal data 静默进入 pre-draft。
- [x] T508 Memory Bank → non-authoritative Context Manifest export + pin/priority control。

## Phase 6 · Character Integrity
- [x] T601 新增 `quality/character_integrity.py`。
- [x] T602 bounded `artifact_audit` packaging。
- [x] T603 forbidden-context scan。
- [x] T604 result → evidence-chained normalized findings。

## Phase 7 · State Graph
- [x] T701 新增 `quality/state_graph.py`。
- [x] T702 node/edge normalization + stable-field diff。
- [x] T703 transition evidence binding。
- [x] T704 before/after finding + derived authority self-test。

## Phase 8 · Multi-pass Revision + CLI / Release Contracts
- [x] T801 新增 `quality/revision_orchestrator.py` narrow pass planning / failure isolation / finding aggregation。
- [x] T802 surface cluster → whole-scene regeneration；reader-flatness → Reader Pressure + Scene Simulation。
- [x] T803 `novelforge.py` → 7.2.0 + Reader/Quality/Context/Memory/Revision routers/doctor/self-test。
- [x] T804 `HARNESS_MANIFEST.yaml` 声明 7.2 author-control/quality contracts。
- [x] T805 reusable CI 接入 7.2 deterministic self-tests，包括 Memory Bank 与 Revision Orchestrator。
- [x] T806 `SKILL.md` / `SKILL.en.md` / `SKILL.zh-CN.md` 更新到 7.2 contract；不重做 customer-facing docs。
- [x] T807 `project_sdk.py` 新项目默认 Framework → 7.2.0，并声明 quality-control scaffold。

## Phase 9 · Verification
- [x] T901 第一批 7.2（Reader/Context/Evolution/Character/State）exact commit CI green。
- [x] T902 第一批验证中旧 7.1 deterministic contracts 保持全绿。
- [x] T903 第一批 bundle double-build reproducible 且 normal CI `model_execution=false`。
- [ ] T904 扩展后的 Memory Bank + Revision Orchestrator exact final HEAD compile/hygiene green。
- [ ] T905 扩展后的全部 7.2 self-tests + 7.1 regressions 全绿。
- [ ] T906 exact final HEAD bundle double-build reproducible + fingerprint 记录。
- [ ] T907 exact final HEAD Normal CI `model_execution=false`。

## Release Follow-up
- [ ] F001 Final green HEAD 后记录 release commit + immutable bundle fingerprint。
- [ ] F002 需要时再做 consuming-project dependency migration；本次不触碰已停止的旧 project repo。
