# NovelForge Changelog · 中文版

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
- 0.8.0 normalization 让当前 machine/version identity 归一，不再同时维护“release version”和“implementation version”两套开发编号。
- Documentation governance 已确定性跟踪 audience、tier、authority source、freshness owner、rewrite policy、lifecycle、双语配对、本地链接、版本对齐与可检查的视觉/文档约束；`studio/` 已纳入 bilingual manifest coverage QA。

### 当前缺口与兼容说明

- Run Receipt 仍有 Core-owned consumer/read-surface 工作：稳定 manifest discoverability、`run.receipt_recorded` 的 event-schema 对齐，以及供 Studio 使用的稳定 query/projection boundary，而不是读取 persistence internals。PR #25 有意没有通过 Host Bridge 暴露不安全的 Control Plane / Run Receipt 读取。
- 已经有意锁定旧 Framework revision 的下游项目继续受那个 revision 约束，直到显式升级；Generic Framework 自身开发则跟随 latest `main`，不维护内部开发 lock。
- 未来真正稳定的 migration guide 必须从冻结后的 contracts 与最终 bundle 生成，不能根据 Issue 或中间开发提交猜最终接口。

### Product / Publication 状态

- Studio 当前已经合并**只读** Phase 1、Phase 2A、Phase 2B 产品切片：observability、Project Hub、Scene workspace、portable host boundary 与 Agent Skill delivery 都已经真实存在于 `main`。
- 这些切片**不代表** Studio 已经成为可写、多人协作、带生产认证或正式云托管的完整应用。Generic invoke/write、project mutation、resume 与更广的 Control Plane read 仍不属于当前 bridge contract。
- Publication / Typesetting 仍是 Issue #16 跟踪的 Core 活跃 workstream。官方 IR/profile/runtime contract 合并之前，EPUB/Web/print publication 仍只能描述为计划中或开发中能力。
- 更完整的 MCP registry/management 与后续 write-capable Studio operation 继续 deferred 给各自 owning workstream。
- UI、Host Bridge 与 Agent Skill state 永远不会因为被展示或调用就成为 Canon、Memory、semantic truth、settlement truth 或 workflow authority。

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
- CI 现在 hard gate：consumer-project leakage、双语 pairing、relative links、manifest、Project SDK、Learning/Corpus、Runtime/MCP、Semantic transport、Evals、authority boundary。
- Normal CI 不调用付费或 login-bound model inference。

### Migration Note
- 少量稳定 executable schema/env 仍保留 pre-v7 `novel_os_*` compatibility identifier。这属于 implementation compatibility detail，不是 consumer-project dependency。后续可通过独立 structural-change spec 完成 schema rename，而不冒险破坏 v7 稳定 runtime。