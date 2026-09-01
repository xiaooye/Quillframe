# Corpus Policy · 管理证据，而不是把“拿得到”变成故事或风格权威

Quillframe 使用 Corpus 研究**写作机制**、检验偏好 / craft hypothesis、构建 eval evidence，并主动寻找反例。Corpus 属于证据域，不是 Project Canon，不是人物知识，也不是隐藏的模仿 prompt，更不会自动成为 Framework guidance。

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

材料可以在已声明依据下被访问 / 分析，但 Quillframe 不能把全文作为 Corpus data 保存。

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

[`rights_gate.py`](rights_gate.py) 只验证：**已经声明的 metadata 与请求的 storage intent，是否在 Quillframe policy 内部自洽。**

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

Discovery result 只说明：**发现了一个候选来源。** 它并不代表 Quillframe 可以复制或持久化该来源内容。

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

旧版 `quillframe_corpus_three_window_benchmark_v1` 匿名公开通用语料库会机械地冻结和限制这个“最小充分范围”：

- 由用户确认精确 120 部不同逻辑作品的清单；
- 每部作品只绑定一个带指纹的版本；
- 每部作品恰好读取开篇、中段、收束三个窗口；
- 每个窗口最多 4,000 个 Unicode 字符；
- 原文只临时物化，不进入持久账本或公开发布包。

这是旧版统计发布范围合同，不代表三个片段足以完整刻画一部作品，也不是文风学习协议。来源漂移或被移除以后，依赖它的逐作品证据和聚合证据必须失效。

旧版提案路径使用私有元数据去重版本家族，并把身份不明、偏短或元数据冲突项目送入本地关注路由。这类诊断不建立文学质量，也不是 Style Atlas 的通用排除规则。对文风学习而言，权利无效或来源身份未解析只阻断受影响的来源证据；语言不一致会缩窄语言专属结论；不完整或连载材料可以支持局部行文／场景结论，但不能支持未经证实的整部作品结论；重启或拼接信号要求使用边界感知窗口或更窄结论。用户确认所声明的权利与范围、唯一研究配置（`general` 或 `adult_explicit`）、精确 120 部来源池成员和 proposal fingerprint。跨配置混合仍被禁止。

三个固定窗口的上限定义的是旧版统计发布，不是行文文风学习深度。在 `quillframe_corpus_style_learning_v1` 目标中，精确 120 部作品构成可寻址证据池，不是任务队列或逐本文学检查表。场景／文风分类、证据缺口、下一份最小充分样本和跨作品收敛由 AI 负责；Python 运行器只负责来源身份／版本绑定、最小有界物化、清洁、预算与回执，模式和泄漏关卡继续作为确定性发布控制，而不是文学判断。每次原文调用仍然只临时物化片段。全池暴露、CPU／内存基准和更多样本都不会自动形成完成或发布权限。登记契约与合成运行器测试现已证明动态激活所请求证据、如实保留未使用池成员，并可在池未耗尽时提前收敛。这项工程结果不等于 V5 已运行或已经学会文风，也不表示盲测、独立泄漏复核或发布已经通过。

内容配置与文风维度彼此正交。身材、解剖、服饰和外貌——包括单独出现的“巨乳”——都是正当 `body_appearance` 观察，不足以成为成人配置的信号。只有真实上下文建立的露骨内容证据才进入独立治理。

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

Quillframe 可以分析广泛、可迁移的 craft mechanism，例如：

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

AI 研究规划器可以：

- 从有界证据判断场景功能与行文文风轴；
- 发现不确定性、矛盾和跨作品证据缺口；
- 请求下一份最小充分来源／窗口；
- 提出更窄的证据范围与跨作品收敛状态。

确定性运行时可以规范化真实返回的来源元数据、绑定身份与版本、执行已声明权利／存储边界、只物化所请求的有界证据、运行清洁／泄漏／模式检查，并记录预算和回执。确定性关键词、标点或分值启发式不得变成文学分类、缺口分析或收敛权威。

它不能：

- 在没有合格、已授权 Web / GitHub / MCP capability 时假装 retrieval 已发生；
- 根据薄弱 metadata 推断 legal rights；
- 伪造 quotation；
- 把 Corpus observation 自动 promote 成 Canon、user taste 或 Framework behavior。

---

## 13 · 匿名公开发布边界

公开发布包是无原文投影，不是把私有账本稍微删减后的副本。封闭模式只允许随机标识、数值指标、八个维度的受控写作特征、跨作品机制标签、适用边界、反例状态、失败模式和完整性指纹。

路径、文件名、书名、创作者、原文、引文、近似复述、可以还原来源的摘要、人物、设定和任意扩展字段都被禁止。发布前还必须把候选公开字符串与私有来源身份、采样原文进行泄漏比对；只通过模式校验并不充分。

发布候选必须先产生精确预览令牌与清单指纹，调用方再次确认两者以后才允许发布。预览、验证报告、空登记表或语义结果都不等于发布。旧版统计登记表在固定 120 部协议通过全部门槛以前保持为空；Style Atlas 候选走独立的无来源、证据充分路径，不会因为处理完 120 部就获得权限。合成契约／运行器证据只证明动态调度与提前停止机制，不提供真实 V5、文风学习、盲测、独立泄漏复核或发布证据。

---

## 14 · 许可证与法律边界

`corpus/general/` 中由仓库权利人拥有的公开派生制品，继承仓库的 [Quillframe 专有源码可见许可证](../LICENSE)。公开仓库可见性不等于采用宽松数据许可，也不会为第三方来源重新授权。

抽象、匿名和非商业目的都是风险控制措施，不会自动形成法律结论。权利门验证已声明元数据与存储目的；发布验证器执行仓库的封闭模式和泄漏政策。当公开权利仍有疑问时，两者都不能代替针对具体来源的法律审查。

---

## 15 · 相关契约

- [语料智能](README.zh-CN.md)：端到端 evidence pipeline。
- [Corpus Ingest Protocol](CORPUS_INGEST_PROTOCOL.zh-CN.md)：bounded ingestion mechanics。
- [`rights_gate.py`](rights_gate.py)：deterministic declared-rights / storage validator。
- [`discovery_runtime.py`](discovery_runtime.py)：typed discovery runtime。
- [Corpus Benchmarks](benchmarks/README.zh-CN.md)：cross-work mechanism evidence。
- [匿名公开通用语料库](general/README.zh-CN.md)：发布模式、空登记表和许可证边界。
- [自适应学习](../docs/adaptive-learning.zh-CN.md)：learning scope 与 hypothesis。

**好的 Corpus 系统会保存足够的证据让分析、审计和 rollback 成立，但绝不会让“拥有来源”变成绕过 rights、authority 或 craft reasoning 的捷径。**
