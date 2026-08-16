<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="560" />
  <p><strong>生产流水线 · 在精确执行边界内让模型负责叙事判断</strong></p>
  <p><kbd>GROUND</kbd>&nbsp;&nbsp;<kbd>SEARCH</kbd>&nbsp;&nbsp;<kbd>SIMULATE</kbd>&nbsp;&nbsp;<kbd>DRAFT</kbd>&nbsp;&nbsp;<kbd>READ</kbd>&nbsp;&nbsp;<kbd>AUDIT</kbd>&nbsp;&nbsp;<kbd>EDIT</kbd>&nbsp;&nbsp;<kbd>GATE</kbd></p>
  <p><a href="production-pipeline.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 生产流水线

NovelForge 把一章正文视为一轮**可恢复的语义生产运行**，而不是固定的 Critic 流水线，也不是 deterministic story engine。

> **模型判断叙事意义，runtime 保证执行真相，Project authority 决定什么属于 Canon。**

## 01 · 写正文之前先建立 authority

`DRAFT` / `REVISE` 开始时先解析：

- current/pinned Framework identity；
- consuming Project 与 exact lock/fingerprint；
- 只能有一个 `task_mode`；
- manager session/run/checkpoint identity；
- 当前 Canon/plan/candidate fingerprint 与 authority cutoff；
- 当前真实 host capabilities / permissions。

旧聊天与 provider-native session 只是上下文，不是 authority。Resume 必须重新验证 current Project/Framework authority 与尚未完成工作的 capability。

## 02 · Agent 自己搜，runtime 只守 context boundary

Manager/model 自己判断缺什么知识。必要时调用 `context.select`，自己形成 query、检查结果、排除无关 match、reformulate / continue，并在证据足够时停止。

Lexical/vector/top-k 等 retrieval primitive 可以产生候选，但不能把候选分数冒充 narrative relevance。

模型选完以后，deterministic context infrastructure 只验证客观边界：

- exact selected/source IDs 与 fingerprints；
- stage / private-state visibility；
- runtime 能机械证明的 temporal eligibility；
- 某操作在机械意义上确实需要时的 exact higher-authority refs；
- hard context/resource budget。

`context_assembly.py` v2 不再声明 literary context class “必需”，也不判断 semantic sufficiency。缺少语义证据应通过 search/selection 修复，而不是再写一条 Python relevance rule。

## 03 · Story / Planning preflight

Manager 判断当前工作相对于 Project state 是否合法。Plan 继续与 Accepted Canon 分离。

`planning_horizon.py` 可以执行 declared commitment strength/depth、promoter class、exact before-state 与 fingerprint 等不变量。**Planner** 决定现在需要规划多深、什么应该保留不确定、是否需要更多 research/replanning。NovelForge 不设置 universal N-chapter / N-volume horizon。

## 04 · 先解决人物因果，再写 prose

Pre-draft causal path 是：**private character/world state → `character.action_propose` → `scene.resolve_actions` → compact writer-safe realization projection → Writer**。

人物 private state 是 causal evidence，不是 prose payload。Runtime 可以执行 evidence identity、authorized visibility 与 story-time eligibility；motivation、plausible inference、integrity、knowledge use 等语义问题由模型判断。

`scene.realization_project` 应保持 compact。它的作用是保存 observable interaction/event trace 与 privacy boundary，不是生成第二份 Character Sheet 或巨型 Realization Sheet。

## 05 · Raw Draft 与 Surface realization

当前因果问题足够 grounded 后，Writer 才生成 event-first Raw Draft。Raw Draft 始终是内部产物。

负面 regression example 在首轮 Writer context 中保持冻结，直到 candidate fingerprint 冻结后才可用于 post-generation diagnosis，避免坏例 priming。

Surface Fundamentals 继续作为 craft knowledge 与 regression vocabulary。段落比率、对话比率等机械指标只通过 optional prose telemetry 按需提供，**default-off**，绝不作为通用文学 verdict。

## 06 · Blind Reader

Production Reader 是 `reader.engagement_audit`。

它只接收 candidate、reader-visible evidence 与最小 target-reader behavior profile。默认看不到：

- author intent / future plan；
- private character state；
- Writer reasoning；
- 完整 quality taxonomy / expected HF code；
- prose telemetry；
- hard-rule audit instruction；
- prior reviewer verdict / repair plan。

它的任务是像真实读者一样阅读，并报告真正影响体验的东西：pull、boredom、confusion、disbelief、emotional response、artificiality、interest、anticipation、irritation、attachment 或其他 salient effect。它不需要为了 schema 把每个文学维度都填一遍。

## 07 · Semantic Rule Auditor

Hard narrative rule 不等于 Python literary rule。

`quality.semantic_rule_audit` 获得 authoritative semantic-rule index 与 authorized evidence，自行判断 applicability，并给出可追踪的 `PASS | FAIL | NOT_APPLICABLE | INSUFFICIENT_EVIDENCE`。

Runtime 只验证正确 rule authority 是否可用、audit 是否真的针对 exact candidate 执行，以及 required independent identity/receipt 是否有效；它不决定 prose 在语义上是否违反规则。

Confirmed blocking FAIL 路由 repair；required audit 缺失时保持 unresolved。

## 08 · Editor 决定 repair mechanism 与 depth

`editor.repair_spec` 综合：

- Blind Reader findings；
- Semantic Rule Auditor findings；
- authorized story/Canon evidence；
- Project/style constraints；
- 当前 repair goal，以及显式选择后确实 relevant 的 active preference evidence。

Editor 判断真正 mechanism、repair owner，以及下一轮应该 `local_or_bounded_repair` 还是 `fresh_realization`。

`quality/repair_policy.py` v2 **不再**根据 owner/scope/cluster 猜文学 repair depth；它只执行 Editor 已选 mode 所要求的 writer information boundary。若选择 fresh realization，可以隐藏 rejected prose / concrete patch instruction，避免 Writer 被 patch-loop anchoring。

HF/RG taxonomy 继续作为 diagnostic vocabulary / regression label。Blind Reader 可以自然报告“这些人像在互相念岗位说明书”；Rule Auditor / Editor 再在有用时映射到 HF-30。

## 09 · Challenger comparison 与 plateau

Revision 不天然等于 improvement。

Material repair 需要比较时，由 `quality.compare` 语义判断 incumbent vs challenger。`quality_evolution.py` 只持久化 candidate fingerprints、comparison receipts、consume-once state 与 configurable workflow plateau limit，不自己选择 literary winner。

Tie / incumbent win 都是合法结果；系统可以停止，而不是无止境重写。

## 10 · Release gate

`production_readiness.py` / `production_release.py` 只验证 exact binding 与 conjunctive gate state，例如：

- required registered Reader / semantic-rule / independent result 是否存在；
- exact candidate/subject/fingerprint 是否匹配；
- worker/provenance/independence requirement 是否满足；
- deterministic structural receipt / authority invariant 是否有效。

它们不会重新判断“这一章好不好”。

缺失 required semantic judgment 时必须保持 `PENDING_MODEL` / pending，而不是 PASS。Workflow 如果只是正确记录“没有模型 capability”，说明执行诚实，不代表 semantic evidence 已通过。

## 11 · Independent semantic review

Independence 是 semantic judgment 之外的独立属性。

Gate 真正要求 independence 时，必须使用 genuinely separate invocation/session/worker、bounded packet 与 exact candidate fingerprint。Manager 可以 package/dispatch/validate/consume，但不能换一个 internal role label 就给自己盖 independent PASS。

Transport failure 可以切换 eligible transport；有效的语义拒绝不是 transport failure，必须进入 repair，也不能反复更换评审直到有人接受 candidate。

## 12 · Acceptance 与 Settlement 仍然分离

Review-ready prose 仍不是 Accepted Canon。

只有 explicit user acceptance / authorized Canon-change intent 才能进入 `SETTLE`。Settlement 继续是 deterministic transaction，要求 exact acceptance evidence、checkpoint/write authorization、before-state/CAS、projection receipts 与 postcondition verification。

Quality evidence 不能把自己批准进 Canon。

## 13 · 默认 adaptive graph

默认生产图按以下阶段顺序执行：

1. authority/session bootstrap；
2. agent-owned search/context selection；
3. deterministic exact-set/stage/fingerprint verification；
4. story/planning preflight；
5. character action、scene collision，再生成 compact realization；
6. Writer Raw Draft、Surface realization，然后冻结 candidate fingerprint；
7. Blind Reader；
8. 必要时 Semantic Rule Auditor；
9. Editor repair specification，以及必要的 repair/challenger comparison；
10. continuity/state checks；
11. required independent semantic gate；
12. user-visible Review Draft；
13. explicit acceptance，随后由独立 `SETTLE` mode/transaction 完成 settlement。

Manager 只加载当前 failure 真正需要的最小 semantic contract set。默认优先一个能力足够强的 agent；只有 information isolation、independent evaluation、private state 或真正 specialist benefit 能证明收益时才拆分。

## 精确参考

- [上下文与记忆](context-and-memory.zh-CN.md)
- [质量与 QA](quality-assurance.zh-CN.md)
- [自适应学习](adaptive-learning.zh-CN.md)
- [编排协议](../harness/ORCHESTRATION_PROTOCOL.zh-CN.md)
- [`harness/semantic_workers/model_contract_catalog.json`](../harness/semantic_workers/model_contract_catalog.json)
- [`quality/repair_policy.py`](../quality/repair_policy.py)
- [`quality/production_readiness.py`](../quality/production_readiness.py)

<div align="center"><sub>限制权力，让模型理解小说，把每个 consequential result 绑定到 exact state。🌸</sub></div>
