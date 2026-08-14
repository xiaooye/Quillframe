# Character & Relationship System · 通用人物与关系系统

## 目的

NovelForge 把人物视为**有状态、有限知识、拥有自己 agenda 的行动者**，而不是性格标签或剧情功能。

一个人物至少由这些层组成：

```text
facts
+ current desire / long desire
+ values / fears / blind spots
+ knowledge / misbeliefs
+ risk / cost boundaries
+ problem-solving habits
+ relationship-specific behavior
+ voice
+ accumulated consequences
```

目标不是写更多人物小传，而是让不同的人面对同一个压力时，真的会用不同方式观察、选择、说话、犹豫、讨价还价、失败和恢复。

## Character Facts

稳定、项目权威的人物事实可以包括：

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

Scene Context 只注入当前真正相关的事实。

## Behavior Engine

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

一个“性格特点”如果从不改变选择，只是 metadata，不算 characterization。

## Knowledge / Belief Model

人物不能共享模型的全局知识。

对重要命题，至少区分：

- 已知；
- 怀疑；
- 错误相信；
- 只听到流言；
- 现在还不可能知道；
- 知道但不敢安全说出；
- 只通过另一个人的偏见版本知道。

Information ownership 必须实际影响行动和对白。

## Voice Engine

Voice 不是一袋口癖。

有用维度：

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

可以存 example 作为参考，但不能变成机械复制句式的模板。

## Semantic Ownership / 语义角色归属

任何心理、评价、比较、总结性句子都必须有合法 owner。

问：

> 此刻到底是谁的脑子、声线、知识和社会位置，能够真实地产生这句话？

如果答案只是“模型/旁白想写一句聪明话”，就重写。

这条同时防止 narrator intelligence 泄漏进角色，也防止所有角色像同一个模型换名字说话。

## Character Simulation

正文前，重要参与者应至少完成：

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

Simulation 产出的是 action/response possibilities，不是漂亮心理独白。

## Supporting-character Autonomy

配角如果只负责：

- 夸主角；
- 解释世界；
- 到点阻挡主角；
- 问 setup question；
- 送一条 clue；
- 执行一个 outline 情绪节点然后消失；

就已经功能 NPC 化。

重要配角应持续拥有其中若干：

- 自己的工作；
- 与主角不完全一致的目标；
- 不围绕主角存在的关系；
- information limit；
- 情绪余波；
- self-interest；
- initiative；
- 能纠正或让主角意外的能力。

## Character Arc

人物弧记录有意义的状态改变，不是“几个成长场面”的清单。

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

Arc evidence 必须来自 Accepted behavior。Plan 可以预测未来改变，但不能提前 settle。

## Appeal / Charisma Evidence

人物魅力应该被证明，而不是被旁白宣布。

常见 mechanism：
- 有代价的 competence；
- 真正付出成本的 generosity；
- 属于这个角色的 wit；
- 压力下的 loyalty；
- 有原则的 refusal；
- 会产生后果的 vulnerability；
- social intelligence；
- 非全知型勇气；
- 出乎意料的主动性；
- 能让另一个角色也变得更鲜活。

场景没有证明时，不要由 narrator 宣布“很有魅力、很强、让人无法拒绝”。

## Presence Continuity

重要人物需要跨场景保留后果。可以跟踪：

```yaml
last_meaningful_action:
current_work_or_obligation:
current_relationship_residue:
known_information:
open_desire_or_problem:
next_plausible_initiative:
```

避免人物被 outline 暂时“收进仓库”，等剧情需要时才重新生成。

# Relationship System

关系是有状态、可不对称、需要 evidence 的。

## REL

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

不要把关系压成“好感度 75”一个数字。

## Relationship Delta

一次重要互动可能改变：

- trust；
- access / permission；
- willingness to help；
- obligation；
- attraction / aversion；
- power / status；
- shared knowledge；
- 对之前行为的 interpretation；
- future expectation。

Current relationship state 只有在 Accepted evidence 后才改变。

## Romance / Intimacy Extension

Romance 不是另一套魔法系统，它只是 Relationship State 的扩展：

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

Age、consent、legal、cultural 与 project constraints 始终优先。

## Dialogue Ownership Integration

多人场景里，relationship state 应该自然改变说话方式：

- 谁敢打断谁；
- 谁可以安全开玩笑；
- 谁会不用称呼、谁必须用正式称呼；
- 谁有资格问私人问题；
- 谁需要解释、谁可以默认 shared knowledge；
- 谁会表现 deferential behavior；
- 谁可以拒绝而不解释。

这比机械“给每个人一个口癖”更强。

## Core Invariant

> 人物在剧情暂时不用他们的时候仍然是人；关系会记得前一个场景到底付出了什么。
