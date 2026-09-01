# AI 原生小说生成源头架构规格

2026-08-31 · SYSTEM-IMPROVE 合同 · 工程实现不等于文学成功。

## 01 · 目标

Quillframe 必须从紧凑的因果场景合同与模型组合的合格 Writer 上下文直接生成小说。不得先写一篇解释充分的完整 Raw Draft，再让第二个模型去除 AI 腔。

当前作者目标必须贯穿最终生成和所有适用审稿。确定性 Core 代码只负责身份、权利、来源、schema、指纹、预算、持久化、幂等和发布不变量。文学相关性、声线、人物策略、修订范围和正文质量属于模型或作者。

## 02 · Author Voice Sheet

Author Voice Sheet 是按用户或 Project 存储、版本化、默认关闭的资产，只能由注册语义合同从以下证据编译：

- 用户自有或明确授权的正文；
- 作者亲自编辑并明确认可的段落；
- 用户明确反馈；
- 合法、带来源、且不要求模仿在世作者的正面证据。

每个来源必须绑定来源类型、rights class 与依据、storage intent、内容指纹、版本、适用范围和作者确认。被否决的模型正文只能作为负面回归证据，不能成为正面锚点。

声线表覆盖叙述距离与 POV 注意、句法与段落节奏、信息释放、对话和关系差异、压力下的幽默、通过行动／判断／代价呈现情绪、读者推断、语言切换与术语、正面证据、边界和不确定性。

Core 只验证结构和资格，不推断声线，也不打分。没有作者明确确认就不能启用；没有 active sheet 时必须返回真实的 disabled/degraded 回执。

## 03 · Character Enactment

正文生成前，人物模型必须为每个出场人物私下描述：

- 此刻的信念与误判；
- 想得到的收益与怕失去的事；
- 对其他出场人物的预期；
- 两到三个可行策略；
- 每项策略的收益、风险和未采用时的拒绝理由；
- 最终选择以及它对他人的限制；
- 针对不同关系对象的说话、回避、试探、让步或转移话题方式。

该制品属于私有规划证据。Writer 可看到已经选择的行为与可观察限制，但绝不能看到整段权衡与心理解释。

## 04 · Scene Realization Contract

模型负责的场景合同只包含：

- POV 当前能看见、知道和误解的事；
- 开场时各方可选方案；
- 人物已经采用的行动策略；
- 环境或他人的反制；
- 哪个选项消失、代价上升或关系改变；
- 必须发生的事实结果；
- 必须保留的潜台词或信息差；
- 场景末形成的新限制；
- 一个能承载冲突的具体物件、动作或空间阻力。

合同不得预写主题、金句、完整对白、固定意象、段落形状、感官配额、笑点配额或强制节拍。

## 05 · Context Composer

场景投影调用同时从 Core 预验证库存中选择最小充分的 Writer 上下文。合格类别为：

- 当前 active Author Voice Sheet；
- 两到四个功能匹配、权利合格的正面锚点；
- 当前 Scene Realization Contract；
- 出场人物的情境声音卡；
- 当前相关世界事实与状态；
- 最近 accepted 或 author-approved 的正文 tail；
- 一条简短、具体的 Director Note；
- 当前作者目标。

Core 只实例化模型选中的标识，并重新验证权利、来源状态、版本和指纹；不替模型选择文学相关性。

fresh realization 必须排除：

- 作者否决或其他不合格正文；
- Reviewer 报告与 Repair 解释；
- 人物私有推演；
- 不相关人物百科或 Lore；
- 当前 POV 不知道的未来事实；
- 重复完整对象或反复规则文档；
- script 生成的文风诊断。

## 06 · 直接 Surface Writer

生产图只有一个正文生成阶段。Surface Writer 直接从紧凑 Writer pack 实现候选正文。

靠近生成端的指导必须短、正向、贴合场景：把判断放进行动、停顿、误解、回避和选择；只写 POV 会注意的东西；让对话争夺信息、关系、时间、责任或资源；让行为与代价显示动机；证据足够时停止解释；以后果或新限制收场；普通叙述默认自然中文，英语只在人物与现场确有必要时短暂出现。

Writer 永远不能看到英语计数、AI 风险分、禁词或 prose telemetry。

## 07 · 修订路由

注册语义路由必须把当前作者目标绑定到候选精确证据，并选择：

- isolated_defect：只暴露目标窗口的局部编辑；
- scene_causality_failure：从因果状态重新实现场景；
- voice_contamination：冻结有效事实，在隐藏旧稿的情况下 fresh surface realization；
- mixed：按场景拆分后分别使用适用路由。

Core 只验证枚举、证据绑定和允许的上下文投影，不选择文学路由。系统性声线污染、解释性旁白、人物同质化或语言污染不得默认最小改动。

Repair 解释属于审计证据，不能进入 Writer。

## 08 · 作者目标绑定审稿

最终 self-audit 与独立审稿必须收到当前作者目标 envelope。每个适用目标返回：

- met、not_met 或 uncertain；
- 候选正文中的精确证据；
- 影响范围；
- local_edit、scene_realization 或 fresh_realization 建议。

自然语言使用、解释性旁白、人物特定选择、关系特定对话、现场产生的幽默与连续性，在适用时是默认审稿维度。

任何硬目标 not_met 都阻止 user-visible readiness，不能被总体流畅、完整、情节清楚、平均分或其他目标抵消。uncertain 必须可见，不能静默转成 met。

模型审稿只是证据，不是文学真值。作者对当前作品的明确反馈拥有更高语义优先级。A/B 隐藏模型身份、交换顺序、优先不同模型族；顺序冲突标 uncertain，最终成功需要作者盲评。

## 09 · 小说能力模型路由

Writer profile 必须要求 fiction_writing 能力，并在阶段回执中冻结 service、模型版本、route/profile 指纹和 request identity。

通用推理排名不能证明小说能力。正式启用前必须由作者批准一个小规模同场景 audition。所有候选失败时，runtime 报告模型能力边界，不自动增加 humanizer 或 Prompt 层。

## 10 · 预算与完成语义

每个模型 job 分离：

- model_context_limit；
- max_output_tokens；
- run_cost_budget。

所有已知限制都在派发前检查。有效完成的响应必须原子写入，即使请求在途期间实际耗时、token 或成本越过软运行预算，也仍然有效。越界可阻止下一次派发，但不能把已完成结果改写成 budget_exhausted_after_response。

## 11 · 通用 checkpoint 与事件驱动 coordinator

每个语义节点 checkpoint 绑定：

- 输入与输出指纹；
- Prompt 与语义合同版本；
- 上游依赖指纹；
- 模型请求身份与模型／版本指纹；
- 验证回执；
- usage 与 billing 回执；
- 不可变 Framework build fingerprint。

Provider 完成后必须原子确认结果并为该 run 入队一个 coordinator wake。Coordinator 验证当前节点后立即派发 ready 后继。HTTP 等待超时只能产生 durable pending，不能杀死 keyed worker，也不能授权重复请求。

Coordinator 重启后必须接管 durable wake 和 ready node，不得重派 confirmed 或 pending 请求。build fingerprint 不一致时 fail closed，只有新 build 通过回归并获得显式 checkpoint-resume 授权后才能继续。

## 12 · 性能目标

- 串行总耗时不超过实际 model time 总和加三分钟。
- 并行总耗时不超过 model critical path 加三分钟。
- ready 节点间无原因空档不超过十秒。
- coordinator 重启后三十秒内自动续跑。
- 无需人工轮询，不重复派发、计费或丢弃 confirmed node。

调用数可通过直接 Surface Writer、合并上下文选择、并行独立审查和 checkpoint 复用降低，不得为省调用删掉必要语义证据。

## 13 · 确定性禁止项

任何生产质量决策、重试、修订范围或发布门都不得依赖：

- 英文字符或单词计数；
- 禁词或 “AI 高频词” 表；
- 句长、段长、对白比例或词性计数；
- 比喻、形容词、感官、打断、笑点或钩子数量；
- AIGC 检测分数；
- 正则或词频产生的 human-likeness 分数；
- 能覆盖失败作者硬目标的平均分。

可选 telemetry 只能位于生产决策路径之外，并明确标作非权威。

DRAFT 与 REVISE 可生成结构化数据、证据和模型请求；不得为语义质量工作生成一次性 Python、PowerShell、Shell 或其他程序。

## 14 · 兼容与回滚

Quillframe 1.0 采用干净调用图切换：没有 legacy Raw Draft adapter 或双派发路径。Project open 只能原子执行 Core 自有、按顺序的 known-prefix schema migration，不得语义改写 run state。历史 run 继续按冻结 build 与合同版本作为不可变证据读取；要在新 build 下恢复，必须经过 typed checkpoint/build-migration 路径、完成计费对账、绑定已持久化的精确离线回归收据，并获得显式迁移授权。

回滚会禁止新合同版本注册，同时保留所有声线资产、来源回执、checkpoint、模型结果和审稿证据；绝不恢复 Raw Draft 生成，也不让被否决正文重新合格。

## 15 · 验收

工程验收需要确定性测试证明上下文排除、权利／指纹绑定、直接 Writer、修订路由隔离、作者目标合取门、预算返回后保留、wake／幂等恢复、build 绑定和生产中不生成质量脚本。

文学验收必须等作者批准并盲评另行授权的中文 canary。代码完成、模型 PASS、置信度或英文数量下降都不等于文学成功。
