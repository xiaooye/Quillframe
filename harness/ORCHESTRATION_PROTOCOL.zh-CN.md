# Orchestration Protocol · 一个任务模式、显式门槛、失败回到真正拥有问题的机制

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>MODE GRAPH</kbd>&nbsp;&nbsp;<kbd>副作用前 CHECKPOINT</kbd></p>

本协议规定 NovelForge manager 如何把一个已经验证的 task mode 变成可执行 run graph。它自己不判断文学意义；semantic node 通过 model-readable contract 交给模型，identity、permission、fingerprint、persistence、routing 和 transaction 则保持确定性。

> **边界 ✦** Orchestration 负责“顺序与门槛”。故事事实仍属于 Project authority；语义判断仍属于受限 contract 中的模型 worker。

## 01 · 所有模式共享的前缀

每种模式都从同一条执行主干开始：

```text
解析 Framework authority
→ 验证 Project + exact lock
→ 选择恰好一个 task_mode
→ 创建 / 恢复 manager session + run
→ 解析 authority cutoff + permission
→ 构建 sparse Context Manifest
→ 解析本次真正需要的 capability
→ 执行当前 mode graph
```

Resume 不能假设昨天的环境今天仍然一样：

```text
加载 checkpoint
→ 重新验证 Framework / Project compatibility
→ 重新验证 artifact fingerprint
→ 按当前 authority 重建允许注入的 sparse context
→ 重新验证 approval / write intent
→ 重新解析 pending external capability
→ 验证并 consume pending result once
→ 从保存的 workflow cursor 继续
```

## 02 · 共享 semantic subroutine

任何语义任务——Reader reaction、Character Integrity、Revision diagnosis、Research interpretation 或 mandatory independent gate——都走同一种通用边界：

```text
冻结 semantic subject
→ 选择 model contract / rubric
→ 打包 bounded context + permission
→ 计算 semantic fingerprint
→ 如果工作会离开当前 invocation，则 checkpoint
→ 路由 eligible runtime
→ execute / handoff / relay / await
→ 收到 typed result
→ 验证 identity + fingerprint + provenance + output contract
→ 在命名 workflow step consume once
```

Input、rubric 或 output contract 发生实质变化，就必须产生新 semantic fingerprint。仅 infrastructure retry、而冻结的语义问题完全相同时，可以保持原 fingerprint。

有效 semantic reject 是语义结果，不是基础设施失败。

## 03 · DRAFT / REVISE

默认生产图：

```text
Context Freeze
→ Story / Canon Preflight
→ Scene Simulation
→ Character Simulation
→ Reader Pressure
→ Event-first Raw Draft
→ Surface Realization
→ freeze candidate
→ 生成后 diagnostics / regression
→ 回 owning mechanism 修复
→ Reader Engagement
→ Continuity / State Audit
→ 必要的 Independent Semantic Gate
→ User-visible Gate
```

关键顺序规则：

- Raw Draft 不对用户展示；
- Regression 坏例和类似 answer key 的证据只能生成后加载；
- Scene / Character / Reader simulation 可以是模型语义工作，但外围 durable invariant 仍由确定性代码维护；
- Surface clean 仍然可能 Reader Engagement fail；
- SAFE-BUT-FLAT 回上游，不做泛化 line polish；
- repair 后的 candidate 内容变了，就要在 fingerprint-bound gate 前产生新 content fingerprint。

REVISE 从冻结 candidate + 明确 repair goal / evidence 开始，不预设所有维度都必须重写。

## 04 · Failure routing

Orchestrator 应先诊断，再决定修复深度。

```text
孤立 Surface 缺陷              → 局部 rewrite
Surface failure 成簇           → block / whole-scene realization
reader-grip / SAFE-BUT-FLAT     → Reader Pressure + Scene Simulation
人物完整性失败                 → Character Simulation / state reasoning
story / plan failure            → Story / Plan
continuity / state mismatch     → Continuity / State owner
context 污染 / stale            → 重建 Context Manifest
derived memory 错误             → invalidate / rebuild memory
research uncertainty            → RESEARCH
runtime / tool failure          → capability / transport 层
艺术方向无法自动决定            → user / human decision
```

不要拿高层失败的文字症状做表层抛光。

## 05 · DESIGN / PLAN

`DESIGN-BOOK`、`DESIGN-VOLUME`、`PLAN-UNIT`、`PLAN-CHAPTER` 只创建 `proposal` / `active_plan` 等规划 artifact。

它们可以：

- 检查当前 authority；
- 比较多个未来方案；
- 在授权后更新 future plan；
- 建立 dependency 与 expected state delta。

它们不能：

- 把 planned event 当成已经发生；
- 结算 current Canon；
- 把人物未来才会知道的事提前写进当前 knowledge state。

采用 rolling elaboration：越靠近 production frontier 越详细，越远越保持低分辨率与可修改性。

## 06 · RESEARCH

Research 输出 source-bound evidence，而不会因为“查到了现实事实”就自动写进故事。

通用 graph：

```text
research question
→ capability / source selection
→ 尽量检索 authoritative / primary source
→ 保存 source / provenance
→ 必要时做 bounded semantic interpretation
→ REF / CLAIM 等价 evidence
→ 交给用户 / plan 消费
```

严格区分：

`现实事实 ≠ 项目虚构化选择 ≠ 人物知识 ≠ current Canon`

Search capability 从来不授予 project write authority。

## 07 · CORPUS-INGEST

Corpus 工作把 discovery、rights、analysis 与 durable storage 分开：

```text
craft / learning question
→ corpus gap
→ discovery request
→ capability-aware source discovery
→ source verification + provenance
→ rights gate
→ bounded ingestion / analysis
→ benchmark / eval evidence
```

Discovery 不等于 ingestion。Corpus 内容不会变成 Canon，也不能默认注入 writer context。

## 08 · LEARN

Learning 必须使用证据支持的最窄 scope：

`one_off | project | user_taste | general_craft`

通用 graph：

```text
feedback / evidence
→ scope classification
→ hypothesis
→ contradiction / counterexample search
→ corpus / eval gap
→ bounded semantic analysis
→ candidate
→ deterministic evidence-completeness gate
→ explicit activation / promotion / rollback
```

模型重复同一个看法不是新证据。General Craft 比项目内 / 局部学习需要更强的 cross-work evidence。

## 09 · AUDIT

AUDIT 负责检查，不静默修复。

它可以产出：

- deterministic violation；
- semantic finding；
- continuity / state discrepancy；
- stale derived view；
- broken dependency / documentation reference；
- 明确的 proposed repair owner。

如果用户还要求修复，那应成为单独授权的 mode / run，而不是藏在 AUDIT 里的副作用。

## 10 · SETTLE

只有明确 acceptance / Canon instruction 才允许 settlement。

```text
freeze Accepted artifact + fingerprint
→ 推导 exact State Delta
→ 验证 target + before-state
→ 计算 dependency impact
→ checkpoint / write intent
→ authorized mutation
→ rebuild derived views
→ verify post-condition
→ trace / receipt
```

任何 mismatch 都返回 `settlement_incomplete`。禁止猜、禁止部分成功却宣称全部成功、禁止 resume 后重复已经执行的 side effect。

## 11 · SYSTEM-IMPROVE

Material Framework change 应走工程流程，而不是“改一下 prompt”：

```text
evidence / problem
→ mechanism analysis
→ alternatives + conflict review
→ structural 时进入 spec / plan / tasks
→ implementation
→ deterministic tests + 必要的 semantic eval evidence
→ rollback point / versioning
→ acceptance
```

Project-specific character、plot fact 或 Canon 不能进入 Generic Framework default。

## 12 · Parallelism

只有当 worker 可以基于 immutable / frozen input 独立工作，而且结果能够分别验证时，parallel 才真正有价值。

没有显式 transaction / version protocol 时，不要并发修改共享 Project / Canon state。

也不要为了“多 agent”重复做同一种判断。

## 13 · Completion state

Run 必须结束在真实明确的状态，例如：

`complete | review | awaiting_user | awaiting_external | semantic_pending | semantic_invalid | failed_gate | blocked | settlement_incomplete`

`semantic_reject` 通常应作为 gate outcome 被消费并进入 repair，而不是被误标为 infrastructure failure。

## 14 · 相关契约

- [Harness Agent](HARNESS_AGENT.zh-CN.md)：manager 职责与权威边界。
- [Session Runtime](session_runtime/SESSION_RUNTIME.zh-CN.md)：生命周期、checkpoint 与 resume。
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)：semantic identity / fingerprint / result boundary。
- [生产流水线](../docs/production-pipeline.zh-CN.md)：面向用户解释 DRAFT / REVISE。
- [正典与状态模型](../core/CANON_STATE.zh-CN.md)：settlement authority。
