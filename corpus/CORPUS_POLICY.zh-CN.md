# Corpus Policy · 语料治理与证据规则

## 1. Corpus 是 Evidence，不是 Authority

Corpus 可以支持：
- project craft 分析；
- user-taste hypothesis 检验；
- general craft 研究；
- regression/capability benchmark 构建。

Corpus 不能自己：
- 建立项目 Canon；
- 决定角色知识；
- settle 关系/资源/信息状态；
- 覆盖用户或项目的明确 authority；
- 变成隐藏的作者模仿 prompt。

## 2. Rights Classes

每一个 source candidate 在 ingestion 前必须分类。

### `redistributable`
只有存在清晰依据时才可保存全文，例如：
- public domain；
- compatible open license；
- explicit permission；
- 用户自有/自写并允许存储的材料。

必须记录 rights basis 与 source provenance。

### `analysis_only`
材料可以合法访问/分析，但 repo storage 只允许：
- source metadata；
- derived metrics；
- mechanism-level observations；
- summaries；
- 真正必要时的短小合规 excerpt。

不得批量镜像现代版权作品全文。

### `unknown`
可以继续做 metadata/source research，但 rights 未明确前阻止全文 ingestion。

Private repo 不会降低这条边界。

## 3. Source Provenance

每个 corpus item 至少记录：

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
accessed_at:
content_fingerprint:
analysis_scope:
research_question:
```

如果 host 无法验证 provenance，应降低 confidence 或直接阻止 ingestion。

## 4. Question-bounded Analysis

不要因为一部作品“拿得到”就默认整本分析。

先从明确问题出发，例如：
- 场景如何在不靠碎句的情况下加压？
- exposition 如何嵌进 task conflict？
- 主角中心场景里，配角如何保持主动存在？
- 章尾如何产生 forward pull，而不靠 narrator advertising？

只选择回答该问题所需要的最小范围。

## 5. Counterexample Requirement

Corpus research 应主动寻找：
- 支持 hypothesis 的例子；
- 表面形式相反但仍成功的例子；
- hypothesis mechanism 失败的例子；
- genre/profile exception。

避免“找三篇支持我原观点的文本”这种 confirmation bias。

## 6. Cross-work Generalization

单一作品可以产生 observation，不能直接产生 universal rule。

General craft promotion 通常要求：
- 多个独立作品/来源；
- mechanism 跨作品一致；
- 至少一个 counterexample/profile-boundary check；
- regression/capability eval；
- 不生成 named-author imitation rule。

## 7. User-taste Learning

User-taste corpus selection 应从 preference hypothesis + gap 出发，而不是“找用户喜欢的类似作品”。

Corpus 的作用是区分 mechanism。

例如：

```text
observed rejection: sentence-per-paragraph pseudo-speed
hypothesis: 用户要的是快因果，不是碎片排版
corpus gap: 对比完整段落高节奏 vs fragment-heavy 场景
result: strengthen / narrow / contest hypothesis
```

## 8. Named-author Boundary

不得建立目标为直接模仿现代/在世作者的 durable profile。

允许：
- broad genre convention；
- high-level structural/craft mechanism；
- cross-author aggregate pattern；
- 用户自己拥有的 style evidence；
- public-domain craft analysis。

不允许作为 framework behavior：
- 可复用的“完全照 Author X 写”机制集；
- 为模仿而提取 signature phrase/cadence；
- 把大量版权 excerpt 当 style prompt 保存。

## 9. Writer Isolation

推荐 Writer 输入：

```text
benchmark / mechanism
+ minimal evidence summary
+ relevant project/user profile
```

而不是 raw corpus text。

Regression bad example 默认仍是 post-generation critic context，除非某个 eval 明确需要其他路径。

## 10. Removal / Correction

如果后来发现 rights、provenance 或 analysis 无效：
1. 标记 source/item invalid；
2. 删除不应保存的材料；
3. 找出 dependent analysis/benchmark/eval；
4. invalidate 或 rebuild；
5. 降级依赖该 evidence 的 learning hypothesis/promotion；
6. 写 rollback trace。

## 11. Autonomous Behavior Boundary

Corpus Scout 可以自主生成 discovery plan 与 candidate queue。实际 external retrieval 只能通过当前 host 已可用、已授权的 tools/connectors 执行。

Scout 不得伪造 source access、rights 或 quotation。
