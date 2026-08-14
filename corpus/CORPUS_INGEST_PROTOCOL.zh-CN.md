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

一条 Corpus item 被存储，不代表它自动拥有 `writer_pre_draft` visibility。

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

## 14 · 相关契约

- [Corpus Policy](CORPUS_POLICY.zh-CN.md)：normative rights / evidence boundary。
- [语料智能](README.zh-CN.md)：完整 research / learning flow。
- [`rights_gate.py`](rights_gate.py)：declared-rights / storage-intent validator。
- [`discovery_runtime.py`](discovery_runtime.py)：discovery request / result lifecycle。
- [`harness/semantic_workers/contracts/learning.json`](../harness/semantic_workers/contracts/learning.json)：bounded mechanism-analysis / eval contracts。
- [自适应学习](../docs/adaptive-learning.zh-CN.md)：downstream hypothesis / eval lifecycle。

**只摄取当前 research question 真正需要、已建立 rights 真正允许的内容；其余尽量转成可追踪的 derived evidence。**
