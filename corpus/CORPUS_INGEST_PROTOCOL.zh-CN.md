# Corpus Ingest Protocol · 只保存研究问题真正需要、rights 真正允许的证据

Corpus ingestion 的职责，是把已经验证过的 discovery candidate 转成带 provenance 的**metadata、被允许保存的 source material、observation 与 derived evidence**。它刻意比“把来源下载下来”更窄。

> **核心不变量 ✦** Ingestion 只是 storage / evidence operation。它不会因此获得 Canon authority、character knowledge、durable user preference 或 Framework behavior authority。

---

## 01 · 开始 Ingestion 之前

不能只拿一条 search result 就开始保存内容。

Candidate 至少应该已经说明：

- discovery request / Corpus gap ID；
- research question；
- proposed source identity；
- source channel / tool capability；
- 预期提供的 contrast / evidence value；
- 适用时的 language / genre / platform metadata。

随后，在当前已授权 host 能力范围内尽量核实：

- canonical work / source identity；
- 相关 creator / publisher / source owner；
- canonical URL / ref 或 local file identity；
- 重要时的 edition / version；
- access timestamp；
- source type；
- 用户 / 本地文件可获得时的 fingerprint。

Search snippet 只是 discovery evidence，不是可靠的全文 quotation，也不是 rights evidence。

---

## 02 · 保存内容前先建立 Rights Class

每个 durable Corpus candidate 只能选择一个 declared rights class：

```text
redistributable | analysis_only | unknown
```

同时明确一个 requested storage intent：

```text
metadata_only | derived_only | short_excerpt | full_text
```

持久化 source content 之前，先运行 deterministic [`rights_gate.py`](rights_gate.py)。

参考 policy：

```text
unknown         → 只能 metadata_only
analysis_only   → 绝不能 full_text
short_excerpt   → 必须有 excerpt_purpose
redistributable → 必须有非空 rights_basis
```

这个 gate 只验证 policy consistency，不做法律分析，也不会根据 title / URL 自动推断 rights。

---

## 03 · Rights 或 Provenance 不清楚时 Fail Closed

如果 rights 是 `unknown`，只保留安全 source metadata，然后停止 content storage。

如果 source identity / provenance 存在实质性不确定，也不能为了让 pipeline “走完”而猜：

```text
足以确认 metadata → 保存 metadata + unresolved status
连 metadata 都不足 → 保留 discovery candidate / blocked state
```

Private repo、local browser session、authenticated connector 或成功 download，只能证明 access；它们不自动证明 redistribution permission。

---

## 04 · 选择最小 Analysis Range

即使允许分析，也只选择回答当前问题真正需要的范围。

建议记录：

```yaml
range_type: chapter | scene | passage | work_metadata | user_selection
range_ref: ...
research_question: ...
why_this_range: ...
source_fingerprint: ...
```

不能因为 host “能拿到整本”，就默认读取或持久化整部作品。

Question-bounded range 同时减少 copyright exposure、context cost、source leakage 与 imitation pressure。

### 旧版第一版统计通用语料库限制

仓库发布配置比一般摄取协议更严格：

```yaml
distinct_logical_works: 120
editions_per_work: 1
windows_per_work: 3
window_scopes: [opening, middle, closing]
max_unicode_chars_per_window: 4000
raw_materialization: ephemeral
```

分析开始以前，用户必须确认精确的 120 部作品池。确认绑定所声明的权利与范围、profile、完整成员和 proposal fingerprint；成员勾选不是文学复核，也不要求最终使用每一部。重复文件或同一作品的其他版本不能占用多个名额。持久片段任务只保存不透明的范围标识、位置、来源／片段／任务指纹和评审准则；真正的片段只为一次受限调用重新打开并复核指纹，随后丢弃。

旧版摄取提案会用私有元数据把高置信同题连载、校订和完本快照归成一个候选家族，并选择一个代表版本；不确定归组不得自动合并。对文风学习而言，身份未解析或权利无效会阻断受影响的来源证据；偏短／不完整、连载、语言不一致和重启／拼接信号属于证据范围路由，不是文学隔离：它们缩窄语言或整部作品结论，并要求使用边界感知窗口。XML 解析只允许在剥离单一、无实体且无内部子集的安全 `DOCTYPE` 后继续；实体声明、内部子集、畸形或重复声明仍然拒绝。

用户确认清单时必须明确选择 `general` 或 `adult_explicit`。提案层只用私有元数据机械隔离强成人信号，不根据原文猜测；没有命中信号的标题只是待人工确认的 `general` 候选。每次研究只绑定一个不可变配置，所有观察和聚合结果都属于这个配置。除非后续请求明确选择对应内容区，否则 `adult_explicit` 研究不能进入通用聚合结果或普通写作指导。

三个固定窗口属于旧版统计发布契约。在行文文风学习目标中，精确来源池是可用证据：场景／文风分类、缺口分析、下一份有界证据请求和跨作品收敛由 AI 负责；Python 运行器只负责身份／版本绑定、最小有界物化、清洁、预算与回执，模式和泄漏关卡继续作为确定性发布控制，关键词、标点或分值启发式不得作文学判断。来源数量、全池暴露和 CPU／内存诊断不能代替饱和、留出复现、盲测和泄漏复核。登记契约与合成运行器测试现已证明动态激活所请求的作品／场景功能证据，并在未触及作品继续留在可用未分析状态时提前收敛。这项证明不等于真实 V5 已运行或已经学会文风，也不表示盲测／泄漏资格或发布已经通过。身体与外貌词汇，包括单独出现的“巨乳”，继续属于普通通用技法证据，除非真实上下文建立露骨内容。

---

## 05 · Source Material 与 Observation 分开

**Observation artifact** 只记录在被允许 evidence range 中可以支持的观察，不假装这些观察已经是 universal craft rule。

示例：

```yaml
observation_id: ...
corpus_id: ...
range_ref: ...
question: ...
observable_features: []
evidence_refs: []
metrics: {}
confidence: ...
```

Evidence ref 要简洁、能回到 source；不保存 private chain-of-thought。

对于 `analysis_only` source，优先持久化 metadata + derived observation，而不是 raw text。

---

## 06 · Semantic Mechanism Analysis 是另一层

Observation 与 interpretation 是不同 artifact。

需要文学 / craft 理解时，把 bounded rights-safe evidence 交给 `learning` semantic contract pack。`learning.mechanism_analyze` 负责提炼：

- mechanism candidates；
- counterexamples；
- applicability boundaries；
- evidence refs；
- uncertainty / confidence。

它的 contract 明确禁止 unrestricted `full_text`、`raw_text`、`source_text` 字段。

Deterministic ingestion code 不能用 heuristic literary scoring 冒充这一层。

---

## 07 · 单一作品不能建立 General Craft

Per-work analysis 可以产生 hypothesis / observation，例如：

```yaml
analysis_id: ...
corpus_id: ...
research_question: ...
mechanism_candidates: []
tradeoffs: []
profile_context: ...
uncertainties: []
counterexample_needed: true
```

但它不能直接变成 universal rule。

Generalize 前必须主动寻找：

- 用不同 surface form 达成同一效果的例子；
- 使用同一 surface form 却效果更差的例子；
- profile / genre / platform exception；
- 直接反驳 proposed mechanism 的 evidence。

Negative evidence 必须保留，不能因为“不支持原 hypothesis”就丢掉。

---

## 08 · Cross-work Benchmark Handoff

只有在出现多个 source-bound observation 与 counterexample 以后，才适合构建 cross-work mechanism benchmark。

有效 benchmark 可以包含：

- mechanism statement；
- supporting observation refs；
- counterexample refs；
- applicability / profile boundary；
- failure modes；
- writer-safe guidance；
- capability / regression eval ideas；
- source / provenance refs。

不能把多个来源的 signature 混在一起做 synthetic author-imitation fingerprint。

参见 [Corpus Benchmarks](benchmarks/README.zh-CN.md)。

---

## 09 · Learning / Eval Handoff

Corpus-derived evidence 可以创建或更新：

- project-specific craft evidence；
- user-taste evidence / hypothesis test；
- General Craft candidate；
- capability eval case；
- regression eval case；
- 新的 Corpus gap。

每个 downstream artifact 都必须保留 upstream evidence / provenance refs。

Promotion 仍由 Adaptive Learning / Self-Improvement 管理。Ingestion 无权激活结果。

---

## 10 · Writer Exposure 是后面更窄的一次决定

Raw Writer 默认应该拿到：

```text
minimal task-relevant mechanism
+ relevant profile boundary
+ 当前场景真正需要的 project authority / context
```

而不是 bulk source text。

现代版权 source text、hidden expected label、regression 坏例默认都不进入 first-pass Writer context。

一条 Corpus item 被存储，不代表它自动拥有 `draft` visibility。

同一次分析也可以形成私有用户偏好候选。即使如此，也只有长期授权、语义复核、独立评测和矛盾复核全部通过以后，写作阶段才可能看到后续生成的无原文机制 / 适用边界投影。每次运行的选择器可以一条都不选；盲读者和独立评审的输入始终不包含语料指导或用户偏好指导。

---

## 11 · 不同 Rights Class 能保存什么

### `redistributable`

如果 declared rights basis 真实支持 redistribution / storage，可以允许 `full_text`。必须保留 provenance 与 fingerprint。

### `analysis_only`

使用 `metadata_only`、`derived_only`，或者有明确理由的 `short_excerpt`；不得持久化全文。

### `unknown`

只能 `metadata_only`。Rights evidence 改变以前，content ingestion 保持 blocked。

保存 short excerpt 时，必须记录为什么这一小段对当前分析不可替代。“以后可能拿来学风格”本身不是充分理由。

---

## 12 · Downstream Evidence 必须能失效

所有 derived artifact 都要保留足够 lineage，确保之后可以 correction。

如果某个 source 后来因为 rights / provenance / error 变成 invalid：

```text
invalidate source / content record
→ 删除已经不再允许保存的 material
→ 找到 dependent observation
→ invalidate / rebuild analysis
→ invalidate / rebuild benchmark / eval
→ contest / narrow dependent learning candidate
→ 必要时 rollback promoted behavior
```

如果一条 benchmark 唯一有效 evidence 已经被移除，不能让它继续装作有效。

---

## 13 · Automation Boundary

Ingestion pipeline 可以自动执行 deterministic validation 与 bookkeeping，但不能伪造 external retrieval、rights evidence 或 quotation。

如果 external capability 不可用：

```text
prepare request
→ 记录 missing capability / awaiting external work
→ 如实停止
```

如果需要 semantic interpretation：

```text
prepare bounded contract job
→ 通过 eligible model / human runtime 执行
→ validate fingerprint-bound result
```

Queue 不是 retrieval；Schema 不是 analysis；model result 也不是 promotion authority。

---

## 14 · 公开发布与仓库登记表

对旧版三窗口统计协议而言，只有 120 部作品全部完成以后，发布流程才会构建封闭模式预览。公开包只允许随机作品标识、数值派生结果、八个维度的受控特征、受控跨作品机制与边界，以及指纹。原文、引文、近似复述、可以还原来源的摘要、名称、书名、创作者、路径、人物、设定和任意扩展字段都会被拒绝。

Style Atlas 发布走另一条无来源、证据充分路径，不要求机械处理全部 120 部。合成契约／运行器测试现已建立动态作品池与提前停止工程路径；它们不证明真实 V5 已运行、已经学会文风、盲测或独立泄漏复核已通过，也不授予发布权限。

验证必须同时执行结构检查和私有来源重叠检查。发布还要求精确确认预览令牌和清单指纹。在此之前，[`general/registry.json`](general/registry.json) 必须保持为空，不能暗示已经存在任何研究结果。

仓库权利人拥有的派生发布继承仓库[许可证](../LICENSE)。本协议不会因为内容经过抽象或用途非商业，就断言公开发布一定合法；针对具体来源的权利审查仍由执行者负责。

---

## 15 · 相关契约

- [Corpus Policy](CORPUS_POLICY.zh-CN.md)：normative rights / evidence boundary。
- [语料智能](README.zh-CN.md)：完整 research / learning flow。
- [`rights_gate.py`](rights_gate.py)：declared-rights / storage-intent validator。
- [`discovery_runtime.py`](discovery_runtime.py)：discovery request / result lifecycle。
- [`harness/semantic_workers/contracts/learning.json`](../harness/semantic_workers/contracts/learning.json)：bounded mechanism-analysis / eval contracts。
- [匿名公开通用语料库](general/README.zh-CN.md)：发布模式、当前登记状态和许可证边界。
- [自适应学习](../docs/adaptive-learning.zh-CN.md)：downstream hypothesis / eval lifecycle。

**只摄取当前 research question 真正需要、已建立 rights 真正允许的内容；其余尽量转成可追踪的 derived evidence。**
