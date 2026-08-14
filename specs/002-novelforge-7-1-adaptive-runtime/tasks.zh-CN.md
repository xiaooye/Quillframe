# 任务 · NovelForge 7.1 Adaptive Runtime

## Phase 1 · Capability Contract
- [ ] T101 新增 `harness/runtime_capabilities.py` + self-test。
- [ ] T102 新增中英 Runtime Capability 文档。
- [ ] T103 Runtime Routing 接入 capability requirement。

## Phase 2 · Corpus Discovery Runtime
- [ ] T201 `corpus_scout.py` 升级为 capability-aware discovery request v2。
- [ ] T202 新增 `corpus/discovery_runtime.py` + typed provenance/result validation。
- [ ] T203 强制 rights/storage gate、dedupe、diversity accounting。

## Phase 3 · Durable Learning Cycle
- [ ] T301 新增 `learning/learning_cycle.py`：SQLite lifecycle/state/versioning。
- [ ] T302 discovery/analysis/eval result 实现 logical consume-once。
- [ ] T303 增加 resume/idempotency/illegal-transition self-test。

## Phase 4 · Semantic Learning Work
- [ ] T401 新增 `learning/learning_eval.py` 打包 Corpus analysis / learning eval job。
- [ ] T402 复用 semantic fingerprint contract，execution lineage 不进入 fingerprint。
- [ ] T403 增加 blind packet / answer-key leakage regression。

## Phase 5 · Promotion Gate
- [ ] T501 新增 `learning/promotion_gate.py`。
- [ ] T502 强制不同 scope 的 evidence threshold。
- [ ] T503 General Craft 强制 cross-work + counterexample + eval + rollback + CI。

## Phase 6 · Immutable Bundle
- [ ] T601 新增 `release/build_framework_bundle.py` build/verify/self-test。
- [ ] T602 新增中英 bundle policy 文档。
- [ ] T603 新增 optional release-bundle GitHub workflow。
- [ ] T604 生成 deterministic 7.1 bundle fingerprint。

## Phase 7 · CLI / CI / Maintenance
- [ ] T701 升级 `novelforge.py` router/version/self-test。
- [ ] T702 reusable CI 覆盖所有 7.1 deterministic contract。
- [ ] T703 weekly maintenance 升级成 capability-aware learning queue。
- [ ] T704 证明 normal CI / weekly maintenance 不执行模型、不 auto-promote。

## Phase 8 · Docs / Manifest / Version
- [ ] T801 `HARNESS_MANIFEST.yaml` → 7.1.0，并声明新 module/contract。
- [ ] T802 中英同步 Skill/Harness/Self-Improvement/Adaptive-Learning/Corpus/Integration docs。
- [ ] T803 更新 README/CHANGELOG/Project SDK docs 与 default framework version。
- [ ] T804 记录来自官方 agent framework 文档的 external mechanism evidence/provenance。

## Phase 9 · Framework Verification
- [ ] T901 exact 7.1 commit 的 NovelForge CI green。
- [ ] T902 Bundle build/verify green 且 fingerprint 已记录。
- [ ] T903 Framework source 无 consumer-project leakage。

## Phase 10 · Chinatown Consumer Upgrade
- [ ] T1001 Project minimum framework version → 7.1.0。
- [ ] T1002 lock 写 exact commit + bundle fingerprint。
- [ ] T1003 更新 framework attestation + 7.1 project validator contract。
- [ ] T1004 Chinatown Project CI green。
- [ ] T1005 确认 Canon / active story state 未变化。

## 非阻塞 Follow-up
- [ ] F001 `frostloom` 历史 embedded Generic OS source 的物理删除/归档，另开 bulk dependency-cleanup migration。
- [ ] F002 原创 anime/manga-inspired repository hero binary + provenance。
