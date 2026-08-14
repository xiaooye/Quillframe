# Harness Agent · 用一个管理器把小说生产做成受限、可恢复、可信的运行

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>单管理器</kbd>&nbsp;&nbsp;<kbd>恰好一个 TASK MODE</kbd>&nbsp;&nbsp;<kbd>AI-NATIVE</kbd></p>

NovelForge Harness 是通用生产协调器：它把“一个已经验证的小说项目 + 一个明确任务”组织成受边界约束、可以中断恢复的 run。它决定**该加载什么、哪些语义工作属于模型、哪些不变量必须交给确定性代码、什么时候外部等待必须 checkpoint，以及什么东西才有资格进入用户可见层**。

> **边界 ✦** Harness 拥有执行策略；下游项目拥有具体故事事实、Accepted Canon、profile、当前状态、计划、稿件和项目自己的权威规则。

## 01 · AI-native 不等于“模型天然有权威”

NovelForge 之所以 AI-native，是因为真正需要理解小说的语义工作通过 model-readable contract 交给模型，例如：

- 故事与场景推理；
- 人物行为与完整性判断；
- Reader reaction / comparison；
- Revision diagnosis；
- Research interpretation；
- 长程叙事 / 读者 expectation 的解释；
- Memory consolidation proposal；
- 其他无法诚实压成确定性规则的判断。

确定性代码只负责它真正能证明的部分：

- identity 与稳定 ID；
- authority 与 permission；
- fingerprint；
- lifecycle / state transition；
- persistence 与 transaction；
- idempotency / consume-once；
- capability resolution；
- hard context budget 与 stage isolation；
- typed-result validation；
- release invariant。

模型输出默认只是 evidence 或 proposal，除非另一个明确的权威机制赋予它更高权限。

## 02 · 默认只有一个 manager

只有在独立 worker 真正提供额外价值时才拆出去，例如：

- 强制独立语义判断；
- 上下文隔离；
- 另一种已经证明可用的工具 / 权限 / runtime capability；
- 对 immutable input 做有价值的并行分析；
- 人工审阅。

不要为了“看起来像多智能体系统”制造 agent round-table。每多一个 worker，就增加上下文、身份、协调、失败恢复和结果绑定成本，因此必须有明确理由。

## 03 · 每个用户可见 run 恰好一个 primary task mode

合法模式：

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

用户明确指定时严格服从。

一个模式内部可以调用共享 subroutine，但不能静默制造另一个模式的用户可见副作用。例如：

- DRAFT 不会自动 SETTLE；
- AUDIT 不会顺手重写稿件；
- RESEARCH 不会自动把现实事实采用进世界状态；
- LEARN 不会自动把候选规则晋升成 durable behavior。

## 04 · 做语义工作前先建立 authority

一次新的 manager run 按顺序解析：

1. 当前 / pinned Framework manifest 与 execution contract；
2. 下游项目 manifest + exact framework lock；
3. Project Adapter validation 与 logical paths；
4. 恰好一个 task mode；
5. manager session + run identity；
6. authority cutoff 与所需 permission；
7. sparse Context Manifest；
8. 当前 run 真正需要的 host/runtime capabilities。

Provider history 或旧聊天 session 不能代替 bootstrap。

如果项目锁定了 framework bundle / fingerprint，必须先验证 materialized Framework，再依赖其中 contract。

## 05 · Context broker：Schema 完整，注入稀疏

Context 既昂贵，也会污染。无关信息浪费预算；future-plan 会泄漏；regression 坏例会 priming；全局知识会越界进人物。

每次 invocation，manager 都应该知道：

- 哪个对象被放进来了；
- 为什么要放；
- authority class；
- source / fingerprint；
- 哪个 stage 可以看到；
- 是否属于 derived / 可失效视图；
- worker 需要完整对象还是受限 projection。

Harness 可以使用 Context Inspector、memory tiers 和 editable memory control，但“被持久化”永远不等于“自动进入 prompt”。

Writer pre-draft、post-draft critic、independent reviewer 与 never-inject 材料必须继续分层。

详见 [上下文与记忆](../docs/context-and-memory.zh-CN.md)。

## 06 · DRAFT / REVISE 生产图

通用生产图是一条 gated sequence，不是一次 completion call：

```text
Context Freeze
→ Story / Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ 生成后诊断 / Regression / Semantic Review
→ 回到 owning mechanism 修复
→ Reader Engagement
→ Continuity / State Audit
→ 必要的 Independent Semantic Gate
→ User-visible Gate
```

项目可以增加 profile-specific 检查，但不能破坏这些关键边界：

- Raw Draft 永远只在内部；
- Regression 坏例只能生成后加载；
- Surface clean 只是质量地板；
- SAFE-BUT-FLAT 必须回上游；
- 强制 independent judgment 必须真的独立；
- 用户 acceptance 与 Canon settlement 永远是两件事。

## 07 · Model-readable semantic contract

Harness 不需要为每一种文学判断写一个 Python “critic engine”。它从 `semantic_workers/model_contracts.json` 打包受限 semantic job。

Job 至少声明：

- kind 与 subject；
- bounded input / context；
- rubric；
- output contract；
- permission；
- semantic fingerprint；
- execution provenance 要求。

模型负责 judgment。确定性 infrastructure 只在 result 影响 workflow state 之前验证 identity、fingerprint、permission 和 typed output。

内部 diagnostic 不会因为用了模型就自动变成 independent gate。

## 08 · Capability broker

做 tool / external work 前，先推导需求，再对 typed host capability manifest 做解析。

一条 capability claim 应回答：

- 现在真的 available 吗？
- 证据是什么？
- permission class 是什么？
- 是否需要用户交互？
- 是否执行模型推理？
- usage / cost class 是什么？

没有声明的 capability 就按 unavailable 处理。Provider 名字、PATH 上存在 executable、旧 session 曾经可用、存在 network primitive、文档写着支持，或者模型自己说“我能做”，都不足以证明远端授权现在成立。

**Capability ≠ authority。** 技术上能写文件，不代表有 Canon write 权限。

## 09 · Session、Run、Checkpoint、Result

执行身份必须分开：

```text
project/resource
→ session
→ run
→ checkpoint
→ event / handoff / job
→ result
→ validated consume-once receipt
→ resume
```

Provider-native conversation / thread ID 可以作为 metadata，但不是 story authority。

以下时点应 checkpoint：

- 等待用户 / external；
- 强制 independent review；
- consequential Project write；
- Canon settlement；
- 长时间 discovery / learning / semantic handoff。

Resume 时重新验证 Framework / Project authority、artifact fingerprint、approval / write precondition，以及**pending external work 当前仍需要的 capability**。已经完成的 side effect 绝不能重复。

## 10 · Independent semantic integrity

当一个 gate 被定义为 independent，manager 可以做：

`freeze → package → checkpoint → dispatch → await → validate → consume → route repair`

但不能自己换一个内部 role label 就代替 reviewer 判断。

Semantic fingerprint 发生实质变化后，reviewer 通常应 fresh。仅 infrastructure retry、而语义问题完全没变时，可以换 eligible transport 保持同一 fingerprint。

有效 semantic reject 就是有效判断。它应该进入 repair，不允许 reviewer shopping。

## 11 · LEARN / CORPUS / SYSTEM-IMPROVE

学习服从证据，而不是模型自信度。

典型 graph：

```text
feedback / hypothesis
→ 最窄 scope
→ evidence gap
→ 合法、capability-aware discovery
→ bounded semantic analysis
→ counterexample / profile boundary
→ eval evidence
→ candidate
→ explicit activation / promotion gate
→ observe / rollback
```

必须保持：

- discovery ≠ ingestion；
- corpus ≠ Canon；
- semantic analysis ≠ promotion；
- model inference alone ≠ durable user taste；
- deterministic promotion readiness ≠ write authority；
- project-specific story fact 不得泄漏进 Generic Framework。

## 12 · Writes 与 Settlement

每个 consequential side effect 都应具备：

- least privilege；
- exact target；
- expected before-state / precondition；
- idempotency strategy；
- 必要时的 checkpoint / write intent；
- post-condition verification；
- trace / rollback semantics。

Canon settlement 只有在项目明确 acceptance 之后才合法，并且必须遵守 Canon / State transaction contract。

Connector、webhook、schedule、worker result、session state、learning state、CI、corpus 或 model judgment 都不会因为“已经到达系统”就自动获得写权限。

## 13 · Completion state 必须说真话

面向用户的 workflow state 必须准确。视模式不同，可以包括：

`complete · review · awaiting_user · awaiting_external · semantic_pending · failed_gate · blocked · settlement_incomplete`

内部的 candidate-ready、plateau、promotion-ready，或者某个 deterministic validator 通过，并不等于 durable behavior 或 Canon 已经改变。

Mandatory gate 还没解决时，绝不能把 artifact 称为 production-ready。

## 14 · 相关契约

- [Orchestration Protocol](ORCHESTRATION_PROTOCOL.zh-CN.md)：不同 task mode 的运行图与共享 subroutine。
- [Session Runtime](session_runtime/SESSION_RUNTIME.zh-CN.md)：身份、生命周期、checkpoint 与 resume。
- [Runtime Routing](session_runtime/RUNTIME_ROUTING.zh-CN.md)：基于 capability 的执行路径选择。
- [Control Plane](control_plane/CONTROL_PLANE.zh-CN.md)：持久 event、handoff、lease 与 consume-once 状态。
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)：受限模型判断与独立审查完整性。
- [正典与状态模型](../core/CANON_STATE.zh-CN.md)：权威与结算。
