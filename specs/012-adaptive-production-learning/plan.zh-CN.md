# Plan 012 · 自适应生产学习与 Realization 边界

## 目标

把 NovelForge 已有 primitive 连接成 stateful co-creative production loop，同时避免重复造 subsystem，也不削弱 authority boundary。

## Live candidate reconciliation · 2026-08-16

本 Plan 已按 PR #90 的 exact pre-write HEAD `0a1679b315366c4a42bda17eff9dffd04ad76db0` 重新审计。当前 branch 已经包含部分 adaptive-production candidate，因此本轮只扩展既有 owner，不新增平行 store、registry、router、simulator 或 release authority。

| Existing mechanism | Current owner / files | 稳定化前覆盖 | Decision | 原因 / migration risk |
|---|---|---|---|---|
| planning commitment horizon | `harness/planning_horizon.py`、schema、专属 CI/evals | deterministic + independent semantic workflow 在 pre-write HEAD 已 PASS | KEEP | 机制已 bounded、non-authoritative 且有证据；不要把后续 runtime 语义再绑进 planning owner |
| durable preference evidence / hypotheses | `learning/learning_store.py` | 既有 self-test + normal contracts CI | KEEP | 已拥有 durable learning state；第二套 Author Model DB 会产生 duplicate truth |
| promotion prerequisites | `learning/promotion_gate.py` | 既有 self-test + normal contracts CI | KEEP + BIND | 新 Author Model 在 durable user-taste activation 前必须绑定该 prerequisite result；调用方 boolean 本身不够 |
| Author Model projection | `learning/author_model.py` | 仅 local self-test；尚未 normal-CI/manifest integration | REFACTOR | 保持 Learning Store ownership，但关闭 activation-authority gap 并注册 runtime |
| context stage isolation | `harness/context_inspector.py` | 已有 self-test，但 manifest schema metadata 已 drift | EXTEND | 现有 owner 已负责 stage visibility；semantic relevance 继续留在 deterministic code 外 |
| required context assembly | `harness/context_assembly.py` | 仅 local self-test | EXTEND | typed satisfaction receipt 应挂在既有 context owner，不建立第二个 relevance engine |
| character / scene simulation | `character.action_propose`、`scene.resolve_actions` contracts | 已注册 semantic contracts | KEEP | action→collision boundary 已是正确 simulator owner，不再造平行 simulator |
| writer-safe realization | `production-loop.json` 的 `scene.realization_project` | contract 已注册；typed CI fixtures 未完整迁移 | EXTEND | projection 正是 private simulation state 与 prose 之间需要的 privacy boundary |
| Reader / Editor loop | `reader.production_audit`、`editor.repair_spec` | contracts 已注册；typed CI fixtures 未完整迁移 | EXTEND | 复用既有 quality/readiness/compare owner，不扩张 literary-agent bureaucracy |
| structural release composition | `quality/production_release.py` + 既有 `production_readiness.py` | 仅 local self-test | EXTEND | structural receipts 只提供 conjunctive evidence，不形成另一套 release authority |
| prose telemetry | `quality/prose_telemetry.py` | 仅 local self-test | KEEP + INTEGRATE | signals-only 设计正确；必须继续不承担 literary verdict |
| HF-30 taxonomy | `quality/taxonomy.json` | registry 已有；Surface 双语 heading/name 与 semantic regression family 缺失 | EXTEND | 同步 human contract 与 counterexample；不得用 lexical heuristic 替代语义判断 |
| write-intent guard | `harness/control_plane/write_intent_guard.py` | 仅 local self-test | EXTEND | 属于既有 Control Plane；exact action/resource/target/before-state match 仍不授予 authority |
| semantic registry integrity | `scripts/semantic_reference_integrity.py` | 仅 local tool | EXTEND | 接入 normal CI，不另建 registry |

### Reconciliation 发现的 candidate-owned failure

- Spec 012 六个双语文档没有注册进 `docs/documentation_manifest.json`。
- 四个新 `production-loop` contract 已注册，但 generic semantic-contract workflow fixture 没有随 registry 迁移。
- HF-30 已进入 `quality/taxonomy.json`，但 Surface 双语文档缺 canonical heading/name。
- `HARNESS_MANIFEST.yaml` 尚未注册新 Author Model / context assembly / write guard / telemetry / structural release runtime，并且 Context Inspector schema id 仍是旧值。
- generic eval manifest 尚无所需 HF-30 capability/counterexample family。
- `learning/author_model.py` 允许仅凭 `durable_user_taste_write_authorized=true` 激活 user-taste hypothesis，没有绑定既有 `promotion_gate` prerequisite result。

已有 Product/Godot 文档与 Studio/Product CI debt 单独记为 pre-existing baseline，不作为本 candidate 的失败证据。

## Branch / PR architecture decision

PR #90 仍是唯一 active general/agent branch，应先形成一个 coherent planning + adaptive-production review unit。Repo branch-budget guidance 倾向最多 1 条 active general/agent branch；Master execution prompt 同时禁止把未来 polyglot rewrite 偷塞进不相关 planning PR。因此：

1. **当前 review unit：** 只稳定化 PR #90 已经存在的 adaptive-production 工作，包括 authority、registry、docs、deterministic CI、HF-30 semantic evidence 与 rollback completeness。
2. **不 rewrite history / 不 force push / 不 merge：** 保留现有九个 commit 历史，并以 `0a1679b3…` 作为本 stabilization slice rollback checkpoint。
3. **Polyglot implementation：** 本 PR 中 DEFER。Rust/Go/WASM/Starlark production implementation 必须等 PR #90 close/merge/supersede，或存在明确 branch-budget exception 后另开 review unit。Architecture research 可以现在记录，但不得为了语言清单把新语言 production source 装饰性塞入 PR #90。
4. **不建立 second Core：** 后续任何 polyglot slice 必须先审计现有 fingerprint/canonicalization authority，并从现有 Python behavior 捕获 golden vectors，之后才能移动 implementation boundary。

这是 reviewability constraint，不是否定长期 polyglot 方向。

## Research adoption snapshot

本轮稳定化按 primary source 重新验证后，得到以下机制决定：

- **ADAPT — LangGraph / OpenAI Agents SDK / AutoGen / CrewAI / PydanticAI：** 保留 explicit session/run state、typed handoff、bounded specialist context、interrupt/resume 与 inspectable graph state 作为 runtime mechanism；拒绝把 provider/session memory 当 Project authority，也拒绝多角色 agent 膨胀。
- **ADAPT — Temporal / Dapr durable execution：** 借鉴 replay-aware checkpoint、workflow-side deterministic decision、idempotent side-effect boundary、typed failure/retry class 与 upgrade caution；本 candidate 不引入 Temporal/Dapr dependency，因为既有 Session Runtime + Control Plane 已拥有这些语义。
- **ADAPT — SQLite：** 正式化既有 embedded WAL-backed Learning/Control Plane store 的 migration/backup semantics，不创建第二套 operational DB。WAL 仍是 same-host substrate，不是 distributed authority plane。
- **ADAPT — Sudowrite / Novelcrafter：** explicit/editable project state、selective AI context、prompt/context visibility、revision history 与 project/series scoping 支持 NovelForge 的 explicit Project state + sparse Context Assembly 方向；NovelForge 保留 evidence、derived state、Canon 之间更强的 authority separation。
- **ADAPT — MAGNET / StoryBox / StoryWriter / Generative Agents：** 保持 `private state → action proposal → shared-world collision → event trajectory → writer-safe realization`，并保留 dynamic history selection 与 bounded planning；拒绝 `character sheet → prose/dialogue paraphrase`，也拒绝 simulation state 自动获得 story truth。
- **DEFER — PR #90 中的 Rust / Go / WASM / Starlark / Zig / C/C++ production ownership：** 当前没有 performance 或 packaging evidence 能证明值得突破 reviewability boundary。Rust 仅在现有 fingerprint semantics 与 golden vectors 完成映射后，才保持 future deterministic-kernel 首选候选；Go 只有在不复制 Python Control Plane 时才是 future execution-fabric 候选；Starlark 只作为 deny-by-default restricted extension 候选；Zig/C/C++ 暂无 current production owner，只保留 interop/portability 触发条件。

## Workstream 1 · Author Model 与 Review feedback

1. 基于现有 Learning Store 增加 deterministic Author Model projection runtime。
2. 增加 semantic `learning.preference_interpret` contract，对明确 Review feedback 做受限解释。
3. 严格区分 observation、hypothesis、activation 与 production projection。
4. 支持 contradiction / supersession 与 scope-aware activation rule。
5. 把已有 `feedback.observed` Author Steering 接到 Review learning lifecycle；通过 contract/orchestration 连接，不静默切换 primary task mode。

## Workstream 2 · Adaptive Context Assembly

1. 扩展 Context stage，使人物私有 simulation state 可以给 simulation 看，但默认不能给 prose generation 看。
2. 增加 typed required-context obligation 与 deterministic satisfaction receipt。
3. 新增 context-assembly runtime，验证 selected IDs 的 stage、authority、invalidation、required class/purpose 与 provenance/fingerprint。
4. `context.select` 继续拥有 semantic relevance judgment。
5. Corpus retrieval 保持条件性；benchmark 只是可选 context class，不是每次必跑的固定节点。

## Workstream 3 · Simulation-before-Prose

1. 复用 `character.action_propose` 与 `scene.resolve_actions`。
2. 增加 semantic `scene.realization_project` contract，把 private simulation evidence 转成 writer-safe interaction/event projection。
3. 默认阻止 raw private-character / simulation context class 进入 `writer_pre_draft`。
4. 明确接口：private state 控制行为；realization projection 控制 Writer 可见的 event/dialogue opportunity。

## Workstream 4 · Reader → Editor closed loop

1. 增加结构化 Reader production audit，判断真实 reading experience、profile fit、paragraph rhythm 与 dialogue realization，同时不暴露 creator-private state。
2. 增加 `editor.repair_spec`，把 Reader evidence 转为 preserve/change priority 与 owning repair layer。
3. material repair 复用 `reader.compare` / `quality.compare` 做 incumbent/challenger comparison。
4. Production Readiness 只增加 deterministic runtime 真正能证明的 structural receipts；不为每个文学维度造一个 deterministic gate。

## Workstream 5 · Quality mechanism

1. 注册 HF-30：Agenda-to-Dialogue Leakage / Character-Sheet-to-Dialogue Serialization。
2. 增加 profile-sensitive prose telemetry，但仅作为 signal。
3. 增加 formal-completeness dialogue 与 legitimate selective-short-paragraph counterexample。
4. Surface / Character / Reader contract 同步 architecture 与 backstop diagnosis。

## Workstream 6 · Safety 与 integrity

1. 新增 write-intent/action guard，阻止 resource/operation/target mismatch。
2. 修复 stale `model_contracts.json` reference，并增加 deterministic semantic-reference integrity check。
3. Framework 能负责的 semantic-bridge failure classification 在 code 中改进；repo setting/configuration owner 单独报告，不假装修好了外部权限。

## Workstream 7 · Integration 与 verification

1. 在 `HARNESS_MANIFEST.yaml` 与 model contract catalog 注册新 tool/contract。
2. 双语更新 Harness / Orchestration / production / context / adaptive-learning docs。
3. 把 deterministic self-test 接入 reusable release contracts CI。
4. 增加 generic semantic fixture，reviewer queue 不泄露 hidden expected label。
5. 跑 exact-head CI，区分 candidate failure 与 pre-existing repo debt。
6. 只在存在 eligible independent transport 时，为 exact candidate fingerprint 获取 independent semantic capability/counterexample evidence。
7. 证据达到人工审核门槛以前 PR 保持 Draft；本 run 不 merge、不 release、不迁移 downstream lock。

## Compatibility strategy

优先 additive schema 与 optional policy requirement。未声明新 required context / structural receipt 的已有 Project 继续兼容。Material version/release identity 只在 exact diff 与 verification 后决定。

## Rollback

每个 workstream 形成 coherent commit，可独立 revert。Downstream consumer 整个 run 都继续 pinned 到 NovelForge 0.8.0，因此 candidate rollback 永远不会改变本书 runtime authority。