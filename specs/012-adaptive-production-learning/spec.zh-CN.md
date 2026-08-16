# Spec 012 · AI-Native 自适应生产架构重构

状态：implementation candidate
范围：仅 Generic NovelForge
Primary mode：`SYSTEM-IMPROVE`

## 1. 问题

NovelForge 需要把**执行真相**与**叙事真相**真正分开。此前 production path 在 Context、Reader、repair depth、telemetry、learning、planning、simulation 周围积累了不少 deterministic helper。其中一部分保护真实 authority / durability；另一部分则容易因为“代码好测试”而把文学判断冻结成 Python 规则。

本 candidate 验证而不是预设以下 hypothesis：

> **Code provides capabilities and constraints; models provide intelligence.**
>
> **Deterministic code enforces execution truth; AI agents evaluate narrative truth.**

目标不是“少写 Python”，而是只让 Python 保留客观可执行不变量，并删除那些假装理解文学意义的 deterministic mechanism。

## 2. 当前 architecture decision

NovelForge 采用 **thin deterministic kernel + model-owned semantic runtime**。

### Deterministic kernel

只拥有可机械证明的行为：

- authority / permission / Project isolation；
- exact artifact identity、hash、fingerprint；
- provenance 与 exact-source reference；
- session/run/checkpoint persistence；
- before-state / CAS / idempotency / transaction；
- capability / credential boundary；
- stage visibility 与 private-state isolation；
- hard resource/context budget；
- typed envelope validation 与 receipt binding；
- semantic execution 是否真实发生、是否绑定 exact candidate、independent worker provenance 是否成立。

它回答的问题只有：**授权操作是否真的针对正确状态发生了？**

### Semantic runtime

模型拥有需要理解意义的工作：

- search intent、query formulation、retrieval continuation / stopping；
- narrative relevance 与 context sufficiency；
- planning depth 与 uncertainty decision；
- character motivation、plausible inference 与 action；
- scene causality 与 dramatic realization；
- Reader experience；
- semantic hard-rule applicability / violation；
- repair mechanism 与 repair depth；
- preference interpretation 与 learning hypothesis。

它回答的问题是：**这段故事/文本/上下文意味着什么，下一步应该怎么做？**

## 3. Current owner map

| Subsystem | Live owner | Decision | Boundary |
|---|---|---|---|
| session / checkpoint / resume | `harness/session_runtime/**` | KEEP | durability、stale-state rejection、capability re-resolution |
| Control Plane / write intent | `harness/control_plane/**` | KEEP | permission、exact action/target/before-state、idempotency |
| context eligibility / stage isolation | `harness/context_inspector.py` | KEEP | 只判断机械 eligibility；明确禁止 `relevance` |
| Context Assembly | `harness/context_assembly.py` | THIN | exact selected refs、stage/fingerprint/private boundary；不判断文学 sufficiency |
| semantic context/search | `context.select` | MIGRATE_TO_AGENT（已实现） | 模型自己决定缺什么、怎么搜、相关性、reformulate 与何时停止 |
| hard-budget packing | `harness/memory_tiers.py` | KEEP | semantic selection 之后的 whole-item budget enforcement |
| planning commitment authority | `harness/planning_horizon.py` | KEEP / ADAPT | code 执行 declared depth/commitment/CAS；Planner 判断什么深度有用 |
| character action | `character.action_propose` | MIGRATE_TO_AGENT（已实现） | private state 是 causal evidence，不是 prose serialization |
| scene collision | `scene.resolve_actions` | MIGRATE_TO_AGENT（已实现） | compact causal trace，不做 deterministic story engine |
| writer-safe realization | `scene.realization_project` | THIN | privacy boundary；不建立 Realization-Sheet serialization obligation |
| Blind Reader | `reader.engagement_audit` | MIGRATE_TO_AGENT（已实现） | 只看 reader-visible evidence；不接受 taxonomy/HF/telemetry priming |
| semantic hard rules | `quality.semantic_rule_audit` | MIGRATE_TO_SEMANTIC_RULE（已实现） | 模型判断 PASS/FAIL/N/A/insufficient evidence |
| Editor repair | `editor.repair_spec` + `quality/repair_policy.py` | MIGRATE_TO_AGENT + THIN | Editor 选 owner/mode；Python 只执行所选 writer-context boundary |
| prose telemetry | `quality/prose_telemetry.py` | OPTIONAL_TOOL | 按需指标；不成为文学真理/default Reader context |
| readiness/release | `quality/production_readiness.py`、`production_release.py` | KEEP | exact semantic binding + conjunctive structural receipts |
| feedback interpretation | `learning.preference_interpret` | MIGRATE_TO_AGENT（已实现） | 模型解释 meaning / scope candidate |
| durable learning | `learning/learning_store.py`、`promotion_gate.py`、`author_model.py` | KEEP / THIN | persistence/write authority/CAS；模型选择当前相关的 active hypothesis |
| HF taxonomy | `quality/taxonomy.json` | MIGRATE_TO_SKILL | diagnostic vocabulary / regression label，不做 default Reader checklist |

本 candidate 不增加第二套 context store、Reader、simulator、release authority 或 durable preference DB。

## 4. Deterministic Overreach Audit

| Former/current mechanism | 为什么可疑 | 当前处理 |
|---|---|---|
| required literary context class/purpose gate | “某类信息在语义上必须相关”本身需要理解任务 | 已从 Context Assembly v2 删除；exact higher-authority required ref 继续 deterministic |
| fixed last-N / similarity threshold 当 relevance | recency/similarity ≠ narrative relevance | 作为 semantic truth REJECT；只允许做候选 retrieval primitive |
| Reader 暴露完整 taxonomy/HF | 会 priming evaluator、制造 checklist finding | 已从 production Blind Reader input 删除 |
| telemetry 预装给 Reader/Editor | 会用机械数字 anchoring semantic judgment | default-off，降为 OPTIONAL_TOOL |
| owner/scope → repair-depth mapping | repair depth 属于文学判断 | 已删除；Editor 显式选择 `generation_mode` |
| Python 规定 contradicted/unknown 不能支持角色行动 | 角色 belief / doubt / inference 需要语义判断 | 已删除；runtime 只检查 evidence identity/story-time eligibility |
| numeric evidence-count promotion threshold | evidence sufficiency/stability 是 semantic | 已删除；semantic promotion review 判断证据语义 |
| 自动注入全部 active Author Model preference | active authority 不等于当前 relevant | 已删除；模型/manager 显式选择 active hypothesis IDs |
| Reader 必填一整套结构维度 | 容易强迫模型“编出”没有真正发生的体验 | Reader schema 已变薄，只保留 salient report/evidence |
| scene/realization 巨型 JSON | 容易变成 Character Sheet → Realization Sheet → prose serialization | 已 thin 成 compact interaction/observable trace + optional evidence |

剩余 deterministic rule 必须能回答客观 execution question。以后任何新 Python 条件如果在判断 prose、dialogue、motivation、relevance、continuity meaning、Reader experience 或 planning quality，默认视为 architecture regression，除非有明确证明。

## 5. Rule architecture

### A. Deterministic invariant

例如 stale fingerprint、wrong Project、unauthorized write、malformed receipt、missing capability、CAS conflict、invalid independent identity、stale semantic result。

### B. Semantic hard rule

例如人物使用不可获得的知识、无因果支撑的 character-integrity break、POV leakage、Canon contradiction、agenda-to-dialogue serialization、Project-declared narrative hard constraint。

Hard 的含义是：**模型确认 FAIL 后可以 blocking**；不是“必须由 Python 检测”。

`quality.semantic_rule_audit` 获得 authoritative rule index 与 authorized evidence，自行判断 applicability，并对每条规则返回 `PASS | FAIL | NOT_APPLICABLE | INSUFFICIENT_EVIDENCE`。

### C. Guideline / craft knowledge

继续作为 skill、profile、reference、agent instruction 存在。不能因为它是重要写作原则，就自动升级成 deterministic gate。

## 6. Blind Reader != Rule Auditor != Editor

**Blind Reader** 只看 reader-visible information，按真实目标读者方式阅读。它看不到 author intent、future plan、private character state、完整 taxonomy、expected HF code、telemetry 或 semantic-rule prompt。

**Semantic Rule Auditor** 获得 authoritative hard-rule index，并可请求/fetch 被授权的 evidence；它做显式 semantic compliance judgment。

**Editor** 综合 Reader、Rule Auditor、Canon/story evidence、Project constraint，判断 mechanism、repair owner、`local_or_bounded_repair | fresh_realization`，以及是否需要 incumbent/challenger comparison。

拆成这些角色是因为 information boundary 互相冲突，而不是为了画 multi-agent 架构图。

## 7. Search / Context architecture

Search 是 capability，不是预计算文学 context pipeline。

模型自己决定：

1. 缺什么；
2. 搜什么；
3. query 怎么写；
4. 哪个结果真正相关；
5. 是否 reformulate / broaden / narrow；
6. 什么值得保留；
7. 什么时候 evidence 已经够了。

Runtime 只提供 authorized search/fetch/extract/index primitive、provenance、exact ref、visibility 与 resource limit。Context Assembly v2 在模型选完以后检查 exact selected refs、stage 与 fingerprint，不给 relevance 打分，也不宣称 narrative sufficiency。

## 8. Planning / Character / Realization

Planning commitment authority 继续 deterministic，因为 committed depth、promoter class、evidence refs、before-state 与 fingerprint 都是 execution state。**什么深度现在有价值由 Planner 决定。** Framework 不设置 universal chapter/volume/time horizon。

Character/scene path：

`private state → model action proposal → model scene/world collision → compact observable interaction trace → Writer`

Private state 是因果证据，不是 dialogue/exposition payload。Writer-safe realization 必须保持 thin，避免成为第二份 Character Sheet。

## 9. Learning / Author Model

模型解释 feedback，并提出最窄 scope / mechanism；deterministic infrastructure 只负责 evidence persistence 与 activation authority。

`active` 只表示**durably eligible**，不表示“每次未来任务都 relevant”。Production 只拿显式选择的 active hypothesis IDs。User-taste activation 仍同时要求 explicit write authority + 当前绑定的 promotion prerequisite；General Craft promotion 仍只属于 SYSTEM-IMPROVE，并继续要求更强 provenance / counterexample / eval / version / rollback / CI。

## 10. Current research ledger

本 candidate 在当前 primary sources 上重新 research，而不是继承旧聊天结论。

| Source family | Mechanism | Decision | NovelForge use |
|---|---|---|---|
| Anthropic current agent/context/harness guidance | simple composable agents、iterative context curation、durable handoff/context reset | ADAPT | harness 保持稳定，模型能力可升级；避免 context bloat 与旧 transcript authority |
| OpenAI Agents SDK + current GPT model guidance | model-driven tool choice、sessions、guardrails、agents-as-tools/handoffs | ADAPT | 模型在 deterministic guardrail 内自己选 semantic tool/search；evaluator pin 必须按 current eval evidence 更新 |
| LangGraph | checkpoint、persistence、interrupt、durable replay | ADAPT | 支持 Session/Checkpoint/receipt 分离；无需引入 dependency |
| AutoGen | 先 single agent，确有 collaboration/specialization 收益才 team | ADOPT | multi-agent discipline |
| CrewAI Flows / agents | structured state vs autonomous teams | ADAPT | 借鉴 stateful execution；REJECT org-chart agent proliferation |
| PydanticAI | dependency/toolset/capability separation、optional durable runtime | ADAPT | capability-scoped hands；DEFER 新 durable dependency |
| Google ADK | Session/Event state 与 tool-using ReAct agent | ADAPT | 支持 durable session != model context |
| AWS AgentCore | isolated runtime、identity、gateway、memory | ADAPT | brain/hands/session 与 credential isolation |
| DSPy | declarative LM program + eval optimization | ADAPT | implementation 与 evaluation 分离；REJECT schema inflation pseudo-rigor |
| ReAct / Self-RAG / Adaptive-RAG | agentic action/retrieval、adaptive retrieve/skip | ADOPT / ADAPT | model-owned retrieval continuation/stopping；REJECT fixed horizon as truth |
| WriteHERE / DOME | dynamic hierarchical long-form planning | ADAPT | Planner-owned depth 与 iterative decomposition |
| MAGNET/ATLAS 等 character simulation | persona/private state 先驱动 action，再进入 prose | ADAPT | 保持 causal private-state boundary；REJECT sheet-to-prose serialization |
| Sudowrite / Novelcrafter | explicit story state、selective context、revision history | ADAPT | explicit state/context visibility；REJECT fixed recency 当 semantic authority |
| current LLM-as-judge / creative-writing eval research | auxiliary-information bias、position bias、human agreement ceiling、decomposed checks | ADOPT / ADAPT | Blind Reader isolation、order-swapped pairwise、独立 decomposed hard-rule audit |
| Rust/Go/WASM/Starlark/Zig/C++/Temporal/DBOS 等 | alternative runtime/extension stack | DEFER | PR #90 没有 current owner/performance/packaging evidence 支持语言或 dependency migration |

## 11. Ablation contract

不能因为新 architecture 看起来干净就宣称更好。Substantial semantic simplification 必须在同 candidate / same authority 下比较。

Required family：

- recent horizon 之外的 remote context；
- superficially similar 但 narratively irrelevant 的 match；
- autonomous search continuation / stopping；
- Blind Reader agenda-dialogue experience vs taxonomy-primed Reader；
- legitimate formal completeness；
- inaccessible knowledge vs plausible inference；
- dynamic planning profiles；
- character embodiment without agenda serialization；
- holistic vs decomposed hard-rule audit；
- Reader/Editor with vs without preloaded telemetry；
- unauthorized-state 与 stale-candidate deterministic rejection；
- context loss 之后 long-horizon resume + authority revalidation。

`evals/ai_native_ablation_manifest.json` 绑定 semantic ablation pairs。Manager 可以检查 packet 与 deterministic invariant，但不能自己编造 semantic outcome。没有 eligible independent model transport 时，semantic outcome 必须保持 `PENDING_MODEL`。

## 12. Security

AI-owned search 不等于 unrestricted search。Tool 继续 capability-scoped；credential/token 不进入 semantic context；external source text 不能重定义 runtime authority；private character/creator/Reader information boundary 保持显式；semantic output 不能自授 write authority；stale/wrong-candidate receipt fail closed。

## 13. Compatibility / rollback

- 不修改 consuming Project lock、manuscript、Canon、Settlement；
- 本 candidate 不 bump/release/promote Framework 版本；
- additive semantic contract 按 progressive disclosure 加载；
- Context Assembly v2 明确删除 semantic class/purpose obligation，但保留 exact-ref/stage/fingerprint safety；
- 旧 caller 如果依赖 class/purpose semantic obligation，应把该判断迁到 `context.select` / Manager，并在真正机械 mandatory 时传 exact authoritative refs；
- PR #90 每个 refactor slice 都可 revert；downstream consumer 继续使用原 lock。

## 14. Acceptance

`READY_FOR_HUMAN_REVIEW` 需要：

1. live owner/docs/manifest 同步；
2. candidate-owned deterministic self-test 与 exact-head CI；
3. blind queue + ablation packet 不泄露 hidden gold；
4. required semantic cases 对 exact candidate 完成真正 independent execution；
5. security/compatibility review 与 rollback evidence。

仅仅因为 workflow 成功记录“缺少模型能力”并不等于 semantic PASS；independent capability 缺失必须标记 `PENDING_MODEL`。
