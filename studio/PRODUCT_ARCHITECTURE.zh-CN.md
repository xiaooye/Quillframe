# NovelForge Studio · 产品架构

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>PHASE 1</kbd>&nbsp;&nbsp;<kbd>READ-ONLY FIRST</kbd></p>

本文把第一版 Studio 产品架构冻结在当前 live NovelForge Core contracts 之上。它是一份 consumer specification，不是另一份 runtime specification。

> **不变量 ✦ `UI CONSUMES CORE STATE. UI DOES NOT INVENT CORE STATE.`**

---

## 01 · Live repo audit

### 已经存在的 Side Goal substrate

NovelForge 其实已经具备相当多 Studio 底座：

- Session / Run / Checkpoint identity 与持久 Control Plane；
- typed host capability evidence，并明确 `capability != authority`；
- Project Adapter 对 Project logical domains 的解析；
- `novelforge_context_inspector_v2`：authority-aware、stage-aware 的 Context view 与安全 derived controls；
- `novelforge_run_receipt_v1`：metadata-only execution evidence；
- semantic contract ID、input/result fingerprint、worker reference 与 typed status；
- Quality Evolution、Reader Expectations、State Graph、scenario branch 与 settlement receipt 等非 Canon 证据/状态机制；
- deterministic docs QA 与 release CI。

这些东西已经足够做出有价值的 observability prototype，不需要另建 Studio database。

### 已有 docs / UI / visual work

Story Loom 文档升级应该被当成基础，而不是推倒重来的实验。现有成果包括：

- 原创 mark 与 lockup；
- `assets/brand/tokens.json` 这一 machine-readable token source；
- Project / Runtime / Editorial / Evidence / Validated / Rejected 的稳定视觉家族；
- diagram lane / node / edge / motif grammar；
- `assets/ui/` 里的中英双语产品级视觉；
- Tier-A visual 必须经过 desktop + narrow real-render inspection；
- 文档 lifecycle 与 QA governance。

Studio 应把这套系统从 static documentation 延展到 interaction design，而不是重新发明一套视觉语言。

### Studio 可以直接消费的 Core interfaces

| Core contract | Studio 用途 | Authority 边界 |
|---|---|---|
| `novelforge_run_receipt_v1` | Run summary、真实 Context loading、semantic jobs、guard outcomes | 只属于 execution evidence |
| `novelforge_context_inspector_v2` | Context source、authority、stage eligibility、derived controls | overlay/proposal；不是 Canon |
| Session / Run identity | navigation、history、resume affordance | operational identity |
| Control Plane | event/handoff/result/consume lineage | operational evidence |
| `novelforge_host_capabilities_v1` | integration/capability health | capability 不是 authority |
| `novelforge_project_adapter_resolution_v1` | Project Hub logical domains / paths | 只负责 path classification |
| semantic contract catalog | Semantic Pack Inspector label / deep link | contract metadata |
| settlement receipts | settlement review / failure explanation | settlement semantics 仍由 Core 拥有 |

### 尚缺的 Core consumer interfaces

Studio 不能在 UI 里私自补这些缺口：

1. 已合并的 Run Receipt tool/schema 目前还没有从 `HARNESS_MANIFEST.yaml` 暴露出来；
2. `run_receipt.py` 会产生 `run.receipt_recorded`，但当前 event schema enum 没有公开这个 event type；
3. Studio 最终需要稳定的 receipt / Control Plane read-query boundary，不能直接读 SQLite internals；
4. Publication / Typesetting 目前仍是 issue-level contract target，本设计不假设已经存在正式 Publication IR/Profile implementation。

这些都属于 Core consumer requirement。Phase 1 只做 thin、read-only adapter，不在 Side Goal 里造替代 schema。

---

## 02 · 产品模型

Studio 首先是 **fiction creation workbench**，不是“运行时 dashboard 外加一个 manuscript tab”。

Creator 默认看到的层级应是：

```text
创作意图
→ 当前创作对象 / blocker
→ evidence / comparison / approval
→ 按需展开 Inspector detail
→ Core command / transaction
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

**Review** —— Reader evidence、Quality Evolution、Context Inspector、branches、continuity findings、pending gates。

**Publish** —— 等 Core Publication contracts 可用后，提供 profile-based preview、validation、deterministic build/export。

**Library** —— Corpus 与 Learning evidence。它们是较低频工作，不应该和日常 Manuscript 路径抢一级导航。

### Inspector Mode

Inspector Mode 在同一个 Project 上增加工程视图：

- Runs / checkpoints；
- Context grounding；
- semantic packs / fingerprints / workers；
- handoffs / attempts / consume receipts；
- capabilities / integrations；
- settlement transaction details；
- build / export provenance。

这里也不展示 private chain-of-thought、hidden regression gold、secret prompt 或无边界 full context dump。

### Command Palette

Command palette 负责高频跨域动作：Open Chapter、Open Character、Inspect Context、Compare Candidates、Show Run Receipt、Check Capabilities、Preview Publication、Build Export。

Global Search 必须保留 source domain 与 authority class。manuscript text、Canon fact、plan、run、finding、Corpus、docs 不能被压成一个没有标签的模糊 vector result。

---

## 04 · Scene / Chapter Workspace

不要把一套四栏布局固定死。相同 Scene 应根据 task 切换工作模式：

**Focus** —— manuscript 占主导；Context/Quality 只保留少量 actionable badge。

**Analysis** —— manuscript + Reader / Character / Context evidence。

**Compare** —— incumbent/challenger pairwise comparison、已修 findings、保留 strengths、新 regression。

**Review** —— user-visible gate、unresolved findings，以及等 typed Core command 成熟以后提供 accept/reject 操作。

底部 activity rail 可以按需展开 run / branch / revision lineage，但不应该永远像 CI console 一样占据屏幕。

---

## 05 · Run / Context Inspector vertical slice

Phase 1 先验证 NovelForge 最有辨识度的 observability promise：

> **“MODEL THOUGHT THIS WAS SUPPORT” 和 “THIS ACTUALLY ENTERED MODEL CONTEXT” 必须是两件不同的事。**

`novelforge_run_receipt_v1` 已经直接支持这个区别：

- `support_block_ids` —— semantic selection 认为可以支持当前问题的 block；
- `loaded_support_block_ids` —— 实际进入 packet 的 support；
- `dropped_support_block_ids` —— 被识别为 support，但因为 hard budget 没有进入；
- `visibility_excluded_block_ids` —— semantic selection 之前就因为 visibility 被排除；
- `grounding_incomplete_due_budget` —— 因预算不足而无法完整 grounding 的 question。

UI 必须把这些做成不同视觉 channel。把它们合并成一个 “Relevant Context” 列表会直接丢失 Core 已经提供的信息。

Receipt 本身没有每个 block 的 authority、source、inclusion reason、lifecycle tier 或全文。Phase 1 因此明确显示“这个 receipt 中不可用；需要 Context Inspector projection”，绝不通过 block ID 猜出来。

---

## 06 · Data Honesty visual grammar

Studio 至少需要四个彼此正交的视觉维度，不能让一种颜色同时承担所有语义。

**Domain** —— Project / Runtime / Editorial / Evidence。继续使用现有 Story Loom domain color。

**Authority** —— locked / accepted / active_plan / review / proposal / derived / runtime。Authority 必须有文字 label/badge；一个 mint card 永远不能单独证明“这是 Canon”。

**Execution status** —— ready / running / pending / blocked / failed / complete / unsupported。至少同时使用 label + icon/shape + color。

**Provenance** —— source run、contract、worker、artifact fingerprint、receipt、settlement transaction。surface 可以截断，完整值必须能一键展开。

Core 没有定义 calibrated measurement 时，UI 禁止发明看起来很科学的百分比。

---

## 07 · Design System direction

**KEEP `assets/brand/tokens.json` 作为 brand token source。** 不再创建一份独立 `studio-colors.json`。

未来的 interactive token layer 只能从它派生，并补充交互层真正需要的维度：

- appearance：light / dark / system；
- density：comfortable / workstation；
- typography roles：manuscript / UI / metadata-mono；
- focus ring 与 keyboard state；
- elevation / border / interactive surface states；
- motion duration 与 reduced-motion；
- viewport / breakpoint semantics；
- authority 与 execution-status encoding，并与 domain color 分离。

视觉人格继续保持 editorial、warm、precise：paper-like surface、柔和 radius、thread/bookmark/card motif、克制的小型 delight。不要做 purple-gradient SaaS dashboard，也不要做假的拟物写字台。

---

## 08 · Technical delivery options

### Phase 1 — Contract probe

Zero-dependency static prototype + synthetic fixture + 本地直接加载真实 receipt JSON。先验证 IA 与 data honesty，不冻结 framework choice。

### Phase 2 — Local read-only Studio

只有 front-end boundary 明确以后才选 Web stack。目标架构：

```text
Studio UI
→ Studio projection/query adapter
→ stable NovelForge Core CLI/schema/query contracts
→ Core persistence
```

Projection adapter 可以整理 presentation shape，但不能成为 source of truth，也不能让浏览器去 import random Python internals。

### Phase 3 — Typed operations

Creator action 通过显式 Core command/transaction + precondition 执行。UI component 不直接写 Canon 或 runtime database。

### Desktop decision gate

等我们真正测清 local filesystem、subprocess/CLI、Git、MCP、offline、renderer process、updater、sandbox、signing 与 WebView consistency 的需求以后，再决定 Electron / Tauri / hybrid。

---

## 09 · Side Goal roadmap

**Phase 1 — Product Architecture + Read-only Inspector**

- IA、product modes、data-honesty grammar；
- Run / Context Inspector prototype；
- synthetic fixture + responsive visual QA；
- Core consumer gaps 作为 dependency 明确记录。

**Phase 2 — Read-only Studio Shell**

- Project Hub 基于 Project Adapter projection；
- Scene/Chapter read/review surface；
- Runs、Context、capability inspection；
- command palette + domain-aware search；
- visual regression harness。

**Phase 3 — Core Workflow Operations**

- typed review/compare/run action；
- safe Context derived controls；
- acceptance / settlement handoff surface；
- 不允许 direct store write。

**Phase 4 — Publication Studio**

- 只有 official Publication IR / Typesetting Profile contracts 存在后才正式开始；
- screen/mobile/ebook/print preview 消费 deterministic renderer output，或者严格 contract-faithful preview adapter；
- publication-only text transform 在 Core 要求时必须走 visible non-Canon diff / approval semantics。

**Phase 5 — Integrations / MCP**

- capability-first integration browser、permission scope、health、provenance；
- 等 stable MCP registry/manifest contract。

**Phase 6 — Installable Distribution**

- 依据真实 local requirements 决定 packaging，不按技术偏好下注。

---

## 10 · KEEP / REFINE / ADD / DEFER / REJECT

### KEEP

- Story Loom brand、tokens、assets、diagram grammar；
- 刚完成的 documentation overhaul 与 visual QA discipline；
- Core Run Receipt、Context Inspector、Project Adapter、capability、Control Plane substrate；
- #8 继续做 umbrella，Publication 继续作为独立 dependency。

### REFINE

- Story Loom 从 documentation 延展为 interactive product grammar；
- 通过 progressive disclosure 分开 creator density 与 inspector density；
- 把 “semantic support” vs “actually loaded” 变成 Context UX 的 first-class distinction；
- 改善 newcomer/task-oriented docs entry path，但不推翻刚做完的视觉升级。

### ADD

- Studio product architecture + view-model boundary；
- Creator Mode / Inspector Mode；
- read-only Inspector vertical slice；
- synthetic public demo fixture；
- application shell 成立后加入 responsive / visual regression coverage。

### DEFER

- production React app；
- desktop wrapper；
- MCP marketplace / manager；
- Core IR/Profile 之前的 Publication editor/preview implementation；
- stable typed command 之前的 write-capable Studio operations。

### REJECT

- 第二套 Canon / Memory / Quality / Session store；
- fake engagement / consistency score；
- UI 自己制造 semantic truth；
- provider brand = capability proof；
- chain-of-thought exposure；
- giant everything-dashboard；
- graph-database-first Story Loom；
- 按个人技术喜好提前选择 desktop stack。
