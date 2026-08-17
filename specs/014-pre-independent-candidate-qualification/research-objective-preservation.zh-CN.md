# 修复过程中的目标保持 · Research Synthesis

日期：2026-08-17  
模式：`SYSTEM-IMPROVE`  
范围：pre-independent candidate qualification / repair loop

本文严格区分 **已有实证支持**、**工程推断** 与 **NovelForge 专用设计选择**。下列研究都没有直接证明某一种小说写作架构。

## Research matrix

| 来源 | 状态 | 现象 / 领域 | 证据强度 | 与本次改进相关的结果 | 局限 | NovelForge 适用性 | 决策 |
|---|---|---|---|---|---|---|---|
| Qi et al., *On the Paradoxical Interference between Instruction-Following and Task Solving*（arXiv:2601.22047，2026） | preprint | 数学、多跳问答、代码；加入本来就已满足的额外约束 | 中等；较新的多模型实证，未同行评审 | 即使额外约束本来已经被成功输出满足，加入约束仍可能降低底层任务表现；失败样本对约束文本分配更多 attention | 非创作任务；attention 结果不能直接证明小说修复中的因果机制 | 直接警告：constraint compliance 不能替代 task objective | **ADOPT principle**，不照搬架构 |
| Harada et al., *When Instructions Multiply*（Findings EMNLP 2025，DOI 10.18653/v1/2025.findings-emnlp.896） | peer reviewed | 多指令文本/代码生成，10 个 LLM | 对 instruction-count interference 证据较强 | 同时指令数量增加时，整体执行能力持续下降 | benchmark 约束比小说目标更容易客观测量 | 支持 sparse repair packet，而不是累积所有规则 | **ADOPT** |
| Zeng et al., *Order Matters*（Findings ACL 2025，DOI 10.18653/v1/2025.findings-acl.646） | peer reviewed | multi-constraint instruction 的 position bias | 对顺序敏感性证据较强 | 改变约束顺序会显著改变表现；研究场景中 hard-to-easy 顺序更好 | 不能据此推出一个通用 prompt 排序公式 | 支持避免 repair history 的偶然顺序暗中改写优先级 | **ADAPT** |
| Robinette et al., *We Are What We Repeatedly Do*（Findings EACL 2026，DOI 10.18653/v1/2026.findings-eacl.254） | peer reviewed | multi-turn long-context instruction following | 较强 | 长上下文会降低 instruction adherence；六种 mitigation 在研究模型上最高改善 79% | 重点是可验证指令，不是 Story quality | 支持 re-anchor / compact-state 实验 | **ADAPT** |
| Singh et al., *MT-OSC*（Findings ACL 2026，DOI 10.18653/v1/2026.findings-acl.1354） | peer reviewed | 13 个 LLM 的多轮对话 condensation | 较强 | one-off sequential condensation 在 10-turn 对话中最多减少 72% token，并改善或保持 accuracy | 不良 condensation 可能丢失创作细节 | 支持 compact current-state reconstruction，而不是无限 append | **ADAPT** |
| Shen et al., *ACR: Adaptive Context Refactoring*（Findings ACL 2026，DOI 10.18653/v1/2026.findings-acl.155） | peer reviewed | multi-turn contextual inertia / state drift | 较强 | 动态 context refactoring 在其任务上优于 baselines，并减少 token | refactoring operators 未直接测试小说生产 | 支持在 drift/inertia 出现时由语义层选择 context reconstruction，而非固定轮数 reset | **ADAPT** |
| Chen et al., *Breaking Contextual Inertia*（Findings ACL 2026，DOI 10.18653/v1/2026.findings-acl.313） | peer reviewed | multi-turn update 与 prior-reasoning inertia | 较强 | 模型可能继续黏着旧 reasoning traces；single-turn anchors 提高研究场景稳定性 | 训练方法不能直接等价成 prompt-time repair 方法 | 支持 clean current-state anchor，不继承失败轨迹 | **ADAPT** |
| Menon et al., *Inherited Goal Drift*（arXiv:2603.03258，2026） | preprint | 股票交易 agent trajectory；初步 ER triage | 中等；较新但未同行评审 | 强模型在看到弱模型预填轨迹后也可能继承 goal drift；hierarchy-following 能力不能可靠预测 drift resistance | agentic 环境与小说创作不同 | 支持把 prior trajectory 视为可能改变行为的 context，而非无害历史 | **ADAPT cautiously** |
| Du et al., *Context Length Alone Hurts LLM Performance Despite Perfect Retrieval*（arXiv:2510.05381，2025） | preprint | 数学、QA、code，在 relevant evidence 可获得时扩展 context | 中等 | 即使 retrieval 完美，更长 context 仍可能降低任务表现 | preprint；非多轮小说任务 | 支持把 context minimization 当作质量保护手段之一 | **ADAPT cautiously** |
| Stechly, Valmeekam & Kambhampati, *On the self-verification limitations of LLMs on reasoning and planning tasks*（ICLR 2025） | peer reviewed | reasoning / planning self-verification | 对测试领域较强 | self-verification 经常不可靠 | 非 prose evaluation | manager self-audit 负责前置过滤，但不能替代 independent review | **ADOPT boundary** |
| Critic-CoT（Findings ACL 2025）与 Table-Critic（ACL 2025） | peer reviewed | reasoning / table 任务中的 iterative critique/refinement | 重要反证 | 某些领域的迭代 critique 能提高结果 | 强烈依赖领域与机制 | 拒绝“iterative repair 天然会退化”的全局结论 | **REJECT blanket anti-refinement** |
| *Monotonic Reference-Free Refinement for Autoformalization*（arXiv:2601.23166，2026） | preprint | formalization 的多维 preservation + improvement | 中等、间接 | 在可验证形式化领域展示了 preservation + improvement acceptance | 小说没有 theorem-prover 式 objective ordering | 只借鉴“修目标同时保护其他维度”的概念，不声称文学质量可严格单调 | **ADAPT concept; reject strict monotonic claim** |
| Anthropic 官方 context engineering / long-running harness guidance（2025–2026） | 官方工程资料，非同行评审 | context pollution、compaction、structured handoff | 工程经验 | 长时运行系统受益于 compact / structured current state；separate evaluation 仍有价值 | 不是受控小说研究 | 用于 implementation detail 和 failure recovery | **ADAPT** |

## EMPIRICALLY SUPPORTED

1. 同时指令 / 约束增加，可能降低 instruction compliance 或 underlying task performance。
2. constraint 的 placement / ordering 会实质影响结果。
3. multi-turn 与 long-context 交互可能降低 instruction adherence 和任务准确度。
4. condensation、context refactoring、re-anchoring 在已研究领域中可以缓解部分 long-context / multi-turn failure。
5. prior trajectory 可以造成 contextual inertia；最新 preprint 还给出了 inherited goal drift 的证据。
6. self-evaluation 不能可靠替代独立验证。
7. iterative critique 并非天然有害：已有多个同行评审系统显示某些领域可以从 critique/refinement 获益，因此 Framework 应检测 regression，而不是禁止 refinement。

## PLAUSIBLE ENGINEERING INFERENCE

1. Repair loop 若不断 append negative findings，可能让局部约束相对原始 creative task 获得越来越高的 salience。
2. Rejected prose 与长 critique history 即使对 Auditor / Editor 有价值，也可能污染 fresh realization Writer 的 context。
3. 出现 contextual inertia、objective regression 或 oscillation 时，重建紧凑 current state 很可能比无限累积 repair history 更安全。

这些都是从邻近任务研究推导出的工程假设，不声称已经被小说写作实验直接证明。

## NOVELFORGE-SPECIFIC DESIGN CHOICE

1. 引入紧凑、fingerprint-bound 的 **objective envelope**，由 manager/model 从 current authorized request / plan / profile / state evidence 中语义选择；runtime 只验证 provenance / fingerprint。
2. Surface / AI-realization rules 继续约束 valid solution space，但不成为 objective function。
3. 升级已有 `quality.compare`，而不是再建一个平行 comparator；repair outcome 分为 `target_not_fixed`、`objective_regression`、`successful_repair`、`inconclusive`，并分开记录 target 与 preservation axes。
4. Material repaired candidate 在 pre-independent qualification 前必须带有 repair-preservation evidence。
5. 保留 incumbent protection：修掉 target 却实质损伤 Story / Reader objective 的 challenger 不得通过矛盾 typed result 自动成为 incumbent。
6. `editor.repair_spec` 从偏重 FIX 改为 **FIX + PRESERVE**；fresh realization 只得到 reconstructed current state + objective envelope + minimal repair packet，不继承 rejected realization 与累积 critique history。
7. 不使用 universal weighted score、lexical ban、固定 constraint-count cap 或固定 repair-cycle reset threshold。
8. Context reset/refactor 是否需要由 semantic evidence（contextual inertia、objective regression、oscillation 等）决定；deterministic runtime 只执行被选择的信息边界。

## 为什么不采用严格“monotonic literary quality”

Repair target 可以要求狭义上的 improvement，但小说质量不是一个可以由 runtime 验证的单一标量。NovelForge 因此采用：

**target improvement + blocking semantic non-regression of the current objective envelope**

而不是宣称整个文学质量函数数学意义上单调。
