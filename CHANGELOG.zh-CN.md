# Quillframe 变更记录 · 中文版

## 尚未发布 · 1.0.0-dev.0 超长篇开书与生产收口

- 新增来源指纹绑定的 Book Setup 提案／作者批准生命周期。达到 500 万字符的项目必须同时提供固定终局、完整分卷剧情、跨卷弧、逐卷高潮、人物魅力节点、进阶阶梯、滚动规划与容量证明；人物、关系和世界资产在批准前不获得权威。
- 卷、单元和章节可以通过 Host Bridge 幂等创建；数据库保证每章只有一个正文文档。Setup 批准绑定精确的 active `DESIGN-BOOK` 计划，中断后只能恢复同一请求，并会如实报告部分完成状态。
- DRAFT／REVISE 恢复模型负责的语义 Context 选择、人物模拟与场景解析。已批准的人物／关系决策模型只进入私有前置阶段；Surface Writer 仅收到限长、指纹绑定且不含私有推理的 Director Note。只在释放前确定性校验组装后的全章最小篇幅，不设置正文最大篇幅或机械逐场配额。
- 叙事落定继续使用紧凑 typed delta，并只保留最近四份完整校验快照。生产释放、作者接受与结算在响应丢失后可按原幂等键返回同一收据；Studio 可恢复接受／结算状态，并能显式选择已启用、已发现目录中的生产模型。自动模式如实表示为 Core 的目录默认项。
- 新增 Project schema fragment 025。开发期 clean break 不迁移已有数据库；回退前停止运行时并恢复父提交 `638afcf24e6bfc27e26c4906186b2175f02b5bb1`，新增 025 Project 必须重新创建，不能由旧 Core 打开。
- 模型端点现在保留显式 `v1`／`v4`／`v4.1` API 基址，只在没有版本末段时补入默认 `v1`，避免发现模型或推理时静默改写 Provider 路径。OpenAI Chat 生产请求显式发送 `json_object` 响应格式，并使用标准 SSE 流式读取长推理结果；对官方文档明确只能开启 thinking 的 `glm-5.3`／`glm-5.3-flash`，固定发送 `reasoning_effort=low`，不再继承 Provider 的默认 `max`；Core 只组装 `delta.content`，不保存 `reasoning_content`，同时只允许单层外部 JSON fence、1–3 个纯尾部 fence 残片，或至多 1024 字节且不含第二个 JSON 值／非空白控制字符的 Provider 尾注作为确定性兼容包装；尾注不会进入类型化结果。Surface 响应若同时返回`raw_content` 与 `manuscript` 逐字相同或为空／null 时视为冗余别名；`answer` 除相同／空值外，只在正文至少 512 字节、单行状态说明不超过 256 字节且短于正文八分之一时作为 Provider envelope 元数据隔离，其他非空差异仍拒绝；若 Provider 对单字段正文返回纯原始文本，Core 可将无 JSON／fence 起始、无控制字符、无 JSON 转义残片且不超过 512 KiB 的精确字节确定性封装为 `manuscript`，混合转义或残缺 JSON 仍拒绝；`chapter_id`／`scene_id` 也只有在与冻结目标精确相等时才作为冗余 echo 移除；至多 8 个顶层字段、2 KiB 且内部深度与字符串受限的 Provider 元数据会被隔离且不参与权威。正文别名或身份不同、元数据越界时继续拒绝。逐场长度目标已经移除，硬门只在组装后的整章执行，避免机械平均破坏场景节奏。Tracking 若把 `character_snapshot_updates` 返回为人物 ID 列表，Core 只从同一结果中精确匹配的 character state delta 机械投影快照；缺少对应状态或 ID 重复时仍拒绝，不进行语义补写。生产模型调用统一使用文档声明的 180 秒截止时间；人物模拟的结构化输出上限收紧到 3000 tokens，并要求 action／scene 字符串中的引语改为无引号转述，避免 Provider 把未转义双引号写进 JSON；人物行动若额外返回空 `action_note`，Core 将其作为无语义冗余字段隔离，非空值或其他未知字段仍拒绝；场景解析与逐场正文至少保留 8000 tokens，以免 Provider 的推理 token 挤占类型化结果或正文造成截断。Corpus 或偏好候选集合为空时，Core 直接冻结可验证的空选择收据，不再为不存在的候选消耗语义调用；候选非空时仍由模型判断相关性。Context Query 也允许模型在计划与精确修订证据已经充分时返回零条 archive query，不再强迫局部修订伪造搜索需求。多轮有界修订追溯最初逐场证据时复用实时 Surface 标准化器，避免已接受的受限 Provider envelope 在 lineage 验证阶段被误拒绝。
- 修复真实连续章节 Canary 暴露的 Surface 规则接线缺口：新运行冻结 Framework 正向 Writer 指导、完整 `HF-01..HF-30`、登记语义 rubric 与从已批准行文来源经原生句柄物化或显式提交、并通过内容指纹验证的项目指导；Writer 只读正向投影，新增 Surface Auditor 必须以反证正文可释放为目标逐项返回 exact-evidence assessment，明确对身体信号、流程、议程对白、微动作、比喻和解释执行跨段 cluster 与删除测试，不能因每一处局部可辩护就放过整体重复；PASS 可不提供例证；若提供的 PASS 引用不是正文逐字片段，Core 只删除该无效引用而保留完整覆盖报告。FAIL 必须提供逐字证据；若判断完整但 FAIL 引用使用省略或非逐字转录，只允许一次证据字段修复，Core 会锁定全部身份、结论、规则状态、报告与修订范围，任何判断变化都拒绝；Provider 回显 `judgment_fingerprint` 时也必须与冻结值精确相等才会被隔离；修订诊断按语义机制及其受控 repair stage 前缀匹配精确结果指纹，避免 base stage 名与 evidence-repair receipt 指纹错绑。缺项、证据不足或确认失败均阻止 v2 release。Writer 不再重复接收完整计划锁／章节计划／独立场景 brief，也不再承担机械逐场最低篇幅；组装后不足全章最小篇幅会先冻结正文与确定性长度诊断，再进入可追踪的 `failed_gate`，不再把运行遗留在 `executing`；Blind Reader 不再接收 Reader Pressure。REVISE 合并而非替换来源规则；局部 repair target 若均为唯一逐字窗口但返回顺序与正文相反，Core 只按原文位置机械排序，重复／缺失窗口仍拒绝；`fresh_realization` 会把 Editor 返回的 incumbent excerpt（含 null）统一替换为非正文哨兵，Fresh Writer 不再接收被拒稿窗口；修订后全篇重新审计；Review 投影展示真实 gate 判定，不再因 receipt 存在就合成 PASS。旧 v1 release 仍可读取，但不能冒充具备新 Surface audit。
- 确定性门只证明契约、事务、隔离与恢复机制；第一次连续章节 Canary 的旧文学评分已撤回。修复后 Canary 已证明 CH002 的 HF-18／HF-25 cluster 会被真实门禁阻断，但 CH001 的内部 PASS 仍被作者侧复核推翻；因此单模型审稿召回率、真正独立的审稿证据和作者确认仍待完成。

## 尚未发布 · 网文 Corpus 分析架构 v2

- 当前 Corpus 调度契约从十个平铺文风轴改为六域、26 个叶级维度，覆盖读者契约、剧情推进、情绪回报、人物关系、场景实现和中文语言节奏。
- 新增封闭的 v2 观察、跨作品候选、source-free 机制目录、证据请求和一到四张 Writer 投影契约；原文锚点和来源身份继续禁止进入产物。
- 登记五个 v2 语义契约，并让五个 v1 文风轴契约退出当前调度。完成的 V5 只保留为历史证据，不能续跑或支撑 v2 晋升。
- v2 追加式运行器、公共 atlas、新候选和真实文学 A/B 仍待完成；本次结构改动不宣称质量已经提升。

## 尚未发布 · 1.0.0-dev.0 场景模拟的输出约束

- 人物行动与场景结算采用明确的原生 JSON 结构约束，只保留原契约的必填字段。问题与修复建议仍由模型判断，原语义契约和审查门不变。
- 可选的 `AgentJob.output_schema` 纳入请求指纹，并传递到 OpenAI Chat Completions / Responses 及 Codex CLI `--output-schema`。不支持时明确停止，不额外探测、不回退、不重试；当前 Anthropic 协议实现尚不支持此约束。
- CLI 账本保留精确结构文件、原始输出字节和校验结果。格式损坏、重复键、截断或拒答不能被记为已完成的受约束任务，也不会就地修补。
- 确定性测试覆盖传输、失败证据保留及未启用约束时的旧指纹稳定性；不宣称真实模型或整条生产链路已经验收。
- 仅为开发改动，未引入 Project 数据库迁移。回退前停止执行器，可恢复 `b43aaeeb7ab00baab8261f22f7731c59b7853f08`；保留证据，不在旧代码下恢复新增的受约束调用。

## 尚未发布 · 1.0.0-dev.0 内部候选稿修订

Studio 可从精确、私有的资格检查失败记录新建 `REVISE`。Core 冻结原稿和已确认的诊断，继承原任务目标及选定的作者偏好，执行已登记的编辑修复与保持方案和真实文本比较。独立审稿、作者接受和结算仍是各自独立的环节。

- 比较落败的修订稿不能成为下一轮基准。父级证据缺失或改变时，在调用模型前阻止继续。
- `quality.compare` 现在要求同时提供两稿的精确文本，其 CLI 也须指定文本文件。调用方须与契约包同步更新，指纹本身不构成语义比较证据。
- 确定性回归覆盖来源篡改、原请求继承、内部草稿隔离、比较失败、预算耗尽和执行中断。这些测试不能证明真实稿件已通过审查。
- 这是开发改动，不是已发布版本；未引入 Project 数据库迁移。回退前须停止执行器，可恢复父提交 `d3f1706ff90f8d68621644576a74f4830c8421fa`；保留运行证据，不在旧代码下恢复新增修订运行。

## 0.9.1 · 小说原生宿主边界

Quillframe v0.9.1 将产品边界收敛为小说契约内核：**宿主运行 Agent，Quillframe 管理小说**。Codex / Claude 原生评审 adapter 消费同一份 exact frozen packet；Project projection、受限 Context、candidate 可见性、独立评审以及 Acceptance / Settlement 仍由 Core 契约负责。

### 已包含

- Codex / Claude 原生评审生命周期 hook：可信的父子 session 隔离、评审工具拒绝、exact packet / nonce 绑定、lease fencing、一次性消费证据与崩溃恢复。
- 确定性的 mapped Project projection preview / apply / status / preflight：source fingerprint、事务 CAS、可重建 SQLite projection、按阶段受限的 Context 与零模型预检。
- 成对的 Novel-Native Host Boundary 文档，并明确 novelist-facing、internal/ops 与 privileged author 三类 surface。
- Framework、CLI、Project SDK、MCP metadata、Host Bridge、Studio、site 与 Tauri packaging 的 v0.9.1 版本身份统一。

### 已知限制

- 内置 Agent / Model Runtime 仍是 optional/reference implementation；通用 session、model/tool、sandbox 与 subagent 执行由宿主负责。
- Acceptance 与 Settlement 仍是作者明确控制的独立操作，不会成为普通 Agent authority。
- hosted multi-user、完整 Studio 重构、全量 benchmark corpus、插件生态、云部署和完整 typesetting 仍属于 v0.9.1 之后的 backlog。

### 发布证据

v0.9.1 必须绑定一个 exact main commit、确定性 Framework bundle fingerprint、CI 结果和可下载 checksum manifest。本地构建或等待评审的状态都不能冒充已发布 release。

## 0.8.0 · 当前 pre-1.0 开发基线

> `0.8.0` 是此前称作“8.0”架构开发线的当前统一版本身份。NovelForge 仍处于 1.0 之前的快速开发阶段：最新 `main` 才是工作实现基线，`0.8.0` **不代表已经冻结出 1.0 级兼容承诺**。

### 版本真相

- 当前 machine-facing version surface 已统一为 **0.8.0**：`HARNESS_MANIFEST.yaml`、`SKILL.md`、`novelforge.py`、Project SDK 默认值、对外 MCP server metadata，以及 documentation governance metadata。
- 这取代了之前“7.2 release metadata / 7.3 implementation metadata”并存的开发期编号。下面的 7.x 历史记录继续保持原始历史语义。
- pre-1.0 开发期间，只要架构确有必要，`main` 仍允许经过验证的 breaking machine-contract cleanup。稳定兼容承诺应来自未来主动冻结后的 release contract。
- 针对最新 `main` 重写的文档，只要 documentation manifest 没有明确晋升生命周期状态，就仍是 `candidate_review`；版本统一不会自动替代语义、母语或视觉审查。

### 已合并的开发变更

- 语义运行采用小型 model-contract catalog + 精确 contract pack 渐进加载。小说语义判断由模型负责；确定性代码负责权威、权限、指纹、持久化、路由、硬预算、类型校验、事务与可复现性。
- PR #11 将 live machine namespace 从 `NOVEL_OS_*` / `novel_os_*` / `.novel-os/` 迁到 `NOVELFORGE_*` / `novelforge_*` / `.novelforge/`，且不保留兼容别名。
- PR #12 加入任务感知的 question→evidence grounding，并在模型上下文组装前确定性执行 perspective / visibility 过滤。
- PR #13 加入 metadata-only 的 `novelforge_run_receipt_v1`，不保存候选正文、不获得 Canon authority，也不成为第二套状态数据库。
- PR #18 让 Framework bundle 真正 release-complete：包含 quality runtime，并在解包后运行 `novelforge.py doctor` 与完整 model-free self-test。
- PR #19 合并 Studio Phase 1：由 Run Receipt 驱动的只读 Run / Context Inspector。
- PR #21 合并 Studio Phase 2A：portable one-product/many-host contract、安全的 Project Hub projection、synthetic project/scene fixtures，以及只读 Project Hub + Scene workspace prototype。
- PR #25 合并 Studio Phase 2B：versioned read-only host bridge + standards-compatible NovelForge Agent Skill。Bridge 只暴露 allowlisted read surface（`bridge.describe`、`framework.doctor`、`project.inspect`、`capabilities.inspect`、`context.inspect`、`semantic.catalog`），不支持的 operation fail closed，默认不泄露 host-private absolute path，并始终保持 `authority=false`。
- PR #24 完成剩余 machine-contract rename：`os_behavior_write` → `framework_behavior_write`；semantic job/result ID 从 `novel-os-*` 迁到 `novelforge-*`；移除 live `.novel-os/` ignore surface；namespace hygiene 也会阻止这些旧 machine identifier 再次回归。没有添加兼容别名。
- PR #27 让 Context grounding 同时遵守故事时间顺序与逐问题 evidence eligibility：来自未来或不兼容的证据会 fail closed，包括被 pin 的 evidence；hard budget 丢失必需 support 时，grounding 会明确标记 incomplete，而不是装作依据充分。
- PR #28 把角色的 epistemic status 与 acquisition mode 分离，并要求 proposed character action 绑定当前故事时间点下、该角色真正可见的 evidence；future / unknown / invalid evidence 不能因为存在于 Framework state 中就被拿来当正面依据。
- PR #29 强化 long-horizon reconciliation：要求 story-ordered evidence、完整 requirement coverage，允许 uncertainty 作为合法 typed state 保留，并明确分开 shared relationship state 与各角色对这段关系的 individual perception。
- PR #31 加入 `novelforge_production_readiness_v1`：同一 candidate fingerprint 上的 deterministic conjunction gate，覆盖 Surface、Reader Engagement、所需 Continuity 与所需 independent semantic review。required gate 缺失、pending 或 fail 都会阻止 review-ready；`RG-15` SAFE-BUT-FLAT 不能通过 Reader Engagement；系统不会引入数值化 literary-score aggregation。
- PR #31 同时加入最小可用 deterministic Publication core：manifest 可发现的 `novelforge_publication_ir_v1`、`publication/compiler.py`、Accepted text 精确 fingerprint preservation，以及 `clean_text`、`web_reflow`、`print_book`、`epub3` 四个 build profile。Publication output 仍是 derived / non-Canon。EPUB 目标为 W3C EPUB 3.3；内部验证确定性执行，而 release conformance 必须额外提供外部 EPUBCheck command。
- PR #32 把 Story Loom 升级为 `novelforge_brand_tokens_v2`，并正式合并 WeiUI foundation contract。`assets/brand/weiui.integration.json` 把 `xiaooye/weiui` 精确固定到 commit `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`，只允许 `@weiui/tokens` + `@weiui/css`，明确禁止 `@weiui/react` / `@weiui/headless` 成为 Studio runtime dependency，并要求 WeiUI runtime JavaScript 为零。`assets/brand/story-loom.weiui.css` 提供 `wui-theme` Story Loom layer，同时禁止 fork WeiUI component selector。
- PR #32 还把 mobile / i18n / accessibility / runtime-overhead 约束变成 machine-checkable contract：mobile-first、44px minimum touch target、`en-US` + `zh-CN`、logical properties、reduced motion、no idle decorative animation、no default polling，以及 light/dark contrast checks 都由 `scripts/design_system_quality.py` + CI 确定性验证。
- Phase 2C 选定的 application framework 是 **SolidJS + TypeScript + Vite + `@solidjs/router`**，WeiUI 只作为 zero-JS CSS/token foundation。Local Web 保持 first-class，并因最小增量 runtime overhead 成为优先形态；Tauri 保留为 optional/installable desktop host，而不是产品架构中心。
- 0.8.0 normalization 让当前 machine/version identity 归一，不再同时维护“release version”和“implementation version”两套开发编号。
- Documentation governance 已确定性跟踪 audience、tier、authority source、freshness owner、rewrite policy、lifecycle、双语配对、本地链接、版本对齐与可检查的视觉/文档约束；`studio/` 已纳入 bilingual manifest coverage QA。

### 当前缺口与兼容说明

- Run Receipt 仍有 Core-owned consumer/read-surface 工作：稳定 manifest discoverability、`run.receipt_recorded` 的 event-schema 对齐，以及供 Studio 使用的稳定 query/projection boundary，而不是读取 persistence internals。PR #25 有意没有通过 Host Bridge 暴露不安全的 Control Plane / Run Receipt 读取。
- Publication core 已经真实存在，但 Issue #16 的更大范围仍未完成：更丰富的 semantic structure/profile contract、通过 paged-media engine 生成 print PDF、更完整 typesetting controls、visual-regression hooks，以及 Studio publication preview/authoring，都不能从当前最小 compiler 推定出来。
- Story Loom / WeiUI foundation integration 已经真实落地，但这些 token/CSS artifact 不等于 Phase 2C SolidJS application 已经完成。App-shell code、route implementation、host lifecycle 与实际 idle CPU/RAM measurement 仍需要独立实现证据。
- 已经有意锁定旧 Framework revision 的下游项目继续受那个 revision 约束，直到显式升级；Generic Framework 自身开发则跟随 latest `main`，不维护内部开发 lock。
- 未来真正稳定的 migration guide 必须从冻结后的 contracts 与最终 bundle 生成，不能根据 Issue 或中间开发提交猜最终接口。

### Product / Publication 状态

- Studio 当前已经合并**只读** Phase 1、Phase 2A、Phase 2B 产品切片：observability、Project Hub、Scene workspace、portable host boundary 与 Agent Skill delivery 都已经真实存在于 `main`。
- Story Loom v2 + exact-pinned zero-JS WeiUI CSS/token foundation 也已经真实存在于 `main`。这是 product-foundation implementation，不是完整 Studio app。
- Phase 2C 方向为 **SolidJS + TypeScript + Vite + `@solidjs/router`**；`@weiui/react` 明确不是 planned runtime dependency。Tauri 只保留 optional installable host，Local Web 继续是一等产品面。
- 这些 Studio 切片**不代表** Studio 已经成为可写、多人协作、带生产认证或正式云托管的完整应用。Generic invoke/write、project mutation、resume 与更广的 Control Plane read 仍不属于当前 bridge contract。
- Publication 现在已经有最小 deterministic Core implementation：exact-text Publication IR，以及 clean text、Web HTML、print-oriented HTML/CSS 与 EPUB 3.3 输出。它**不等于**完整 Typesetting Toolkit 或 Studio Publish 体验已经完成；Issue #16 继续承载更大的剩余范围。
- 更完整的 MCP registry/management 与后续 write-capable Studio operation 继续 deferred 给各自 owning workstream。
- UI、Host Bridge、Agent Skill、production-readiness receipt 与 publication output 都不会因为存在、通过或被展示就成为 Canon、Memory、semantic truth、settlement truth 或 workflow authority。

## 7.0.0 · Adaptive Fiction Framework

### Architecture
- 仓库正式重构为完全 project-agnostic 的 Fiction Agent Framework。
- 确立单向依赖：Consumer Project → NovelForge Framework。
- 增加 Standard + Mapped Project Adapter，成熟小说工程无需 destructive directory rewrite 也能迁移。
- 增加 `novelforge.toml` project manifest 与 `novelforge.lock.json` framework dependency lock。

### Fiction Core
- 增加 Generic Story Architecture、Character/Relationship、Canon/State、dependency、settlement、continuity contract。
- 将长期反复出现的 AI 文风修正升格为 Framework-level Surface Fundamentals（HF-01..HF-29）。
- 增加 Generic Reader Engagement 正向质量模型（RG-01..RG-15），包括 SAFE-BUT-FLAT。

### Runtime
- 保留 session-native Harness 与 manager/specialist/reviewer 分离。
- 增加 SQLite Control Plane：sessions、events、handoffs、leases、result hashes、logical consume-once receipts。
- 增加 provider-neutral routing：普通 chat、本地 Codex/Claude、MCP、provider API、GitHub/service jobs、local model、human reviewer。
- Mandatory independent semantic judgment 继续 fingerprint-bound，默认 fresh-per-fingerprint。
- 增加 typed GitHub event ingress 与无需 API 的 peer-chat semantic bridge。
- 增加可选的手工 provider-backed semantic eval workflow；必须显式配置 secret，绝不进入 normal CI。
- 增加 weekly deterministic maintenance：只观察、测试、生成 work queue，不执行 LLM，也不自动 promote Framework behavior。

### Adaptive Learning
- 增加 durable Learning Store，保存 preference evidence、可推翻 hypothesis、contradiction、Corpus gap、promotion candidate、rollback record。
- 支持自主发现新的 preference dimension 与自动生成 Corpus gap。
- Evidence hierarchy 明确：模型推断本身不能升级为 durable user taste 或 General Craft。

### Corpus Intelligence
- 增加 provider-neutral Corpus Scout 与 rights/storage gate。
- Rights class：`redistributable | analysis_only | unknown`。
- 增加 question-bounded analysis、counterexample search、cross-work generalization、named-author imitation boundary。
- 迁移 8 个 Generic cross-work mechanism benchmark seed，不保存 raw source text 或 consumer-project fact。
- Scheduled maintenance 可以生成 typed Corpus discovery queue；真正 Web/GitHub/MCP discovery 仍要求已授权 host connector，不能伪造 source access。

### Evals
- 增加 deterministic + semantic generic eval runner。
- 增加 blind semantic queue builder，reviewer 前移除 expected/gold/release label。
- 增加 v7 Surface/Reader/Character/Canon/Corpus fixture suite。
- 无 independent judgment 时 normal CI 明确显示 `PENDING_MODEL`，不会伪造 PASS。

### Project Engineering
- 增加 executable Project SDK：`init / validate / spec-new / build / self-test`。
- 增加 Generic Mapped Project Adapter 支持成熟/legacy repo。
- Structural change 采用：`spec → plan → tasks → implementation → verification → acceptance`。
- 增加 deterministic compact project bundle/fingerprint build model。

### Documentation / Repository Quality
- Human-facing authoritative docs 采用 English + 简体中文成对版本。
- 大量架构、Learning、Runtime、Project 图采用 Mermaid。
- 增加 Agent Framework adopt/adapt/reject research matrix。
- CI 现在 hard gate：consumer-project leakage、双语 pairing、relative links、manifests、Project SDK、Learning/Corpus、Runtime/MCP、Semantic transport、Evals、authority boundary。
- Normal CI 不调用付费或 login-bound model inference。

### Migration Note
- 少量稳定 executable schema/env 仍保留 pre-v7 `novel_os_*` compatibility identifier。这属于 implementation compatibility detail，不是 consumer-project dependency。后续可通过独立 structural-change spec 完成 schema rename，而不冒险破坏 v7 稳定 runtime。
