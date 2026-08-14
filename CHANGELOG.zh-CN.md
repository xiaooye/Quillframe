# NovelForge Changelog · 中文版

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
