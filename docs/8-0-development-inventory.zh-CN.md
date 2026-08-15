# NovelForge 0.8.0 / 8.0 开发线变更清单

> 本文档记录开发状态。`0.8.0` 是此前称作“8.0”架构开发线的 pre-1.0 SemVer 身份，**不是已经冻结的 1.0 级兼容承诺，也不是最终迁移指南**。持续开发期间，最新 `main` 仍是工作实现基线。

[English](8-0-development-inventory.en.md)

## 用途

这份清单用于让发布沟通始终与 `main` 上真正存在的实现保持一致。它把**已经合并的实现、仍属于 Core 的依赖、以及 deferred product work**分开，避免把 Issue、设计或 prototype 提前写成它们尚未提供的正式能力。

它不是完整 roadmap，只记录会影响使用者理解、authority boundary、兼容性或发布判断的变化。

## 版本身份

NovelForge 当前已经把 machine manifest、Skill metadata、CLI、Project SDK 默认值、对外 MCP server metadata 与 documentation governance metadata 统一为 **0.8.0**。

这是一次 pre-1.0 开发编号重置，用来结束过去 “7.2 release metadata / 7.3 implementation metadata” 并存的状态；历史 7.x 记录不会因此被倒写。

持续开发期间：

- 最新 `main` 是 Framework implementation baseline；
- `0.8.0` 表示当前开发线，不表示 API 已冻结；
- 1.0 前如果架构确有需要，仍允许经过验证的 breaking machine-contract cleanup；
- 已经有意锁定旧 Framework revision 的下游项目继续留在旧 revision，直到显式升级。

## 已合并到 `main`

### Machine namespace + 最终 machine-contract cleanup

PR #11 已把 live machine-facing 名称从旧 Novel OS namespace 迁到 NovelForge namespace，包括 `NOVEL_OS_*` → `NOVELFORGE_*`、live `novel_os_*` schema ID → `novelforge_*`、`.novel-os/runtime.db` → `.novelforge/runtime.db`、MCP tool/server 与相关 Session / Control Plane identifier，并且没有添加兼容别名。

PR #24 完成剩余 machine-contract cleanup：`os_behavior_write` → `framework_behavior_write`；semantic job/result ID 从 `novel-os-*` 迁到 `novelforge-*`；移除 live `.novel-os/` ignore surface；namespace hygiene 也会阻止这些旧 machine identifier 再次回归。没有添加 compatibility alias。

### 任务感知、视角安全的上下文 grounding

PR #12 升级了 context selection：active grounding question 变成显式输入；visibility 在 semantic selection 前由确定性系统执行；与当前视角不兼容的 evidence 不能进入 model packet；系统还能区分“语义上选中的 support”和“后来因为硬预算没有真正加载的 support”。

模型负责判断语义相关性；确定性代码负责 visibility、预算、provenance、authority class 与最终 packet 构造。

### Metadata-only Run Receipt

PR #13 加入 `novelforge_run_receipt_v1` 与确定性的记录边界，用于保存 artifact/context identity、semantic job、guard outcome，以及 selected support 与 actually loaded support 等执行证据，同时禁止 candidate prose，也不授予 Canon authority。

Run Receipt 是可观察性证据，不是第二套状态数据库。

### 可实际运行的 Framework bundle

PR #18 修复了 release-substrate 缺陷：之前 bundle 即使 byte-reproducible，也可能漏掉 `quality/` runtime。现在 bundle CI 会验证生成包，并在解包后实际执行 `novelforge.py doctor` 与完整 model-free self-test。

### Studio Phase 1 · 只读 Run / Context Inspector

PR #19 合并第一阶段 Studio 产品架构，以及由 `novelforge_run_receipt_v1` 驱动的零依赖 Run / Context Inspector。它始终只读，不拥有 Canon、Memory、semantic truth、settlement truth 或 workflow authority。

### Studio Phase 2A · portable Project Hub + Scene workspace

PR #21 已合并下一段只读产品 vertical slice：CLI/local/hosted/agent-package surface 共用一套 portable product contract；Project Hub projection 确定性生成；browser-safe projection 默认不暴露 host-only absolute path；所有 projection 绑定 source fingerprint 并明确 `authority=false`；同时加入 synthetic project/scene fixtures 与只读 Project Hub + Scene workspace prototype。

### Studio Phase 2B · read-only Host Bridge + Agent Skill

PR #25 已合并 versioned read-only host bridge 与 standards-compatible NovelForge Agent Skill package。

Bridge 当前只 allowlist：

- `bridge.describe`；
- `framework.doctor`；
- `project.inspect`；
- `capabilities.inspect`；
- `context.inspect`；
- `semantic.catalog`。

其他 operation fail closed。Browser/remote-safe projection 默认不泄露 host-private absolute path。外部 Agent Skill 通过 bridge 消费能力，而不是直接 import Core persistence 或私有实现。整个 surface 始终 `authority=false`，并明确没有 Canon / Framework-write / Settlement authority。

### 0.8.0 version normalization 与文档真相

machine manifest、Skill metadata、CLI、Project SDK 默认值、对外 MCP server version 与 documentation governance metadata 现在共用一个 `0.8.0` 开发身份；文档同时登记了当前 Studio authority sources，并继续把 `studio/` 纳入 bilingual manifest coverage QA。

## 仍未完成的依赖与缺口

以下内容**尚未完成**，不得描述成已经 shipped 的稳定能力。

### Run Receipt / Control Plane read-surface 缺口

Studio 仍依赖 Core-owned consumer/read-surface 工作：

1. Run Receipt schema/tool 通过 Framework manifest 稳定 discover；
2. `run.receipt_recorded` 与 event schema 一致；
3. 提供稳定 receipt/query projection，而不是直接读取 persistence；
4. 在 portable host bridge 纳入 Session/Event/Handoff/Run Receipt read 与 resume 之前，先建立安全稳定的 typed query/command boundary。

PR #25 有意 defer 这些不安全查询，而不是在 UI/Bridge 层创造替代 contract。Core Issue #23 负责稳定 query/command boundary。

### Publication / Typesetting Toolkit

Issue #16 定义目标中的确定性 publication pipeline：`Accepted manuscript → Publication IR → Typesetting Profile → Renderer → Validator → derived outputs`。

本文档不会假定 `novelforge_publication_ir_v1` 已经正式实现。Publication preview、EPUB/Web/print renderer 与 publication validator 必须等 owning Core implementation 真正合并后才能写成现有能力。

### Write-capable / production-hosted Studio

当前已合并的 Studio product slice 仍然只读。Generic invoke/write、project mutation、settlement command、production cloud hosting、authentication、collaboration 与 vendor-specific write adapter 都不属于当前 product contract。

### 更广的 MCP ecosystem

Issue #8 仍是 MCP registry/management 与后续 product surface 的 umbrella。Capability discovery 必须继续与 authority 分离；UI/MCP 是否存在也不能成为 Core runtime 正确性的前提。

## pre-1.0 开发期间的兼容策略

- 最新 `main` 是 Framework 开发基线；
- 架构确有需要且 deterministic CI 可验证时，允许 breaking machine-contract cleanup；
- 不默认添加 compatibility alias；
- 历史 changelog/spec 保留原始历史语义；
- Project / user 数据永远不能进入 Generic Framework source；
- 文档必须明确区分 merged implementation、active dependency 与 proposal；
- Issue、设计文档、prototype 或 candidate schema 的存在，本身都不会获得 authority；
- machine version surface 应保持一致，不再累积多套并行开发版本标签。

未来真正稳定的 migration guide 只应在 release contract 被主动冻结后生成，并列出精确 old→new identifier、兼容说明、删除行为、升级步骤与最终 bundle evidence。

## 当前 readiness 边界

`0.8.0` 表示 active pre-1.0 development identity 已经统一，**不表示所有 8.0-line product goal 都完成，也不表示 API 已冻结**。

在 NovelForge 可以做更强的稳定 release claim 之前，仍需要围绕 Run Receipt/query surface、Publication 是否纳入、Studio write boundary、exact bundle/CI evidence，以及面向客户的中英双语同步审查作出明确决定并拿到验证证据。

在此之前：**0.8.0 = latest `main` 上持续推进的 pre-1.0 开发线。**