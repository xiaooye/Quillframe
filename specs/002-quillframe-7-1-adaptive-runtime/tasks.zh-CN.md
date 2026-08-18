# 任务 · NovelForge 7.1 Adaptive Runtime

> 历史状态：**7.1 已完成并通过 release verification**。原文件的空 checkbox 是 implementation 完成后未回填的 ledger drift；此处只修正历史记录，不重新执行已停止的 consumer project。

## Phase 1 · Capability Contract
- [x] T101 新增 `harness/runtime_capabilities.py` + self-test。
- [x] T102 新增中英 Runtime Capability 文档。
- [x] T103 Runtime Routing 接入 capability requirement。

## Phase 2 · Corpus Discovery Runtime
- [x] T201 `corpus_scout.py` 升级为 capability-aware discovery request v2。
- [x] T202 新增 `corpus/discovery_runtime.py` + typed provenance/result validation。
- [x] T203 强制 rights/storage gate、dedupe、diversity accounting。

## Phase 3 · Durable Learning Cycle
- [x] T301 新增 `learning/learning_cycle.py`：SQLite lifecycle/state/versioning。
- [x] T302 discovery/analysis/eval result 实现 logical consume-once。
- [x] T303 增加 resume/idempotency/illegal-transition self-test。

## Phase 4 · Semantic Learning Work
- [x] T401 新增 `learning/learning_eval.py` 打包 Corpus analysis / learning eval job。
- [x] T402 复用 semantic fingerprint contract，execution lineage 不进入 fingerprint。
- [x] T403 增加 blind packet / answer-key leakage regression。

## Phase 5 · Promotion Gate
- [x] T501 新增 `learning/promotion_gate.py`。
- [x] T502 强制不同 scope 的 evidence threshold。
- [x] T503 General Craft 强制 cross-work + counterexample + eval + rollback + CI。

## Phase 6 · Immutable Bundle
- [x] T601 新增 `release/build_framework_bundle.py` build/verify/self-test。
- [x] T602 新增中英 bundle policy 文档。
- [x] T603 新增 optional release-bundle GitHub workflow。
- [x] T604 生成 deterministic 7.1 bundle fingerprint。

## Phase 7 · CLI / CI / Maintenance
- [x] T701 升级 `novelforge.py` router/version/self-test。
- [x] T702 reusable CI 覆盖所有 7.1 deterministic contract。
- [x] T703 weekly maintenance 升级成 capability-aware learning queue。
- [x] T704 证明 normal CI / weekly maintenance 不执行模型、不 auto-promote。

## Phase 8 · Docs / Manifest / Version
- [x] T801 `HARNESS_MANIFEST.yaml` → 7.1.0，并声明新 module/contract。
- [x] T802 中英同步 Skill/Harness/Self-Improvement/Adaptive-Learning/Corpus/Integration docs。
- [x] T803 更新 README/CHANGELOG/Project SDK docs 与 default framework version。
- [x] T804 记录来自官方 agent framework 文档的 external mechanism evidence/provenance。

## Phase 9 · Framework Verification
- [x] T901 exact 7.1 commit 的 NovelForge CI green。
- [x] T902 Bundle build/verify green 且 fingerprint 已记录。
- [x] T903 Framework source 无 consumer-project leakage。

## Phase 10 · Historical Consumer Upgrade
- [x] T1001 当时的 consumer Project minimum framework version → 7.1.0。
- [x] T1002 当时的 lock 写入 exact commit + bundle fingerprint。
- [x] T1003 当时更新 framework attestation + 7.1 project validator contract。
- [x] T1004 当时的 consumer Project CI green。
- [x] T1005 当时确认 Canon / active story state 未因 dependency migration 改变。

> 该 consumer repo 现已由用户停止维护；7.2 本轮不再读取、修改或迁移它。

## 非阻塞 Follow-up
- [ ] F001 历史 embedded Generic OS source 的物理删除/归档仅在未来有仍在维护的 consumer 需要时再做。
- [ ] F002 原创 repository hero binary + provenance（非 runtime blocker）。
