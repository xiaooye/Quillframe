# NovelForge · Story Workspace & Narrative Runtime

## 问题

NovelForge 已经拥有 sparse Context、character / scene semantic simulation、scenario fork、state graph、reader expectation、quality compare、session / checkpoint / settlement 等独立机制，但它们仍然以底层 contract / tool 为中心存在，缺少一个统一、可解释、可回放的小说工作空间语义层。

当前主要缺口：

1. 没有统一的 Story Workspace projection，把结构、人物、关系、世界状态、计划、读者承诺、当前 Context 与 exploration branch 放在同一只读视图中，同时保留 authority class。
2. Context Inspector 能判断 eligibility / stage isolation，但作者仍难以看到一次实际 run 中“为什么这条被选中、为什么那条被排除、最终预算里真正装载了什么”。
3. Scene simulation 已有 `character.action_propose` / `scene.resolve_actions`，却缺少统一的 Event IR 与 simulation-run envelope，难以把角色行动碰撞稳定传给 plan、draft、state verification 与 Studio。
4. `state_graph.py` 能检测 stable-field contradiction / unexplained state change，但缺少 candidate prose → candidate state delta → narrative verification 的正式边界。
5. Studio 当前更像 Framework developer console；如果 Core 不先提供统一 Story projection，直接做 timeline / character board 会形成第二套 story model。

## 目标

- 建立 `novelforge_story_workspace_v1`：Project-agnostic、只读、source-bound 的 Story Workspace projection；统一暴露 structure / timeline / characters / relationships / world-state / active plans / reader expectations / current context / scenario branches，但不复制 Project Canon authority。
- 建立 `novelforge_context_trace_v1`：记录一次 bounded context build 的 candidate eligibility、author control、semantic selection、budget packing、exclusion reason、stage visibility、source fingerprint 与最终 loaded working set。
- 建立 `novelforge_event_ir_v1`：在 Scene Simulation 与 prose realization 之间表达角色、前置条件、意图、行动、阻力、反应、后果、状态变化、知识变化、关系变化、资源变化与 reader-question evolution。
- 建立 `novelforge_scene_simulation_run_v1`：把 character action proposal、scene resolution、Event IR candidates、scenario branches 与 comparison evidence 绑定到同一 subject / state fingerprint，不引入永久 stateful character agents。
- 建立 `novelforge_candidate_state_delta_v1`：明确 candidate artifact 导出的 state / knowledge / relationship / resource / obligation / location changes；candidate delta 始终非权威。
- 建立 `novelforge_narrative_verification_v1`：把 deterministic state contradiction 与 model-owned narrative plausibility / knowledge-boundary judgment 汇合成 typed findings，但不让 deterministic runtime 判断文学合理性。
- 为 Studio 提供稳定 read/query contract，使后续 UI 消费 Core projection，而不是重新解析 Novel Bible 或建立第二 Canon store。

## 核心不变量

1. Workspace / Context Trace / Event IR / Simulation Run / Candidate State Delta / Verification Report 全部默认 `authority=false`。
2. `locked / accepted / active_plan / review / proposal / derived / scenario` 必须保留为不同 lifecycle / authority class，不能在 Workspace 中扁平化。
3. Project authority 仍由 consuming Project manifest / adapter / database 决定；Framework 不内置具体 BOOK/VOL/CHAR/Canon。
4. Context Trace 可以解释选择过程，但 semantic relevance 仍由模型拥有；deterministic runtime 只拥有资格、stage、hard budget、author control、fingerprint 与 typed validation。
5. Event IR 是 prose 前的因果中间表示，不是 Canon；生成正文后必须允许实际 realization 与 Event IR 偏离，并通过 evidence 更新 candidate delta，而不是强迫正文复述 outline。
6. Scene Simulation 默认 `one manager + bounded semantic invocations`；不得为了角色拟真制造共享可变 memory 的永久 agent society。
7. Candidate state extraction / verification 不能自动 SETTLE；只有 Project 明确 acceptance + settlement transaction 才能改变 Canon。
8. Studio 不直接拥有 Canon write authority；任何编辑受保护事实的操作必须进入 proposal / Project write contract。

## Event IR 最小语义

至少支持：

- `event_id` / `scene_id` / `story_order`；
- `actors` 与 `preconditions`；
- `intent` / `action` / `obstacle` / `response` / `consequence`；
- `state_delta` / `knowledge_delta` / `relationship_delta` / `resource_delta`；
- `reader_question_before` / `reader_question_after` / `reader_reward`；
- `source_refs` / `evidence_refs` / `subject_fingerprint`；
- `authority=false` / `canon_write=false`。

字段允许 profile / genre 扩展，但 Generic Framework 不写死某一本小说的数据表。

## Context Trace 最小语义

对每个 candidate item 至少能回答：

- source / source fingerprint；
- authority class；
- inclusion reason；
- stage visibility；
- author pin / priority / hidden / invalidated state；
- eligibility verdict；
- semantic-selection verdict / order（如果执行）；
- loaded / skipped；
- budget impact；
- exclusion reason；
- semantic result fingerprint / provenance（如果执行）。

不得把任意 numeric relevance heuristic 写成 durable literary truth。

## Narrative Verification 分层

Deterministic runtime 负责：

- stable-field contradiction；
- unexplained typed state transition；
- invalid / stale source fingerprint；
- future knowledge / stage visibility / lifecycle class 的可证明违规；
- candidate delta schema 与 before-state binding。

Model semantic contract 负责：

- 某个行为是否被已知人物 agenda / relationship / pressure 合理支持；
- 某个角色是否基于其可见证据形成了不合理知识跳跃；
- 某个关系变化是否缺少足够 narrative evidence；
- event consequence 是否与 scene-level causal trajectory 明显脱节。

两层 findings 使用统一 finding contract，但必须保留 owner / provenance。

## 非目标

- 不用 Knowledge Graph / vector DB 取代 Project Canon database。
- 不把 Event IR 变成必须逐项兑现的僵硬 outline。
- 不让 deterministic code 给 tension、character realism、reader grip 打文学分数。
- 不创建默认多角色 round-table / autonomous agent society。
- 不把 selected scenario branch 自动升级成 active plan 或 Canon。
- 不在本 slice 直接升级 consuming Project 的 `novelforge.lock.json`。
- 不要求第一版 Studio 支持 Canon mutation；首版允许只读 exploration / trace / simulation projection。

## Acceptance

1. Story Workspace projection 对 synthetic standard / mapped Project 都能返回稳定 schema，并明确每个 object 的 source / authority / lifecycle；不得复制出第二份 authoritative state。
2. Context Trace 能从现有 Context Inspector + `context.select` + memory-tier packing evidence 重建一次 run 的 include / exclude / loaded explanation，并保持 semantic relevance owner = model。
3. Event IR schema 能表达至少一个多角色冲突事件、一个知识变化和一个资源/关系变化，并通过 deterministic validation。
4. Scene Simulation Run 能把 exact base-state fingerprint、character proposal results、scene resolution、Event IR candidates 与 branch fingerprints 绑定；stale / mismatched result 必须 fail closed。
5. Candidate State Delta 明确 `before -> after + evidence`，但返回 `authority=false`、`settlement_authority=false`。
6. Narrative Verification 能同时返回 deterministic contradiction 与 semantic narrative finding，并保留不同 repair owner / provenance；semantic reject 不被当 transport failure。
7. Scenario selection、simulation result、verification PASS 都不能获得 Canon / Settlement / Framework-write authority。
8. Studio / bridge 首批 read operations 只消费 Core contracts；不得直接解析 consuming Project 私有 schema 来制造 parallel truth。
9. Generic tests 全部使用 synthetic fixtures，不导入任何 consuming Project 的具体正文、Canon、标识符或私有 schema。
10. 新 contract / docs / schemas 必须进入 deterministic CI、bundle content manifest 与中英双语文档完整性检查。
