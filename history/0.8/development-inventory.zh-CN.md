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

### 任务感知、视角安全、遵守故事时间顺序的 Context grounding

PR #12 升级 context selection：active grounding question 变成显式输入；visibility 在 semantic selection 前由确定性系统执行；与当前视角不兼容的 evidence 不能进入 model packet；系统还能区分“语义上选中的 support”和“后来因为硬预算没有真正加载的 support”。

PR #27 进一步加入确定性的 story-order eligibility 与逐问题 evidence eligibility 检查。来自未来或与当前上下文不兼容的 pinned evidence 会 fail closed；如果 hard budget 导致某个问题所需 evidence 无法完整进入 packet，grounding result 会明确报告不完整，而不是假装已经获得充分依据。

模型负责判断语义相关性；确定性代码负责 visibility、story-order eligibility、预算、provenance、authority class 与最终 packet 构造。

### 绑定证据的 Character 与 Long-horizon reasoning

PR #28 把角色的 epistemic status 与 acquisition mode 分开，并要求 proposed action 绑定当前故事时间点下、该角色真正可见的 evidence。Future、unknown 或其他无效 evidence 不能因为存在于 Framework state 中，就被拿来当成某个角色行动的正面依据。

PR #29 要求 long-horizon continuity reconciliation 使用遵守 story order 的 evidence，并完整覆盖 required requirements；uncertainty 可以作为合法 typed state 保留下来；shared relationship state 与各角色对这段关系的 individual perception 也被明确分离。

这些变化是在现有 semantic-contract architecture 内强化 evidence discipline；没有新增另一套 agent，也没有创造新的 authority layer。

### Metadata-only Run Receipt

PR #13 加入 `novelforge_run_receipt_v1` 与确定性的记录边界，用于保存 artifact/context identity、semantic job、guard outcome，以及 selected support 与 actually loaded support 等执行证据，同时禁止 candidate prose，也不授予 Canon authority。

Run Receipt 是可观察性证据，不是第二套状态数据库。

### 同一 fingerprint 的 Production Readiness gate

PR #31 加入 `novelforge_production_readiness_v1`，并通过 `HARNESS_MANIFEST.yaml` 暴露出来。

这不是一个 composite literary score。它把所有 required gate 绑定到**同一个精确 candidate fingerprint**，再执行 fail-closed conjunction policy：

- Surface 与 Reader Engagement 必须通过；
- Continuity 可以由 policy 设为 required；
- independent semantic review 可以由 policy 设为 required；
- required gate 缺失、`pending` 或 `fail` 都会阻止 `ready_for_user_visible_review`；
- `RG-15` SAFE-BUT-FLAT 不能同时成为通过的 Reader Engagement gate；
- readiness record 固定 `authority=false`，不会授予 Canon / Framework-write / durable-user-taste 权限。

这让 user-visible readiness boundary 真正可执行，同时仍然不让确定性代码假装自己能判断文学质量。

### Deterministic Publication core

PR #31 也加入第一版 manifest-authoritative Publication implementation：

- `publication/publication_ir.schema.json`，schema 为 `novelforge_publication_ir_v1`；
- `publication/compiler.py`；
- Accepted text 精确 fingerprint 检查与 `text_preservation = exact-unicode-text`；
- derived output 固定 `authority=false`；
- deterministic profiles：`clean_text`、`web_reflow`、`print_book`、`epub3`；
- deterministic EPUB generation，以及内部 structural/text-roundtrip validation；
- 目标规范为 W3C EPUB 3.3，release conformance 必须显式提供外部 EPUBCheck command。

当前 `print_book` 输出的是 print-oriented HTML/CSS，**不是**完整 paged-media → PDF engine。当前 IR 也刻意保持最小，只覆盖 book metadata 与 chapter title/text/fingerprint；Issue #16 描述的更丰富 semantic structure 和 typesetting profile 还没有全部进入实现。

### 可实际运行的 Framework bundle

PR #18 修复 release-substrate 缺陷：之前 bundle 即使 byte-reproducible，也可能漏掉 `quality/` runtime。现在 bundle CI 会验证生成包，并在解包后实际执行 `novelforge.py doctor` 与完整 model-free self-test。

PR #31 进一步把新的 production-readiness 与 Publication runtime contracts 纳入 bundle surface，并在 normal deterministic CI 中验证它们，同时继续禁止伪造 semantic verdict。

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

### Story Loom v2 + exact-pinned WeiUI zero-JS foundation

PR #32 把 `assets/brand/tokens.json` 升级为 `novelforge_brand_tokens_v2`，并真正落地 application design foundation。

`assets/brand/weiui.integration.json` 现在记录精确的 generic UI dependency contract：

- source repo：`xiaooye/weiui`；
- exact commit：`d84d1cd365fb5f90cbbab794d2358f7a13b29b79`；
- license：MIT；
- allowed WeiUI packages：`@weiui/tokens`、`@weiui/css`；
- forbidden runtime packages：`@weiui/headless`、`@weiui/react`；
- WeiUI runtime JavaScript required：`false`；
- theme layer：`wui-theme`；
- import order：WeiUI tokens → WeiUI CSS → `assets/brand/story-loom.weiui.css`。

`story-loom.weiui.css` 提供真正的 light/dark `--wui-*` aliases 与 NovelForge `--nf-*` product-semantic variables，同时不 fork WeiUI component selectors。

machine token contract 现在也包含 application rules：mobile-first、44px minimum touch target、focus-ring geometry、`en-US` + `zh-CN`、logical properties、禁止 fixed-width locale assumptions、reduced motion、no idle animation、no default polling、no heavy default component import。`scripts/design_system_quality.py` 会在 CI 中确定性检查这些 invariant、WeiUI exact pin/provenance、required variables、CSS layer，以及 light/dark contrast。

### Phase 2C application stack decision

Product/runtime-overhead 决策已经选定 **SolidJS + TypeScript + Vite + `@solidjs/router`** 作为 Phase 2C application code。

WeiUI 被刻意作为 **zero-JavaScript CSS/tokens foundation** 使用，而不是通过 React 或 WeiUI runtime/headless package。Local Web 保持 first-class，并在“最小增量 CPU/RAM”目标下作为优先形态；Tauri 只是 optional/installable desktop host，不再是产品架构中心。

这个 stack decision 继续维持 one-product/many-host invariant：transport / host choice 不能改变 Canon、Settlement、Context、semantic-result、production-readiness 或 receipt semantics。

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

### Publication / Typesetting Toolkit · 最小 Core 已合并，更大范围仍开放

Publication 已经不再只是 issue-level proposal：`novelforge_publication_ir_v1` 与 deterministic compiler 都真实存在于 `main`。

Issue #16 仍然 open，因为它的最终目标比当前 compiler 更大。当前仍未完成或尚未由最小实现表达的内容包括：

- part / section / scene break / epigraph / note / figure / front/back matter / in-world document 等更丰富 semantic IR structure；
- 比当前 named compiler profiles 更完整、versioned 的 Typesetting Profile contract；
- 更丰富的 CJK/Latin typography、font embedding 与 publication-style controls；
- 通过 Vivliostyle-compatible 等 paged-media engine 生成 print PDF；
- 更完整 accessibility / visual-regression / asset-validation hooks；
- Studio publication preview 与 authoring UX。

因此文档必须精确描述当前 compiler：它是已经可用的 deterministic core，**不是整个 Typesetting Toolkit 已完成**。

### Phase 2C application implementation

Story Loom / WeiUI foundation 与 SolidJS stack decision 都已经具体化，但这不代表 Phase 2C product application 已经完成。

仍需要真实 implementation evidence 的部分包括：SolidJS route/workspace shell、host lifecycle、typed bridge consumption、optional Tauri packaging，以及实际 runtime behavior。Product acceptance 应基于真实 idle CPU/RAM 与 first-interaction measurement，而不是因为 stack 看起来轻就直接宣称轻量。

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
- 文档必须明确区分 merged implementation、selected product direction、active dependency 与 proposal；
- Issue、设计文档、prototype 或 candidate schema 的存在，本身都不会获得 authority；
- machine version surface 应保持一致，不再累积多套并行开发版本标签。

未来真正稳定的 migration guide 只应在 release contract 被主动冻结后生成，并列出精确 old→new identifier、兼容说明、删除行为、升级步骤与最终 bundle evidence。

## 当前 readiness 边界

`0.8.0` 表示 active pre-1.0 development identity 已经统一，**不表示所有 8.0-line product goal 都完成，也不表示 API 已冻结**。

Core 现在已经有可执行的 production-readiness conjunction gate 与最小 deterministic Publication compiler。Product foundation 也已经有 exact-pinned、zero-JS 的 WeiUI token/CSS layer，以及 SolidJS Phase 2C stack decision。要做更强的 stable-release claim，仍然需要围绕 Run Receipt/query surface、Issue #16 剩余 Publication scope、Studio write boundary、真实 Phase 2C application/runtime measurements、exact bundle/CI evidence，以及面向客户的中英双语同步审查作出明确决定并拿到验证证据。

在此之前：**0.8.0 = latest `main` 上持续推进的 pre-1.0 开发线。**
