# 编排协议 · 一个 task mode，模型做语义决策，runtime 执行精确门槛

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>MODE GRAPHS</kbd>&nbsp;&nbsp;<kbd>CHECKPOINTED SIDE EFFECTS</kbd></p>

本协议定义 manager 如何把一个已验证的 task mode 变成可恢复 run graph。Orchestration 控制**顺序、capability 与 gate**，不判断文学意义。

## 01 · Common prefix

每个 mode 都先执行：

```text
resolve current/pinned Framework authority
→ validate Project + exact lock/fingerprint
→ choose single task_mode
→ create/resume manager session + run
→ resolve authority cutoff + permissions
→ establish sparse mechanically eligible context candidates
→ resolve current capabilities
→ execute the selected mode graph
```

Resume 永远不能信任 stale environment / transcript。继续 workflow cursor 前必须重新验证 Framework/Project compatibility、relevant fingerprints、approval/write intent 与 pending capabilities。

## 02 · Shared semantic subroutine

任何 semantic task 都走同一个边界：

```text
freeze semantic subject
→ choose exact model contract / rule set / reader profile
→ package bounded authorized evidence
→ compute semantic fingerprint
→ checkpoint if work may leave the current invocation
→ execute through an eligible model/runtime
→ receive typed result
→ validate identity + fingerprint + provenance + output envelope
→ consume once at the named workflow step
```

模型负责 interpretation，runtime 负责 exact execution binding。

有效的语义拒绝是结果，不是 infrastructure failure。

## 03 · DRAFT / REVISE

默认 adaptive graph：

```text
authority/session bootstrap
→ model-owned search/context selection（必要时 `context.select`）
→ Context Inspector / Context Assembly exact boundary
→ Story / Canon Preflight
→ Planning Commitment State
→ Character Private State
→ Character Action / Tactic Simulation
→ Scene Collision / World Resolution
→ compact Writer-safe Realization Projection
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ freeze exact candidate fingerprint
→ Blind Reader (`reader.engagement_audit`)
→ Semantic Rule Auditor when required (`quality.semantic_rule_audit`)
→ Editor Repair Spec (`editor.repair_spec`)
→ repair / fresh realization / incumbent-challenger comparison as warranted
→ Continuity / state audit
→ required independent semantic gate
→ User-visible Gate
```

### Context rule

`context.select` 判断 semantic relevance、search/reformulation 与 sufficiency。`context_inspector.py`、`context_assembly.py` v2、memory packing 只验证 mechanical eligibility、exact refs/fingerprints、stage/private boundary、explicit pin 与 hard budget。

不存在 deterministic “required literary context class” gate。某个 operation 在机械意义上必须拿到特定 authoritative artifact 时，caller 传 exact required ref/fingerprint。

### Reader / Rule Auditor / Editor rule

Blind Reader 只看 reader-visible evidence，不接收 creator-private intent、taxonomy/HF/telemetry priming 或 rule-audit instruction。

Rule Auditor 获取 Reader 不该看到的 authoritative hard rules，并判断 semantic applicability / violation。

Editor 综合这些 finding 与 authorized story evidence，**语义上**选择 repair owner、repair plan、comparison need，以及 `local_or_bounded_repair | fresh_realization`。Runtime 不把 failure code/owner/scope 映射成 literary depth。

### Repair routing

Diagnosis 可以指出 story、plan、scene、character、reader pressure、surface、continuity、context、research、runtime、human owner，但**当前 candidate 的 mechanism / depth 由 Editor/model 决定**。Deterministic orchestration 只路由已做出的 decision，并执行 chosen information boundary。

例如 HF-30 可能需要 interaction/character/realization repair，而 legitimate formal completeness 可能完全正确。Python 不能根据 dialogue length 或固定 code table 推断这两者。

REVISE 从 frozen candidate + explicit goals/evidence 开始，并优先保留已经有效的内容。

## 04 · DESIGN / PLAN

`DESIGN-BOOK`、`DESIGN-VOLUME`、`PLAN-UNIT`、`PLAN-CHAPTER` 在 Project authority 下创建/更新 planning artifact。

Planner semantic intelligence 决定：

- 现在需要规划什么；
- 什么 detail depth 有价值；
- 哪些部分保留 open / uncertain；
- 是否需要 research；
- 是否应调整 near future。

Deterministic planning-horizon infrastructure 可以执行 declared commitment/depth、promoter class、evidence refs、exact before-state 与 fingerprints，但不能把 universal chapter/volume/time horizon 冒充 planning quality truth。

Planned event 继续与 occurred/Accepted state 分离。

## 05 · RESEARCH

Research graph：

```text
question
→ resolve allowed search/fetch capabilities
→ model formulates/selects queries and sources
→ runtime executes authorized retrieval with provenance
→ model decides relevance / continuation / stopping
→ exact source-bound evidence
→ bounded interpretation
→ Project/plan consumption
```

`real-world fact ≠ fictionalization ≠ character knowledge ≠ Canon`。

External source text 不能重定义 runtime authority。

## 06 · CORPUS-INGEST

Corpus work 明确分开：

`discovery → source verification/provenance → rights gate → bounded ingestion/analysis → benchmark/eval evidence`

Discovery ≠ ingestion；Corpus ≠ Canon；analysis ≠ automatic Writer context / Framework promotion。

## 07 · LEARN

Learning graph：

```text
explicit feedback/evidence
→ model-owned preference interpretation
→ scoped durable evidence/hypothesis
→ contradiction/counterexample/eval work
→ durable activation 被提出时运行 semantic promotion review
→ deterministic binding + authority prerequisites
→ active eligibility
→ model 为未来任务选择 relevant active hypothesis IDs
```

Numeric evidence-count threshold 不能代替 semantic evidence sufficiency。Promotion Gate 不授予 write authority。`general_craft` 继续属于 Framework `SYSTEM-IMPROVE`。

## 08 · AUDIT

AUDIT 只检查并报告 deterministic violation / semantic finding，不偷偷修改 manuscript、Canon 或 durable preference。

Audit 后需要 repair 时，进入对应的 authorized mode/run boundary。

## 09 · SETTLE

只有 explicit acceptance / authorized Canon intent 才允许 settlement：

```text
freeze accepted artifact + fingerprint
→ derive exact State Delta
→ validate target + before-state/CAS
→ checkpoint / write intent / authorization
→ authorized transaction
→ required projections + receipts
→ postcondition verification
```

Settlement runtime 不推断 acceptance / literary meaning。

## 10 · SYSTEM-IMPROVE

Material Framework change 按以下链路执行：

```text
live bootstrap
→ current-candidate reconciliation / owner map / rollback point
→ current external research
→ ADOPT / ADAPT / REJECT / DEFER decisions
→ deterministic-overreach audit
→ architecture decision
→ spec / plan / tasks
→ incremental implementation
→ ablations + deterministic tests
→ blind semantic eval / independent gate when required
→ CI / security / compatibility
→ docs / manifest synchronization
→ human-review readiness
```

每次 consequential write 前重新验证 current branch/HEAD/before-state。Long operation 必须 bounded，禁止 blind waiting。Pre-existing unrelated failure 与 candidate-owned failure 分开报告。

## 11 · Parallelism / multi-agent discipline

只有 immutable work 真有收益时才 parallelize。Agent 拆分要有真实 information boundary、independent evaluation、private state 或 proven specialist benefit。

不要为了制造 consensus theater 而让多个 agent 重复同一 judgment。

## 12 · Completion states

Truthful state 包括：

`complete | review | awaiting_user | awaiting_external | semantic_pending | semantic_invalid | failed_gate | blocked | settlement_incomplete`

Required semantic result 没真正执行就是 pending。Green workflow 只记录 `PENDING_MODEL` 时，也不是 semantic PASS。

## 相关合同

- [Harness Agent](HARNESS_AGENT.zh-CN.md)
- [Session Runtime](session_runtime/SESSION_RUNTIME.zh-CN.md)
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)
- [生产流水线](../docs/production-pipeline.zh-CN.md)
- [上下文与记忆](../docs/context-and-memory.zh-CN.md)
- [自适应学习](../docs/adaptive-learning.zh-CN.md)
- [正典与状态模型](../core/CANON_STATE.zh-CN.md)
