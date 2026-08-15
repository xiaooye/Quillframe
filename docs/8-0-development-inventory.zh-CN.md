# NovelForge 8.0 开发变更清单

> 本文档记录开发状态，**不是已经发布的迁移指南，也不定义稳定的兼容边界**。8.0 仍在持续开发期间，以最新 `main` 作为工作基线；只有发布契约真正冻结后，才应生成正式 Release Notes 与升级指南。

[English](8-0-development-inventory.en.md)

## 用途

这份清单用于让发布沟通始终与 `main` 上真正存在的实现保持一致。它把**已经合并的实现、仍在推进的依赖、以及尚未落地的产品目标**分开，避免把计划、Issue 或原型提前写成“已经发布的能力”。

它不是完整 roadmap，只记录会影响使用者理解、兼容性或发布判断的变化。

## 已合并到 `main`

### NovelForge machine namespace 迁移

PR #11 已把 live machine-facing 名称从旧 Novel OS namespace 迁到 NovelForge namespace，并且没有额外加入兼容别名：

- `NOVEL_OS_*` → `NOVELFORGE_*`；
- live `novel_os_*` schema ID → `novelforge_*`；
- `.novel-os/runtime.db` → `.novelforge/runtime.db`；
- MCP tool/server 名称 → `novelforge_*`；
- peer packet、Session 与 Control Plane 的 machine schema 统一到 NovelForge 命名。

该 PR 有意没有处理独立的 permission 字段 `os_behavior_write`。

### 任务感知、视角安全的上下文 grounding

PR #12 升级了 context selection：active grounding question 变成显式输入；visibility 在 semantic selection 前由确定性系统执行；与当前视角不兼容的 evidence 不能进入 model packet；系统还能区分“语义上选中的 support”和“后来因为硬预算没有真正加载的 support”。

这里继续保持架构边界：模型负责判断语义相关性；确定性代码负责 visibility、预算、provenance、authority class 与最终 packet 构造。

### Metadata-only Run Receipt

PR #13 加入 `novelforge_run_receipt_v1` 与确定性的记录边界，用于保存 artifact/context identity、semantic job、guard outcome，以及 selected support 与 actually loaded support 等执行证据，同时禁止把 candidate prose 塞进 receipt，也不授予 Canon authority。

Run Receipt 是可观察性证据，不是第二套状态数据库。

### 可实际运行的 Framework bundle

PR #18 修复了一个 release-substrate 缺陷：之前 bundle 即使 byte-reproducible，也可能漏掉 `quality/` runtime。现在 bundle CI 会验证生成包包含 quality runtime，并在解包后实际执行 `novelforge.py doctor` 与完整 model-free self-test。

### Studio Phase 1 只读产品验证原型

PR #19 合并了第一阶段 Studio 产品架构，以及由 `novelforge_run_receipt_v1` 驱动的零依赖 Run / Context Inspector 原型。

Phase 1 刻意保持只读。它用于验证信息架构与可观察性体验；它不是已经发布、具备写入能力的完整 Studio，也不拥有 Canon、Memory、semantic truth 或 workflow authority。

### Documentation release-truth 清理

当前文档已经开始明确区分 development architecture 与 release metadata；未发布变化被单独记录；Studio 文档已经纳入 documentation manifest；`studio/` 也进入 bilingual-document coverage QA，今后新增双语 Studio 文档如果忘记登记 manifest，CI 会直接失败。

## 仍未完成的依赖与缺口

以下内容**尚未完成**，不得描述成已经发布的 8.0 能力。

### Framework-write permission rename

`os_behavior_write` 的目标 rename 仍未完成。PR #14、#15 在发现迁移方式无效或 stale 后均未合并。Core-owned migration 真正落地之前，规范性文档必须在需要时继续使用 live machine field 的精确名称。

### Run Receipt consumer contract 缺口

Studio Phase 1 已明确发现三个仍属于 Core 的 consumer gap：

1. Run Receipt schema/tool 尚未完整通过 `HARNESS_MANIFEST.yaml` 暴露为稳定 discoverable surface；
2. `run_receipt.py` 会产生 `run.receipt_recorded`，但当前 Control Plane event schema 还没有公开该 event type；
3. Studio 仍需要稳定的 receipt/query projection，不应该直接读取 Control Plane persistence internals。

文档只能把它们写成 dependency，不能在 UI 层自行创造替代 contract。

### Version metadata drift

仓库里仍存在 release metadata 与 implementation metadata 的开发期 drift。8.0 还在开发时，这份文档按最新 `main` 作为实现基线，不把该 drift 当成开发阻塞条件；但真正发布前仍必须统一正式 release/version metadata。

### Studio Phase 2A

Issue #20 定义下一阶段只读 Studio：portable Project Hub + Scene workspace，并要求 CLI、本地 UI、Hosted UI、agent-skill/package adapter 等不同 delivery surface 共用同一套 product contract。它目前仍是 active target，不是 shipped capability。

核心不变量仍然是：多种交付界面只能消费同一套 Core truth model；任何 delivery surface 都不能获得 Canon 或 workflow authority。

### Publication / Typesetting Toolkit

Issue #16 定义了目标中的确定性 publication pipeline：

`Accepted manuscript → Publication IR → Typesetting Profile → Renderer → Validator → derived outputs`

本文档不会假定 `novelforge_publication_ir_v1` 已经正式实现。Publication preview、EPUB/Web/print renderer 与 publication validator 都必须等 owning Core implementation 真正合并后才能写成现有能力。

### MCP ecosystem 与后续 Studio

Issue #8 仍是 MCP registry/management、更完整 runtime observability 和后续 Studio surface 的 umbrella。Capability discovery 必须继续与 authority 分离；UI/MCP 是否存在也不能成为 Core runtime 正确性的前提。

## 8.0 开发期间的兼容策略

因为 8.0 仍在高速开发：

- 最新 `main` 是开发基线；
- 架构确有需要时允许 breaking machine-contract cleanup；
- 不默认添加 compatibility alias；
- 历史 changelog/spec 保留原始历史语义；
- Project / user 数据永远不能进入 Generic Framework source；
- 文档必须明确区分 merged implementation、active dependency 与 proposal；
- Issue、设计文档、prototype 或 candidate schema 的存在，本身都不构成 release truth。

等 8.0 freeze 后，再从这份清单生成真正的 migration guide，列出精确 old→new identifier、兼容说明、删除行为、升级步骤和最终 release metadata。

## Release-readiness checklist

文档要把 8.0 称为正式发布，至少应满足：

- Framework release/version metadata 内部一致；
- `HARNESS_MANIFEST.yaml` 的 machine schema/tool 名称与 live implementation 对齐；
- 已知 Run Receipt event/discoverability gap 已解决，或明确排除在该 release contract 之外；
- 计划中的 permission rename 要么完成，要么正式 defer；
- Framework bundle 解包后的 doctor/self-test 通过；
- exact release commit 上 deterministic CI 全绿；
- 面向用户的英文与简体中文文档针对同一个 release commit 完成同步审阅；
- release notes 明确区分 Core、Studio、Publication 与 deferred work，不把 prototype 提前升级成正式产品能力。

在这些条件完成之前，NovelForge 8.0 应表述为 **`main` 上持续进行的开发工作**，而不是已经冻结的兼容目标。
