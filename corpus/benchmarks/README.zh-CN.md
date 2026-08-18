# 语料机制基准 · 保存机制证据，不制造风格模板

本目录保存**跨作品、项目无关的写作机制基准**。它们的作用，是把反复出现的写作机制压缩成可检查的证据，用来设计评测、检验假设和校准指导，而不是把版权语料原文直接塞给 Writer。

> **边界 ✦** Benchmark 不是正典，不是用户偏好，不是某位作者的风格指纹，也不会因为写进 JSON 就自动升级为 Framework 规则。

---

## 01 · 基准在证据链中的位置

```text
受限来源观察
→ 单作品机制分析
→ 对照 / 反例检索
→ 跨作品机制基准
→ 能力评测 + 回归评测
→ 升级候选
→ 授权后的激活 / 升级，或拒绝
```

检索不等于入库；分析不等于升级。Benchmark 只是 Corpus + Learning 整条证据链中的一个中间产物。

---

## 02 · 一条好基准应该保存什么

有效 benchmark 应至少说明：

- 稳定 ID；
- 正在检验的机制；
- 它试图避免或修复的失败；
- 正向操作模式；
- 失败 / 反例边界；
- 适用 profile；
- 关联的 Surface / Reader / eval 机制；
- 来源类别与当前状态；
- 用“机制”表达、而不是要求模仿某位作者的 writer-safe guidance。

它既要足够短，便于评测，又要足够具体，能够被反例推翻。

差的基准：

> 好小说需要生动细节。

更好的基准：

> 制度性细节只有在改变许可、成本、时间、身份位置或人物下一步可选行动时，才真正进入场景因果。

后者描述了可以观察、可以反驳的机制，而不是口号。

---

## 03 · Seed Registry

[`mechanisms.json`](mechanisms.json) 保存第一批迁入 Quillframe 的通用机制基准：

- 有功能的小动作；
- 与具体决定绑定的内心活动；
- 被当前压力触发的背景信息；
- 通过任务 / 物件 ownership 保持具身化的对话；
- 通过现实后果呈现历史 / 制度质感；
- 与现场任务绑定的说明性对话；
- 会改变选择集合的压力阶梯；
- 由真实后果产生的前推式结尾。

这些记录属于**迁移后的 seed evidence**。Registry 内部的版本字段描述这份 seed artifact，本身**不是当前 Quillframe release number**。

这里不保存任何消费项目事实，也不保存原始版权段落。

---

## 04 · Benchmark 不会绕过语义判断

需要文学理解的机制分析与评测，由 `learning` semantic contract pack 负责；确定性代码负责来源、权利边界、状态转移、证据完整性和升级前置条件。

因此，一条 benchmark 不能因为“已经存在 JSON 里”就自动变成真理。后续证据可以让它：

- 被新的独立证据加强；
- 缩窄到更小的适用范围；
- 在一个标签其实混了多个机制时被拆分；
- 被反例标记为 contested；
- 被更好的解释 supersede；
- 在评测证明副作用或泛化很差时 deprecated。

---

## 05 · 通用写作机制的升级门槛刻意很高

要把某条机制升级成 Framework 级通用指导，仅有一条 benchmark 远远不够。当前 promotion gate 至少要求这类证据：

- 多个彼此独立的跨作品来源；
- 至少一个明确的反例 / 对照来源；
- 清楚的 profile / applicability boundary；
- 通过 capability eval 与 regression eval；
- 版本与 rollback 依据；
- 绑定精确 commit 的绿色 Framework CI；
- 可追踪 provenance refs。

即使结果是 `promotable`，也**不会自动获得 Framework 写权限**。它只是一个类型化候选，后续仍需要授权的 manager / human workflow。

---

## 06 · Writer 隔离

推荐路径是：

```text
来源证据
→ 受限观察
→ 机制分析
→ benchmark / eval 校准
→ 最小、任务相关的指导
→ Writer
```

不要把这个目录当 prompt dump。大块来源原文、隐藏评测答案、回归坏例和“模仿某位作者”的材料都不应进入 Writer 的 pre-draft context。

---

## 07 · 相关契约

- [语料智能](../README.zh-CN.md)：完整检索、权利与分析流程。
- [语料政策](../CORPUS_POLICY.zh-CN.md)：存储、权利与模仿边界。
- [语料摄取协议](../CORPUS_INGEST_PROTOCOL.zh-CN.md)：合法、受限的 ingestion。
- [自适应学习](../../docs/adaptive-learning.zh-CN.md)：证据、假设、评测与升级。
- [`learning/promotion_gate.py`](../../learning/promotion_gate.py)：确定性升级前置条件。

**这套机制基准真正有价值，是因为每一条结论都能被检查、挑战、缩窄和撤回。**
