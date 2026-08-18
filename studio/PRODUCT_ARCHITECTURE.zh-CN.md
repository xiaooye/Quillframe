# Quillframe Studio · 产品架构

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>READ-ONLY CORE</kbd>&nbsp;&nbsp;<kbd>LOW-OVERHEAD PRODUCT SHELL</kbd></p>

本文记录建立在当前 live Quillframe Core 与 Product contracts 之上的 Studio 产品架构。它是一份 consumer specification，不是另一份 runtime specification。Phase 2C 现在明确采用 **SolidJS + TypeScript + Vite + `@solidjs/router`**，WeiUI 只作为 **zero-JavaScript CSS/token foundation**。Local Web 保持一等产品面；Tauri 只是 optional/installable desktop host，不再是产品架构中心。

> **不变量 ✦ `UI CONSUMES CORE STATE. UI DOES NOT INVENT CORE STATE.`**

---

## 01 · Live repo audit

### 已经存在的 Side Goal substrate

Quillframe 已经具备相当完整的 Studio 底座：

- Session / Run / Checkpoint identity 与持久 Control Plane；
- typed host capability evidence，并明确 `capability != authority`；
- Project Adapter 对 logical project domains 的解析；
- `quillframe_context_inspector_v2`：authority-aware、stage-aware 的 Context view 与安全 derived controls；
- `quillframe_run_receipt_v1`：metadata-only execution evidence；
- `quillframe_production_readiness_v1`：同一 fingerprint 的 user-visible readiness conjunction；
- `quillframe_publication_ir_v1` + deterministic compiler：从 Accepted manuscript text 生成 derived publication；
- semantic contract ID、input/result fingerprint、worker reference 与 typed status；
- Quality Evolution、Reader Expectations、State Graph、scenario branch 与 settlement receipt 等非 Canon 证据/状态机制；
- deterministic docs、design-system、Framework-contract 与 release CI。

这些底座已经足够构建真实产品 surface，不需要另建 Studio database，也不需要第二套 publication / quality truth model。

### 已落地的 Story Loom / WeiUI foundation

Story Loom 现在已经不只是 documentation styling，而是 application-ready foundation。

当前 `main` 已包含：

- `assets/brand/tokens.json`，schema 为 `quillframe_brand_tokens_v2`；
- `assets/brand/weiui.integration.json`，把 generic WeiUI foundation 精确固定到 commit `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`；
- Phase 2C 只允许 `@weiui/tokens` 与 `@weiui/css`；
- `@weiui/react` 与 `@weiui/headless` 明确禁止成为 Studio runtime dependency；
- `assets/brand/story-loom.weiui.css`，在 WeiUI tokens/CSS 之后以 `wui-theme` layer 加载；
- WeiUI runtime JavaScript required = `false`；
- machine-owned light/dark theme roles，以及 Quillframe `--qf-*` product-semantic variables；
- mobile-first breakpoint、44px minimum touch target、focus geometry、`en-US` + `zh-CN`、logical properties、reduced motion 与 no-default-polling contract；
- `scripts/design_system_quality.py` + CI，确定性验证 exact pin/provenance、CSS layering、contrast、mobile/i18n/a11y 与 runtime-overhead invariants。

Story Loom 继续拥有 Quillframe 产品语义。WeiUI 拥有 generic CSS/token primitives。Integration contract 是 dependency boundary，不会把产品身份或 story authority 交给 WeiUI。

### Studio 可以直接消费的 Core interfaces

| Core contract | Studio 用途 | Authority 边界 |
|---|---|---|
| `quillframe_run_receipt_v1` | Run summary、真实 Context loading、semantic jobs、guard outcomes | 只属于 execution evidence |
| `quillframe_context_inspector_v2` | Context source、authority、stage eligibility、derived controls | overlay/proposal；不是 Canon |
| `quillframe_production_readiness_v1` | 解释同一 candidate fingerprint 上哪些 gate pass/fail/pending | deterministic gate evidence；不是文学分数，也不是 Canon |
| `quillframe_publication_ir_v1` + `publication/compiler.py` | 把 Accepted text 确定性编译为 clean text、Web HTML、print-oriented HTML/CSS 与 EPUB 3.3 | derived output；精确保留正文；`authority=false` |
| Session / Run identity | navigation、history、resume affordance | operational identity |
| Control Plane | event/handoff/result/consume lineage | operational evidence |
| `quillframe_host_capabilities_v1` | integration/capability health | capability 不是 authority |
| `quillframe_project_adapter_resolution_v1` | Project Hub logical domains / paths | 只负责 path classification |
| semantic contract catalog | Semantic Pack Inspector label / deep link | contract metadata |
| settlement receipts | settlement review / failure explanation | settlement semantics 仍由 Core 拥有 |

### 尚缺的 Core consumer interfaces

Studio 不能在 UI 里私自补这些缺口：

1. 已合并的 Run Receipt tool/schema 目前还没有从 `HARNESS_MANIFEST.yaml` 暴露出来；
2. `run_receipt.py` 会产生 `run.receipt_recorded`，但当前 event schema enum 没有公开这个 event type；
3. Studio 最终需要稳定的 receipt / Control Plane read-query boundary，不能直接读 SQLite internals；
4. Publication 已经有真实 minimum Core，但 Issue #16 仍拥有 richer semantic IR/profile controls、paged-media PDF、更完整 validation/visual-regression hooks 与更高层 publication authoring/preview。

这些都属于 Core consumer requirement。Studio 必须保持 thin，只消费真正存在的正式 public primitives。

---

## 02 · 产品模型

Studio 首先是 **fiction creation workbench**，不是“运行时 dashboard 外加一个 manuscript tab”。

Creator 默认看到的层级应是：

```text
创作意图
→ 当前创作对象 / blocker
→ evidence / comparison / approval
→ 按需展开 Inspector detail
→ Core query / command / transaction
```

工程层级仍然完整存在，但通过 progressive disclosure 展开：

```text
Project / Resource
→ Session
→ Run
→ Checkpoint
→ Context / Semantic Job / Handoff / Guard
→ Result / Receipt
→ Decision / User Gate
→ optional Settlement
```

Creator Mode 不应该被迫按第二条链路思考。

---

## 03 · Studio Information Architecture

不要把十五个领域全部放成 top-level sidebar item。信息架构应围绕“小说作者回来以后怎么继续工作”来组织。

### Creator Mode

**Desk** —— resume point、当前正文位置、待完成 review/repair、blocker、最近 accepted change、publication status。

**Manuscript** —— Book / Volume / Arc / Unit / Chapter / Scene navigation；支持 writing、reading、comparison、review mode。

**Story** —— Story Loom、Characters、Relationships、World。它们应该是 evidence-rich creative view，而不是通用 CRUD profile。

**Review** —— Reader evidence、Quality Evolution、Context Inspector、branches、continuity findings、pending gates，以及当前 exact candidate 的 `quillframe_production_readiness_v1` gate explanation。

**Publish** —— 通过当前 Core Publication IR/compiler 对 Accepted manuscript 做确定性 compile / validate，并展示 Core 真正支持的 output profile 与 provenance。更丰富的 typesetting controls 必须等对应 Core contract，而不是存在于 UI state 里自说自话。

**Library** —— Corpus 与 Learning evidence。它们是较低频工作，不应该和日常 Manuscript 路径抢一级导航。

### Inspector Mode

Inspector Mode 在同一个 Project 上增加工程视图：

- Runs / checkpoints；
- Context grounding；
- semantic packs / fingerprints / workers；
- handoffs / attempts / consume receipts；
- capabilities / integrations；
- production-readiness gate evidence；
- settlement transaction details；
- publication IR / build / validation provenance。

这里也不展示 private chain-of-thought、hidden regression gold、secret prompt 或无边界 full context dump。

### Command Palette

Command palette 负责高频跨域动作：Open Chapter、Open Character、Inspect Context、Compare Candidates、Show Run Receipt、Check Readiness、Check Capabilities、Preview Publication、Build Export。

Global Search 必须保留 source domain 与 authority class。manuscript text、Canon fact、plan、run、finding、Corpus、docs 不能被压成一个没有标签的模糊 vector result。

---

## 04 · Scene / Chapter Workspace

不要把一套四栏布局固定死。相同 Scene 应根据 task 切换工作模式：

**Focus** —— manuscript 占主导；Context/Quality 只保留少量 actionable badge。

**Analysis** —— manuscript + Reader / Character / Context evidence。

**Compare** —— incumbent/challenger pairwise comparison、已修 findings、保留 strengths、新 regression。

**Review** —— user-visible gate、unresolved findings、当前 candidate fingerprint 的 exact production-readiness conjunction，以及等 typed Core command 成熟以后提供 accept/reject 操作。

手机端 machine design contract 要求 **focus-first** workspace；tablet Inspector 使用 overlay-or-route；desktop 只有在空间允许时才保持 persistent Inspector。这是 viewport-driven progressive disclosure，不是另一套产品模型。

---

## 05 · Run / Context Inspector vertical slice

Phase 1 先验证 Quillframe 最有辨识度的 observability promise：

> **“MODEL THOUGHT THIS WAS SUPPORT” 和 “THIS ACTUALLY ENTERED MODEL CONTEXT” 必须是两件不同的事。**

`quillframe_run_receipt_v1` 已经直接支持这个区别：

- `support_block_ids` —— semantic selection 认为可以支持当前问题的 block；
- `loaded_support_block_ids` —— 实际进入 packet 的 support；
- `dropped_support_block_ids` —— 被识别为 support，但因为 hard budget 没有进入；
- `visibility_excluded_block_ids` —— semantic selection 之前就因为 visibility 被排除；
- `grounding_incomplete_due_budget` —— 因预算不足而无法完整 grounding 的 question。

UI 必须把这些做成不同视觉 channel。把它们合并成一个 “Relevant Context” 列表会直接丢失 Core 已经提供的信息。

Receipt 本身没有每个 block 的 authority、source、inclusion reason、lifecycle tier 或全文。Studio 因此明确显示“这个 receipt 中不可用；需要 Context Inspector projection”，绝不通过 block ID 猜出来。

---

## 06 · Data Honesty visual grammar

Studio 至少需要四个彼此正交的视觉维度，不能让一种颜色同时承担所有语义。

**Domain** —— Project / Runtime / Editorial / Evidence。继续使用现有 Story Loom domain color。

**Authority** —— locked / accepted / active_plan / review / proposal / derived / runtime。Authority 必须有文字 label/badge；一个 mint card 永远不能单独证明“这是 Canon”。

**Execution status** —— ready / running / pending / blocked / failed / complete / unsupported。至少同时使用 label + icon/shape + color。

**Provenance** —— source run、contract、worker、artifact fingerprint、readiness receipt、publication source fingerprint、build result、settlement transaction。surface 可以截断，完整值必须能一键展开。

Core 没有定义 calibrated measurement 时，UI 禁止发明看起来很科学的百分比。`quillframe_production_readiness_v1` 是 typed gate status 的 conjunction，不是质量百分比。

---

## 07 · Design System direction

**`assets/brand/tokens.json` 是 Quillframe product-token authority。** 当前 schema 已升级为 `quillframe_brand_tokens_v2`，同时包含 Story Loom visual semantics 与 machine-readable app constraints。

当前 live dependency chain 是：

```text
Quillframe Story Loom v2 tokens
→ assets/brand/weiui.integration.json
→ @weiui/tokens + @weiui/css
→ assets/brand/story-loom.weiui.css (`wui-theme`)
→ SolidJS product surfaces
```

没有 planned `@weiui/react` runtime layer。Integration contract 明确禁止 Phase 2C 使用 `@weiui/react` 与 `@weiui/headless`，并要求 `runtime_javascript_from_weiui=false`。

所有权继续明确分开：

- Quillframe 拥有 Story Loom domain semantics、authority/status/provenance encoding、typography roles、density、responsive/i18n interaction rules 与视觉人格；
- WeiUI 拥有 generic reusable token/CSS primitives 与公开 CSS/token contracts；
- `weiui.integration.json` 拥有 exact upstream pin 与 consumption boundary；
- `story-loom.weiui.css` 拥有到 WeiUI variables + Quillframe `--qf-*` semantics 的确定性映射；
- `design_system_quality.py` 拥有 machine-checkable integration gate。

WeiUI 通用的 `success` state 不能被拿来暗示 Accepted Canon、通过的 production-readiness conjunction 或有效 publication artifact。产品 authority 与 validation state 必须继续是分开的、带文字标签的表达通道。

### 已在 `main` 强制执行的 app design invariants

- light + dark roles；
- minimum touch target `44px`；
- focus ring `3px` + `2px` offset；
- mobile-first responsive behavior；
- phone workspace = `focus-first`；
- baseline locales = `en-US`, `zh-CN`；
- 必须使用 CSS logical properties；
- 禁止 fixed-width locale assumptions；
- reduced motion required；
- idle decorative animation forbidden；
- default polling forbidden；
- heavy default component import forbidden；
- required light/dark role contrast ≥ 4.5:1；
- Story Loom theme layer 禁止 `!important` 与 WeiUI component-selector fork。

视觉人格继续保持 editorial、warm、precise：paper-like surface、柔和 radius、thread/bookmark/card motif、克制的小型 delight。不要做 purple-gradient SaaS dashboard，也不要做假的拟物写字台。

---

## 08 · Technical delivery direction

### 一个产品，多种宿主

所有 delivery surface 都通过 typed projection/query/command boundary 消费同一套产品语义。UI framework 与 packaging 不能获得 Core authority。

```text
Studio surface
→ Studio projection/query adapter
→ stable Quillframe Core CLI/schema/query/command contracts
→ Core persistence / deterministic derived build
```

Adapter 可以整理 presentation shape，但不能成为 source of truth，也不能让浏览器去 import random Python internals。

### Phase 2C application stack

选定的 low-overhead application stack 是：

```text
Core public boundary
→ Studio view models
→ SolidJS + TypeScript + Vite + @solidjs/router
→ @weiui/tokens + @weiui/css + story-loom.weiui.css
→ Local Web（first-class）
→ optional Tauri installable host
```

选择这个形状的原因：

- SolidJS 是当前为了最小 idle / incremental UI overhead 选定的 application runtime；
- WeiUI 提供 zero-JavaScript CSS/tokens，不再引入第二套 component runtime；
- Local Web 是完整的一等产品面，不需要桌面宿主时就不承担额外 host overhead；
- Tauri 只负责把同一产品做成 optional installable host，不定义产品语义；
- CLI、Agent Skill、Core tests 与 Framework bundle 都不依赖 SolidJS、Vite、WeiUI runtime JavaScript 或 Tauri。

### Runtime discipline

- 不允许为了让 UI “看起来 live”就默认 polling；
- 不允许 idle decorative animation；
- 公共 Core boundary 支持时优先显式 query/event；
- 低频或较重 route 按需加载，不制造 permanently resident workbench stack；
- installable host 启动 Core subprocess/service 时，lifetime 必须显式、可检查；
- Phase 2C production-ready 前必须实际测量 idle CPU/RAM、first-interaction latency、route chunk cost 与 Core-process lifetime。

仓库明确**不会**因为某个 framework 名声上“很轻”就直接推定真实 runtime performance。

### Typed operations

Creator action 通过显式 Core query/command/transaction + precondition 执行。Solid component、browser adapter 与 Tauri command 都不能直接写 Canon 或 runtime database。

Publication build / validation 同样由 Core 拥有。Studio 可以 package input、dispatch 已支持的 compiler operation、展示 typed result/provenance；但不能静默改写 Accepted text，也不能拿 browser rendering 代替 Core publication validation。

### Host decision

**Tauri 继续作为 optional installable desktop host。** 它不是 primary architecture layer，也不是 Local Web 的前置条件。Tauri package 仍必须实际证明 filesystem/subprocess/CLI/Git/MCP/offline/updater/signing/WebView behavior，以及 idle CPU/RAM/process lifetime，才能称为 production-ready。

未来若改变 application framework 或 host，必须走显式 Product decision；不能静默分叉 Core / product semantics。

---

## 09 · Side Goal roadmap

**Phase 1 — Product Architecture + Read-only Inspector**

- IA、product modes、data-honesty grammar；
- Run / Context Inspector prototype；
- synthetic fixture + responsive visual QA；
- Core consumer gaps 作为 dependency 明确记录。

**Phase 2A — Portable Project Hub / Scene workspace**

- Project Hub projection；
- Scene/Chapter read/review prototype；
- one-product/many-host machine contract。

**Phase 2B — Portable host boundary**

- read-only Host Bridge；
- allowlisted typed operations；
- standards-compatible Agent Skill；
- 不安全 Core read/write 继续 deferred。

**Phase 2C — SolidJS product shell**

- SolidJS + TypeScript + Vite + `@solidjs/router`；
- Local Web first-class；
- Story Loom v2 + exact-pinned zero-JS WeiUI tokens/CSS foundation；
- responsive/i18n/accessibility machine contract 已建立；
- route/workspace implementation 必须继续满足 no-default-polling 与 low-idle-overhead constraints；
- 先让 web/product shell truthfully measurable，再做 optional Tauri packaging。

**Phase 3 — Core Workflow Operations**

- typed review/compare/run action；
- safe Context derived controls；
- 对 exact candidate fingerprint 展示 production-readiness explanation；
- acceptance / settlement handoff surface；
- 不允许 direct store write。

**Phase 4 — Publication Studio**

- 现在可以直接基于已合并的 `quillframe_publication_ir_v1` 与 deterministic compiler 开始；
- 第一阶段只 preview / validate Core 真实支持的四类输出：clean text、Web HTML、print-oriented HTML/CSS、EPUB 3.3；
- release EPUB 必须展示 external EPUBCheck requirement，不能把 internal validation 冒充完整 conformance；
- print-oriented HTML 不能标成 final print PDF；
- richer IR/profile controls、paged-media PDF 与 publication authoring 继续等待 Issue #16 剩余 contracts；
- publication output 始终是 derived / non-Canon，不能静默改写 Accepted manuscript text。

**Phase 5 — Integrations / MCP**

- capability-first integration browser、permission scope、health、provenance；
- 等 stable MCP registry/manifest contract。

---

## 10 · KEEP / REFINE / ADD / DEFER / REJECT

### KEEP

- Story Loom brand、product semantics 与 visual grammar；
- exact-pinned WeiUI zero-JS token/CSS foundation；
- existing documentation 与 design-system QA discipline；
- Core Run Receipt、Context Inspector、Project Adapter、capability、Control Plane substrate；
- Core production-readiness 与 minimum Publication contracts，作为对应产品 surface 的 authority basis；
- #8 继续做 Studio/MCP umbrella，#16 继续承载更大的 Publication/Typesetting 剩余范围；
- CLI、Local Web、optional Tauri、Hosted UI、Agent Skill 共用同一个产品 truth model。

### REFINE

- 通过已合并 `wui-theme` mapping 把 Story Loom 从 documentation 延展到真实 SolidJS application；
- 通过 responsive progressive disclosure 分开 creator density 与 inspector density；
- 把 “semantic support” vs “actually loaded” 变成 Context UX 的 first-class distinction；
- 把 readiness 展示成 exact conjunctive gate evidence，而不是发明质量百分比；
- 用实际 measurement 验证 runtime overhead，而不是把 stack choice 当成性能证明。

### ADD

- SolidJS + TypeScript + Vite + `@solidjs/router` product shell；
- Local Web first-class delivery surface；
- 同一 product shell 上的 optional Tauri package；
- responsive / i18n / accessibility 与 runtime-overhead acceptance measurements；
- Creator Mode / Inspector Mode；
- 当前 Core Publication preview/validation surfaces。

### DEFER

- stable typed Core command 之前的 write-capable Studio operations；
- owning Core contracts 出现以前的 MCP marketplace / manager；
- Issue #16 剩余 contract 之前的 richer Publication authoring、paged-media PDF 与 advanced typesetting UI；
- 本地产品契约并不需要的 production cloud/auth/collaboration infrastructure。

### REJECT

- `@weiui/react` 或 `@weiui/headless` 作为 Phase 2C runtime dependencies；
- 第二套 Canon / Memory / Quality / Session / publication-truth store；
- 与 WeiUI CSS/tokens + Story Loom semantics 竞争的第二套 bespoke Studio design system；
- 把 SolidJS / Vite / Tauri 变成 Generic Core correctness 的前置条件；
- default polling 或 idle decorative animation；
- fake engagement / consistency / readiness percentage；
- UI 自己制造 semantic truth；
- publication 阶段由 UI 静默修改 Accepted manuscript text；
- provider brand = capability proof；
- chain-of-thought exposure；
- giant everything-dashboard；
- graph-database-first Story Loom。
