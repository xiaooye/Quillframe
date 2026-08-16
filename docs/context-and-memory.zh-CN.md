<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><strong>上下文与记忆 · 在确定性权威边界内让 agent 自己决定语义选择</strong></p>
  <p><kbd>SEARCH</kbd>&nbsp;&nbsp;<kbd>SELECT</kbd>&nbsp;&nbsp;<kbd>VERIFY</kbd>&nbsp;&nbsp;<kbd>PACK</kbd>&nbsp;&nbsp;<kbd>RESUME</kbd></p>
  <p><a href="context-and-memory.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 上下文与记忆

NovelForge 明确区分：**存储的信息、机械 eligibility、semantic relevance、working context、durable session history、Project truth**。

> **模型决定自己缺什么、搜什么、什么真正相关、是否继续搜、什么时候证据已经够了；deterministic runtime 只决定模型允许访问什么、item/result 是否真实且 current、是否允许进入目标 stage，以及 hard budget / authority constraint 是否满足。**

## 1. Ownership model

**Project authority** 拥有 Canon / accepted facts 与 Project-level truth。

**Session Runtime** 拥有 durable run/checkpoint/event identity。Model context window 不是 durable session。

**Context Inspector** 拥有 mechanical eligibility、stage visibility、显式 pin/priority control、protected edit 与 invalidation。它拒绝 `relevance` 字段，因为 relevance 是 semantic judgment。

**`context.select`** 拥有 semantic context/search decision。

**Context Assembly v2** 对模型已选好的 exact set 执行 deterministic verification。

**Memory tiers / hard-budget packing** 在客观预算下装载已选择的 whole item。

**Memory Bank** 保存 source-bound runtime/derived memory，不是 shadow Canon。

## 2. Context Inspector：只看 eligibility，不看 relevance

`harness/context_inspector.py` 实现 `novelforge_context_inspector_v3`。

它可以规范化/检查：

- item/source identity 与 source fingerprint；
- authority class；
- allowed stage；
- explicit numeric priority / pin；
- derived/hidden/invalidated state；
- protected-edit proposal behavior。

稳定排序（`pinned → explicit priority → stable id`）代表显式作者/runtime control，不代表文学重要性。

`accepted` / `locked` source 不能通过 Context overlay 直接修改；修改请求只能成为 proposal，不会 mutate Canon。

## 3. Stage isolation 属于 deterministic boundary

Private 或 answer-key-like information 不能仅仅因为“存储里有”就跨 stage 泄漏。

例如：

- hidden gold / expected verdict / regression answer key 不得进入 Writer context；
- private character / scene simulation state 可以给 simulation，但不能自动给 Writer；
- compact writer-safe realization trace 可以给 Writer，而生成它的 private state 可以继续隐藏；
- Blind Reader 默认不能继承 manager/author/private-character reasoning。

这是 information-security boundary，因此 deterministic enforcement 是合理的。

## 4. `context.select`：Search 是 capability

`context.select` semantic contract 接收 bounded task、mechanically eligible candidate blocks，以及 allowed search capabilities/resource budget。

模型自己决定：

1. 当前任务还缺什么；
2. supplied blocks 中哪些真正有用；
3. 现有 evidence 是否已经足够；
4. 下一条 focused query 是什么；
5. 看完结果后是否 broaden / narrow / reformulate；
6. 什么值得进入 working context；
7. 什么时候应该停止搜索。

Runtime 不把 recency、vector similarity、fixed top-k、item class 或 task-mode mapping 变成 narrative truth。这些机制最多只能产生候选，不是 authoritative relevance judgment。

Pinned item 是 explicit execution constraint，也不是 semantic importance 的证明。

## 5. Context Assembly v2：只验证 exact set

`harness/context_assembly.py` 实现 `novelforge_context_assembly_v2`。

它在 model/manager 完成 selection **之后**，只验证 deterministic property：

- selected IDs 真实存在于 inspected eligible set；
- exact receiving stage 合法；
- hidden/invalidated/private-state restriction 没被破坏；
- mechanically required 时 source fingerprint / exact higher-authority ref 匹配；
- selected projection 没跨 privacy/stage boundary。

它明确**不判断**：

- 某个 literary context class 是否“required”；
- selected item 是否 narratively relevant；
- 当前 selection 在语义上是否 sufficient；
- 是否应该继续 search。

这些都属于模型/Manager。若某个 authoritative artifact 对操作来说是机械 mandatory，caller 传入的是它的 **exact required ref/fingerprint**，而不是用 semantic class/purpose 代替。

## 6. Hard-budget packing 继续 deterministic

使用 tiered packing 时，`harness/memory_tiers.py` 可以执行 hot/working budget、whole-item packing、invalidated exclusion 与 explicit pin。

它不能因为自称“文学相关”就自行 summary/rank/truncate。Explicit pinned item 连 hard budget 都放不下时，应暴露 conflict，而不是悄悄取消 pin。

## 7. Character knowledge：visibility 是机械的，inference 是语义的

Runtime 可以证明某条 evidence 在 story-time boundary 尚未 available，或者不在 authorized perspective packet 中；但不能仅凭 label 就断言人物“语义上不可能推断”某事。

Character knowledge / inference / consistency 属于 semantic character/rule-audit contract。Evidence identity 与 temporal/visibility eligibility 仍作为 deterministic 输入边界。

## 8. Author Model context 使用同一原则

Active Author Model hypothesis 表示**durably eligible preference evidence**，不表示每个任务都 relevant。

`learning/author_model.py` 暴露 compact active index；manager/model 显式选择当前有用的 hypothesis IDs，deterministic code 只验证它们确实 active 且 Project-compatible，然后才暴露细节。

## 9. 典型 adaptive context loop

```text
resolve Project/session authority
→ build mechanically eligible candidates
→ model inspects task and current evidence
→ model selects or requests search
→ runtime executes allowed search/fetch primitive
→ model inspects results and may reformulate
→ model stops when sufficiently grounded
→ Context Assembly v2 verifies exact refs/stage/fingerprints
→ hard-budget packing if needed
→ execute target semantic/writing contract
→ persist only source-bound, non-authoritative derived memory
```

Context-window transcript 永远不是 resume authority。Context loss/reset 之后，Session Runtime 重新解析 current Project/Framework authority，并从 durable events/artifacts/checkpoints 重建 working set。

## 10. Failure routing

- 真正相关的 evidence 被漏选 → 修 semantic selection/search，不新增 Python relevance rule；
- selected ref stale/missing/wrong fingerprint → deterministic assembly failure；
- private state 进入 forbidden stage → deterministic isolation failure；
- 第一次 search 不够 → 模型在 allowed capability 内继续/reformulate；
- evidence 已经足够 → 模型应该 stop，runtime 不强制继续检索；
- hard budget 无法满足 explicit pin → deterministic control conflict；
- 人物看起来知道得太多 → semantic knowledge/rule audit，基于 authorized evidence 判断；
- protected Canon 真要修改 → proposal → Project acceptance/Settlement，绝不由 Context overlay 直接 mutate。

## 11. 精确参考

- [架构总览](architecture.zh-CN.md)
- [生产流水线](production-pipeline.zh-CN.md)
- [项目 SDK](project-sdk.zh-CN.md)
- [`harness/context_inspector.py`](../harness/context_inspector.py)
- [`harness/context_assembly.py`](../harness/context_assembly.py)
- [`harness/memory_tiers.py`](../harness/memory_tiers.py)
- [`harness/memory_bank.py`](../harness/memory_bank.py)
- [`harness/semantic_workers/contracts/context-research.json`](../harness/semantic_workers/contracts/context-research.json)

<div align="center"><sub>模型判断意义，runtime 限制权力，Project 决定真相。🌸</sub></div>
