# Framework 自我改进协议 · 证据可以提出改变，但不能自行获得写权限

NovelForge 可以从用户反馈、项目结果、语料证据、评测和外部框架研究中持续学习。只有当证据支持**最窄且正确的作用域**、改变可测试可回滚，并且真正有权限的流程执行了升级以后，行为变化才可以持久化。

> **核心不变量 ✦** Learning 可以产生 evidence、hypothesis、eval result 和 promotion candidate；这些产物本身都不会获得 Framework write、Canon write 或 durable user-taste write authority。

---

## 01 · 四种作用域

每条学习结论都必须属于以下一种：

- `one_off`：只服务当前 request / run；
- `project`：只适用于某一本下游小说；
- `user_taste`：某个用户跨项目的持久偏好假设；
- `general_craft`：准备进入 NovelForge 通用机制的候选。

永远选择证据真正支持的最窄作用域。一个项目偏好不会因为出现两次就自动变成 user taste；user taste 也不会因为模型觉得“很有道理”就升级成 General Craft。

---

## 02 · 先有证据，再有假设

Production feedback intake 自动的是 evidence capture，不是 promotion。模型先判断 `capture | skip`；同一个 durable feedback event 的 retry 不是新 evidence，真正独立的新 user turn 才可能成为新的 evidence ref。用户的 universal claim 可以成为 candidate，但不能跳过下面的 research/counterexample/eval/authority 路径直接成立为 General Craft。Project/user 内容默认留在 Project/runtime 私有层，只有之后抽象成 rights-safe、anonymized Generic evidence 才可能进入 Framework。

有效 evidence 可以包括：

1. 用户明确规则；
2. 用户直接编辑；
3. 带理由的明确接受 / 拒绝；
4. 多次彼此独立、方向一致的修正；
5. 已接受的项目约定；
6. 跨作品语料机制证据；
7. 外部 primary / framework evidence；
8. 模型推断。

模型推断属于最弱层。**只有模型自己推断，不能建立持久 user taste，也不能改变 Framework behavior。**

被用户拒绝的模型输出只能作为负面 regression evidence，不能因为“曾经生成过”就反过来当 positive exemplar。

---

## 03 · 持久 Learning Cycle

[`learning/learning_cycle.py`](../learning/learning_cycle.py) 负责跨 runtime boundary 保存学习流程进度，但它不做语义判断。

整体生命周期近似：

```text
evidence / hypothesis
→ corpus gap
→ discovery plan
→ verified discovery
→ semantic analysis
→ eval evidence
→ promotion candidate
→ 有权限的 activation / promotion decision
```

Cycle 保存状态、artifact hash 与 consume-once receipt，并始终保持：

```text
canon_authority = false
framework_write_authority = false
durable_user_taste_write_authority = false
```

Scheduler 或 durable DB 可以记住“做到哪一步”，但不能因此决定“这条 mechanism 从现在起就是规则”。

---

## 04 · 需要理解的分析交给模型契约

`learning` semantic pack 负责需要语义理解的部分。

当前主要契约包括：

- `learning.mechanism_analyze`：分析受限、rights-safe evidence，提炼 mechanism、counterexample 与 applicability boundary；
- `learning.evaluate`：在看不到 hidden expected label 的情况下，用 blind fixture / profile boundary 检验候选 mechanism。

确定性运行时负责绑定输入与结果、执行权限边界、记录 provenance、验证类型化输出；它不使用 heuristic 假装自己能判断写作机制。

Semantic result 可以支持 promotion gate，但不能自己执行 promotion。

---

## 05 · Corpus Discovery 只是找证据，不代表学习完成

当 hypothesis 缺少 contrast evidence 时，可以创建 Corpus gap。

已授权宿主可以通过 Web、GitHub、图书馆 / 平台 metadata、用户合法文件或 MCP / search connector 检索，但必须始终区分：

```text
discovery ≠ ingestion
找到来源 ≠ 获得使用权
analysis ≠ preference
benchmark ≠ Framework rule
```

Corpus 工作必须保留 source identity、provenance 与 rights class。General Craft 需要跨作品 mechanism synthesis 与反例，不允许生成 named-author imitation fingerprint。

---

## 06 · User Taste 激活

持久 `user_taste` 不能来自一次模型 impression。

当前 deterministic promotion prerequisite gate 至少要求：

- 用户明确 evidence，或多次彼此独立且方向一致的修正；
- 可追踪 evidence refs；
- personalized eval evidence；
- contradiction review；
- 证据足够时明确 applicability boundary。

即使结果是 `ready_for_activation`，也不代表 generic source control 可以吸收私人偏好数据。User-taste state 默认留在用户 / host 管理的存储中。

---

## 07 · General Craft 升级门槛

General Craft 会影响通用 Framework，因此门槛最高。

候选至少要证明：

- mechanism 不依赖单一用户 / 项目；
- 有多个彼此独立的 cross-work evidence refs；
- 至少一个 counterexample / contrast ref；
- 明确 profile / applicability boundary；
- capability eval 通过；
- regression eval 通过；
- 有 version target 与 rollback ref；
- 有 provenance refs；
- Framework CI 绿色并绑定 exact commit；
- 没有尚未解决、实际上应该缩窄 scope 的 contradiction。

[`learning/promotion_gate.py`](../learning/promotion_gate.py) 可以返回 `promotable`。它只表示**证据前置条件已经满足**，同时仍然返回 `behavior_write_authority = false`。

下一步是有权限的 manager / human engineering workflow，不是自动修改 source code。

---

## 08 · 真正改变 Framework 的流程

Generic behavior change 仍然遵守正常软件工程纪律：

```text
冻结 evidence + candidate
→ 找到 owning mechanism
→ 定义最小充分改变
→ 检查 compatibility / profile boundary
→ implementation
→ deterministic tests
→ required capability + regression evals
→ rubric 要求时取得 independent evidence
→ 审查 exact diff / version / rollback
→ authorized write
→ green post-change CI
→ 继续观察后续结果
```

大型结构变化使用 spec → plan → tasks；一个微小文案修正不需要假装成大型 feature project。

---

## 09 · 从外部框架学习

OpenAI Agents SDK、LangGraph、ADK / agents-cli、AutoGen、Claude Code、MCP 等系统只是 runtime engineering 的证据来源。

上游变化只会创建 `adopt | adapt | reject` hypothesis，不会自动触发 dependency update。

应该问：

- 到底哪个 mechanism 发生了变化？
- 它解决的真实问题是什么？
- NovelForge 是否已经用另一种方式解决？
- 采用以后会不会模糊 runtime state、Canon、independence 或 permission boundary？
- 需要什么 capability / regression evidence 才能证明它真的更好？

参见 [Agent Framework Adoption](../knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md)。

---

## 10 · Scheduled Maintenance 没有 Promotion Authority

Schedule 可以触发 deterministic observation、queue construction、capability check 或 learning-cycle advancement。

它不会授权系统：

- 在 workflow 禁止时偷偷花 model usage；
- 伪造当前并不存在的 Web / search capability；
- 自动 promote hypothesis；
- 修改 Framework behavior；
- 写 Project Canon。

**时间只是 trigger，不是 authority。**

---

## 11 · 冲突、衰减与回滚

Learning 必须始终可逆。

Hypothesis 或已经升级的 mechanism 可以进入：

- `contested`：新 evidence 与旧结论冲突；
- `superseded`：更精确的新解释替代旧假设；
- `deprecated`：用户方向改变，或 eval 证明它造成明显副作用。

证据推翻旧行为时：

```text
记录 contradiction
→ 找出 dependent benchmark / profile / eval
→ block / deprecate affected candidate
→ 必要时恢复旧 behavior / profile
→ 保留 rollback provenance
→ 重跑相关 regression
```

模型反复同意自己多少次，都不算新的 independent evidence。

---

## 12 · 硬边界

Framework self-improvement 可以修改**通用机制**，但绝不能把某本下游小说的人物、Canon、private project state、plot outcome 或私人用户 preference record 吸收到 generic source。

项目证据只有在去掉项目专属内容、抽象出 generic mechanism，并且这条机制重新获得独立证据以后，才可能支持通用改进。

---

## 13 · 相关契约

- [自适应学习](../docs/adaptive-learning.zh-CN.md)：面向使用者的 Learning model。
- [语料智能](../corpus/README.zh-CN.md)：受治理的证据 discovery / analysis。
- [语料机制基准](../corpus/benchmarks/README.zh-CN.md)：可检查的 cross-work mechanism evidence。
- [`learning/learning_cycle.py`](../learning/learning_cycle.py)：持久、无权威的 Learning workflow。
- [`learning/promotion_gate.py`](../learning/promotion_gate.py)：deterministic promotion prerequisites。
- [`harness/semantic_workers/contracts/learning.json`](semantic_workers/contracts/learning.json)：Learning semantic contracts。

**Autonomy 可以推进取证与验证；真正改变持久行为的那一刻，authority 必须仍然显式存在。**
