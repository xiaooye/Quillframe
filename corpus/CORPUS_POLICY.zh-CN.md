# Corpus Policy · 管理证据，而不是把“拿得到”变成故事或风格权威

NovelForge 使用 Corpus 研究**写作机制**、检验偏好 / craft hypothesis、构建 eval evidence，并主动寻找反例。Corpus 属于证据域，不是 Project Canon，不是人物知识，也不是隐藏的模仿 prompt，更不会自动成为 Framework guidance。

> **核心不变量 ✦** Access、rights、storage、analysis、learning、promotion 是六个不同 gate。通过前一个，永远不代表后一个已经通过。

---

## 01 · Corpus 可以支持什么

Corpus evidence 可以支持：

- 单项目 craft analysis；
- user-taste hypothesis 检验；
- 跨作品 General Craft 研究；
- capability / regression eval 设计；
- mechanism benchmark；
- counterexample / profile-boundary discovery；
- 面向明确 research question 的外部证据。

Corpus evidence 本身不能：

- 建立或修改 Project Canon；
- 证明某个人物已经知道一件事；
- settle 关系、资源或信息状态；
- 覆盖用户 / 项目的明确 authority；
- 激活 durable user taste；
- promote Framework behavior；
- 建立可复用的 named-author imitation profile。

---

## 02 · Rights Class 与 Storage Intent 是两件事

任何准备进入 durable Corpus handling 的 source candidate，都需要声明 `rights_class` 和 `storage_intent`。

参考 rights classes：

### `redistributable`

只有存在明确依据时，才可能允许保存全文，例如 public domain、兼容 open license、explicit permission，或用户自己拥有 / 创作并允许存储的材料。

必须保留非空 rights basis 与 provenance。

### `analysis_only`

材料可以在已声明依据下被访问 / 分析，但 NovelForge 不能把全文作为 Corpus data 保存。

允许持久化的通常是：

- source metadata；
- derived observation / metric；
- mechanism analysis；
- summary；
- 只有在明确 analysis / eval purpose 真正需要时，才保存短小 excerpt。

### `unknown`

当前证据不足以支持内容存储。直到 rights evidence 改变以前，只允许 metadata-level storage。

Private repository 不会把 unknown rights 自动变成 redistributable rights。

---

## 03 · Deterministic Rights Gate 不是法律判断器

[`rights_gate.py`](rights_gate.py) 只验证：**已经声明的 metadata 与请求的 storage intent，是否在 NovelForge policy 内部自洽。**

例如它会直接拒绝：

```text
unknown + metadata_only 以外的存储 → reject
analysis_only + full_text          → reject
short_excerpt 但没有 excerpt_purpose → reject
redistributable 但没有 rights_basis   → reject
```

这个 validator **不会**根据 URL、标题、作者名或 repo visibility 推断 copyright status。`legal_analysis_performed = false` 是刻意设计。

真实 rights / source status 必须由有授权的 research process 根据实际 evidence 建立。

---

## 04 · Provenance 是必要证据

一条 durable Corpus record 应该能够回答：

```yaml
corpus_id:
source_title:
creator:
source_url_or_ref:
source_type:
language:
publication_date:
rights_class:
rights_basis:
storage_intent:
accessed_at:
content_fingerprint:
analysis_scope:
research_question:
source_tool_or_capability:
```

不是每一种 source 都需要所有字段，但所有 substantive claim 都必须能追溯到真实 source / ref，以及真正完成 retrieval 的 capability。

如果 provenance 无法建立，就降低 confidence、只保留安全 metadata，或者直接 block。绝不能为了让 pipeline 看起来完成，而伪造 quotation 或 source-access event。

---

## 05 · Discovery 不等于 Ingestion

Discovery result 只说明：**发现了一个候选来源。** 它并不代表 NovelForge 可以复制或持久化该来源内容。

```text
discovery
→ verify source identity + provenance
→ 建立 declared rights basis
→ 选择 storage intent
→ deterministic rights gate
→ bounded ingestion / observation
```

Corpus Scout 与 discovery runtime 可以准备和规范化 candidate evidence，但不能替 host / source 凭空制造授权。

---

## 06 · Analysis 必须围绕具体问题

不能因为一部作品“拿得到”就默认整本分析。

先提出具体 research question，例如：

- 快场景如何在不依赖伪速度碎段的情况下制造压力？
- exposition 如何通过当前 task / conflict 进入因果链？
- 主角中心场景里，配角如何维持自己的 agenda？
- 章尾如何制造 forward pull，而不靠 narrator advertising？

只选择回答问题所需要的**最小充分范围 / evidence**。

Bounded analysis 可以同时减少 context 浪费、模仿压力、source leakage 和 confirmation bias。

---

## 07 · Generalization 必须主动找反例

Corpus research 应主动寻找：

- 支持当前 mechanism 的 evidence；
- 表面形式相反但仍然成功的例子；
- mechanism 明显失败的例子；
- genre / platform / profile exception；
- 对同一效果的其他解释。

如果检索只找到了“支持当前 hypothesis 的例子”，那还不足以成为强 General Craft evidence。

单一作品可以产生 observation，不能产生 universal rule。

---

## 08 · Named-author Imitation Boundary

NovelForge 可以分析广泛、可迁移的 craft mechanism，例如：

- scene causality / pressure sequencing；
- information timing；
- paragraph function；
- dialogue embodiment；
- character-agenda independence；
- setup / payoff management；
- broad genre / platform convention。

但不能把现代 / 在世作者变成可复用 imitation fingerprint。

Framework behavior 不得以这些目标设计：

- “完全照 Author X 写”；
- 从版权作品提取 signature phrase / cadence 用于复刻；
- 保存大量 copyrighted passage 当 style prompt；
- 为了 source imitation 而优化 Writer context，而不是为了理解 mechanism。

用户自有 evidence 与 public-domain material 仍然服从它们真实的 rights / provenance，以及同一套 authority boundary。

---

## 09 · Writer Isolation

Raw Writer context 默认应该收到**当前任务真正需要的 mechanism / profile guidance**，而不是 bulk Corpus text。

推荐路径：

```text
source evidence
→ rights-safe bounded observation
→ per-work mechanism analysis
→ counterexample / cross-work synthesis
→ benchmark / eval calibration
→ minimal relevant guidance
→ Writer
```

Regression 坏例和 hidden eval answer 不进入 Writer pre-draft context。Corpus / learning memory 默认属于 post-generation use，除非更高层 contract 明确证明某一条受限内容 writer-safe。

---

## 10 · Learning 与 Promotion 仍然是独立 Gate

Corpus observation 可以支持 `project`、`user_taste` 或 `general_craft` scope，但 Corpus layer 无权激活它们。

General Craft 通常还需要：

- 多个独立 cross-work refs；
- counterexample / profile-boundary evidence；
- capability + regression eval；
- provenance；
- version / rollback evidence；
- green Framework CI；
- prerequisites 通过后的 authorized promotion。

参见 [Self-Improvement Protocol](../harness/SELF_IMPROVEMENT_PROTOCOL.zh-CN.md)。

---

## 11 · Correction 与 Removal

如果后来证明 rights、provenance 或 analysis evidence 无效：

```text
mark source / item invalid
→ 删除已经不再允许保存的内容
→ 找出 dependent analysis / benchmark / eval
→ invalidate / rebuild derived evidence
→ narrow / contest / deprecate dependent learning hypothesis
→ 必要时 rollback 已受影响的 promoted behavior
→ 保留 correction provenance
```

Derived evidence 必须保持足够可追踪，才能完成这类 dependency repair。

---

## 12 · Autonomous Behavior Boundary

Corpus automation 可以：

- 检测 evidence gap；
- 准备 discovery request；
- 规范化真实返回的 source metadata；
- 执行 deterministic rights / storage check；
- 把 bounded evidence 打包给 semantic analysis；
- 记录 missing capability 或 blocked rights state。

它不能：

- 在没有合格、已授权 Web / GitHub / MCP capability 时假装 retrieval 已发生；
- 根据薄弱 metadata 推断 legal rights；
- 伪造 quotation；
- 把 Corpus observation 自动 promote 成 Canon、user taste 或 Framework behavior。

---

## 13 · 相关契约

- [语料智能](README.zh-CN.md)：端到端 evidence pipeline。
- [Corpus Ingest Protocol](CORPUS_INGEST_PROTOCOL.zh-CN.md)：bounded ingestion mechanics。
- [`rights_gate.py`](rights_gate.py)：deterministic declared-rights / storage validator。
- [`discovery_runtime.py`](discovery_runtime.py)：typed discovery runtime。
- [Corpus Benchmarks](benchmarks/README.zh-CN.md)：cross-work mechanism evidence。
- [自适应学习](../docs/adaptive-learning.zh-CN.md)：learning scope 与 hypothesis。

**好的 Corpus 系统会保存足够的证据让分析、审计和 rollback 成立，但绝不会让“拥有来源”变成绕过 rights、authority 或 craft reasoning 的捷径。**
