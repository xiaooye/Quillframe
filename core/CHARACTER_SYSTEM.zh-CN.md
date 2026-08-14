# 人物与关系系统 · 独立的人、不对称的关系、受边界约束的知识

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>人物状态</kbd>&nbsp;&nbsp;<kbd>关系状态</kbd>&nbsp;&nbsp;<kbd>知识边界</kbd></p>

NovelForge 把重要角色视为**拥有独立目标、知识、限制、工作、关系与后果的有状态行动者**。角色不是一张性格标签卡，配角也不是为了把主角剧情送到下一站而存在的工具。

> **边界 ✦** 本系统定义通用人物 / 关系机制与模拟输入。具体有哪些人物、他们真正经历过什么、当前权威状态是什么，全部由下游小说项目自己拥有。

## 01 · 这个系统负责什么

人物与关系系统定义：

- 稳定人物事实与可变化行为状态；
- 当前欲望与长期欲望；
- 已知、怀疑、传闻、误信与信息限制；
- 价值观、恐惧、盲点、风险 / 代价边界与解决问题习惯；
- 会随关系与压力变化的声线；
- 跨场景的人物持续存在状态；
- 人物弧线与可被正文证明的人物吸引力；
- 不对称的关系状态；
- 由 Accepted 证据支持的关系变化；
- 场景级 Character Simulation；
- 有证据边界的人物完整性审查。

它不拥有：

- 世界全局真相；
- 正典结算；
- 研究事实；
- 剧情规划权；
- 会话 / 运行时记忆；
- 叙述者的全知权限；
- 独立语义门槛的最终结论。

## 02 · 人物状态要分层

人物模型应把相对稳定的身份事实，与会随故事变化的行为状态分开。

### 稳定 / 项目权威事实

```yaml
names:
birth:
age_by_period:
family:
origin:
class_or_social_position:
occupation:
education:
languages:
legal_status:
health:
material_conditions:
biography:
```

进入当前上下文的，只应是本次任务真正相关的部分。

### 行为状态

```yaml
current_desire:
long_desire:
fear:
what_they_protect:
values: []
biases: []
blind_spots: []
first_response_to_trouble:
problem_solving_habit:
risk_tolerance:
acceptable_cost:
unacceptable_cost:
professional_strength:
professional_boundary:
knowledge_boundary:
misbeliefs: []
```

如果一个“性格特点”从不改变角色的选择、观察、策略、关系或愿意承担的代价，它大多只是资料，而不是有效人物机制。

## 03 · 先问目标，再问形容词

每个重要场景参与者都应回答一些具体问题：

```yaml
character_id:
what_do_they_want_now:
what_do_they_think_is_happening:
what_are_they_wrong_about:
what_can_they_leverage:
what_will_they_not_pay:
what_are_they_doing_physically_or_professionally:
what_will_make_them_change_tactic:
what_residue_do_they_carry_from_prior_scenes:
```

目的不是写人物心理小论文，而是让**不同的人因为真的不同，所以会做出不同动作和反应**。

面对同一种压力，两个人不应天然看到同一件事、接受同一种代价、使用同一种办法，或者用同一种方式解释自己。

## 04 · 知识是状态，不是模型权限

人物不能继承模型看到的全部上下文。

对任何真正影响行动的命题，都要区分人物是：

- 知道；
- 怀疑；
- 误以为另一件事；
- 只听过传闻；
- 现在不可能知道；
- 知道但不能安全说出；
- 只通过另一个人的偏见版本知道。

世界事实与人物认知属于不同状态域。

```text
世界真相 ≠ POV 可见范围 ≠ 人物知识 ≠ 人物信念 ≠ 传闻
```

信息归属必须真正改变行动和对白。如果一个场景只有在角色“顺手知道模型知道的东西”时才成立，那么它在进入正文之前就已经失败。

## 05 · 声线是条件下的行为

声线不是口头禅清单。

可用维度包括：

```yaml
address_terms:
vocabulary_range:
words_they_would_not_use:
sentence_length_tendency:
directness:
interrupt_or_wait:
what_they_avoid_saying:
stress_voice_change:
voice_by_relationship: {}
language_or_dialect:
professional_register:
humor_mechanism:
```

声线会自然受到这些因素影响：

- 正在跟谁说话；
- 此刻想得到什么；
- 掌握什么信息；
- 地位与权限；
- 时间压力与风险；
- 是在隐瞒、谈判、试探、教学、安慰还是攻击。

参考例句可以帮助校准，但不能变成复制固定句式的机器。

## 06 · 语义归属

任何心理、评价、比较、解释和总结性句子，都必须有合法的拥有者。

要问：

> **此刻**究竟是谁的头脑、声线、知识、职业经验、社会位置和关系，能够真实地产生这句话？

如果答案只是“模型觉得这样写很聪明”，这句话就没有归属。

这条规则用来防止：

- 叙述者智力泄漏到当前人物；
- 不同名字背后其实都是同一个模型声线；
- 人物提前拥有时代 / 社会 / 专业上不可能具备的知识；
- 关系判断凭空从叙述层掉下来。

语义归属不是一种文风偏好，而是模拟与正文共同遵守的不变量。

## 07 · 配角必须有自主性

当配角只负责以下功能时，人物已经塌缩：

- 夸主角、验证主角；
- 解释世界；
- 按大纲时间表阻挡主角；
- 负责问铺垫问题；
- 送来一个线索；
- 演完一个情绪 beat 就消失。

重要配角应保留其中若干项：

- 自己的工作或义务；
- 不以主角为中心的目标；
- 世界中其他关系；
- 信息限制与私有知识；
- 自利动机；
- 情绪余波；
- 主动性；
- 能够惊讶、纠正、拒绝、讨价还价，甚至胜过主角。

自主性不等于人人获得相同篇幅，而是**镜头不在他身上时，他仍然具有因果存在**。

## 08 · 人物持续存在

重要人物不能被放进仓库，等大纲下次需要才重新取出来。

至少保留足够状态让再次出现时成立：

```yaml
last_meaningful_action:
current_work_or_obligation:
current_relationship_residue:
known_information:
open_desire_or_problem:
next_plausible_initiative:
```

Presence continuity 问的是：镜头离开以后，这个人正在做什么、承担什么、欠着什么、期待什么、试图解决什么？

答案可以很稀疏，但不能永远是零。

## 09 · 人物弧线必须有证据

人物弧线是一条状态轨迹，不是一串计划好的“成长时刻”。

```yaml
id:
character_id:
scope:
arc_type: growth|flat|negative|corruption|mixed
start_state:
start_misbelief_or_limit:
latent_strength:
pressure_sources: []
turning_points: []
choices_that_prove_change: []
cost_of_change:
end_state:
status:
```

计划可以提出未来转折点；当前 arc state 只有在 Accepted 行为真正提供证据后才能变化。

角色不会因为大纲写着“更勇敢了”就真的更勇敢。项目应能指出哪些选择、代价、拒绝、失败或行为改变建立了这次变化。

## 10 · 人物吸引力要被正文证明

人物吸引力应来自场景证据，例如：

- 在付出代价时仍表现出能力；
- 真正有成本的慷慨；
- 属于这个人的机智；
- 压力下的忠诚；
- 有原则的拒绝；
- 带后果的脆弱；
- 社交判断力；
- 不依赖全知的勇气；
- 可信但出人意料的主动行为；
- 能让另一个人物也变得更鲜活。

如果场景没有证明，就不要靠叙述者宣布某人“迷人、强大、可爱、聪明、气场很强”。

## 11 · 关系状态通常是不对称的

关系是有状态的，而且两边往往并不对称。不要把关系压成“好感度 75”这种单一数字。

```yaml
id:
participants: []
relationship_type:
current_state:
trust_by_side: {}
status_by_side: {}
permissions_by_side: {}
obligations_by_side: {}
known_private_information: {}
conflict_points: []
shared_history_refs: []
current_expectations: {}
last_meaningful_change:
evidence_refs: []
status:
```

一方可能更信任、更了解、欠得更多、更想亲近、给出的权限更少，或者对同一段共同历史有完全不同的解释。

这种不对称本身经常就是场景能量来源。

## 12 · 关系变化需要 Accepted 证据

一次重要互动可以改变：

- 信任；
- 接近 / 行动权限；
- 帮忙意愿；
- 义务；
- 吸引或排斥；
- 权力或地位；
- 共享知识；
- 对过去行为的理解；
- 对未来的期待。

计划可以预测关系变化，Review Draft 也可以写出这种变化；但**当前关系状态只有在 Accepted 证据出现，并走完项目正常结算后才真正改变。**

## 13 · 爱情与亲密关系只是关系状态的扩展

爱情不是另一套魔法系统，只是在普通关系状态上增加一些维度：

```yaml
attraction_by_side: {}
romantic_awareness_by_side: {}
jealousy_or_exclusivity:
physical_intimacy_permission:
emotional_intimacy_permission:
public_private_gap:
relationship_definition:
future_expectation:
```

年龄、同意、法律、文化和项目自己的限制始终具有权威。

## 14 · 关系会改变对白归属

多人场景中，关系状态应影响：

- 谁可以打断谁；
- 谁可以安全开哪种玩笑；
- 谁用职位、姓、昵称，或者故意不称呼；
- 谁有资格问私人问题；
- 谁可以纠正谁；
- 哪些话只能绕着说；
- 哪种帮助可以不解释就开口；
- 哪一种沉默很普通，哪一种沉默会付出代价。

当人物拥有不同目标、知识、任务、社交权限和共同历史时，对白本身就更容易辨认归属。

speaker tag 可以解决句法歧义，但不能替代人物归属。

## 15 · Character Simulation 输出

正文之前，Character Simulation 应产出受限、可操作的视图，而不是提前写漂亮正文。

```yaml
participants:
  CHAR-X:
    current_goal:
    model_of_situation:
    knowledge:
    misbelief_or_gap:
    leverage:
    unacceptable_cost:
    task_or_position:
    likely_first_tactic:
    tactic_change_trigger:
    relationship_constraints:
    residue:
plausible_collisions: []
surprise_opportunities: []
knowledge_conflicts: []
```

模拟的任务是让冲突和可信反应范围变得清楚，同时把句子级实现留给 Draft 阶段。

## 16 · 人物完整性审查接口

候选稿存在以后，NovelForge 可以运行受限的 Character Integrity audit，检查：

- 目标是否一致；
- 是否越过知识边界；
- 声线是否漂移；
- 关系位置是否成立；
- 空间 / 任务状态是否正确；
- 意外行为是“人物活了”还是纯随机。

审查只能收到候选片段，以及当前判断真正需要的人物 / 关系状态。不能注入 hidden gold、private chain-of-thought、writer scratchpad 或 regression 坏例。

结果是一条类型化 finding。它不会直接修改人物状态，也不会自动满足独立语义门槛。

详见 [质量演进](../docs/quality-evolution.zh-CN.md)。

## 17 · 失败语义

问题必须回到所属机制：

- 人物知道不可能知道的信息 → 修知识状态或 Character Simulation；
- 所有人都选择同一种办法 → 拉开目标、代价边界与解决问题习惯；
- 配角只有剧情功能 → 恢复独立目标、工作、限制和主动性；
- 对白归属崩坏 → 先修任务 / 声线 / 空间 / 关系，不要给每句话机械加 tag；
- 关系无证据跳变 → 恢复当前状态并修计划 / 结算；
- 计划中的人物变化提前写成当前事实 → 恢复 Plan ≠ Canon；
- 正文出现无人能拥有的判断 → 修 POV / 语义归属；
- integrity audit 拒绝候选稿 → 修它指出的问题，不要为了迁就草稿去改正典。

## 18 · 不变量

1. 重要人物保留独立目标与信息边界。
2. 人物知识永远不能默认等于模型知识。
3. 关系状态允许、而且经常应该是不对称的。
4. 计划不能更新当前人物 / 关系状态。
5. 当前状态变化需要 Accepted 证据与项目结算。
6. 声线属于“条件下的某个人”，不是口头禅模板。
7. 心理与解释性语言必须有合法 POV / 声线归属。
8. 质量审查只负责诊断，不获得状态写权限。

## 19 · 相关契约

- [故事系统](STORY_SYSTEM.zh-CN.md)：规划尺度与 Scene Card 的职责。
- [正典与状态模型](CANON_STATE.zh-CN.md)：权威、Accepted 证据与结算。
- [表层基本规则](../surface/FUNDAMENTALS.zh-CN.md)：说话人漂移、功能型人物塌缩与语义归属失败。
- [读者吸引力](../surface/READER_ENGAGEMENT.zh-CN.md)：人物自有能量、可信意外、关系推进与读者投入。
- [质量演进](../docs/quality-evolution.zh-CN.md)：受限人物完整性诊断与问题归因。
