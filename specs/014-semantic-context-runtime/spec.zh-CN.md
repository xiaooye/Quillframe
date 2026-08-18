# Spec 014 — 语义上下文运行时

状态：Quillframe 0.9.x 分支实现并验证
Primary task mode：`SYSTEM-IMPROVE`
冻结 Quillframe main：`0d211675fd9f545b83d02ab4102563f0c67e11b9`
研究用 Shujuku main：`12fec85bae325cacd8370b4dd0f4aff0dfd6da0e`

## 1. 问题

Quillframe 已经区分持久 Project State 与稀疏注入 Context，也已经规定“语义相关性属于模型判断”。缺失的是中间这一层完整、可持久化、可检查的运行时：生命周期资格、派生语义索引、stage-specific greenlights、预算打包、Context Freeze 可复现性，以及 SQLite-backed Inspector projection 尚未形成一个完整 typed contract。

本特性把路径明确为：

```text
AUTHORITATIVE PROJECT STATE
→ deterministic eligibility / lifecycle / visibility gate
→ fingerprint-bound Semantic Context Profiles
→ mechanically eligible candidate universe
→ Agent semantic context decision
→ exact-id/fingerprint validation
→ stage-specific Context Greenlights
→ hard-budget packing
→ Context Freeze
→ frozen stage payloads
→ production runtime
→ receipts / Inspector projections
```

依赖方向仍然只有 `Project → Quillframe`。Semantic metadata 永远只是派生索引，不是第二套 truth model。

## 2. 不变量

1. `stored ≠ injected`；`relevant ≠ authoritative`。
2. `Plan ≠ Canon`；`Review ≠ Accepted`；`Accepted ≠ Settled`。
3. `Corpus ≠ Canon`；`Research ≠ Character Knowledge`；Memory / Telemetry / AI inference ≠ Canon。
4. 先做 eligibility，再做 relevance。相关性永远不能修复 lifecycle / visibility 不合格。
5. 模型返回的 id 必须在冻结 candidate universe 内，并通过 source/profile fingerprint 与 stage 校验；越界不是“尽量猜”。
6. Semantic Context Profile 不拥有 authority，并绑定 exact source-object fingerprint。
7. hard budget 不制造最低 token 配额；不能为了凑预算选无关 Context。
8. Context Freeze 之后，stage 不得自行回 DB 扩展上下文。
9. refresh / extension 必须显式发生，并产生新的 context fingerprint / checkpoint。
10. Context selector ≠ independent literary reviewer；现有独立语义审查不减弱。
11. contracts 必须 host-neutral；Desktop 本地 Tauri/Python/SQLite 不依赖 Cloudflare。
12. Inspector 只暴露短 reason code / provenance explanation，不暴露 private chain-of-thought。

## 3. Semantic Context Profile

`quillframe_semantic_context_profile_v1` 是 derived semantic metadata，不是 source object。

核心字段：`profile_id`、`source_object_id/type`、`source_fingerprint`、`description`、`trigger_when`、`estimated_tokens`、`semantic_tags`、`stage_affinities`、`generated_at`、`generator_provenance`、`status`、`stale_reason`、`profile_fingerprint`、可选 manual override，以及固定 `authority=false`。

Generic source family 至少覆盖 Character、Relationship、World Fact、Location、Timeline Event、Story Node、Plan、Research、Accepted manuscript context、previous scene/chapter、Canon claim、Corpus evidence、Review artifact、Character Knowledge、Candidate、runtime state 与 derived memory。

Profile identity 是 source-version-specific。source fingerprint 一变，旧 profile 必须 stale，新版本获得新的 profile id。Framework 可通过 `context.profile_derive` 自动再生成语义 metadata，但 regeneration 不产生 authority。Manual override 单独持久化，自动 regeneration 默认继续套用，除非用户明确修改 override。

## 4. Semantic Indexing

`context.profile_derive` 接收 exact source id/type/fingerprint、bounded model view 与可选 stage hints，只能输出 retrieval metadata，不能输出 Canon / acceptance / settlement / authority mutation。

以下情况可自动产生 indexing work：没有 current profile、source fingerprint 改变、明确要求 regeneration、generator version 需要重建。自动的是 indexing work 与派生 metadata 持久化，不是 Canon 写入、Learning promotion 或 Project profile promotion。

## 5. Eligibility Gate

Eligibility 是 deterministic 且 stage-specific 的。它在模型看到候选前检查：对象存在、lifecycle、authority class、visibility、invalidation、allowed stage、source/profile fingerprint、private/hidden class、domain boundary。

典型规则：

- rejected Candidate 即使高度相关也必须 lifecycle-excluded；
- Research 可作为 research evidence，却不会因此变成 Character Knowledge；
- 同一对象可以 Continuity eligible、Draft ineligible；
- hidden regression material 不进 writer stage；
- 没有 accepted/locked authority 的 `accepted_manuscript` projection 无资格冒充 Accepted；
- stale semantic profile 必须 regeneration/refresh 后才能进入候选池。

Profile 的 stage affinity 只是 semantic hint，不是 eligibility override。

## 6. Context Decision Agent

`context.stage_select` 只接收一个 stage 的 mechanically eligible candidate universe。模型返回 profile id、stage id、priority、短 reason code / explanation、可选 `required_for_grounding`。

Runtime 对每个 id 做 exact validation。任何 unknown / out-of-universe / wrong-stage id 都把结果标记为 `semantic_invalid`，绝不自动猜测或替换。

公开原因是短 provenance explanation；analysis / scratchpad / chain-of-thought 一类字段被 runtime contract 拒绝。

## 7. Stage Context Greenlights 与预算

`quillframe_context_stage_greenlight_v1` 持久记录 candidate count、semantic-selected ids、budget 后实际 loaded ids、selection reason、estimated/actual cost、hard budget、budget drops、authority labels、source fingerprints、selector provenance、candidate universe fingerprint、selection fingerprint，以及 required grounding 被预算挤掉时的 `grounding_incomplete_due_budget`。

预算打包必须 deterministic。relevance / requirement > quota filling；`hard_budget=0` 表示零正成本上下文，不是无限预算。

## 8. Context Freeze

`quillframe_context_freeze_v1` 绑定 run/task mode、每个 stage 的 candidate-universe fingerprint、selection fingerprint、所有 source/profile fingerprints，以及构造 stage payload 所需的 frozen profile projection。

`freeze_fingerprint` 不包含 wall-clock `created_at`，所以同样输入得到同样 fingerprint。

Freeze 后 `stage_context(freeze, stage)` 不依赖 persistence，只读取冻结 payload。如果 Project state 变化，`validate_freeze` 返回 `stale_conflict` 并要求新的 context fingerprint。显式 extension/refresh 通过 supersede 旧 freeze 实现，不在原 freeze 上偷改。

## 9. Character 与 Persona 分域

Fictional Character Context 仍然属于多角色 stateful simulation，可投影 identity、agenda/current desire、knowledge boundary、current task、location、relationship state、emotional carryover、stakes、misbeliefs、scene presence、known/unknown facts。

作者 persona、user taste、narrative preference、provider personality 属于其他域，绝不能替代 fictional character state。Semantic profile 只是检索/激活 metadata，不把 Character System 降级成单 persona chat。

## 10. Adaptive Routing

Framework 把 Mandatory Graph Constraints 与 Adaptive Mechanisms 明确分开。Agent 只能在 Framework 已允许的 decision space 内选择/调整，不得关闭 Context Freeze、Story/Canon Preflight、Character Simulation、Reader Pressure、Continuity、independent semantic gate 或 user-visible gate 等 mandatory mechanism。

`validate_adaptive_graph` 会机械拒绝漏掉或 disable mandatory mechanism 的方案。

## 11. Typed Context Query

Quillframe 不采用 prompt 内 SQL / `{[db...]}` 模板。`quillframe_context_query_v1` 只表达 `domain / filters / projection / limit / authority_requirement`，不出现 SQL、table name、DB path 或物理 SQLite schema。Native SQLite adapter 与 hosted persistence adapter 都可以实现同一个 Core contract。

## 12. Persistence

`002_semantic_context_runtime.sql` 新增：

- `semantic_context_profiles`
- `context_profile_overrides`
- `context_stage_selections`
- `context_freezes`

它们只保存 derived metadata 与 runtime receipts。现有 `context_manifests` 继续作为兼容的 summary projection。所有新增表固定 `authority=0`；stage selection/freeze 通过 foreign key 绑定 `runs`。现有 ordered/checksummed migration、WAL、backup/restore、integrity/FK 与 doctor 继续负责 durability。

## 13. Inspector public projection

`quillframe_context_inspector_projection_v4` 面向 Studio/Core boundary 提供：Eligible、Considered、Selected、Loaded、Dropped due budget、Visibility excluded、Lifecycle excluded、Stale、Invalid。

每项可公开 source object/domain/authority/lifecycle/stage、短 reason、estimated/actual cost、source/profile fingerprint、selector 与 receipt；不公开 private CoT。

Studio Host Bridge 只增加一个 read-only projection operation，不改 SolidJS/Tauri UI 视觉设计。

## 14. Shujuku Agent Worldbook vs Quillframe Context Runtime

| 维度 | Shujuku current-main 模式 | Quillframe 决策 |
|---|---|---|
| Worldbook Skill meta | `description / triggerWhen / tk / updatedBy` | 吸收 semantic indexing；改为正式 SQLite typed derived profile，不写 source comment block |
| Skillify | AI 自动从 worldbook entry 生成检索 metadata | 吸收为 `context.profile_derive`；不修改 source authority |
| Greenlights | plot task 与 final generation worldbook refs | 泛化成所有 production stage 的 typed Context Greenlights |
| snapshot / takeover | snapshot 候选并通过 takeover 改 entry enable/constant 状态 | 吸收 snapshot/freeze 思想；拒绝通过修改 source entry 实现 runtime isolation |
| strict runtime reads | scoped lorebook read + failure classification | 吸收为 freeze 前 Core strict read；freeze 后禁止任意 DB discovery |
| id validation | 只接受 allowed-key 范围内的模型 refs | 吸收并增强 source/profile fingerprint validation；越界 fail closed |
| token budget | deterministic max-token packing | 吸收；明确拒绝 minimum-token quota filling |
| shard/concurrency | candidate shards 并发 semantic decision | 可作为执行优化吸收；merge 后仍绑定同一 frozen universe |
| taskPlan | selectable task 可 run/effectiveStage/effectiveOrder | 只允许在 adaptive mechanism 内；mandatory graph 不可跳过 |
| persona/current character | chat-centric persona/current-character prompting | 拒绝作为小说人物架构；保持多角色 simulation 与 knowledge boundary |
| prompt SQL | host 体系中可通过模板动态查询 DB | 拒绝；改用 typed Context/Projection Query |
| fallback | fallback summary / task-plan fallback | 改成显式 `semantic_invalid / stale / incomplete`，不把 ineligible data 偷塞入 Context |
| authority | 主要是 retrieval/runtime state | Quillframe 继续先判断 Canon/lifecycle authority，再谈 relevance |
| candidate/acceptance/settlement | 不具备 Quillframe 的同一条 staged Canon path | 保留 Candidate → explicit Acceptance → Settlement |
| semantic review | context decision 属于 Agent | 保持 genuinely independent literary reviewer；selector 不算独立 reviewer |

### 吸收

Semantic metadata、自动 derivation/regeneration、allowed-candidate validation、stage greenlights、snapshot/freeze、strict runtime reads、deterministic token packing、可选 sharding、bounded adaptive routing。

### 拒绝

comment-block metadata 作为正式存储、通过 source-entry takeover 隔离 Context、prompt SQL、minimum-token quota、single persona 替代 fictional characters、模型授予 authority、Agent 自创 mandatory graph。

## 15. Backward compatibility

- 现有 `context.select` 保留且不破坏旧 caller。
- 现有 `context_manifests` 继续可读，新 freeze 会写兼容 summary。
- Agent Runtime / Model Runtime 不被替换。
- 本任务不 migration consumer Project、不 repin frostloom。
- Canon / Acceptance / Settlement schema 与 precedence 不变。
- Studio 只得到 additive read-only projection operation，不改 UI route/layout。

## 16. Acceptance

只有 deterministic/integration tests 证明以下事实才可称完成：profile 可派生且无 authority；eligibility 先于 relevance；Agent 不能越界/create authority；stage greenlights 可不同；freeze fingerprint 可复现；budget/visibility/lifecycle/stale/invalid 状态可区分；公开 receipt 无 hidden reasoning；Generic Framework 没有 Project-specific story data；本地 SQLite 无 Cloudflare 依赖；consumer repo 没有 repin。
