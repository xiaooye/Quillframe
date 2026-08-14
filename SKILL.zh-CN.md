# NovelForge Skill Contract · 7.1 中文版

## 定位

NovelForge 是完全 project-agnostic 的小说生产 Framework。它拥有通用 Story/Character/Canon 机制、Surface/Reader 质量基础、capability-aware Harness/runtime orchestration、Corpus Intelligence、durable Adaptive Learning、Eval/Regression、deterministic Framework bundle、Project Engineering Contract 与 provider-neutral integrations。

Framework 内不得内置任何具体小说、人物、剧情、Canon 或用户私有 taste data。

## Bootstrap

任何 NovelForge 任务：

1. 读取 `HARNESS_MANIFEST.yaml`；
2. 读取 `harness/HARNESS_AGENT.md` 及适用语言版；
3. 确定且只确定一个 primary task_mode；
4. 通过 `novelforge.toml + novelforge.lock.json` 或 supported adapter 解析、验证 consuming project；
5. lock 若包含 `bundle_fingerprint`，先验证 materialized Framework bundle，再把它作为 runtime bytes；
6. 创建/恢复 manager session + run；
7. 需要 external/tool work 时，建立/读取 typed host capability manifest，再 resolve 所需 capability；
8. 建立 sparse Context Manifest；
9. 只加载当前任务需要的 Project object 与 Framework module；
10. external wait / consequential write 前 checkpoint；
11. mandatory semantic judgment 必须来自真正独立的 invocation/session；
12. 适用 quality/authority gate 全部通过后才能 expose/write；
13. resume 后重新验证 Project authority、lock compatibility、fingerprints、pending approval，以及 pending external/tool work 所需 capability。

未声明 capability = unavailable。Provider 名字、earlier session 曾可用、network primitive 或 model 自称会做，都不是 capability proof。

## Task Modes

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

每次只有一个 primary mode。用户明确指定时严格服从。

## Generic Quality Stack

```text
Framework Fundamentals
→ Genre / Platform Profile
→ Project Profile
→ User Taste Profile
→ Current Request
```

Framework anti-AI Surface fundamentals 默认启用。Profile-sensitive exception 必须显式 opt-in。Project 可以调阈值和风格目标，但不能偷偷关闭 generic failure mechanism。

正文任务读取：
- `surface/FUNDAMENTALS.zh-CN.md`
- `surface/READER_ENGAGEMENT.zh-CN.md`
- Context Manifest 选择出的 project profiles
- Regression/benchmark 如需 critic isolation，只能在 Raw Draft 冻结后进入 critic/auditor context。

## Story / Canon Stack

通用机制：
- `core/STORY_SYSTEM.zh-CN.md`
- `core/CHARACTER_SYSTEM.zh-CN.md`
- `core/CANON_STATE.zh-CN.md`

具体 Project 提供 BOOK/VOL/ARC/UNIT/CH/SCN 实例、人物/世界/关系状态、research、plans 与 Accepted Canon。

Plan ≠ Canon。Review ≠ Accepted。Session ≠ Canon。Corpus ≠ Canon。Semantic Judgment ≠ Canon。Learning Cycle state ≠ Canon。

## Project Engineering

每一本 consuming novel 都应该满足 Project SDK：
- `novelforge.toml` Project manifest；
- exact `novelforge.lock.json` Framework dependency lock；
- release-grade consumer 可记录 `framework.bundle_fingerprint` 做 byte-level materialization verification；
- source / plan / derived / generated 边界明确；
- deterministic validate/build/tests；
- 需要时 structural change 执行 `spec → plan → tasks → implementation → verification → acceptance`；
- Canon migration 使用 exact before-state、evidence、dependency impact、post-condition、rollback/trace；
- Project build 生成 compact indexed Project bundle，但不制造第二 Canon authority。

Framework runtime materialization 单独见 `release/FRAMEWORK_BUNDLE.zh-CN.md`。

## Session / Runtime

身份模型：

`resource/project != session/thread != run/invocation != checkpoint`

读取：
- `harness/session_runtime/SESSION_RUNTIME.md`
- `harness/session_runtime/RUNTIME_ROUTING.md`
- `harness/session_runtime/RUNTIME_CAPABILITIES.zh-CN.md`
- `harness/control_plane/CONTROL_PLANE.md`

Runtime/session state 只记录“工作做到哪里”，永远不是项目事实。

Capability 表示“技术上能不能尝试”；Authority 表示“允许不允许改变 durable state”。两者不得混淆。

## Semantic Independence

读取 `harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`。

Independent path 可以来自独立本地 Codex/Claude invocation、provider call、MCP/service worker、GitHub job、独立 peer chat、local model 或 human reviewer——但**只有当前 host capability contract 与 independence rule 证明 eligible 时才能使用**。

Router/schema/queue ≠ worker capability。同 session manager role-play 不算独立。Reviewer 默认 fresh-per-fingerprint。

Infrastructure failure 可以 checkpoint + capability re-resolution 后安全 fallback；有效 `semantic_reject` 必须回 owning repair layer，禁止换 reviewer 一直审到 PASS。

## Adaptive Learning · Durable Cycle

读取 `docs/adaptive-learning.zh-CN.md`。

Learning state 与 runtime state、Project Canon 三者分离。

```text
feedback evidence / hypothesis
→ corpus gap
→ capability-aware discovery plan
→ verified discovery + rights/provenance
→ bounded fingerprinted mechanism analysis
→ capability/regression eval evidence
→ promotion candidate
→ activation/promotion gate
→ observe / revise / rollback
```

7.1 使用：
- `learning/learning_store.py`：evidence/hypothesis/gap/candidate；
- `learning/learning_cycle.py`：durable cycle state、artifact hash、consume-once receipt；
- `learning/learning_eval.py`：blind semantic analysis/eval work packet；
- `learning/promotion_gate.py`：deterministic evidence-completeness gate。

Model inference 本身不能成为 durable user taste。Promotion Gate 结果永远不自动授予 write authority。

General Craft 必须具备 cross-work evidence、counterexample/profile boundary、capability + regression eval、provenance、target version、rollback ref、exact-commit green Framework CI 后，才可以标记 promotable。

## Corpus Intelligence

读取：
- `corpus/README.zh-CN.md`
- `corpus/CORPUS_POLICY.zh-CN.md`
- `corpus/CORPUS_INGEST_PROTOCOL.zh-CN.md`

Corpus 是 evidence/benchmark，不是 Canon，也不是作者模仿剪贴簿。

`corpus/corpus_scout.py` 生成 capability-aware discovery request；`corpus/discovery_runtime.py` 只 dispatch 当前 host manifest 已满足的 channel，并校验 returned source/tool provenance、evidence fingerprint、dedupe/diversity 与 rights/storage intent。

**Discovery ≠ Ingestion。** Source access、rights、quotation、tool execution 或 retrieval success 都不得伪造。

## Runtime Philosophy

默认一个 manager。只有 capability、context isolation、真正 independence 或有价值的 parallelism 需要时才增加 bounded worker。

Deterministic code 负责 identity、persistence、state transition、capability resolution、fingerprint、provenance validation、permission、idempotency、consume-once receipt、bundle verification 与 invariant；semantic worker 负责 deterministic test 无法替代的判断。

## Writes

任何 side effect 都需要 least privilege、exact target、precondition/before-state、idempotency、post-condition 与适当 rollback/trace。

Connector、webhook、schedule、Corpus/discovery result、learning hypothesis、promotion-gate result、semantic result、session state 都不会自动授予 Canon 或 Framework-write authority。

## CI / Release / Self-improvement

Normal CI 必须 deterministic，不得静默消耗 API/Codex/Claude/model usage。

Normal CI 必须覆盖 host-capability guard、durable Learning Cycle、blind learning packet、Promotion Gate prerequisite、Corpus discovery provenance/rights boundary、deterministic Framework bundle reproducibility/tamper detection。

Scheduled maintenance 可以 observe / plan / queue，但不能假装执行未声明的 Web/model capability，也不能 auto-promote Framework behavior。

Material Framework behavior change 必须有：
- demonstrated mechanism/capability gap；
- evidence/provenance；
- smallest sufficient change；
- conflict/profile check；
- capability/regression coverage；
- version/rollback point；
- green post-change CI。

外部 Framework 更新只生成 adopt/adapt/reject candidate，不自动成为 dependency。

> 后台生产系统应越来越严格，前台小说应越来越像真实的人在真实压力中行动，而不是越来越像系统输出。
