# Quillframe Skill Contract · 中文版

<p><kbd>TIER C · 框架契约</kbd>&nbsp;&nbsp;<kbd>AI-NATIVE</kbd>&nbsp;&nbsp;<kbd>CONTRACT-FIRST</kbd></p>

Quillframe 是一个与具体项目解耦的小说生产框架。它提供通用的故事、人物、Canon、质量、运行时、学习、Corpus、评测与项目工程机制；下游 Project 提供某一部作品的具体事实。

> **核心边界 ✦** 需要理解文本、人物、读者体验和创作机制的语义判断由模型负责；确定性代码负责 authority、权限、指纹、持久化、路由、硬预算、阶段隔离、类型校验、事务与可复现性。两边都不得静默越权代替另一边。

Quillframe 内不得内置任何具体小说、人物、剧情、Canon 或用户私有偏好数据。

## 01 · 从权威状态启动，不从记忆启动

任何 Quillframe 任务都按以下顺序开始：

1. 读取 `HARNESS_MANIFEST.yaml`；
2. 读取本 Skill 契约、`harness/HARNESS_AGENT.md` 及适用语言版本；
3. 通过唯一的 native 1.0 Project contract 解析下游 Project；
4. 确定且只确定一个 primary `task_mode`；
5. 创建或恢复 manager session 与当前 run；
6. 从 Project 当前权威状态构建稀疏 Context Manifest；
7. 外部工具或服务执行前，先解析当前 host capability；
8. 只加载当前语义问题真正需要的 semantic contract pack；
9. 外部等待和 consequential write 前 checkpoint；
10. 只有通过当前 user-visible gate 与 authority gate 的产物才可展示或持久化。

禁止使用旧聊天记忆、provider session history、历史 embedded Framework copy 或未锁定的 Framework checkout 替代当前 authority。

## 02 · 恰好一个 task mode

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

一次用户可见 run 只有一个主模式。用户明确指定的模式优先。内部可以调用受限子流程，但不得静默变成另一个用户可见任务。

## 03 · Project authority 与 Canon

通用 Framework 机制与具体 Project 事实必须分开。

默认生命周期区分为：

`locked > accepted > active_plan > review > proposal`

下游 Project 可以进一步定义 precedence，但绝不能把 plan/review 合并成 Accepted Canon。

以下内容**本身都不是 Canon**：

- session 或 checkpoint 状态；
- 模型记忆或 derived memory；
- Context overlay；
- Scene Card 与 plan；
- Review Draft；
- semantic judgment；
- reader diagnostic；
- scenario branch；
- Corpus 或 research evidence；
- learning hypothesis；
- CI / eval 结果。

只有 Project 的明确接受，再经过该 Project 的 settlement transaction，才能改变 Canon / current state。

## 04 · AI-native semantic contract

当前开发架构使用**按需渐进加载的 semantic contract packs**。

Catalog：

`harness/semantic_workers/model_contract_catalog.json`

Contract packs：

`harness/semantic_workers/contracts/`

确定性 semantic router 只负责：解析 exact contract ID、封装 bounded input / permissions / rubric / typed output contract、计算 semantic fingerprint、校验返回结构与 provenance，以及支持 consume-once。它**不负责文学判断**。

不要恢复或重新发明一个巨大的 `model_contracts.json` 兼容总表。Catalog 是唯一 registry index；具体 pack 按当前任务渐进加载。

典型 semantic work 包括：

- 故事、场景、人物模拟；
- 读者反应与 A/B 成对比较；
- 人物完整性与 revision diagnosis；
- narrative-world 与 reader-expectation 解释；
- memory consolidation；
- Corpus discovery strategy 与 mechanism analysis；
- learning / eval judgment；
- creative-evolution comparison。

模型结果只是受边界约束的证据。它本身永远不会授予 Canon write、Framework promotion 或 durable user-taste write authority。

## 05 · DRAFT / REVISE 质量图

需要读取：

- `core/STORY_SYSTEM.zh-CN.md`
- `core/CHARACTER_SYSTEM.zh-CN.md`
- `core/CANON_STATE.zh-CN.md`
- `surface/FUNDAMENTALS.zh-CN.md`
- `surface/READER_ENGAGEMENT.zh-CN.md`
- 下游 Project 当前选中的 profiles

通用生产图：

`Context Freeze → Story/Canon Preflight → 人物私有行动推演 → Scene Resolution → Scene Realization Contract + 模型组合的 Writer Pack → Reader Pressure → direct Surface Writer → 冻结候选指纹 → Reader Engagement → Continuity → 逐项目标自检与资格门 → 必要时回 owning layer 修订/比较 → 独立评审 → User-visible Gate`

被否决正文、Reviewer 分析、人物私有推演与 hidden expected label 不得进入 fresh Writer pack。局部修订只能收到精确指纹绑定的编辑窗口。确定性检查只验证 schema、provenance 与边界；文学判断仍属于模型和作者。

**Production visibility 必须 fail closed。** 在 `DRAFT` / `REVISE` 中，读过这些合同不等于执行了 Quillframe。Host 必须调用经过验证的 Quillframe production runtime，且只有 exact fingerprint-bound production release 才能提供用户可见 manuscript。若 runtime、模型执行、required independent review 或 release evidence 不可用，必须返回 typed pending/blocked 状态，禁止用 host 自己写的正文补齐缺失机制。Ephemeral agent sandbox 可以 materialize deterministic Framework bundle，但执行前必须验证 exact commit/bundle fingerprint；其中的 SQLite 只是 runtime materialization，不是第二套 Canon authority。

失败必须回到真正拥有该问题的机制：

- 单点 Surface 缺陷 → local rewrite；
- Surface cluster → 重新生成 scene / realization；
- SAFE-BUT-FLAT 或 reader-grip 失败 → Reader Pressure + Scene Simulation；
- 人物失败 → Character Simulation；
- Story / Plan 失败 → Story / Plan；
- continuity / state 失败 → state / transition repair；
- Context / Memory 失败 → Context / Memory layer。

不要拿句子润色去掩盖上游机制失败。

## 06 · Context 与 Memory

持久存储不等于自动注入 prompt。

Quillframe 必须区分 Project 当前 authority、derived memory、runtime state 与模型推断。Context/Memory 工具可以对 derived/context view 做预算、pin、排序、invalidate 或 rebuild，但不能静默改写受保护 Canon。

`locked` / `accepted` reference 必须保持受保护状态。编辑受保护 memory reference 时，应产生 proposal 或其他明确非权威的 artifact，而不是覆盖故事事实。

需要语义判断时，relevance 属于模型。确定性 Context/Memory 代码可以执行 hard budget、authority class、provenance、lifecycle constraint 与显式用户控制，但不能拿任意 scalar heuristic 冒充文学相关性。

## 07 · Runtime、Session 与 Capability

必须区分：

`project/resource ≠ session/thread ≠ run/invocation ≠ checkpoint`

当前 chat 可以作为 manager。独立 peer chat、本地 Codex / Claude invocation、provider call、MCP/service worker、GitHub job、local model 或 human，都可以在当前 capability evidence 支持时成为受限 worker。

Runtime 名称本身不是 capability proof。必须从当前 host manifest 解析能力；未声明能力视为不可用。

Capability 回答“技术上能不能尝试”；authority 回答“允许不允许改变 durable state”。两者不可混淆。

Mandatory independent semantic judgment 必须来自真正不同的 invocation/session，并返回 fingerprint-bound typed result。同 session 角色扮演不算独立审查。有效 `semantic_reject` 是判断结果，不是基础设施故障；禁止 reviewer-shopping。

## 08 · Corpus 与 Adaptive Learning

Corpus 是受治理的 evidence，不是 Canon，也不是模仿作者的剪贴簿。

User / authorized human 对既有产物或工作方式给出的有意义反馈，在任何 primary mode 中都自动具备 bounded Learning intake 资格：`feedback.observed → semantic capture|skip → 最窄 scope evidence/candidate`。当前显式指令立即生效；automatic intake **不会**自动改 Project Profile、激活 durable user taste、promote General Craft、修改 Framework behavior 或写 Canon。LEARN 仍用于更深的 learning/corpus/eval/promotion 工作。

Discovery、access、rights classification、storage、semantic analysis、learning 与 promotion 是不同 gate。能搜索到内容，不等于可以保存全文。现代版权作品不得被默认完整镜像到 Generic Framework，也不应整体灌入 Writer context。

Learning 永远采用证据支持的最窄 scope：

`one_off | project | user_taste | general_craft`

仅靠模型推断不能成为 durable user taste 或 General Craft。General Craft promotion 需要 provenance、跨作品或其他足够证据、counterexample / profile boundary、eval/regression evidence、版本/rollback，以及 green deterministic CI。

## 09 · Project Engineering

下游 Project 应当能够独立 clone、自描述、测试、构建、按 native contract 验证并 rollback，而不依赖聊天记忆。

项目身份至少由以下内容锚定：

- `quillframe.toml` 且只含四个原生键（`schema`、`id`、`title`、`language`），以及顶层含 `scope: "novel"` 的上下文、manifest fingerprint 与 `.quillframe/data`；
- 清晰的 source / plan / derived / generated 边界；
- deterministic validation / build / tests；
- 配置后可验证、可复现的 Framework bundle。

`CH001` 和 `DOC-CH001` 只是初始章节与正文文档，不代表整部小说的范围。后续章节引用必须指向项目中真实存在的章节。多出的 `chapter_scope` manifest 键或不兼容的开发状态会被拒绝，打开时不会自动迁移、修复或补建数据。

结构级变更在确有必要时使用：

`spec → plan → tasks → implementation → verification → acceptance`

普通正文 micro edit 不要人为制造软件工程仪式。

## 10 · Writes 与 Settlement

任何 consequential write 都要求 least privilege、exact target、before-state / precondition、idempotency strategy、post-condition，以及必要的 trace / rollback。

Canon settlement 还必须具备：明确 Accepted artifact 或显式 Canon 指令、exact State Delta、dependency impact、authorized mutation、derived-view refresh 与 post-condition validation。

before-state mismatch 或 post-condition failure → `settlement_incomplete`。不得猜测，也不得把部分成功说成全部完成。

## 11 · CI 与 Maintenance

Normal CI 必须保持 deterministic，不得静默消耗 API、Codex、Claude 或其他 model usage。

CI 应验证 schema、lifecycle boundary、semantic contract catalog/packs、hidden-gold isolation、fingerprint、permissions、Context/Memory authority、session/control-plane invariant、Corpus rights/provenance、eval queue、native Project manifest/context/fingerprint/novel/data-boundary contract 与真实章节关系、Framework bundle reproducibility 与 documentation integrity。

Scheduled maintenance 可以观察、报告、封装和排队任务。schedule 或 webhook 本身不会授予 story、Canon、taste 或 Framework promotion authority。

## 12 · Completion truth

使用真实状态，例如：

`complete | review | awaiting_user | awaiting_external | semantic_pending | semantic_invalid | failed_gate | settlement_incomplete | blocked`

只要 mandatory gate 仍未解决，就不能把 artifact 称为 production-ready。

> Quillframe 的后台应越来越严格、可恢复、可验证；最终小说则应该越来越自然、有因果、有具体性、有意外，也更像活人写出来的故事。
