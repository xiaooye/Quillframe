# 规格 · NovelForge 7.2 Author Control + Quality Evolution

## 基线

- 上一版本：NovelForge 7.1.0
- Framework 开发基线：`5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`
- 7.1 已发布 consumer lock：`d9126b2ac39abce0554d83ad74a0ded97017b2a2`
- Rollback：开发基线 commit
- Change class：Framework release / structural feature
- Primary mode：`SYSTEM-IMPROVE`

## 问题

7.1 已建立 typed capability、durable learning cycle、provenance、independent semantic runtime、immutable bundle 与 strict Canon boundary，但作者侧与质量闭环仍有六个缺口：

1. Reader Engagement 是强通用质量模型，但还缺“不同阅读行为的模拟读者反应”与 disagreement signal；
2. Rewrite/Regenerate 有 owning-mechanism 规则，但缺可恢复、可比较、能检测 plateau 的 candidate evolution ledger；
3. Sparse Context 很严格，但作者很难直接检查“这次到底注入了什么、为什么、在哪个阶段、能否 pin/unpin”；
4. Learning/Project/Runtime storage 已分离，但缺一个 authority-aware、可编辑而不越权的 memory/control surface contract；
5. Character Simulation 与 Continuity 有规则，但缺统一 typed integrity artifact，把 agenda/knowledge/voice/relationship/space-task state 与 evidence chain 明确暴露；
6. 长篇历史压缩仍主要依赖 Project Adapter/Context Manifest 选择，缺少 event-relevance + tiered derived memory 的通用 deterministic budget layer。

## 外部机制证据

这些来源只形成 `adopt | adapt | reject` candidate，不成为 dependency：

- AuthorAgent `47e9570fb96b9d151a3b1f9c22e3a365eab9bd9c`
  - reader panel：pairwise tournament、position swap、judge-collapse/score-clustering diagnostics；
  - beta reader：tension、pacing、continue intent、confusion、favorite/stumble；
  - revision orchestrator：narrow expert passes + unified findings；
  - memory tier：budgeted CORE + archival retrieval。
- autonovel `d165f267a0ffd34f3b0a70a8a72ac38cb8e4a542`
  - multi-reader disagreement/consensus；
  - iterative revision、pairwise comparison、plateau stopping。
- NovelClaw `226d50d3ec284c9cc037c47eb14af39505f9ed74`
  - author-visible workspace、memory banks、runs、storyboard、character/world control surface。
- StoryWriter `08c32d74ce08b46a762951c7f2235772022baa77` / arXiv:2506.16445
  - event-based outline；
  - current-event-aware dynamic history compression。
- MAGNET + ATLAS / arXiv:2607.00918
  - persona-grounded character actions based on shared world state and evolving goals；
  - graph-based scene/world-state verification。
- StoryState / arXiv:2602.01305
  - explicit editable story state；
  - localized edits without treating implicit model memory as authority。

## 目标

### G1 · Reader Simulation Panel

新增 provider-neutral `quality/reader_panel.py`：

- 默认使用 reading-behavior personas，而不是人口属性画像；
- 支持 single-candidate reaction 与 A/B pairwise comparison；
- semantic jobs 使用已有 `external_review` contract，仍由独立 runtime routing 决定实际 worker；
- aggregate tension / continue intent / confusion / favorite / stumble / emotion / next-page desire；
- 识别 persona disagreement、reason templating/judge collapse、first-shown bias 等诊断；
- panel 结果是 diagnostic evidence，**不自动等于 mandatory independent semantic gate**。

### G2 · Durable Quality Evolution

新增 `quality/quality_evolution.py`：

`baseline → candidate → comparison → keep/discard → repair owner → next candidate → plateau/complete`

要求：

- SQLite durable run/candidate/comparison ledger；
- candidate/result fingerprint binding；
- comparison result logical consume-once；
- 记录 repair owner，不把所有失败归结为 line edit；
- pairwise winner 只能在当前比较的两个候选中选择；
- 连续无增益达到阈值时进入 `plateau`，避免无限 revision；
- evolution state 没有 Canon/Framework-write authority。

### G3 · Context + Memory Inspector

新增 `harness/context_inspector.py`：

- 统一展示 Context Manifest item 的 id/class/source/authority/inclusion reason/stage/relevance/pin state；
- 区分 `locked | accepted | active_plan | review | proposal | runtime | learning | corpus | derived`；
- 支持 `pin_context | unpin_context | set_priority | hide_derived | invalidate_derived` 等低 authority overlay；
- 对 Accepted/locked 内容的“编辑”只生成 proposal，不能直接改变 Canon；
- 明确 `writer_pre_draft | post_draft_critic | independent_reviewer | never` 等注入阶段；
- regression/hidden-gold isolation 仍强制执行。

### G4 · Tiered Derived Memory + Event Relevance

新增 `harness/memory_tiers.py`：

- 只消费 already-derived / project-provided memory items，不擅自总结 Canon；
- `hot | working | archival` 三层；
- explicit pin > current event overlap > participant/relationship match > relevance/priority；
- whole-item-or-skip budget；
- 每个 derived item 必须携带 source refs/fingerprints；
- derived memory 永远 `authority=false`，可失效重建；
- current event id 可提升与 StoryWriter 类似的相关历史，而不是整库注入。

### G5 · Character Integrity + Evidence-Chained Findings

新增：

- `quality/findings.py`：统一 normalized finding schema；
- `quality/character_integrity.py`：为当前场景重要角色打包 bounded audit job。

至少审：

- agenda alignment；
- knowledge boundary；
- voice drift；
- relationship position；
- spatial/task state；
- surprise-within-consistency。

Finding 至少带：candidate evidence、established/authority evidence、repair owner、severity、confidence、source refs。Reviewer 不获得 writer private reasoning/hidden gold。

### G6 · Scene/World State Graph Audit

新增 `quality/state_graph.py`：

- scene snapshot 使用 typed nodes/edges；
- deterministic diff 只报告“需要解释的状态变化”或明确 stable-field contradiction，不替代 semantic judgment；
- change 必须能绑定 transition/event evidence；
- 输出 before/after evidence chain；
- graph 只是 derived verification view，不成为第二 Canon authority。

### G7 · Author-facing CLI Surface

顶层 CLI 新增：

- `reader-panel`
- `quality-evolution`
- `context-inspect`
- `memory-tiers`
- `character-integrity`
- `state-graph`

CLI 只提供 deterministic packaging/inspection/state transition；没有声明 semantic capability 时不得自行调用模型。

### G8 · Release / CI Contract

- `HARNESS_MANIFEST.yaml` 升级到 7.2.0 并声明新 quality/control modules；
- Normal CI 编译并运行全部 7.2 self-tests；
- bundle 仍 deterministic；
- docs visual/customer rewrite 不属于本 feature；仅更新 machine/harness/engineering contract 所需版本信息；
- consumer project 不在本 run 自动升级，必须等 Framework exact commit green + new bundle fingerprint 后另行 dependency migration。

## Adopt / Adapt / Reject

### Adopt

- reader disagreement 作为 editorial signal；
- pairwise comparison 优先于绝对分数；
- narrow pass + unified finding taxonomy；
- author-visible memory/context inspection；
- tiered memory budget；
- event-relevance retrieval；
- character goal/shared-state verification；
- graph-based state diff。

### Adapt

- reader personas 以 reading behavior/genre expectation 为主，不默认建立人口画像；
- memory bank 不是 source of truth，而是 authority-aware view/overlay；
- panel 可由同一模型多个 persona 产生，但不能冒充 mandatory independent reviewer；
- graph/world state 是 derived verification layer，Canon 仍由 consuming project 持有；
- revision loop 必须绑定 owning mechanism 与 fingerprint，而不是“哪个分数最低就润哪里”。

### Reject

- 固定多 Agent round-table 作为默认质量方案；
- 同一 manager role-play 多 persona 后宣称 independent semantic PASS；
- model memory / summary / dashboard edit 自动升级为 Canon；
- demographic persona 自动推断用户或目标读者敏感属性；
- absolute 1–10 分数单独决定 keep/discard；
- 无限 reviewer shopping / revision until someone says pass；
- 为了“动态记忆”整库注入或 future-data leak。

## Acceptance Criteria

1. Reader Panel self-test 证明 persona jobs fingerprint-bound，aggregation 能检测 disagreement 与 templated-reason collapse。
2. Pairwise self-test 证明 swapped order 正规化后 first-shown bias 可检测。
3. Quality Evolution self-test 证明 durable resume、comparison consume-once、illegal winner rejection、plateau stopping。
4. Context Inspector self-test 证明 Accepted/locked direct mutation 被阻止并降为 proposal。
5. Memory Tier self-test 证明 hard budget、whole-item-or-skip、event relevance、derived authority=false。
6. Character Integrity self-test 证明 bounded job 不含 forbidden context，result 可转 normalized evidence-chained finding。
7. State Graph self-test 证明 stable-field contradiction 与 evidence-backed transition 能区分。
8. `novelforge.py self-test` 覆盖全部 7.2 deterministic modules。
9. Normal CI `model_execution=false`，不因 reader panel/evolution 自动花费 provider usage。
10. Framework hygiene 证明无 consumer-project Canon/private user-taste leakage。
11. deterministic bundle 两次 build bytes/fingerprint 一致。
12. exact 7.2 candidate commit CI green 后才可标 release-ready。
13. 未执行 consumer lock/Canon migration。
