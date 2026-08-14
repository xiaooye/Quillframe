# NovelForge Changelog · 中文版

## Unreleased · 面向 8.0 的开发中架构

> 本节是**开发变更台账，不是 NovelForge 8.0 发布声明**。在 Core acceptance / release 流程明确晋升新版本之前，`HARNESS_MANIFEST.yaml` 仍是 Framework 的发布权威。

### 发布真相

- 当前 `HARNESS_MANIFEST.yaml` 的发布权威版本仍为 **7.2.0**。
- 顶层 CLI `novelforge.py` 当前报告 **7.3.0**，而 Project SDK 默认版本仍为 **7.2.0**。这是实现状态与发布元数据之间的漂移；在 Core / Release 所属流程正式解决前，文档必须如实保留这一差异，不能替它们静默统一版本号。
- 针对当前 `main` 重写过的文档，除非 `docs/documentation_manifest.json` 已明确将其标记为对发布权威复核完成的 `reviewed_current`，否则仍只是候选文档。
- `main` 上出现面向 8.0 的机制或文档，**不等于 NovelForge 8.0 已经发布**。

### 已合并的开发变更

- 语义运行已经转向“小型 contract catalog → 渐进披露 → 精确 contract pack”。小说语义判断由模型负责；确定性代码负责权威、权限、指纹、持久化、路由、硬预算、类型校验、事务与可复现性。
- live machine namespace 已从 `NOVEL_OS_*` / `novel_os_*` / `.novel-os/` 迁移到 `NOVELFORGE_*` / `novelforge_*` / `.novelforge/`，且不保留兼容别名。这是一次预发布 breaking migration。
- Context selection 已支持面向当前任务的问题→证据 grounding，并在组装模型上下文之前确定性执行 perspective / visibility 过滤。不符合可见性要求而又被 pin 的证据会 fail closed，而不是先展示给模型再用提示语要求它忽略。
- metadata-only 的 `novelforge_run_receipt_v1` 可观察性 primitive 已合并。它可以绑定 run、context、semantic job、guard 与 grounding evidence 的元数据，但不保存候选正文、不获得 Canon authority，也不成为第二套状态数据库。
- 当前 Settlement Runtime 继续把 Accepted artifact 的持久化修改置于明确接受、精确 before→after 写入意图、checkpoint / write authorization、compare-and-swap、post-condition 与 required projection receipts 之后；派生 projection 仍然不是 Canon。
- Documentation governance 已开始确定性跟踪 audience、tier、authority source、freshness owner、rewrite policy、lifecycle、双语配对、本地链接、发布版本漂移与可检查的视觉/文档约束。清晰度、语义真实性、母语质量和视觉质量仍需要独立的语义审查，不能由正则表达式宣称完成。

### Breaking change / Migration 台账

- 上述 machine namespace migration **已经发生在 live `main`**。下面的 7.0 历史说明记录的是当时状态，不应再被当作当前 machine guidance。
- 独立的 permission schema rename：`os_behavior_write` → `framework_behavior_write` **目前尚未在 live `main` 完成**。已经关闭的 PR #14 / #15 不具备发布权威，不能把它们当作成功迁移的证据。
- 已锁定旧 NovelForge commit 的下游项目仍受其 exact dependency 约束。不得因为 `main` 更新就静默替换现有 `novelforge.lock.json`；升级必须走显式 Framework upgrade / migration，并重新验证 Project、bundle fingerprint、相关 contracts 与受影响的 runtime state。
- 最终 8.0 migration guide 必须从 Core 已接受的正式 contracts 与 release bundle 推导，不能根据 issue 描述或中间开发提交猜测最终接口。

### Product / Publication 状态

- Publication / Typesetting 是 Core workstream 的活跃开发项，由 Issue #16 跟踪。在正式 schema/runtime 进入 live release authority 之前，文档只能把它描述为计划中或开发中能力，不能写成已发布功能。
- NovelForge Studio / observability UX 是 Product Experience workstream 的活跃开发项，由 Issue #8 / #17 跟踪。Core 已合并 Run Receipt 或 Inspector primitive，并不等于 Studio 已经交付。
- Studio 必须消费 Core 提供的稳定状态/读取接口；UI state 永远不会因为被展示出来就成为 Canon、Memory、语义真相或写入权威。

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