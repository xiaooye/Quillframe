# Quillframe 文档中心

Quillframe 文档先建立 mental model，再进入 contract 与 reference。只要解释性文档与 implementation、schema、tests、current manifest 冲突，后者优先。

<img src="assets/architecture/framework-vs-project.zh-CN.svg" alt="Framework 与 Project：Quillframe 提供通用生产机制，每个 Project 保留自己的故事事实与 Canon 权威" width="100%" />

## 从这里开始

先读[总体架构](architecture.zh-CN.md)，再读[生产流水线](production-pipeline.zh-CN.md)与[质量保障](quality-assurance.zh-CN.md)。这三篇解释为什么长篇项目不能把 plan、draft、evidence 与 Canon 混成一团“记忆”。

## 核心概念

[架构图谱](architecture-atlas.zh-CN.md)把通用机制映射到 implementation owner；[Canon State](../core/CANON_STATE.zh-CN.md)是 authority 的规范契约；[Candidate Lineage](CANDIDATE_LINEAGE_V1.zh-CN.md)解释 candidate ancestry 与 exact review binding 为什么仍然只是 provenance。

## 写作

[生产流水线](production-pipeline.zh-CN.md)、[Surface Fundamentals](../surface/FUNDAMENTALS.zh-CN.md)与[Reader Engagement](../surface/READER_ENGAGEMENT.zh-CN.md)覆盖 generation、diagnosis、repair ownership 与 reader-facing quality。

## 质量

[质量保障](quality-assurance.zh-CN.md)解释 release truth 与 pre-independent qualification；[质量演进](quality-evolution.zh-CN.md)解释 incumbent/challenger、objective preservation、regression protection 与停止条件；[Eval Reference](../evals/README.zh-CN.md)区分 deterministic 与 semantic evaluation。

## Canon 与 Settlement

[Canon State](../core/CANON_STATE.zh-CN.md)定义 authority class。Settlement 是独立授权事务：明确 acceptance、exact before/after intent、current-state compare-and-swap、required projection 与 post-condition validation。

## Context 与 Memory

[上下文与记忆](context-and-memory.zh-CN.md)说明 Sparse Context Manifest、protected authority、derived memory，以及为什么 persistence 从不等于 automatic prompt injection。

## Learning

[自适应学习](adaptive-learning.zh-CN.md)覆盖 automatic feedback intake 与 governed promotion；[Corpus Intelligence](../corpus/README.zh-CN.md)和[Corpus Policy](../corpus/CORPUS_POLICY.zh-CN.md)把 evidence、rights 与 Canon 分开。

## Semantic Execution

[Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.zh-CN.md)定义 typed semantic work；[Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.zh-CN.md)定义 dispatch、provenance、result validation 与 independent execution 边界。

## Session 与 Control Plane

[运行时与集成](integrations.zh-CN.md)、[Session Runtime](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md)、[Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.zh-CN.md)和[Control Plane](../harness/control_plane/CONTROL_PLANE.zh-CN.md)共同定义 resource/session/run/checkpoint identity 与 durable external work。

## Corpus 与 Research

Corpus 是 evidence，不是 Canon；Research truth 也不会自动成为 Character Knowledge。应同时遵守 [Corpus overview](../corpus/README.zh-CN.md)、[ingest protocol](../corpus/CORPUS_INGEST_PROTOCOL.zh-CN.md)与 Project 自己的 knowledge boundary。

## Project Integration

[Project SDK](project-sdk.zh-CN.md)、[Project Adapters](project-adapters.zh-CN.md)、[Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md)与[Framework Bundle](../release/FRAMEWORK_BUNDLE.zh-CN.md)确保小说 Project 可独立复现，又不会把私有故事事实反向写进 generic framework。

## Development

[8.0 Development Inventory](8-0-development-inventory.zh-CN.md)、[Agent Framework Adoption](../knowledge/AGENT_FRAMEWORK_ADOPTION.zh-CN.md)与 [Changelog](../CHANGELOG.zh-CN.md)记录当前演进；historical spec 即使经历 public brand 变化，也仍保持历史原貌。

## Reference

Operational authority 在 [SKILL](../SKILL.zh-CN.md)、[Harness Agent](../harness/HARNESS_AGENT.zh-CN.md)、schemas、implementation modules 与 tests 中。文档编写遵守 [Documentation Standard](DOCUMENTATION_STANDARD.zh-CN.md)和[Documentation QA](DOCUMENTATION_QA.zh-CN.md)。

稳定路径 `why-novelforge.zh-CN.md` 为兼容保留；当前内容解释[为什么是 Quillframe](why-novelforge.zh-CN.md)以及为何 technical namespace 不随 public brand 一起改名。
