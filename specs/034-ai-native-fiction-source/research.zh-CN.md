# AI 原生小说生成源头研究

2026-08-31 · SYSTEM-IMPROVE 研究记录 · 一手论文与官方机制文档核查至 2026-08-31 · 未运行真实小说生成。

现有证据不支持“靠 Prompt 在数学意义上永远消灭 AI 腔”的承诺。它支持一个更窄、也更可验证的工程判断：指令微调模型存在稳定的默认表达，而流水线若先生成解释充分的完整正文，再把被否决正文与规划解释放到近生成上下文中让另一个模型润色，就会主动放大这种默认表达。Quillframe 应停止制造这条失败路径，让作者目标贯穿 Writer 与审稿图；若作者 canary 仍失败，则诚实报告模型能力边界。

## 01 · 证据边界

本研究优先采用同行评审论文、论文集页面、官方文档和官方仓库。产品文档只用于确认产品机制，不作为文学质量实验。预印本仅标作前沿证据。流行结构工具只作为可选规划视角，不作为普遍章节公式。

每项来源只作三种实施决策：

- 采用：机制与 Quillframe 的权限、证据边界一致。
- 改造：保留有用机制，但改变范围或表达。
- 拒绝：不进入生产质量路径。

## 02 · 模型默认文风与能力边界

PNAS 论文 “Do LLMs write like humans?” 发现，指令模型即使在非正式提示下，仍倾向信息密集、名词偏多的稳定表达。这支持把默认声线视为模型与流水线问题，而非禁词问题；它并不证明所有模型或所有中文小说样本完全相同。

Fiction-Writing Mode 在其评测范围内显示，专项训练可提高人类对创意写作的偏好。这支持小说能力路由与受控 audition，但不能证明存在一个普遍最优的中文网文模型。

决策：

- 采用 fiction_writing 能力要求、精确模型／版本指纹和作者盲选。
- 把文风指导改造成靠近生成端、简短、正向、贴近当前场景的指令。
- 拒绝“一个 Prompt 保证 0 AI 腔”的说法。
- 所有授权 audition 均失败时停止叠 Prompt，报告能力边界，并把专项模型或训练留给另行授权。

## 03 · 先有人物行动，再有正文

ConPer 在表层生成前把人格信息转成人物中心事件。Character-centric generation 与 Psychological Depth 也支持把人物目标、信念和关系建成因果状态，而非装饰性形容词。

决策：

- 采用私有 Character Enactment：信念、误判、欲望、害怕失去的事、对他人的预期、两到三个可行策略、得失、最终行动和关系特定的互动方式。
- 私有推演不得整包进入 Writer。Writer 只看已经选择的行动、可观察限制与后果，不看心理解释文章。
- 拒绝把人物标签当作充分计划，也拒绝确定性的“人物独特性分数”。

## 04 · 有层级的因果规划，不做正文模板

DOC 与 DOME 支持渐进、分层的大纲细化与长程记忆。Snowflake 明确采用迭代扩展，并说明作者应舍弃不适合自己的方法。Story Grid 可提供选择、复杂化与后果视角。这些来源都没有证明普遍有效的每章节拍配额。

决策：

- 把这些方法改造成 Scene Realization Contract：开场选择、人物行动策略、反制、消失的选项或上升的代价、事实结果、信息差、具体阻力和场景末的新限制。
- 分离因果内容与正文形状。
- 拒绝强制十五节拍、五诫命、反转、钩子、感官、笑点或张力峰数量。

## 05 · 最小上下文与近生成端指导

Novelcrafter 说明有序 Codex 上下文和写作样本；Sudowrite 说明 Style 会直接影响正文，并按当前提及内容选择 Story Bible；NovelAI 区分长期 Memory 与靠近生成端的 Author’s Note，并按条件激活 Lorebook；SillyTavern 说明示例对话、动态 World Info 和靠后的 Prompt 指令。

这些是产品机制说明，不是对照质量研究。它们共同证明：选择性上下文、示范和近生成端指令是常见的可控机制。

决策：

- 改造出由模型从 Core 预验证库存中选择最小充分材料的 Context Composer。
- 允许两到四个用户自有或明确授权、带来源权利版本指纹并由作者确认的正面锚点。
- 只允许 accepted 或 author-approved 的近文 tail。
- fresh realization 禁止被否决正文、Reviewer 分析、Repair 解释、人物私有推演、不相关 Lore 和 POV 不知道的未来事实。
- 输入重合时，把场景投影、上下文选择和 Director Note 合并为一次语义调用。
- 拒绝自动 top-k 原文 RAG 与在世作者模仿。

## 06 · 审稿证据与 Judge 偏差

G-Eval 明确指出 LLM 评审可能偏爱 LLM 生成文本。Personalized evaluation 说明评估可以绑定用户偏好，而不是泛化的总分。两者都不能把模型 Judge 变成文学真值。

决策：

- 采用逐作者目标判断：met、not_met 或 uncertain，并给出正文精确证据、影响范围和修订路由。
- 当前硬目标使用合取门：not_met 不能被流畅、完整或总分平均掉。
- 模型审稿只产证据；作者对当前作品的明确反馈拥有更高语义优先级。
- A/B 时隐藏模型身份、交换顺序、优先不同模型族；顺序冲突标 uncertain。
- 拒绝把一个总体 PASS 当作作者目标已满足的充分证据。

## 07 · 外部实现调研

调研的开源仓库含有可取的编排机制，也包含不符合 Quillframe 边界的做法。

| 来源 | 采用或改造 | 拒绝 |
| --- | --- | --- |
| Oh Story | 分开规划、写作与审稿责任 | 禁词和 AIGC 式质量门 |
| Chinese Novelist Skill | 明确阶段与作者 checkpoint | 固定钩子、节奏和公式承诺 |
| AI Novel Writer | 人工编辑对比与阶段来源 | 把流程完成误写成文学成功 |
| Novel Studio | POV 范围状态、封闭章节合同、租约与 checkpoint | 把 AIGC 指标当文学 guard |
| 番茄创作课程 | 把平台语境作为可选证据 | 把平台建议普遍化成 Framework 配额 |

发现仓库不等于获得摄取、依赖或 Framework 写入授权。

## 08 · 失败证据与过度推断审计

冻结的失败修订能证明以下流水线事实，同时不把坏稿用作正面样本：

- 作者目标进入了 Repair Editor 和 Surface Writer；
- Surface Writer 同时看到完整旧稿、Repair 解释、重复计划和大量规划上下文；
- 路由选择了保守表层修补，而非 fresh realization；
- 后续 self-audit 与独立审稿没有拿到当前作者目标；
- 一份已经返回的 Writer 结果被事后 token 预算检查作废；
- coordinator 活跃时，模型阶段间几乎没有空档；主要墙钟空档在模型执行之外。

证据不能证明英文计数器或 prose telemetry 决定了本次发布。失败审计当时，该 telemetry 模块只是可选工具且生产 runtime 没有 import；后续 AI-native 收口已把它从 Framework 完全删除。曾有 run-specific helper scripts，但文件内容已不可得，不能把其中是否含文学计数器写成已证事实。

拒绝的过度推断：

- 用英文字符变少证明中文自然；
- 用任何确定性测试充当文学裁判；
- 在事件没有记录时虚构精确 database_ms 或 validation_ms；
- 把 Reviewer 置信度当作者接受；
- 把英文或短篇研究的效果量直接保证到中文网文。

## 09 · 工程假设

Quillframe 可以用紧凑因果场景合同、经验证的作者声线资产和模型选择的相关上下文，直接生成 Surface Writer 正文，从而移除一条已知的系统性污染源。它可以让作者目标贯穿所有适用 Reviewer，把系统性污染路由到 fresh realization，并让已返回的有效结果不受软预算事后作废。

这仍是工程假设。只有经过用户授权和付费的中文 canary 获得作者盲评认可，才能证明文学效果。本次改造不运行该 canary。

## 10 · 一手与官方来源

- PNAS “Do LLMs write like humans?”：https://doi.org/10.1073/pnas.2422455122
- ConPer：https://aclanthology.org/2022.naacl-main.245/
- DOC：https://aclanthology.org/2023.acl-long.190/
- DOME：https://aclanthology.org/2025.naacl-long.63/
- Character-centric generation：https://aclanthology.org/2025.findings-acl.82/
- Psychological Depth：https://aclanthology.org/2024.emnlp-main.953/
- Fiction-Writing Mode：https://aclanthology.org/2023.eacl-main.128/
- G-Eval：https://aclanthology.org/2023.emnlp-main.153/
- Personalized evaluation：https://aclanthology.org/2024.emnlp-main.737/
- 中文网文结构同质化预印本：https://arxiv.org/abs/2603.14430
- Snowflake Method：https://www.advancedfictionwriting.com/articles/snowflake-method/
- Story Grid 101：https://store.storygrid.com/wp-content/uploads/sites/3/2020/07/STORY-GRID-101-Print.pdf
- Novelcrafter 上下文与写作样本：https://www.novelcrafter.com/help/faq/ai-and-prompting/codex-context-in-prompting 与 https://www.novelcrafter.com/help/faq/write/writing-samples
- NovelAI Memory、Author’s Note 与 Lorebook：https://docs.novelai.net/en/text/editor/storysettings/ 与 https://docs.novelai.net/en/text/lorebook/
- SillyTavern Prompt 与 World Info：https://docs.sillytavern.app/usage/prompts/ 与 https://docs.sillytavern.app/usage/core-concepts/worldinfo/
