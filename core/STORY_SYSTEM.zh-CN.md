# 故事系统 · 管理长篇规划尺度，但绝不把“将来要发生”当成“已经发生”

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>故事层级</kbd>&nbsp;&nbsp;<kbd>计划 ≠ 正典</kbd></p>

Quillframe 把长篇小说建模为**不同规划尺度上的持久故事对象**，再配合通常不需要长期保存的场景 beat。它解决的是一个长篇连载问题：怎样让几十、几百章持续保持结构与因果，却不要求作者提前把遥远未来写到场景级细节。

> **边界 ✦** 故事系统负责规划结构、戏剧目标、依赖关系与预期状态变化；它不负责判断“故事里现在什么是真的”。当前事实属于下游项目自己的正典与状态系统。

## 01 · 这个系统负责什么

故事系统提供以下通用机制：

- BOOK / VOLUME / ARC / UNIT / CHAPTER / SCENE 多尺度规划；
- 滚动细化：离写作前沿越近，分辨率越高；越远，越保持可修改；
- 场景模拟需要的目标、知识、误判、筹码与约束；
- 读者压力要求，例如当前问题、选择、代价、回报与继续阅读动力；
- 跨对象依赖：上游前提变化时，能知道哪些未来计划必须失效或重算。

它不拥有：

- 某一本小说的具体剧情事实；
- 已接受正典；
- 人物或关系的当前状态；
- 研究事实；
- 会话 / 运行时状态；
- 模型记忆；
- 语义审查权威。

这些领域可以给规划提供输入，但不会因此变成故事系统自己的权威来源。

## 02 · 规划层级

```text
BOOK
└─ VOLUME
   ├─ ARC      长期推进的戏剧线，可以跨 UNIT / VOLUME
   └─ UNIT     连续的生产与阅读单元
      └─ CHAPTER
         └─ SCENE
            └─ beat   通常是瞬时结构；项目确有需要时才持久化
```

`ARC` 和 `UNIT` 不是同一个东西。

**Arc / 长期线**回答：哪一条长期冲突、关系、调查、成长或社会变化正在推进？

**Unit / 单元**回答：哪一组连续章节共同完成一个具体目标、压力序列、回报、代价和退出状态？

一个 VOLUME 可以包含多个 UNIT，同时有多条 ARC 从这些单元中穿过。

## 03 · BOOK 契约

BOOK 级设计负责长篇承诺与最外层约束。

```yaml
id:
title:
genre:
audience:
premise:
core_fantasy:
reader_promise:
protagonist_long_desire:
central_conflict:
expansion_ladder: []
core_progression: []
major_themes: []
relationship_promise:
end_state:
hard_limits: []
status:
```

一个有效的 BOOK 设计应当能回答：

- 为什么读者愿意跟这本书走很久？
- 哪一种核心乐趣或幻想会被持续更新，而不是机械重复？
- 故事怎样扩大范围，却不只是把同一个游戏换成更大的数字？
- 主角的长期欲望是什么？
- 哪些关系、世界或终局承诺迟早必须兑现？
- 哪些方向明确不属于本书？

BOOK 设计锁定全书终局、分卷剧情骨架、横向剧情/关系/人物弧与高潮链，但不是逐章预言。具体章数、场景顺序、局部障碍、对白和表现手法由滚动规划细化；修改已批准的宏观骨架必须形成新指纹并重新取得作者批准。

## 04 · VOLUME 契约

一个有效的卷应该表现为**状态变换**，而不是一袋事件。

```yaml
id:
book_id:
title:
timeframe:
primary_stage:
start_state:
end_state:
volume_desire:
volume_question:
reader_promise:
primary_opposition:
major_arcs: []
major_events: []
resource_delta:
status_delta:
relationship_delta:
character_arc_delta:
world_expansion:
midpoint_shift:
low_point:
climax:
final_payoff:
exit_condition_to_next_volume:
status:
```

读者应该能看出 `start_state → end_state` 的差异。如果进入下一卷时人物、权限、资源、关系、世界可达范围和悬而未决的问题几乎可以原样复制，那么这一卷很可能只是“发生了很多集”，而没有真正完成结构性变化。

## 05 · ARC 契约

ARC 是跨较长时间推进的一条压力与变化线。它可以属于主角、对手、配角、关系、机构、调查、家庭、爱情线或社会运动。

```yaml
id:
volume_ids: []
name:
type:
central_question:
participants: []
start_state:
desired_end_state:
owner_goal:
opposing_forces: []
stakes:
turning_points: []
planned_payoff:
dependencies: []
crosslinks: []
status:
```

ARC 可以跨 UNIT、跨 VOLUME。它写下的转折点仍然只是计划，直到已接受正文真正提供证据。

## 06 · UNIT 契约

UNIT 防止长篇连载退化成彼此无关的一章章事件。

```yaml
id:
volume_id:
title:
chapter_window:
primary_arcs: []
concrete_objective:
entry_state:
pressure_sequence: []
major_choices: []
payoff:
cost:
exit_state:
new_open_loops: []
status:
```

一个强 UNIT 应有清楚的进入条件、逐步变化的压力、至少一次有后果的选择或重新定向，并以回报 / 代价改变下一单元可行的局面。

## 07 · CHAPTER 契约

CHAPTER 既是生产单元，也是一次读者体验契约。

```yaml
id:
unit_id:
title:
time_range:
locations: []
pov:
chapter_task:
entry_state:
main_problem:
reader_question:
scenes: []
must_happen: []
may_change: []
forbidden: []
payoff:
cost_or_counterpressure:
exit_state:
new_open_loops: []
state_delta_expected:
status:
```

章节计划应足够具体，能够进入模拟和写作；但不能细到替正文预写每一句话。

**章节计划表达未来意图，从来不能证明这些事件已经发生。**

## 08 · SCENE 契约

Scene Card 负责约束模拟，不是缩小版剧本。

```yaml
id:
chapter_id:
time:
location:
pov:
participants: []
entry_state:
scene_problem:
agenda_by_character: {}
knowledge_by_character: {}
misread_by_character: {}
leverage_by_character: {}
constraints: []
trigger:
action_reaction_sequence: []
pivot:
result:
relationship_delta:
resource_delta:
permission_delta:
information_delta:
emotional_aftereffect:
exit_state:
physical_anchors: []
voice_constraints: []
forbidden_forms: []
```

进入正文前，一个有意义的场景至少应说清：

- 每个重要参与者**此刻**想要什么；
- 每个人以为发生了什么；
- 他们知道、怀疑、误解或绝不可能知道什么；
- 他们真正拥有的筹码和限制是什么；
- 什么会迫使他们换策略或做选择；
- 场景结束时，哪些具体状态可能不同。

模拟层产出的是可信的行动 / 反应可能性，不应提前写好一段漂亮内心戏或对白让正文模型照抄。

## 09 · 滚动细化

不要用同一种分辨率规划一千章。

一个实用的默认梯度是：

```text
BOOK / 固定终局与跨卷弧        明确并锁定
全部 VOLUME 剧情骨架/高潮      明确并锁定
当前 VOLUME + 活跃 ARC         详细
下一 UNIT                      可直接进入生产
未来 1–3 个 CHAPTER            可进入场景模拟
更远章节                       稀疏方向占位
```

具体距离可以由项目和 profile 调整。真正的不变量是：**宏观发生什么、为什么发生、造成什么不可逆结果从 Setup 起锁定；越靠近执行，才越细化如何发生。** 远期章级实现可以重排，已批准的终局、卷级核心剧情、弧线终点和高潮链不能被静默推翻。

当已接受正典改变了上游前提，下游计划应重新评估，而不是因为“之前生成得很贵”就强行保留。

## 10 · 读者压力本来就是规划的一部分

规划不能只排事件顺序，还要考虑读者注意力怎样变化。

一个常见但不是强制公式的节奏是：

```text
当前问题
→ 压力改变可选方案
→ 部分回报 / 有用信息
→ 问题变得更尖锐或被新问题替代
→ 有后果的选择
→ 状态改变
→ 产生继续阅读的理由
```

它的作用不是制造模板，而是防止章节变成“正确流程播报”。

常规操作通常应压缩；真正值得展开的是冲突、错误、代价、选择、关系变化、意外和后果。

## 11 · 依赖感知规划

计划可以依赖：

- 人物状态；
- 关系状态；
- 信息归属；
- 资源、权限或义务；
- 已接受的先前事件；
- 伏笔 / 揭示状态；
- 研究 claim；
- 尚未解决的 loop / promise；
- 当前项目约束。

依赖应显式到足以在上游变化后找到受影响的下游计划。

**不要为了保住旧计划而偷偷修改当前事实。应该失效或重做的是未来计划。**

## 12 · 输入与输出

常见输入：

- 项目权威与当前状态；
- 已接受正典证据；
- 人物 / 关系状态；
- 活跃计划和依赖；
- 已验证研究 claim；
- 项目 / profile 约束；
- Reader Engagement 目标。

常见输出：

- `proposal` 或 `active_plan` 故事对象；
- Scene Card；
- 依赖引用；
- 预期但尚未结算的状态变化；
- 读者问题、压力、回报与开放循环预期。

在别的权威机制明确改变其状态之前，这些输出永远只是规划产物。

## 13 · 失败语义

问题必须回到真正拥有它的层：

- 卷 / 单元没有真实状态变化 → 重做 Story / Volume / Unit；
- 章节逻辑正确但平 → 回到 Reader Pressure + 章节 / 场景规划；
- 场景依赖人物不可能拥有的信息 → 回到人物模拟 / 信息归属；
- 未来计划与 Accepted 状态冲突 → 失效或重做未来计划；
- Scene Card 已经写成脚本 → 收回到约束、目标、状态与 pivot；
- 遥远章级实现越来越僵硬 → 降低单元/章节/场景分辨率，但保留已批准的全书终局与分卷因果骨架。

不要用正文润色掩盖规划失败。

## 14 · 权威不变量

1. `proposal` 与 `active_plan` 只是未来意图，不是已发生事件。
2. Review Draft 不是 Accepted Canon。
3. Scene Card 不能证明某场景发生过。
4. 语义审查 / eval 可以批评计划，但不会因此成为故事事实。
5. Accepted 证据和项目明确权威可以推翻未来计划。
6. 规划机制不得通过副作用写入正典。

## 15 · 相关契约

- [正典与状态模型](CANON_STATE.zh-CN.md)：什么是真的、什么被接受、什么完成结算。
- [人物与关系系统](CHARACTER_SYSTEM.zh-CN.md)：目标、知识、声线、关系和人物持续存在状态。
- [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)：规划阶段用于施加读者压力的正向质量模型。
- [生产流水线](../docs/production-pipeline.zh-CN.md)：规划、模拟、写作与修订在整条生产链中的关系。
