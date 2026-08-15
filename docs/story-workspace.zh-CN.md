# Story Workspace 与 Narrative Runtime

NovelForge 的 Story Workspace 不是另一份 Story Bible，也不是把整本小说塞进一个大 JSON。它是一组**只读、来源绑定、保留权威等级的投影与运行证据**，让作者和 Studio 能看到“故事现在是什么状态、这次模型实际看到了什么、人物怎样产生行动、场景怎样形成事件、候选正文会改变什么，以及哪里出现了叙事问题”。

这套机制连接已有的 Story / Character / Canon、Context、Scenario Fork、State Graph 与 Quality 系统，但不会建立第二份 Canon。

## 1 · Story Workspace 是视图，不是权威数据库

`harness/story_workspace.py` 输出 `novelforge_story_workspace_v1`。

Workspace 可以同时呈现：

- Book / Volume / Arc / Unit / Chapter / Scene 等结构对象；
- timeline / story order；
- characters 与 relationships；
- world / resource / obligation 等当前状态；
- active plans；
- reader expectations；
- 当前 Context；
- scenario branches。

每个对象仍然保留自己的 `source_ref`、`source_fingerprint`、`authority_class` 与 `lifecycle`。`locked`、`accepted`、`active_plan`、`review`、`proposal`、`derived`、`scenario` 不会因为同时出现在一个界面里就被扁平化。

Workspace 本身始终：

`authority=false · canon_write=false · settlement_authority=false`

Project Adapter / SDK 先把项目对象正规化，Workspace 再做投影。Generic Framework 不应该为了画 timeline 或人物板而猜某个下游项目的私有 Markdown / database schema。

## 2 · Context Trace 回答“这次为什么看到了这些”

Context Inspector 负责资格、阶段隔离与作者 overlay；`context.select` 负责模型语义相关性；Memory Tiers 负责确定性的预算装载。

`harness/context_trace.py` 把这三个阶段的证据合并成 `novelforge_context_trace_v1`，因此一次真实 Context build 可以解释：

- 候选对象来自哪里、当前是什么 authority；
- 哪个 stage 可以看到；
- 作者是否 pin / hide / invalidate；
- Inspector 是否判定 eligible；
- `context.select` 是否选择、放在哪个 tier、为什么；
- hard budget 最终是否真正装载；
- 被排除时是 future-story-order、perspective visibility、author hidden、invalidated 还是预算原因。

这里仍然保持 owner 分离：

- semantic relevance：模型；
- eligibility / stage / authority：确定性 runtime；
- hard budget：确定性 runtime。

Context Trace 不发明一个“文学相关度 0.83”的持久分数，也不会因为某条材料被模型选中就提升它的权威。

## 3 · Event IR 是 Scene Simulation 与正文之间的因果中间表示

`core/event_ir.py` 定义 `novelforge_event_ir_v1`。

一个 Event candidate 至少表达：

- actors 与 preconditions；
- intent、action、obstacle、response、consequence；
- state / knowledge / relationship / resource delta；
- reader question 前后如何变化；
- reader reward；
- source / evidence refs；
- exact subject fingerprint。

Event IR 的目的不是把小说写成程序，也不是要求正文逐项复述 outline。它让 Scene Simulation 先回答更基础的问题：**谁因为什么采取什么行动，和谁发生碰撞，结果改变了哪些选项、成本、关系、知识或世界状态。**

实际 prose realization 可以偏离 Event IR。正文冻结以后，系统应根据实际文本重新形成 candidate evidence / state delta，而不是为了“符合 IR”强行把已经活起来的正文改回机械计划。

Event IR 永远不是 Canon。

## 4 · Scene Simulation 仍然是一名 manager 加受限调用

`harness/scene_simulation_run.py` 输出 `novelforge_scene_simulation_run_v1`。

一个 simulation run 绑定：

1. exact base checkpoint / state fingerprint；
2. 一个或多个完成的 `character.action_propose` 结果；
3. 完成的 `scene.resolve_actions`；
4. Event IR candidates；
5. 可选 scenario branches；
6. 可选 pairwise comparison evidence。

NovelForge 不因此创建永久驻留的“人物 Agent 社会”。人物拟真来自 perspective-bounded state、agenda、relationship、pressure 与受限 semantic invocation，而不是多个共享可变 memory 的长期 agent 互聊。

任何 stale Event / branch / semantic binding 都必须 fail closed。即使一个 branch 被标记 selected，它仍然只是 scenario，不会自动变成 active plan 或 Canon。

## 5 · Candidate State Delta 描述正文“如果成立会改变什么”

`quality/candidate_state_delta.py` 输出 `novelforge_candidate_state_delta_v1`。

它把候选事件或实际 prose evidence 聚合成 source-bound 的：

`before → after + evidence`

当前支持 state、knowledge、relationship、resource，并允许 obligation / location 等补充 domain。连续事件修改同一个字段时，前一个 `after` 必须能成为后一个 `before`；断链属于明确的 candidate-state inconsistency。

Candidate State Delta 只是 verification / review 的输入：

`authority=false · settlement_authority=false`

只有用户明确接受正文以后，Project Settlement 才能重新读取 live before-state，并按自己的权威 schema 生成真正的 Canon transaction。

## 6 · Narrative Verification 把“能确定的错误”和“需要理解的错误”分层

NovelForge 不应该让 Python 猜人物是否真实，也不应该让模型负责可以精确证明的 before-state mismatch。

`quality/narrative_verification.py` 因此把两层证据统一到 `novelforge_narrative_verification_v1`：

**确定性层**可以检查 stable-state contradiction、unexplained typed transition、stale fingerprint、可证明的 future-knowledge / lifecycle / stage violation 与 candidate-delta binding。

**语义层**使用按需加载的 `narrative.verify`，判断：

- 重要行动是否得到人物 agenda / pressure / relationship / visible evidence 支持；
- 人物是否使用了自己当前不可能拥有的信息；
- 关系变化是否缺少足够叙事证据；
- consequence 是否与事件因果轨迹脱节。

两层都返回 shared finding contract，并保留 repair owner 与 provenance。有效的 `issues_found` 是一个语义判断，不是 transport failure，也不能通过换 reviewer 消掉。

`narrative.verify` 是 diagnostic contract，不代替 `quality.production_review` 等真正配置为 production gate 的独立审查。

## 7 · Studio 只消费 Core projection

Studio Host Bridge 首批暴露只读操作：

- `story.workspace`
- `context.trace`
- `scene.simulation.inspect`
- `state.candidate.inspect`
- `continuity.verify`

这些 operation 只接受当前 `project_root` 内的 project-relative、已正规化 evidence 文件；Host Bridge 不允许绝对路径越界，也不会把 host-private path 回传给产品界面。

`/workspace` 面向作者展示 Story、Context、Simulation 与 Verification；底层 JSON 只作为折叠证据。原来的 execution preview 保留在 `/playground`，用于观察 contract / execution boundary，而不是冒充真实小说工作空间。

Studio 不直接解析下游项目私有数据库，不保存第二份 Canon，也没有 Canon / Settlement write authority。

## 8 · 在 DRAFT / REVISE 中的位置

Story Workspace 并没有替换现有生产图，而是把已有机制之间的数据边界变得可检查：

Context Freeze 后，Context Trace 可以解释当前 working set。Scene / Character Simulation 可以形成因果 Event candidates。Writer 仍然在隔离的 first-pass context 中完成 Raw Draft。Raw Draft 冻结后，实际 prose evidence 可以形成 Candidate State Delta，再由 deterministic + semantic Narrative Verification、Reader / Character / Surface / Continuity 等机制检查。

如果发现 SAFE-BUT-FLAT，仍然应该回 Reader Pressure / Scene Simulation，而不是靠 Event IR 增加更多字段或对句子进行贴补。Event IR 是因果载体，不是质量替代品。

## 9 · Authority 心智模型

可以把这套机制理解成：

**Project authority 提供事实 → Workspace 提供可读视图 → Context Trace 解释一次工作集 → Simulation 提出因果可能 → Event IR 表达候选事件 → prose 实现 → Candidate Delta 描述候选变化 → Verification 产生证据 → 用户决定是否接受 → Settlement 才改变 Canon。**

中间任何一步“看起来很合理”都不会自动获得写权限。

## 10 · 精确实现入口

- `harness/story_workspace.py` / `harness/story_workspace.schema.json`
- `harness/context_trace.py` / `harness/context_trace.schema.json`
- `core/event_ir.py` / `core/event_ir.schema.json`
- `harness/scene_simulation_run.py` / `harness/scene_simulation_run.schema.json`
- `quality/candidate_state_delta.py` / `quality/candidate_state_delta.schema.json`
- `quality/narrative_verification.py` / `quality/narrative_verification.schema.json`
- `harness/semantic_workers/contracts/story-simulation.json`
- `harness/semantic_workers/contracts/narrative-verification.json`
- `harness/semantic_workers/model_contract_catalog.json`
- `studio/host_bridge.py`
- `studio/app/src/routes/NarrativeWorkspace.tsx`

这套 Story Workspace 的目标不是把小说工程化到失去生命，而是让**因果、上下文、人物知识、状态变化和权威边界可检查，同时把真正的文学判断继续留给模型与作者。**
