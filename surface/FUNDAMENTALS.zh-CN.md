# 表层基本规则 · 给模型实现出来的小说正文设一条质量底线

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>通用失败机制</kbd>&nbsp;&nbsp;<kbd>阈值可由 PROFILE 调整</kbd></p>

Surface Fundamentals / 表层基本规则是 Quillframe 默认的正文实现安全层。它存在，是因为语言模型会跨项目反复出现一批稳定失败机制：用碎句假装节奏、把连续动作切成镜头、叙述者替场景总结意义、设计语言泄漏、空洞微动作、流程播报、虚假意义感，以及许多“看起来很会写、实际上没有小说功能”的漂亮句子。

> **边界 ✦** 表层规则约束的是通用模型失败机制，不是某一本小说的私有文风。通过 Surface 也**不代表**章节已经好看、有情绪力量，或者达到了 production-ready；正向质量由 Reader Engagement 等后续机制继续判断。

## 01 · 表层规则处在什么位置

规则叠加方向是：

```text
Framework Surface Fundamentals
→ 类型 / 平台 Profile
→ 项目 Profile
→ 用户口味 Profile
→ 当前请求
```

更低层可以调整阈值、允许明确的风格例外，或者提高修辞强度；但不能悄悄把一个已经被确认的跨项目模型失败机制重新变成默认写法。

**文字干净只是地板。Reader Engagement 是另一层正向质量模型。**

## 02 · 实现原则：后台设计语言必须消失在“真实发生的小说”里

内部生产概念，例如 state transition、permission change、pressure、payoff、relationship delta、information advantage、resource constraint、character arc，通常不应该被叙述者直接解释。

它们应该在正文里变成：

- 人正在完成某个任务；
- 物件被使用、丢失、转交、藏起或误读；
- 金钱、时间、权限和义务开始真正卡住选择；
- 错误与不完整信息改变下一步；
- 拒绝、谈判、打断和后果改变关系；
- 角色按照自己真正拥有的知识去观察与判断。

如果叙述者只是在把 Scene Card 或状态表翻译成抽象散文，即使每句话都语法正确，Surface Realization 仍然失败。

## 03 · 它在生产流程中的接口

Surface 只能在故事、场景与人物模拟已经造出“值得实现的东西”以后工作。

一个典型接口是：

```text
受限上下文 + 人物私有行动推演
→ Scene Realization Contract + 模型组合的 Writer 上下文
→ Reader Pressure
→ 单次 direct Surface Writer
→ 候选指纹冻结
→ Reader Engagement / 连续性 / 逐项目标语义审查
→ 必要时 bounded 局部修改或上游 / fresh realization
→ 独立评审与用户可见门槛
```

被否决正文、Reviewer 分析和人物私有推演不得给 fresh Writer 做负面 priming。确定性检查只验证 schema、provenance、指纹和上下文边界；文学判断属于模型和作者。

Surface 修复必须尊重问题归属：

- 单个句子级问题 → 局部改写；
- 同一种机制反复出现 → 段落 / block 级改写；
- 多机制同时成簇 → 回到 Scene Simulation；
- 流程正确但平 → 修因果场景设计 / Reader Pressure；
- 功能型配角塌缩 → Character Simulation；
- 解释性语言无人拥有 → 修 POV / semantic ownership。

不要为了“安全”把正文中的能量、幽默、意外、神秘感或修辞乐趣全部删掉。

## 04 · 节奏与切分失败

这一组机制抓的是：文本用排版、碎句和“镜头感”假装速度或重要性，而不是让故事本身发生变化。

### HF-01 · NON-FUNCTIONAL FRAGMENTATION / 无功能碎片化

当句子或段落被切碎，只是为了模拟速度、严肃感或电影剪辑，而没有真实的信息、压力、决定、归属或状态变化时，判失败。

真正的快节奏主要来自：信息更快到达、可选方案变少、阻力立刻出现、deadline 收紧、后果迫近、状态持续改变，而不是把普通动作单独拆成一行行。

项目可以明确选择 fragment-heavy 风格，但每一个碎片仍然要有叙事功能。

### HF-02 · MICRO-SHOT STORYBOARDING / 微镜头分镜化

当一个连续自然动作被拆成多个像摄影机切镜一样的小动作，而这些小动作各自并不值得成为叙事单位时，判失败。

修复应恢复自然叙事单位，而不是只把句号机械换成逗号。

### HF-20 · SUBJECT / SENTENCE TEMPLATE REPETITION / 主语与句式模板重复

当连续句子总以“角色名 / 代词 + 小动作”重新开头，或者固定的“短—短—长”节奏不顾内容一直重复时，判失败。

句子节奏应该服从信息、动作、声线与压力，而不是复用模型模板。

## 05 · 叙述者越权与抽象解释

这一组抓的是：叙述层解释、宣传或判断得太多，超过当前 POV / 人物真正拥有的认知权限。

### HF-03 · NARRATOR THESIS / AUTHOR SUMMARY / 叙述者总结中心思想

当场景已经通过动作和证据表达清楚，叙述者又补一句“真正的意义是……”“这意味着……”之类的总结时，判失败。

删除总结后读者仍然完全理解，就删。若意义真的没建立，优先补事件、选择或证据，而不是补抽象解释。

### HF-04 · DESIGN-LANGUAGE LEAK / 设计语言泄漏

当规划 / 数据库术语作为叙述者解释进入正文，而它又不属于角色真实词汇时，判失败。

relationship upgrade、pressure node、permission delta、payoff、information advantage、arc progression 等后台概念，通常应变成可观察后果，而不是直接标签化。

### HF-07 · ABSTRACT EMOTION LABEL / 抽象情绪标签

当“复杂、说不清、奇怪、困惑、感动”之类模糊词替代了具体判断对象、恐惧、欲望、计算、记忆或社交管理时，判失败。

有效内心活动应该让读者知道：角色到底在衡量什么、拒绝什么、担心什么、想保住什么。

### HF-18 · ABSTRACT AGENT / 抽象概念充当行动者

默认情况下，当时间、记忆、历史、命运、城市、沉默、黑暗等抽象概念被拟人化，主要只是为了制造文学质感时，判失败。

这是 profile-sensitive 规则。问题不是“绝不准拟人”，而是这种写法是否真的改善了感知、声线或意义。

### HF-25 · EXPLANATION AFTER EVIDENCE / 证据后重复解释

动作 / 对白已经证明一个意思后，叙述者立刻再抽象复述一遍，判失败。

相信最强的表达层，不要重复解释同一件事。

### HF-27 · SEMANTIC ROLE MISATTRIBUTION / 语义角色错归属

当心理、比较、总结或评价性语言其实属于模型 / 全知叙述者，而当前 POV 或人物不可能真实拥有这种措辞与知识时，判失败。

每一句解释性文字都问：**现在到底是谁的头脑、知识、社会位置和声线能够合法产生这句话？**

## 06 · 装饰性意义与合成“文艺感”

这一组抓的是：句子主要功能只是显得文学、电影化、深刻或“很会写”。

### HF-06 · ORNAMENTAL METAPHOR / 装饰性比喻

当比喻或拟人主要负责装饰，尤其反复围绕身体、时间、记忆、城市、命运、沉默、历史制造泛化修辞时，判失败。

文学型 profile 可以容许更高修辞密度。不变量是：它必须让感知、声线、意义或情绪精度变得更好。

### HF-15 · SIGNIFICANCE INFLATION / 虚假意义膨胀

当普通物件 / 动作被单独强调、加反应停顿、对比词或漂亮 follow-up，只为了让它“看起来很重要”时，判失败。

一个 beat 真正值得强调，通常因为它改变了行动、推断、风险、关系、身份、位置、资源或其他具体状态。

### HF-16 · STAGED ROUTINE REVEAL / 常规信息舞台式揭示

当普通身份 / 背景信息被组织成合成电影揭示：先扫 inventory，再缩小焦点，再孤立一个名字 / 日期 / 物件，再加装饰细节和反应停顿，判失败。

真正不可逆的重要信息可以有仪式感；常规事实通常应通过有目的的行动或搜索自然出现。

### HF-19 · MANNERISM CONNECTOR / 习惯性转折连接词

“没想到、反而、就在这时、仿佛、显然、原来”等词本身不禁用。只有当它们反复制造本来不存在的对比或重要感、替缺失因果抛光时才失败。

### HF-29 · AI POLISH WITHOUT STORY FUNCTION / 无故事功能的 AI 抛光

兜底型 cluster fail：句子主要职责是显得精致、电影化、深刻、像“作家写的”，但没有增加有效感知、声线、因果、张力、关系、信息或节奏功能。

只要能归到更精确的 HF code，就不要偷懒用 HF-29。

## 07 · 身体、动作与物件使用失败

具体细节不是越多越好。Embodiment 必须属于任务、空间、人物目标和后果。

### HF-08 · EMPTY MICRO-ACTION / 空洞微动作

点头、看一眼、端杯子、摩挲手指、沉默等动作，如果只是为了让对白“看起来有画面”，判失败。

一个动作值得保留，通常因为它改变了时间、说话归属、信息、关系、任务推进、空间约束或情绪解释。

### HF-09 · RANDOM EMBODIMENT PATCH / 随机身体化补丁

当一个原本悬空的场景只是被撒上一堆无关手势，而没有恢复真实任务、人物目标、物件、空间和因果动作时，判失败。

### HF-17 · PROP CATALOGUE / 道具清单化

当具体细节来自 inventory，而不是角色目的时，判失败。

一个物件真正值得占篇幅，是因为有人使用、需要、付钱、移动、丢失、转交、检查、隐藏、误读、扣留它，或者因为它作出了决定。

## 08 · 人物与对白失败

这一组保护人物归属、自主性，以及对白发生时仍然存在的现实世界。

### HF-05 · DOSSIER INTRODUCTION / 档案式人物登场

角色初次出现时一次性交代年龄、衣服、职业、历史、性格、名声与当前态度，而场景根本没有同时需要这些信息，判失败。

只在当前行动、关系或判断真正用到时揭示身份信息。

### HF-10 · MECHANICAL DIALOGUE TAGGING / 机械对白标签

当说话人不清楚的问题被“每句都加某某说”解决，而人物声线、目标、任务、知识和空间归属仍然缺失时，判失败。

Tag 是工具，ownership 才是目标。

### HF-11 · SPEAKER DRIFT / DISEMBODIED DIALOGUE / 说话人漂移与悬空对白

多人对白如果主要依赖 ABAB 轮流顺序让读者猜谁在说话，判失败。

归属可以来自明确称呼、独立目标 / 声线、角色专属任务 / 物件、独有知识、空间位置、因果动作或另一个角色的回应目标。第三个说话者进入以后，不要继续依赖二人轮流假设。

### HF-12 · DIALOGUE WORLD ERASURE / 对白抹掉世界

长对话一开始，当前工作、物件、空间、deadline 和人物目标全部消失，判失败。

对话始终发生在一个仍然继续运转的世界里。

### HF-13 · INTERVIEW / TRANSCRIPT DIALOGUE / 采访稿式对白

对白退化成纯信息交换，人物只是排队等自己那句台词，判失败。

角色应该在需要时追求目标、隐瞒、误解、打断、讨价还价、试探、回避、教学、拒绝，或边说边做真正有因果作用的事。

### HF-30 · AGENDA-TO-DIALOGUE LEAKAGE / CHARACTER-SHEET-TO-DIALOGUE SERIALIZATION / 议程泄漏与角色表对白序列化

**Agenda 驱动说话；Agenda 不是对白本身。** 当对白只是把人物私有目标、职位、风险、责任、知识边界、恐惧、信念、不可接受代价或策略理由近乎一一对应地翻译成自然语言，而没有先经过“对谁说、此刻要达到什么、关系成本是什么”的变形时，判失败。

理想的实现边界是：

```text
人物私有状态
→ 当下 tactic
→ listener model + shared context
→ 社会 / 关系成本
→ 省略 / 压缩 / 扭曲
→ 任务 / 物件互动
→ 说话 / 行动
→ 打断 / 回应
```

人物可以专业、理性、善于表达，也可以说很长。真正的语义问题是：**为什么这个人要对这个听者，在这个时刻，以这个成本，说得这么完整？** 刚参加完同一场会议、共享相同历史或明显利害关系的人，通常不需要彼此重新完整复述自己的 character sheet。

不得用行长、连接词数量、碎句、ellipsis、打断次数、口语化程度或其他 lexical proxy 直接判 HF-30。只要“完整”本身就是当前 speech act / interaction requirement，完整陈述完全合法，例如 deposition / testimony、incident debrief、board / military briefing、medical risk explanation、instruction / teaching、formal refusal rationale、clause negotiation、record-making，以及本身要求完整说明的 confession / apology。

HF-30 首先是 interaction / realization interface failure。若它成簇或覆盖整场，repair owner 应回到 Character / Scene Simulation 或 writer-safe realization projection，而不是把每一句对白机械缩短。

### HF-26 · FUNCTIONAL-CHARACTER COLLAPSE / 功能型人物塌缩

配角只负责解释、夸赞、阻挡、送信息或按计划触发一个 beat，判失败。

重要人物应保留自己的目标、工作、信息限制、情绪余波、关系、自利性与可信主动行为。

## 09 · 规则防御与后台泄漏

这一组抓的是：正文主动暴露后台禁令，或者提前替自己回应不存在的批评。

### HF-14 · CONSTRAINT LEAK / RULE DEFENSE / 约束泄漏与规则辩护

当项目后台规则作为“负面证明”进入正文，例如因为项目禁止某 trope，叙述者特地解释为什么所有人都没这么怀疑，判失败。

问一句：**如果后台从没写过这条规则，这句话还会自然存在吗？** 如果不会，就应回到真实场景实现。

### HF-28 · CONTEXT DEFENSE PROSE / 上下文防御式正文

文本专门解释人物为什么没问、没发现、没怀疑、没按某个 trope 行动，只为了预先堵住批评，而这种“没有发生”本身又没有因果作用时，判失败。

## 10 · 流程与因果失败

商业、法律、政治、技术、调查、专业能力型小说尤其容易触发这一组，因为模型天然爱把“正确流程”平均展开。

### HF-21 · PROCESS BROADCAST / 流程播报

仅仅因为 outline 写了每一步，就把常规操作都用相同叙事权重播报出来，判失败。

压缩 routine；展开摩擦、错误、分歧、责任转移、时间 / 资源开始卡死、需要在坏选项中选择、关系改变流程、意外与后果。

### HF-22 · CHECKLIST CAUSALITY / 清单式因果

场景只是一步接一步执行正确步骤，而不是前一步的后果逼出下一步，判失败。

弱结构：

```text
打开 → 检查 → 修正 → 再确认 → 发出
```

更强的结构：

```text
问题 → 部分解决暴露代价 → 选择 → 反应 → 可选方案改变 → 后果
```

时间顺序不等于因果推进。

## 11 · 悬念与结尾失败

### HF-23 · FAKE CLIFFHANGER / NARRATOR ADVERTISEMENT / 假悬崖与叙述者广告

章节结尾只靠“真正的危机才刚开始”这类抽象广告制造继续阅读动力，而故事状态本身没有改变，判失败。

具体后果、新信息 / 人 / 物进入、有成本的选择、逆转、关系变化、独特声音或下一状态侵入，都可以提供 forward pull，并不要求每章都有 twist。

### HF-24 · FORCED MYSTERY / 强造神秘

普通信息被故意遮住或写得含糊，只为了廉价 suspense，判失败。

真正的 mystery 应来自真实信息边界、不确定性、欺骗、缺失证据或人物限制。

## 12 · 段落、句法与 POV 基本原则

### 段落是叙事单位

一个段落可以同时包含动作、观察、对白、反应、本地判断、空间 / 物件变化和即时后果；不需要样样都有，但段落边界必须有自然叙事理由。

独立短段最适合真正的打断、不可逆动作、关键信息、高压停顿或具有方向性的对白。

### 默认完整句法

商业 / 可读型正文通常优先清楚完整的句子。Fragment 可以使用，但必须有真实语义冲击，而不是因为模型把“短 = 快”当公式。

### 细节服从 POV 任务

具体细节应由 focal character 正在做什么、需要什么、害怕什么、比较什么、寻找什么、误解什么、决定什么，或者其职业训练让他会注意什么来选择，而不是由隐形摄影机做 inventory。

### 叙述距离必须有目的

不同 profile 和 POV 可以采用不同叙述距离，但叙述者不应像站在场景外的编辑，每个 beat 后都标注“这很重要”“他很复杂”“关系已经不同了”。

## 13 · 诊断输出

Surface audit 应报告可观察机制证据，而不是 private reasoning。

```yaml
artifact_type: surface_audit
candidate_fingerprint:
findings:
  - mechanism_id: HF-XX
    severity: low|medium|high|cluster
    evidence_ref:
    scope: sentence|paragraph|block|scene
    repair_owner: surface|scene|character|reader|story
result: pass|rewrite|regenerate
```

确定性 lint 可以抓高风险 pattern；复杂文学机制的最终分类可能仍需要语义判断。

## 14 · 失败路由

选择真正拥有问题的最小修复层：

```text
孤立词句问题                  → 局部改写
同机制重复出现                → 段落 / block 改写
多机制场景级成簇              → Scene Simulation / 整场景重生
流程 / checklist 平淡          → 因果场景设计 + Reader Pressure
功能型人物塌缩                → Character Simulation
语义归属漂移                  → POV / 人物 ownership 修复
故事前提 / 状态失败            → Story / Canon 层
```

不要把结构性失败一路句子级修补，最后得到“技术上安全，但完全没生命”的正文。

## 15 · 不变量

1. Surface 规则针对失败机制，不是 banned-word list。
2. Profile-sensitive 例外必须明确，而且有真实功能。
3. 后台设计语言通常应该消失在生活化后果里。
4. 具体细节服从 POV / 任务 / 因果，而不是 inventory。
5. Surface Safety 不能替代 Reader Engagement。
6. Regression 坏例只能作为生成后证据。
7. Cluster failure 应回上游，而不是无限积累 cosmetic patch。
8. Surface audit 只诊断正文，不获得 Canon authority。

## 16 · 相关契约

- [读者吸引力](READER_ENGAGEMENT.zh-CN.md)：正文越过质量地板以后，继续判断正向阅读价值。
- [人物与关系系统](../core/CHARACTER_SYSTEM.zh-CN.md)：语义归属、说话人归属、人物自主性与知识边界。
- [故事系统](../core/STORY_SYSTEM.zh-CN.md)：因果场景设计与规划职责。
- [质量演进](../docs/quality-evolution.zh-CN.md)：类型化 finding、修订路由与候选稿比较。
- [生产流水线](../docs/production-pipeline.zh-CN.md)：Surface Realization 与生成后检查在整条流程中的位置。
