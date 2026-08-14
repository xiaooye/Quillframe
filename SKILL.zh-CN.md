# NovelForge Skill Contract · v7 中文版

## 定位

NovelForge 是完全 project-agnostic 的小说生产 Framework。它拥有通用 Story/Character/Canon 机制、Surface/Reader 质量基础、Harness/runtime orchestration、Corpus Intelligence、自适应学习、Eval/Regression、Project Engineering Contract 与 provider-neutral integrations。

Framework 内不得内置任何具体小说、人物、剧情、Canon 或用户私有 taste data。

## Bootstrap

任何 NovelForge 任务：

1. 读取 `HARNESS_MANIFEST.yaml`；
2. 读取 `harness/HARNESS_AGENT.md`；
3. 确定且只确定一个 primary task_mode；
4. 通过 `novelforge.toml + novelforge.lock.json` 或其他受支持 adapter 解析、验证 consuming project；
5. 创建/恢复 manager session + run；
6. 建立 sparse Context Manifest；
7. 只加载当前任务需要的 project object 与 framework module；
8. external wait / consequential write 前 checkpoint；
9. mandatory semantic judgment 必须来自真正独立的 invocation/session；
10. 适用 quality/authority gate 全部通过后才能 expose/write；
11. resume 后重新验证 project authority、lockfile compatibility、fingerprints 与 pending approval。

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
- Regression/benchmark 如需 critic isolation，只能在 Raw Draft 冻结后进入对应 critic/auditor context。

## Story / Canon Stack

通用机制：
- `core/STORY_SYSTEM.zh-CN.md`
- `core/CHARACTER_SYSTEM.zh-CN.md`
- `core/CANON_STATE.zh-CN.md`

具体 Project 提供 BOOK/VOL/ARC/UNIT/CH/SCN 实例、人物/世界/关系状态、research、plans 与 Accepted Canon。

Plan ≠ Canon。Review ≠ Accepted。Session ≠ Canon。Corpus ≠ Canon。Semantic Judgment ≠ Canon。

## Project Engineering

每一本 consuming novel 都应该满足 Project SDK：
- `novelforge.toml` 项目 manifest；
- `novelforge.lock.json` framework lock；
- source / plan / derived / generated 边界明确；
- deterministic validate/build/tests；
- 需要时 structural change 执行 `spec → plan → tasks → implementation → verification → acceptance`；
- Canon migration 使用 exact before-state、evidence、dependency impact、post-condition、rollback/trace；
- build 生成 compact indexed bundle，不制造第二 authority。

见 `docs/project-sdk.zh-CN.md` 与 `project_sdk.py`。

## Session / Runtime

身份模型：

`resource/project != session/thread != run/invocation != checkpoint`

读取：
- `harness/session_runtime/SESSION_RUNTIME.md`
- `harness/session_runtime/RUNTIME_ROUTING.md`
- `harness/control_plane/CONTROL_PLANE.md`

Runtime/session state 只记录“工作做到哪里”，永远不是项目事实。

## Semantic Independence

读取 `harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.md`。

Independent path 可以来自：独立本地 Codex/Claude invocation、provider call、MCP/service worker、GitHub job、独立 peer chat、local model 或 human reviewer。

Router/schema/queue ≠ worker capability。同 session manager role-play 不算独立。Reviewer 默认 fresh-per-fingerprint。

Infrastructure failure 可以安全 fallback；有效 `semantic_reject` 必须回 owning repair layer，禁止换 reviewer 一直审到 PASS。

## Adaptive Learning

读取 `docs/adaptive-learning.zh-CN.md`。

Learning state 与 runtime state、project Canon 三者分离。

```text
feedback evidence
→ preference hypothesis
→ contradiction/profile check
→ corpus gap
→ discovery
→ rights/provenance gate
→ mechanism analysis
→ personalized/general eval
→ active profile / candidate promotion / rollback
```

模型推断本身不能成为 durable user taste。General craft promotion 必须有 evidence、counterexample/profile boundary、eval/regression、version 与 rollback。

## Corpus Intelligence

读取：
- `corpus/README.zh-CN.md`
- `corpus/CORPUS_POLICY.zh-CN.md`
- `corpus/CORPUS_INGEST_PROTOCOL.zh-CN.md`

Corpus 是 evidence/benchmark，不是 Canon，也不是作者模仿剪贴簿。允许通过已授权 host tool/connector 自主 discovery；不得伪造 source access、rights 或 quotation。

## Runtime Philosophy

默认一个 manager。只有 capability、context isolation、真正 independence 或有价值的 parallelism 需要时才增加 bounded worker。

Deterministic code 负责 identity、persistence、state transition、fingerprint、permission、idempotency、invariant；semantic worker 负责无法被 deterministic test 取代的判断。

## Writes

任何 side effect 都需要 least privilege、exact target、precondition/before-state、idempotency、post-condition 与适当 rollback/trace。

Connector、webhook、schedule、corpus result、learning hypothesis、semantic result、session state 都不会自动授予 Canon authority。

## CI / Self-improvement

Normal CI 必须 deterministic，不得静默消耗 API/Codex/Claude/model usage。

Material framework behavior change 必须有：
- demonstrated mechanism/capability gap；
- evidence/provenance；
- smallest sufficient change；
- conflict/profile check；
- capability/regression coverage；
- version/rollback point；
- green post-change CI。

外部 framework 更新只生成 adopt/adapt/reject candidate，不自动成为 dependency。

> 后台生产系统应越来越严格，前台小说应越来越像真实的人在真实压力中行动，而不是越来越像系统输出。
