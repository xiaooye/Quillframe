# 规划承诺视界——规格

## 状态

这是 #67 的实现候选，仅属于通用 NovelForge Framework。它不修改任何下游 Project lock、Canon、正文、用户偏好或 Settlement 状态。

## 证据基础

本候选从两套彼此独立、且已有真实实现的系统中做 `ADAPT`：

1. `VioletEvergar-den/AI-Novel-Writing-Assistant@43a78b8d295ba060c1037df49bca942014154074`：实现了机器校验的 hard/soft 卷级规划，以及目标卷重生成后的相邻重平衡。可借鉴的是“承诺强度”；反例是 soft 卷仍能被后续调用过度展开，因此不能只复制标签。
2. `joonspk-research/generative_agents@fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4`：先做一天的粗粒度计划，再做小时级计划；执行时只把当前附近大约两小时继续分解为分钟级任务；事件反应只重写受影响的日程片段。可借鉴的是运行时真正限制未来细化深度、以及局部重规划；其固定“两小时”窗口是领域常数，不能照搬。

## 问题

NovelForge 已经有：

- `plan.reconcile`：新因果证据出现后判断保留计划、提出局部 patch，或升级到 Story/Plan 重设计；
- `scenario_fork`：探索多种未来分支；
- #63 propagation debt：记录上游变化造成的下游重规划/重验证工作。

缺少的是更早的一道问题：**在证据还没发生之前，未来允许被规划到多细？**

如果没有承诺视界，连载小说 planner 可能仅仅因为 schema 允许，就提前把很远的章节写得过细。之后角色/世界自然涌现出的变化会制造大量无谓 stale state，并诱导系统强行把故事拉回旧计划。

## 目标

1. 用显式承诺强度与最大规划深度描述一个 plan region。
2. 对已登记的 planning artifact kind 做 deterministic admission control，超过 region 上限就拒绝。
3. region 要获得更强/更深的规划权限，必须走显式、fingerprint-bound transition。
4. 根据明确 dependency evidence 选择第一圈局部重平衡目标：非相邻但有关联的必须包含，相邻但无证据的不得仅因位置被包含。
5. 保持现有 authority：规划强度永远不等于 Canon、Acceptance、Settlement 或自动 active-plan mutation。
6. profile-sensitive：短篇严密规划项目可以大面积深度 hard-plan；探索写作项目即使近端也可以保持 soft。

## 非目标

- 不建立第二套 active-plan store。
- 不用 deterministic Python 替代 `plan.reconcile` 的故事判断。
- 不建立第二张 propagation/dirty graph。
- 不让 Python 从任意自然语言中假装准确判断“是否写得太细”。
- 不自动 promotion、regenerate、reconcile、settle 或写 Canon。
- 不规定通用的“固定 N 章 / N 卷 / N 天”视界。

## Planning region

便携式 planning-region artifact 至少记录：

- `project_id`
- `region_id`
- `plan_ref`
- 可选 story-order 范围 / semantic scope
- `commitment_strength`: `open | soft | hard`
- `max_planning_depth`
- `assumption_refs`
- `dependency_refs`
- 如果别的 decision system 存在，可带 opaque `unresolved_decision_refs`
- `version`
- exact artifact fingerprint

这里的 `hard` 只表示更强的**活动计划承诺**，绝不是不可改变事实或 Accepted Canon。

## 规划深度

v1 使用一组很小的通用层级：

1. `arc_boundary`：篇章角色、边界、奖励/升级义务、宽泛结果类别
2. `beat`：因果 beat 或 milestone intent
3. `scene_intent`：scene 级行动/戏剧意图
4. `chapter_detail`：足够直接指导起草的详细章节计划

已登记 planning artifact kind 与最低所需深度固定映射：

- `arc_role` -> `arc_boundary`
- `beat_sheet` -> `beat`
- `scene_card` -> `scene_intent`
- `chapter_plan` -> `chapter_detail`

未知 kind fail closed，直到显式登记。这个映射是 admission contract，并不声称没有 semantic reviewer 就能完美识别任意文本中的过度具体化。

## Profile policy

Policy 为每种 commitment strength 指定最大深度。例如：

- 连载/适应型：`open <= arc_boundary`、`soft <= beat`、`hard <= chapter_detail`
- discovery-heavy：可以让 soft 到 `scene_intent`，但即使近端仍选择保持 soft
- 严密短篇：大多数 region 一开始就可为 `hard + chapter_detail`

Framework 不提供通用“前 2–3 卷必须 hard”的常数。

## Realization admission

Realization request 必须引用现有 region 的 fingerprint/version 和一个已登记 artifact kind。Deterministic runtime：

1. 验证 region 与 policy；
2. 将 artifact kind 解析成 required depth；
3. 同时检查 region ceiling 与 profile ceiling；
4. 返回 `allowed` 或 `blocked_depth_ceiling`；
5. 不执行模型，也不写 plan。

调用方不能给更具体的已登记操作贴一个较浅的 `requested_depth` 标签来绕过限制。

## Horizon transition

改变承诺强度或最大深度必须有显式 transition：

- actor class 必须被 policy 授权；
- exact before `version` + artifact fingerprint；
- target strength/depth 不得超出 profile ceiling；
- 简短、可公开的 reason 与 evidence refs；
- 产生新 version/fingerprint。

Writer 默认不是 horizon promoter。Transition artifact 本身仍然没有权限修改另一套 active-plan store。

## Dependency-bounded rebalance frontier

Runtime 接受 source change 与显式 dependency evidence。每条 dependency 至少绑定：

- `dependency_ref` + fingerprint
- `source_ref`
- `dependent_ref` + 当前 fingerprint
- `scope=all_source_changes`，或明确的 `assumption_refs`
- `required_action=replan`
- 可选 #63 `propagation_debt_ref`

只有 source 匹配且声明 scope 被本次变化命中的 dependent 才进入 frontier。物理相邻没有 authority。非相邻但证据匹配的必须进入；相邻但无证据的必须排除。

Frontier 刻意只计算“一圈”。如果 reconcile 后某个 dependent 真的发生变化，再由 #63 记录新的 downstream debt，形成下一圈。这样不会因为上游“可能变化”就递归污染整个未来。

## Context 与 authority guardrails

- `open/soft` 的投机未来细节不能被当作角色知识、current state、读者可见事实或 Accepted Canon。
- Context projection 仍由现有 context/worker contracts 管理；本机制只输出 strength/depth metadata，不授予可见性权限。
- `scenario_fork` 继续负责未来分支探索。
- `plan.reconcile` 继续负责 semantic reconciliation。
- #63 继续负责 durable propagation-debt lifecycle。
- 如果 #65 存在，只把 creative-decision refs 当 opaque refs；#67 不依赖 #65 安装或合并。

## 验收 / 回归

1. `soft + beat ceiling` 的 region 必须拒绝 `chapter_plan`。
2. profile 允许时，有效 `hard` region 可接纳 `chapter_plan`。
3. 授权 actor + exact-before transition 可以加深/提升 region，并且 version/fingerprint 只前进一次。
4. writer/self-declared authority 不能 promotion。
5. stale version/fingerprint fail closed。
6. 非相邻但有 evidence link 的 dependency 进入 rebalance frontier。
7. 相邻但无 evidence 的 region 被排除。
8. frontier 不自动运行 `plan.reconcile`，也不自动创建 debt。
9. 严密短篇 profile 可以合法地大面积深度 hard-plan。
10. discovery profile 可以合法让近端保持 soft。
11. 所有输出均无 Canon/Project/Framework/Settlement authority。
12. semantic counterexample eval 必须证明：真正高成本的远期过度具体化应被阻止；普通局部规划不应被变成官僚化 horizon 管理。

## 回滚

关闭 horizon enforcement 后，现有 active-plan artifact 必须保持原样，并退回既有 `plan.reconcile` / scenario / context 行为。回滚不得重写 Canon。
