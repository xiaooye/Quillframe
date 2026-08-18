# Harness Agent · 一个 manager，模型判断意义，确定性系统保证执行真相

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>ONE MANAGER</kbd>&nbsp;&nbsp;<kbd>ONE PRIMARY MODE</kbd>&nbsp;&nbsp;<kbd>AI-NATIVE</kbd></p>

Quillframe Harness 把经过验证的小说 Project 与明确任务组织成一轮 bounded、resumable run。它拥有 execution policy，不拥有 story truth。

> **Project authority 拥有 Canon 与项目专属事实；模型拥有 semantic fiction judgment；deterministic runtime 拥有 identity、power、persistence 与 exact execution state。**

## 01 · AI-native 不等于 model-authoritative

需要理解意义的工作默认由模型承担，例如：

- search intent、query formulation、relevance、continuation / stopping；
- story / scene / planning interpretation；
- character action、motivation、plausible inference、integrity；
- Reader experience；
- semantic hard-rule applicability / violation；
- repair mechanism / depth；
- research interpretation；
- feedback 是否 learnable、feedback / preference interpretation、scope / contradiction / reconciliation。

Deterministic code 只保留可机械证明的不变量：

- Project/resource/session/run/checkpoint identity；
- permissions / capability boundaries；
- exact artifacts、hashes、fingerprints；
- provenance / exact-source binding；
- stage / private-state visibility；
- persistence、CAS、transaction、idempotency；
- hard budgets / resource limits；
- typed envelope/result/receipt validation；
- required semantic execution 是否真实发生，以及是否绑定 exact candidate；
- settlement / release-role invariant。

Semantic result 默认只是 evidence / proposal，除非另外的 authority mechanism 明确授予更多权力。

## 02 · 默认只用一个 manager

优先一个能力足够强的 manager/agent。只有以下情况能证明收益时才拆分：

- mandatory independent evaluation；
- information/context isolation；
- per-character private state；
- genuinely different permission/tool/runtime；
- immutable input 上真正有价值的 parallel work；
- human review。

不要为了模仿软件组织架构而制造 multi-agent round-table。

## 03 · 恰好一个 primary task mode

每个 user-visible run 只能有一个 primary mode：

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

Mode 可以内部调用共享 subroutine，但不能悄悄执行另一个 mode 的 user-visible side effect。DRAFT 不自动 SETTLE；AUDIT 不偷改 manuscript；LEARN 不自授 durable behavior。

**Basic feedback Learning intake 是 bounded internal subroutine，不是第二个 primary mode。** 用户在 REVISE/DRAFT/PLAN 等 mode 对既有产物给出明确评价时，不需要额外切换 LEARN 才能保存 evidence candidate。LEARN 继续用于 dedicated learning analysis、Corpus expansion、hypothesis evaluation 与 promotion work。

## 04 · Semantic work 前先 bootstrap live authority

Fresh manager 依次解析：

1. current/pinned Framework manifest / identity；
2. consuming Project manifest + exact lock/fingerprint；
3. Project Adapter / logical paths；
4. 只能有一个 task mode；
5. manager session/run identity；
6. authority cutoff + permissions；
7. sparse Context Manifest / candidate set；
8. current host capabilities。

旧聊天 / provider session 不能替代 bootstrap authority。Resume 必须重新验证 Framework/Project compatibility、current fingerprints、approval/write precondition 与 pending capabilities。

## 05 · Search / Context：语义选择，确定性边界

Manager/model 自己判断缺什么、搜什么、query 怎么写、哪个结果真正相关、是否 reformulate / continue、什么保留、什么时候 evidence 足够。

Runtime 可以提供 search/fetch/extract/index primitive 与 candidate generation，但 recency、fixed last-N、vector similarity、top-k、item class 都不能冒充 narrative truth。

`context_inspector.py` 只检查 mechanical eligibility / stage / protected-edit state，并明确拒绝 `relevance` 字段。

`context_assembly.py` v2 在 semantic selection **之后**运行，只验证 exact selected/source refs、receiving stage、hidden/private/invalidated state、fingerprints，以及操作在机械意义上确实要求时的 exact higher-authority refs。它不再执行 literary class/purpose obligation，也不宣称 semantic sufficiency。

Hard-budget packing 可以在 selection 后执行 whole-item resource limit。Persistent storage 不代表 automatic prompt injection。

## 06 · DRAFT / REVISE production responsibilities

默认 adaptive path 大致是：

```text
authority/session bootstrap
→ agent-owned context/search
→ deterministic exact-set/stage/fingerprint verification
→ Story / Canon + planning preflight
→ private character state
→ character.action_propose
→ scene.resolve_actions
→ compact writer-safe realization
→ Reader Pressure
→ event-first Raw Draft
→ Surface realization
→ freeze candidate fingerprint
→ Blind Reader (`reader.engagement_audit`)
→ Semantic Rule Auditor when required (`quality.semantic_rule_audit`)
→ Editor repair spec (`editor.repair_spec`)
→ repair / challenger comparison as warranted
→ continuity/state checks
→ required independent semantic gate
→ user-visible Review Draft
```

必须保留这些边界：

- Raw Draft 是内部产物；
- regression bad examples 在 Raw Draft/candidate freeze 前不得进入 Writer context；
- private character state 是 causal evidence，不是 Writer exposition payload；
- Surface clean 只是地板，不是 production readiness；
- Blind Reader 不是 hard-rule checklist executor；
- Rule Auditor 获得 Reader 不该看到的 authoritative rule material；
- Editor 语义上选择 repair owner 与 generation mode；
- `repair_policy.py` 只执行所选 mode 对 writer-context 的信息边界；
- material candidate change 会使旧 fingerprint-bound review result 失效；
- explicit acceptance 与 SETTLE 继续分离。

如果用户在 production loop 中给出 feedback，当前明确指令立即约束当前 run；同一 turn 也可以独立进入 automatic Learning intake。Learning capture 不需要等 durable promotion 才让当前指令生效。

## 07 · Model-readable semantic contracts

Catalog authority：`harness/semantic_workers/model_contract_catalog.json`。

Semantic work 通过这个 progressive-disclosure catalog 精确解析 contract ID。Job 绑定：

- kind / subject / exact contract version；
- bounded input/context；
- rubric；
- output contract；
- permissions；
- semantic fingerprint；
- execution provenance requirement。

模型负责 judgment。Runtime 只验证 identity/fingerprint/permission/type/provenance，并 consume-once。内部 semantic work 不自动获得 independent 属性。

`learning.preference_interpret` 先语义判断 `capture | skip`；capture 时再判断最窄 scope、mechanism 与 exact hypothesis relation。不要用关键词/regex 判断“是不是反馈”。该 contract 默认 `independent_gate=false`，不因名字里有 Learning 就强制启动昂贵独立 reviewer。

## 08 · Capability broker

任何 tool / external action 都必须针对 current host capabilities 重新解析。Undeclared capability 视为 unavailable。

Provider name、PATH 上的 executable、旧 session 记忆、network primitive、documentation page、model self-assertion 都不是 authorization proof。

Capability 也不等于 authority：filesystem write capability 不代表 Canon write permission。

Credential / authority token 不进入普通 semantic context。

## 09 · Durable session != model context

Execution identity 保持分层：

```text
Project/resource
→ session
→ run
→ checkpoint
→ event/handoff/job
→ result
→ validated consume-once receipt
→ resume
```

External wait、required independent review、consequential write 前按合同 checkpoint。Context-window 丢失可以恢复，因为 authority state 存在 durable artifacts/events/checkpoints，而不是聊天 transcript。

`feedback.observed` 也遵守这个模型：同一 durable event 可以被 Author Steering 与 Learning Intake 以不同 consumer identity 分别 consume。若 semantic capability 暂不可用，Learning 状态保持 `awaiting_semantic`，后续 resume 重核 event/hash/job fingerprint 后继续，不丢反馈、不 heuristic 猜测。

## 10 · Independent semantic integrity

Gate 真正要求 independence 时，manager 可以：

`freeze → package → checkpoint → dispatch → await → validate → consume → route repair`

但不能换个 internal role label 就自己完成 judgment。

Materially changed candidate 默认需要新的 bound review，除非合同显式允许 reuse。Transport failure 可切换 eligible transport；有效的语义拒绝必须进入 repair，也不能反复更换评审直到有人接受 candidate。

没有 eligible independent provider/model 时必须 `PENDING_MODEL`，绝不能 PASS。

## 11 · LEARN / CORPUS / SYSTEM-IMPROVE

Learning 必须分开：

```text
feedback observation
!= semantic interpretation
!= evidence
!= hypothesis
!= promotion review
!= write authority
!= active eligibility
!= current relevance
```

### Automatic feedback intake

对 user / authorized human 针对已有模型产物、创作结果或工作方式的 semantic feedback：

```text
feedback.observed
├→ current-run Author Steering（适用时）
└→ learning/feedback_intake.py
   → learning.preference_interpret
   → capture | skip
   → Author Model evidence/hypothesis candidate
   → consumer-specific receipt
```

两个 consumer 相互独立。Steering consume 不会让 Learning 看不到 event；Learning retry 也不能重复写同一 evidence。

Automatic intake 默认所有 activation/write authority 为 false。它不会自动修改 Project Profile、durable user taste、General Craft、Framework behavior 或 Canon。

同一个 event retry 使用 stable evidence identity；真正不同的 user turns 可以提供独立 evidence，由模型决定 strengthen/contest/supersede/split。Contradiction 是一等 semantic operation，不由 Python 的字符串/embedding similarity 决定。

Rejected output 只可保存 ref/fingerprint + negative meaning，不把 rejected prose 当 positive exemplar，也不反向注入 Writer pre-draft context。

`learning/feedback_query.py` 是 side-effect-free read-only observability surface；不创建表、不 consume、不执行 model，也不暴露 whole conversation / private reasoning / hidden gold。

### Durable activation and General Craft

`learning.preference_interpret` 解释 feedback；LearningStore / Author Model 在 authority/CAS 下持久化 evidence/hypothesis。Promotion Gate 验证 exact bound semantic review 与客观 prerequisite，不用 arbitrary evidence-count threshold 冒充 semantic truth，也不能授予 write authority。

Active preference 不会自动注入；manager/model 为当前任务显式选择 relevant active hypothesis IDs。Current explicit request 始终高于旧 active preference。

General Craft change 继续属于 `SYSTEM-IMPROVE`，必须有 current research、counterexamples/evals、compatibility、rollback 与 explicit promotion authority。Production feedback 中的 universal claim 只能成为 candidate evidence，不能自己升级成 Framework rule。

## 12 · Writes / Settlement

每个 consequential side effect 都需要 least privilege、exact target、before-state/precondition、idempotency、必要时 checkpoint/write intent、postcondition verification、trace/rollback semantics。

Canon settlement 只有在 explicit Project acceptance / authorized Canon intent 后才合法。Connector、schedule、webhook、model result、learning state、feedback intake、CI、corpus evidence 都不会因为“到达系统”就自动授予 write authority。

## 13 · Truthful states

合法状态包括：

`complete · review · awaiting_user · awaiting_external · semantic_pending · semantic_invalid · failed_gate · blocked · settlement_incomplete`

Learning intake 内部可以更细地记录 `observed | awaiting_semantic | skipped | persisted | blocked | failed`；这不是新的 primary task mode。

Green deterministic workflow 不能替代 required semantic judgment；没有真正执行的 semantic job 继续 pending。Required gate 未解决时不得声称 production-ready。

## 14 · SYSTEM-IMPROVE execution discipline

Material Framework work 按以下链路执行：

```text
live bootstrap
→ candidate/owner reconciliation
→ current research
→ overreach audit
→ spec/plan/tasks
→ incremental implementation
→ ablations + deterministic tests
→ independent semantic evidence when required
→ CI/security/compatibility/docs synchronization
→ human-review readiness
```

每次 consequential write 前重新验证 current branch/HEAD/before-state。Long operation 必须 bounded；同一 pending 状态没有新 evidence 时转入 jobs/logs diagnosis，而不是 blind waiting。Candidate-owned failure 与 pre-existing unrelated repository debt 必须区分。

## 相关合同

- [编排协议](ORCHESTRATION_PROTOCOL.zh-CN.md)
- [Session Runtime](session_runtime/SESSION_RUNTIME.zh-CN.md)
- [Runtime Routing](session_runtime/RUNTIME_ROUTING.zh-CN.md)
- [Control Plane](control_plane/CONTROL_PLANE.zh-CN.md)
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)
- [上下文与记忆](../docs/context-and-memory.zh-CN.md)
- [生产流水线](../docs/production-pipeline.zh-CN.md)
- [自适应学习](../docs/adaptive-learning.zh-CN.md)
- [正典与状态模型](../core/CANON_STATE.zh-CN.md)
