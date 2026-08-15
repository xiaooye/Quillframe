<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge 自适应小说智能体框架" width="560" />
  <p><strong>生产流水线 · 先模拟因果，再演化候选稿，最后通过明确门槛发布</strong></p>
  <p><kbd>冻结</kbd>&nbsp;&nbsp;<kbd>模拟</kbd>&nbsp;&nbsp;<kbd>起草</kbd>&nbsp;&nbsp;<kbd>诊断</kbd>&nbsp;&nbsp;<kbd>演化</kbd>&nbsp;&nbsp;<kbd>门槛</kbd></p>
  <p><a href="production-pipeline.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

<img src="../assets/brand/story-thread.svg" alt="" width="100%" />

# 生产流水线

NovelForge 把一章正文视为一轮**可恢复的生产运行**。它既不是“一次模型生成”，也不是一条固定的“Writer → Critic → Editor”智能体流水线。

管理器只为当前判断选择最小的语义契约包。真正需要理解故事、人物、读者与修改效果的问题交给模型；权威、权限、内容指纹、持久化、路由、检查点、类型校验、硬预算与结算事务由确定性系统负责。

<img src="../assets/ui/home-pipeline.zh-CN.svg" alt="NovelForge 正文生产运行：冻结与模拟、生成内部候选稿、诊断与演化，再通过发布门槛" width="100%" />

---

## 01 · 四类核心职责

每一次 `DRAFT` 或 `REVISE` 都围绕四类职责组织。

**冻结 + 模拟**：先确认当前合法的故事状态、稀疏工作上下文、人物真正会采取的行动、场景因果，以及这一章对读者有什么即时压力。

**生成内部候选稿**：先产出事件优先的 Raw Draft，再完成正文表层实现。Raw Draft 始终属于内部生产过程。

**诊断 + 演化**：用精确语义契约和确定性证据找到问题真正属于哪一层，在正确层修复，并验证新候选稿是否真的优于现稿。

**发布门槛**：检查读者体验、长程承诺、状态 / 权威完整性，以及当前任务真正要求的独立判断，然后才允许展示可审阅正文。

这是一张会回流的图，不是一条必须从头跑到尾的传送带。某个阶段失败后，可以直接回到拥有该问题的上游机制。

---

## 02 · 写正文之前，先把运行本身建立起来

生产运行开始时，先解析下游 Project 与它锁定的精确 Framework 依赖，再创建或恢复 manager 的 `session`、`run` 与 checkpoint 身份。

在生成正文前，至少必须明确：

- 当前只有一个 `task_mode`；
- 项目权威与正典截止点；
- 当前计划、候选稿与已接受状态对应的精确指纹；
- 当前宿主有哪些真实可用的执行能力；
- 是否即将执行需要先 checkpoint 的 consequential side effect。

聊天记录可以帮助继续对话，但不能替代 Project authority，也不能冒充持久状态数据库。

**失败回路：** 回运行时 / Project bootstrap。权威都没有确认清楚时，不进入创作层。

---

## 03 · 冻结稀疏上下文

NovelForge 把上下文当作有预算的工作集，而不是默认把整本小说、整套语料和所有历史都塞给模型。

当前任务真正需要的内容可能包括：

- Project profile 与当前文本约束；
- 直接相关的已接受正典和当前状态；
- 当前章节 / 单元计划与场景目标；
- 本场景涉及的人物与关系；
- 未解决、但当前章节必须承担的承诺或依赖；
- 当前场景确实需要的研究结论；
- 在允许且有帮助时选中的派生记忆。

如果“此刻哪些信息真正相关”本身需要理解语义，管理器可以加载 `context-research` 契约包并调用 `context.select`。确定性代码仍然负责硬预算、来源、权威等级和最终封装边界。

默认不加载无关未来计划、整套 Corpus、管理器全部聊天历史、隐藏评测标签或 regression bad examples。

**失败回路：** Context / Memory。

---

## 04 · 故事 / 正典预检

进入场景模拟前，先确认当前工作相对于项目权威是否合法。

例如：

- 这个事件只是计划，还是已经 Accepted？
- 场景是否要求尚未获得的人物知识、资源、关系或位置？
- 当前状态变化是否与正典和已有依赖兼容？
- 新发生的因果是否已经让旧计划失效？
- 用户真正要做的是 `DRAFT` / `REVISE`，还是已经跨进 `PLAN-*` / `SETTLE`？

当故事自然演化后需要调整活动计划时，可以使用 `long-horizon` 契约包里的 `plan.reconcile`。计划协调可以提出新的计划关系，但不能反向改写已经接受的正典。

**失败回路：** Story / Plan / Project authority。

---

## 05 · 先让人物行动，再求解场景

当前开发架构把“写正文前先解决因果”明确实现为 `story-simulation` 契约包。

`character.action_propose` 先根据人物当前状态提出其真正可能采取的行动。重要输入包括：

- 人物议程与眼前目标；
- 信念与知识边界；
- 利益、风险与代价；
- 当前关系状态；
- 空间位置与客观条件；
- 上一事件留下的情绪与现实余波。

随后 `scene.resolve_actions` 才把多个人物的行动与世界状态碰撞在一起，解析成一条因果事件轨迹。

顺序很重要：不是先决定“剧情必须发生 X”，再让所有人物配合 X；而是先尊重人物拥有的行动，再求解这些行动会把场景推向哪里。

**输出：** 人物行动提案 + 场景级因果轨迹。

**失败回路：** Character Simulation / Scene Simulation；如果一个场景只有靠人物失真才能成立，则回 Story / Plan。

---

## 06 · 写之前先建立读者压力

因果成立的场景也可能很无聊。Reader Pressure 关注的是：**读者为什么现在要在乎这一场？**

有效压力可能来自：

- 正在发生的欲望、威胁、困境或承诺；
- 有真实后果的不确定性；
- 关系张力；
- 必须付代价的选择；
- 揭示、反转、失败或赚来的阶段性回报；
- 避免单调升级的反差；
- 前文已经建立、这一章应该推进或复杂化的读者预期。

Reader Pressure 是场景设计目标，不是强迫每章最后加一个机械 cliffhanger。

如果后续被诊断为 `SAFE-BUT-FLAT`，修复应回到这里和 Scene Simulation，而不是继续堆漂亮句子。

---

## 07 · 生成事件优先 Raw Draft

只有当前因果问题已经足够解决，Writer 才进入正文生成。

“事件优先”意味着 Raw Draft 先写清真正会改变状态的内容：

- 选择与失误；
- 冲突与回应；
- 信息移动；
- 状态变化；
- 代价与后果；
- 关系移动；
- 读者真正得到的阶段性回报。

没有冲突、人物、信息或后果功能的 routine procedure 应主动压缩。

Raw Draft **始终是内部产物**。它不是 Review Draft，更不会自动展示给用户。

负面 regression 样本必须等 Raw Draft 冻结后才允许进入上下文，避免已知坏例污染首轮写作。

---

## 08 · 完成表层实现

Surface Realization 把事件优先材料转换成 Project 要求的文本实现，同时执行 Framework 的 Surface Fundamentals。

这一层真正负责的是表层 realization 问题，例如：

- 反复出现的 AI 式节奏；
- 旁白强行 hype；
- 机械微动作；
- POV / 声线泄漏；
- 流程播报式正文；
- 假意义感；
- 不合理的压缩或展开。

修复尺度不能混淆：

- 孤立表层问题 → 局部改写；
- 表层失败成簇 → 重做整场景 realization；
- 文本很干净但场景没有生命力 → **不要**继续停在句子层。

表层干净只是地板，不是发布标准。

---

## 09 · 冻结候选稿，再读取生成后回归证据

第一份完成 realization 的候选稿出现后，先冻结 artifact fingerprint，再引入 post-generation regression evidence。

只有这时才读取当前问题真正相关的负面回归或已知坏例。

这样做有两个目的：

1. 不让坏例在首轮生成前形成反向 priming；
2. 让之后所有诊断都绑定一个确定版本，而不是面对不断变化的文本。

候选稿发生实质变化就会产生新指纹；绑定旧指纹的 review result 不能继续当成新稿件的证据。

---

## 10 · 通过精确语义契约诊断

NovelForge 不存在一个万能 critic prompt。

管理器先从 `model_contract_catalog.json` 选择当前问题最相关的最小契约包；确定性运行时再把精确 contract ID 解析到唯一 pack。

针对候选稿质量，`quality` pack 当前提供：

- `reader.reaction` —— 读者体验证据；
- `reader.compare` —— 有界的读者视角成对比较；
- `character.integrity` —— 人物行为完整性判断；
- `revision.diagnose` —— 问题诊断与 repair owner 归因。

如果问题属于别的语义域，则按需加载其他 pack：

- `narrative-memory` —— 派生叙事状态与读者预期；
- `long-horizon` —— 计划、关系记忆与长程承诺；
- `creative-evolution` —— 真正不同的场景分叉，以及 incumbent / challenger 比较。

模型结果是证据，不会因为“模型已经判断了”就自动获得正典或写入权威。

---

## 11 · 把诊断变成明确 findings 与修复归属

诊断不应该只留下“再改好一点”这种模糊要求。

Quality findings 负责记录问题与证据，让它能在多轮候选稿演化中被追踪。`revision.diagnose` 则负责判断缺陷真正属于哪个机制。

常见路由包括：

**表层缺陷** → 局部改写或重做场景 realization。

**SAFE-BUT-FLAT / reader-grip fail** → Reader Pressure + Scene Simulation。

**人物完整性失败** → Character Simulation；如果场景前提本身要求人物失真，则进一步回 Story / Plan。

**故事 / 因果失败** → Story / Plan。

**上下文 / 记忆失败** → Context / Memory。

**长程承诺失败** → continuity / plan / relationship reconciliation，而不是句子润色。

**有效独立语义拒绝** → 回真正拥有问题的 repair layer，不允许 reviewer-shopping。

---

## 12 · 演化候选稿，而不是假设“改过就一定更好”

修改不是天然进步。

NovelForge 记录候选稿谱系，并允许把当前 incumbent 与 challenger 进行显式比较。`creative-evolution` pack 中的 `quality.compare` 用来判断修复稿是否真的有证据支持的提升；`scene.diverge` 则用于需要真正不同因果路径时，而不是换几个词重新生成同一场戏。

比较结果可以是：

- challenger 更好；
- incumbent 仍然更好；
- 没有足够证据证明任一方明显更好 / tie。

因此 Quality Evolution 支持 **plateau stopping**。当继续修改已经没有真实收益时，系统可以停止，而不是进入无穷 rewrite churn。

深入指南：[质量演化](quality-evolution.zh-CN.md)。

---

## 13 · 审核读者体验与长程承诺

进入发布前，候选稿必须通过当前任务真正要求的门槛。

Reader Engagement 判断章节是否有真实压力、因果、回报、反差、有效状态移动与继续阅读动力。

长程一致性可以使用 `long-horizon` pack 的 `continuity.commitment_audit`，把候选稿与已经明确存在的事实和叙事承诺进行核对。长期关系证据出现冲突时，可以使用 `relationship.memory_reconcile` 协调证据。

这里的连续性远不只是“小设定记错”：

- 人物知道什么、是否在场；
- 位置与移动；
- 承诺、义务、期限、资源、伤势、债务；
- 关系变化；
- 开放线索与 setup / payoff 义务；
- 时间顺序；
- 情绪和事件余波。

发现矛盾后，不能通过“那就把新版本写进正典”来解决。

---

## 14 · 只有真正要求独立性时，才进入 independent gate

独立语义审查是一种**特定门槛**，不是所有模型判断的同义词。

只有当当前 rubric / workflow 明确要求 independence 时，结果才必须来自真正不同的 invocation / session，并绑定精确 artifact fingerprint。review packet 保持有界，也不能包含 hidden gold 或管理器整段历史。

transport failure 可以换另一条同样合格的执行路径；有效的 `semantic_reject` 是真实判断，必须进入修复。

如果某个语义契约本身并不要求独立性，则可以通过其他合格 model route 执行，不得为了“看起来更严格”伪装成 independent reviewer。

深入参考：[语义执行器协议](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md) 与 [语义执行运行时](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)。

---

## 15 · 真实地跨过用户可见门槛

Raw Draft 永远不能跨过这道门槛。

只有当前任务要求的质量与连续性门槛都已经解决，候选稿才能作为可审阅正文展示。真实的未完成状态包括：

`awaiting_user` · `awaiting_external` · `semantic_pending` · `failed_gate` · `settlement_incomplete`

缺少 mandatory judgment 不是 PASS；指纹已经过期不是 PASS；流畅文字掩盖的连续性问题也不是 PASS。

目的不是制造最大流程，而是建立一条诚实边界：哪些只是后台候选稿，哪些已经有资格让用户看到。

---

## 16 · 用户接受后进入另一种事务：SETTLE

用户可见 Review Draft 与 Accepted Canon 是两个不同权威等级。

只有明确 acceptance 或明确授权的 Canon 修改请求才能进入 settlement。确定性 settlement runtime **不会**自己推断用户是否接受、State Delta 是什么、哪条事实应该成为正典，也不会代替模型理解文学意义。

一个 settlement transaction 必须拿到精确的接受证据与写入意图，例如：

- accepted artifact reference + fingerprint；
- acceptance receipt；
- checkpoint reference；
- write-authorization reference；
- 精确 create / update / delete 操作；
- 需要 compare-and-swap 的 before-state fingerprint；
- required derived projection 与对应 receipt；
- authoritative postcondition 验证。

required projection 失败时，状态是 `settlement_incomplete`；已经完成的 projection receipt 也不能被静默当作新任务重复执行。

因此，**生成、审阅、接受、写入正典**始终是四件不同的事。

---

## 17 · 这套流水线真正优化什么

后台严格，是为了让前台正文不显得像系统产物。

这套流程主要防止：

- future plan 泄漏进 current truth；
- 人物使用只有管理器知道的信息；
- 平淡场景被不停做句子美容，而不是修因果；
- regression 坏例污染首轮生成；
- 不同 reviewer 实际审了不同指纹的稿件；
- 修改已经进入平台期却仍然无限继续；
- 派生记忆或模型判断偷偷获得故事权威；
- resume 后重复 consequential write；
- 用户“看过 / 喜欢”被误当成 settlement 已完成。

目标不是让正文看起来很“工程化”，而是让**工程系统退到幕后，留下自然、鲜活、有推进力的小说**。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="52" />
  <br />
  <sub>先解因果，再写正文；精确诊断；用证据演化；明确接受后才结算。🌸</sub>
</div>
