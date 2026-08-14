# 规格 · NovelForge 7.2 Author Control + Quality Evolution

## 基线

- 上一版本：NovelForge 7.1.0
- Framework 开发基线：`5e8f586b4ce0c1b90c71d0ec38064e3445daff7a`
- 历史 consumer 曾锁定的 7.1 release commit：`d9126b2ac39abce0554d83ad74a0ded97017b2a2`
- Rollback：开发基线 commit
- Change class：Framework release / structural feature
- Primary mode：`SYSTEM-IMPROVE`

## 问题

7.1 已建立 typed capability、durable learning、provenance、independent semantic execution、immutable bundle 与 strict Canon boundary。下一步真正缺的不是“更多 Agent”，而是 **作者可观察/可干预的控制面 + 可恢复、可比较、可停止的质量闭环**。

7.2 解决：

1. Reader Engagement 很强，但缺 first-class 模拟读者反应与 disagreement signal；
2. Rewrite/Regenerate 有 owning-mechanism 规则，但缺 durable candidate evolution / pairwise / plateau；
3. Sparse Context 严格，却缺“到底注入了什么、为什么、在哪个 stage”的作者可见 inspector；
4. Runtime/Learning/Project storage 已分离，却缺 durable、可编辑、又不越过 Canon authority 的 Memory Bank；
5. Character/Continuity/Quality audit 缺统一 evidence-chained finding contract；
6. 长篇历史选择缺 event-relevance + tiered derived-memory budget；
7. 多类审查缺一个统一 narrow-pass revision report，把失败真正送回 owning mechanism。

## 外部机制证据

外部系统只产生 `adopt | adapt | reject` candidate，不成为 dependency：

- AuthorAgent `47e9570fb96b9d151a3b1f9c22e3a365eab9bd9c`：reader/beta-reader signal、narrow revision passes、tiered memory；
- autonovel `d165f267a0ffd34f3b0a70a8a72ac38cb8e4a542`：reader consensus/disagreement、pairwise comparison、iterative revision、plateau stopping；
- NovelClaw `226d50d3ec284c9cc037c47eb14af39505f9ed74`：author-visible workspace、memory banks、runs、storyboard、character/world control surface；
- StoryWriter `08c32d74ce08b46a762951c7f2235772022baa77` / arXiv:2506.16445：event-based outline + current-event-aware history compression；
- MAGNET + ATLAS / arXiv:2607.00918：角色目标/shared world state 驱动行动 + graph-based world-state verification；
- StoryState / arXiv:2602.01305：explicit editable story state，同时不把 implicit model memory 当 authority。

## 目标

### G1 · Reader Simulation Panel

`quality/reader_panel.py` 必须：
- 默认使用 reading-behavior persona，不做 demographic profiling；
- 支持 single-candidate reaction 与 A/B pairwise comparison；
- pairwise 对每个 persona 做 visible-order swap；
- 聚合 continue intent、confusion、attention loss、favorite/stumble、reward、emotion；
- 识别 persona disagreement、templated-reason/judge collapse、first-shown bias；
- 复用 bounded `external_review` job，但同模型多个 persona 绝不能冒充 independent reviewer。

### G2 · Durable Quality Evolution

`quality/quality_evolution.py`：

`baseline → candidate → comparison → keep/discard → repair owner → next candidate → plateau/complete`

要求：
- SQLite run/candidate/comparison ledger；
- candidate/result fingerprint binding；
- exact replay idempotency + logical result consume-once；
- winner 只能是被比较候选或 no-decision/tie；
- repair-owner tracking；
- no-gain plateau stopping；
- 无 Canon / Framework-write authority。

### G3 · Context Inspector

`harness/context_inspector.py` 显示 item id/class/source/authority/inclusion reason/stage/relevance/pin state，并区分：

`locked | accepted | active_plan | review | proposal | runtime | learning | corpus | derived`

支持低 authority 的 pin/unpin/priority/hide/invalidate。Protected edit 只能变 proposal。Regression / hidden-gold 不得进入 `writer_pre_draft`。

### G4 · Tiered Derived Memory + Event Relevance

`harness/memory_tiers.py`：
- 只消费 already-derived / project-provided item，不擅自总结 Canon；
- `hot | working | archival`；
- explicit pin > current-event overlap > participant overlap > relevance/priority；
- hard budget + whole-item-or-skip；
- derived item 必须有 source refs/fingerprints；
- derived `authority=false`。

### G5 · Durable Editable Memory Bank

`harness/memory_bank.py` 提供 7.2 需要的 author-editable storage/control surface：
- SQLite durable entry，按 context/character/relationship/thread/style/learning/runtime/corpus/derived bank 分组；
- 与 Context Inspector 使用同一 authority taxonomy；
- `locked` / `accepted` row 只是受保护 reference snapshot，不是可写 Canon copy；
- 修改 protected row 时创建 proposal child，原 row 不变；
- 可编辑 row 使用 exact before-fingerprint guard；
- proposal 默认 `never` injection stage，禁止 contested/future data 静默 prime drafting；
- pin/priority 只影响 retrieval；
- 导出的 Context Manifest 仍然 non-authoritative。

### G6 · Character Integrity + Evidence-Chained Findings

`quality/findings.py` 定义 normalized finding。`quality/character_integrity.py` 对重要角色打包 bounded audit：agenda alignment、knowledge boundary、voice drift、relationship position、spatial/task state、surprise-within-consistency。

Finding 带 candidate evidence、authority evidence、repair owner、severity、confidence、source refs、stable fingerprint。Writer private reasoning / hidden gold 不进入 packet。

### G7 · Scene / World State Graph Audit

`quality/state_graph.py` 只是 derived verification view：
- typed nodes/edges/transitions；
- stable-field contradiction；
- unexplained nonstable change warning；
- transition/event evidence 可解释变化；
- before/after evidence chain；
- graph 永远不是第二 Canon authority。

### G8 · Multi-pass Revision Orchestrator

`quality/revision_orchestrator.py` 必须：
- 规划 continuity / character / reader / surface / research 窄 pass；
- 某个 pass unavailable/fail 时不拖死其他 eligible pass；
- 聚合、去重 normalized finding；
- 保留 diagnostic/provenance；
- finding 必须回 owning repair mechanism；
- surface cluster → whole-scene regeneration，而不是无穷 local patch；
- SAFE-BUT-FLAT / reader-grip fail → Reader Pressure + Scene Simulation，不是 line edit。

它是 quality-control orchestrator，不是默认 multi-agent round table。

### G9 · Author-facing CLI / Project Scaffold

`novelforge.py` 暴露 Reader Panel、Quality Evolution、Revision Orchestrator、Context Inspector、Memory Tiers、Memory Bank、Character Integrity、State Graph 等 deterministic route。没有显式 semantic capability 时不得静默调用模型。

`project_sdk.py` 新 scaffold 默认 Framework 7.2.0，并声明 reader simulation、quality evolution、author context-memory control support。

### G10 · Release / CI Contract

- `HARNESS_MANIFEST.yaml` 报告 7.2.0，并声明全部 7.2 author-control / quality module；
- `SKILL.md`、`SKILL.en.md`、`SKILL.zh-CN.md` 同步 7.2 runtime authority contract；
- Normal CI 编译/自测全部新 deterministic module，同时保留全部 7.1 regression；
- Normal CI / packaging 不隐藏 model execution；
- deterministic Framework bundle reproducibility 继续 mandatory；
- customer-facing Story Loom visual/doc redesign 不属于这个 feature；
- 本 run 不迁移已停止的 consumer repo。

## Adopt / Adapt / Reject

### Adopt

Reader disagreement；pairwise > absolute score；narrow specialist pass；unified finding taxonomy；author-visible context/memory；durable editable memory；tiered/event-relevant retrieval；character goal/shared-state verification；graph diff；explicit plateau stopping。

### Adapt

Reader persona 以 reading behavior / genre expectation 为主。Memory Bank 是 authority-aware view/store，不是 source of truth。同模型 persona 不冒充 independent review。State graph 仍是 derived。Revision 绑定 fingerprint + owning mechanism，而不是“哪个分最低就润哪个”。

### Reject

默认 multi-agent round table；same-manager persona roleplay 冒充 independent PASS；model memory/summary/dashboard edit 自动成为 Canon；proposal/future data 静默进入 drafting；demographic-sensitive persona inference；absolute 1–10 score 单独决定版本；reviewer shopping；无限 revision；整库注入。

## Acceptance Criteria

1. Reader Panel job fingerprint-bound，并检测 templated-reason collapse + first-shown bias。
2. Quality Evolution 证明 durable resume、exact replay idempotency、consume-once、illegal-winner rejection、plateau stopping。
3. Context Inspector 阻止 protected direct mutation，并拒绝 pre-draft regression/hidden-gold leak。
4. Memory Tiers 证明 hard budget、whole-item-or-skip、event relevance、pin priority、derived `authority=false`。
5. Memory Bank 证明 protected edit→proposal、exact before-state guard、editable derived memory、proposal pre-draft isolation、non-authoritative context export。
6. Character Integrity 证明 bounded packet 无 forbidden context，并输出 evidence-chained finding。
7. State Graph 区分 stable-field contradiction 与 evidence-backed transition。
8. Revision Orchestrator 证明 pass failure isolation、finding dedupe、owning-mechanism routing 与 surface-cluster regeneration。
9. `novelforge.py self-test` 覆盖全部 7.2 deterministic module。
10. Project SDK self-test 证明 7.2 default scaffold + quality-control capability flags。
11. Normal CI `model_execution=false`，且全部旧 7.1 deterministic contract 继续绿。
12. Framework bundle 连续两次 build bytes/fingerprint 一致，tamper verify 仍正确失败。
13. Framework hygiene 检出 consumer Canon/private taste leakage。
14. 只有 exact final 7.2 HEAD CI green 才能称 release-ready。
15. 本 run 不执行 consumer lock / Canon migration。
