# Quillframe Studio · Product Architecture

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>READ-ONLY CORE</kbd>&nbsp;&nbsp;<kbd>LOW-OVERHEAD PRODUCT SHELL</kbd></p>

This document records the Studio product architecture against live Quillframe Core and Product contracts. It is a consumer specification, not a competing runtime specification. Phase 2C is now directed toward **SolidJS + TypeScript + Vite + `@solidjs/router`**, consuming WeiUI as a **zero-JavaScript CSS/token foundation**. Local Web remains first-class; Tauri is an optional/installable desktop host rather than the center of product architecture.

> **Invariant ✦ `UI CONSUMES CORE STATE. UI DOES NOT INVENT CORE STATE.`**

---

## 01 · Live-repo audit

### Existing side-goal substrate

Quillframe already has substantial Studio substrate:

- Session / Run / Checkpoint identity and a durable Control Plane;
- typed host capability evidence with `capability != authority`;
- native Project resolution for logical project domains;
- `quillframe_context_inspector_v2` for authority-aware, stage-aware context views and safe derived controls;
- `quillframe_run_receipt_v1` for metadata-only execution evidence;
- `quillframe_production_readiness_v1` for same-fingerprint conjunctive user-visible readiness;
- `quillframe_publication_ir_v1` plus a deterministic compiler for Accepted manuscript text;
- semantic contract IDs, input/result fingerprints, worker references and typed statuses;
- Quality Evolution, Reader Expectations, State Graph, scenario branches and settlement receipts as non-Canon evidence/state machines;
- deterministic docs, design-system, Framework-contract and release CI.

This is enough to build useful product surfaces without creating a Studio database or a second publication/quality truth model.

### Existing Story Loom / WeiUI foundation

Story Loom is now an application-ready foundation rather than documentation-only styling.

Current `main` includes:

- `assets/brand/tokens.json` with schema `quillframe_brand_tokens_v2`;
- `assets/brand/weiui.integration.json`, which pins the generic WeiUI foundation to exact commit `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`;
- only `@weiui/tokens` and `@weiui/css` allowed from WeiUI for Phase 2C;
- `@weiui/react` and `@weiui/headless` explicitly forbidden as Studio runtime dependencies;
- `assets/brand/story-loom.weiui.css`, loaded in `wui-theme` after WeiUI tokens/CSS;
- zero required WeiUI runtime JavaScript;
- machine-owned light/dark theme roles plus Quillframe `--qf-*` product-semantic variables;
- mobile-first breakpoints, 44px minimum touch target, focus geometry, `en-US` + `zh-CN`, logical properties, reduced-motion and no-default-polling rules;
- `scripts/design_system_quality.py` + CI enforcing pin/provenance, CSS layering, contrast, mobile/i18n/a11y and runtime-overhead invariants.

Story Loom still owns Quillframe product semantics. WeiUI owns generic CSS/token primitives. The integration contract is a dependency boundary, not a transfer of product identity or story authority.

### Current Core interfaces Studio can consume directly

| Core contract | Studio use | Authority note |
|---|---|---|
| `quillframe_run_receipt_v1` | Run summary, actual context loading, semantic jobs, guard outcomes | execution evidence only |
| `quillframe_context_inspector_v2` | context item source, authority, stage eligibility, explicit derived controls | overlay/proposal; not Canon |
| `quillframe_production_readiness_v1` | explain which same-fingerprint gates pass/fail/pending | deterministic gate evidence; not a literary score and not Canon |
| `quillframe_publication_ir_v1` + `publication/compiler.py` | deterministic Accepted-text compilation to clean text, Web HTML, print-oriented HTML/CSS and EPUB 3.3 | derived output; exact text preservation; `authority=false` |
| Session / Run identity | navigation, history, resume affordances | operational identity |
| Control Plane | event/handoff/result/consume lineage | operational evidence |
| `quillframe_host_capabilities_v1` | integrations/capability health | capability is not authority |
| `quillframe_project_v1_0` + `quillframe_project_context_v1_0` | Project Hub native five-key manifest, CH001, fingerprint, and `.quillframe/data` boundary | browser projection only; `authority=false` |
| semantic contract catalog | Semantic Pack Inspector labels and deep links | contract metadata |
| settlement receipts | settlement review and failure explanation | settlement semantics remain Core-owned |

### Core consumer gaps

Studio must not paper over these gaps locally:

1. the merged Run Receipt tool/schema is not yet discoverable from `HARNESS_MANIFEST.yaml`;
2. `run_receipt.py` emits `run.receipt_recorded`, while the current event schema enum does not advertise that event type;
3. Studio needs a stable read/query boundary for receipts and Control Plane views rather than reading SQLite internals;
4. Publication has a real minimum Core, but Issue #16 still owns richer semantic IR/profile controls, paged-media PDF, broader validation/visual-regression hooks, and higher-level publication authoring/preview.

These are Core consumer requirements. Studio stays thin and consumes only formal public primitives that actually exist.

---

## 02 · Product model

Studio is a **fiction creation workbench**, not a runtime dashboard with a manuscript tab attached.

The default hierarchy is:

```text
Creator intent
→ creative object or blocker
→ evidence / comparison / approval
→ optional Inspector detail
→ Core query / command / transaction
```

The runtime hierarchy is still available, but progressively disclosed:

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

The second hierarchy never replaces the first in Creator Mode.

---

## 03 · Information architecture

Do not make fifteen top-level sidebar items. Group the product around how a novelist returns to work.

### Creator Mode

**Desk** — resume point, current manuscript position, pending review/repair, blockers, recent accepted changes and publication status.

**Manuscript** — Book / Volume / Arc / Unit / Chapter / Scene navigation; writing, reading, comparison and review modes.

**Story** — Story Loom, characters, relationships and world. These are evidence-rich creative views, not generic CRUD profiles.

**Review** — Reader evidence, Quality Evolution, Context Inspector, branches, continuity findings, pending gates, and `quillframe_production_readiness_v1` explanations for the exact candidate under review.

**Publish** — deterministic compilation/validation of Accepted manuscript through the current Publication IR/compiler, plus preview/provenance for the output profiles the Core actually supports. Richer typesetting controls must wait for corresponding Core contracts rather than being invented in UI state.

**Library** — Corpus and Learning evidence. Lower-frequency than the manuscript path, so it should not compete with daily writing navigation.

### Inspector Mode

Inspector Mode expands the same project with engineering views:

- Runs / checkpoints;
- Context grounding;
- semantic packs / fingerprints / workers;
- handoffs / attempts / consume receipts;
- capabilities / integrations;
- production-readiness gate evidence;
- settlement transaction details;
- publication IR / build / validation provenance.

It does not reveal private chain-of-thought, hidden regression gold, secret prompts, or unbounded context dumps.

### Command palette

The command palette becomes the high-frequency cross-cutting navigation layer: Open Chapter, Open Character, Inspect Context, Compare Candidates, Show Run Receipt, Check Readiness, Check Capabilities, Preview Publication, Build Export.

Search results must retain their source domain and authority class; manuscript text, Canon facts, plans, runs, findings, Corpus and docs are not flattened into one unlabeled vector result.

---

## 04 · Scene / Chapter workspace

One permanent four-pane layout is too rigid. The same underlying scene should support task-specific modes:

**Focus** — manuscript dominates; contextual signals collapse to small, actionable badges.

**Analysis** — manuscript plus reader/character/context evidence.

**Compare** — incumbent/challenger pairwise comparison, repaired findings, preserved strengths and regressions.

**Review** — user-visible gate, unresolved findings, the exact production-readiness conjunction for this candidate fingerprint, and acceptance/reject actions once typed Core commands exist.

On phones, the machine design contract requires a **focus-first** workspace. Tablet Inspector becomes overlay-or-route; desktop may keep Inspector persistent only when space allows. This is progressive disclosure by viewport, not a different product model.

---

## 05 · Run / Context Inspector vertical slice

Phase 1 proves the most distinctive observability promise:

> **“The model thought this evidence supported the question” is different from “this evidence actually entered the model context.”**

`quillframe_run_receipt_v1` supports this distinction directly through:

- `support_block_ids` — support identified by the semantic selection result;
- `loaded_support_block_ids` — support actually loaded;
- `dropped_support_block_ids` — support identified but excluded by the hard budget;
- `visibility_excluded_block_ids` — items excluded before semantic selection;
- `grounding_incomplete_due_budget` — questions whose support could not fully enter the packet.

The UI must preserve these as different visual channels. A single “Relevant context” list would destroy information.

The receipt does **not** include each block's authority, source, inclusion reason, lifecycle tier or full text. Studio therefore says “details unavailable in this receipt; open Context Inspector projection” instead of inferring them.

---

## 06 · Data-honesty grammar

Studio visual semantics need four orthogonal dimensions. Never overload one color with all of them.

**Domain** — Project / Runtime / Editorial / Evidence. Existing Story Loom colors own this dimension.

**Authority** — locked / accepted / active_plan / review / proposal / derived / runtime. Authority must be written as a label or badge; a mint card is never sufficient evidence of Canon status.

**Execution status** — ready / running / pending / blocked / failed / complete / unsupported. Use label + icon/shape + color.

**Provenance** — source run, contract, worker, artifact fingerprint, readiness receipt, publication source fingerprint, build result, settlement transaction. Truncation is allowed in the surface; full values remain one click away.

Never invent calibrated-looking percentages when the Core does not define a calibrated measurement. `quillframe_production_readiness_v1` is a conjunction of typed gate statuses, not a quality percentage.

---

## 07 · Design-system direction

**`assets/brand/tokens.json` is the Quillframe product-token authority.** It is now `quillframe_brand_tokens_v2` and includes both Story Loom visual semantics and machine-readable app constraints.

The live dependency chain is:

```text
Quillframe Story Loom v2 tokens
→ assets/brand/weiui.integration.json
→ @weiui/tokens + @weiui/css
→ assets/brand/story-loom.weiui.css (`wui-theme`)
→ SolidJS product surfaces
```

There is no planned `@weiui/react` runtime layer. The integration contract explicitly forbids `@weiui/react` and `@weiui/headless` for Phase 2C and requires `runtime_javascript_from_weiui=false`.

The ownership split remains explicit:

- Quillframe owns Story Loom domain semantics, authority/status/provenance encodings, typography roles, density, responsive/i18n interaction rules and visual personality;
- WeiUI owns generic reusable token/CSS primitives and its public CSS/token contracts;
- `weiui.integration.json` owns the exact upstream pin and consumption boundary;
- `story-loom.weiui.css` owns deterministic mapping into WeiUI variables plus Quillframe `--qf-*` semantics;
- `design_system_quality.py` owns the deterministic machine-checkable integration gate.

A generic WeiUI `success` state must never become shorthand for Accepted Canon, a passing production-readiness conjunction, or a valid publication artifact. Product authority and validation state remain separate labeled channels.

### App design invariants already enforced on `main`

- light + dark roles;
- minimum touch target `44px`;
- focus ring `3px` with `2px` offset;
- mobile-first responsive behavior;
- phone workspace = `focus-first`;
- baseline locales = `en-US`, `zh-CN`;
- CSS logical properties required;
- fixed-width locale assumptions forbidden;
- reduced motion required;
- idle decorative animation forbidden;
- default polling forbidden;
- heavy default component import forbidden;
- required light/dark role contrast ≥ 4.5:1;
- no `!important` or WeiUI component-selector forks in the Story Loom theme layer.

The visual personality remains editorial, warm and precise: paper-like surfaces, soft radii, thread/bookmark/card motifs, small intentional delight. No gradient-card SaaS dashboard and no faux-skeuomorphic writing desk.

---

## 08 · Technical delivery direction

### One product, many hosts

Every delivery surface consumes the same product semantics through typed projections/query/command boundaries. UI frameworks and packaging do not become Core authority.

```text
Studio surface
→ Studio projection/query adapter
→ stable Quillframe Core CLI/schema/query/command contracts
→ Core persistence / deterministic derived build
```

The adapter may normalize presentation shape, but it never becomes a source of truth and never reaches into random Python internals.

### Phase 2C application stack

The selected low-overhead application stack is:

```text
Core public boundary
→ Studio view models
→ SolidJS + TypeScript + Vite + @solidjs/router
→ @weiui/tokens + @weiui/css + story-loom.weiui.css
→ Local Web (first-class)
→ optional Tauri installable host
```

Why this shape:

- SolidJS is the selected application runtime for minimum idle/incremental UI overhead;
- WeiUI contributes zero-JavaScript CSS/tokens, not a second component runtime;
- Local Web remains a complete first-class product surface and avoids desktop-host overhead when it is unnecessary;
- Tauri packages the same product as an optional installable host rather than defining product semantics;
- CLI, Agent Skill, Core tests, and Framework bundle remain independent of SolidJS, Vite, WeiUI runtime JavaScript, and Tauri.

### Runtime discipline

- no polling by default just to make the UI look live;
- no idle decorative animation;
- prefer explicit queries/events when public Core boundaries support them;
- lazy-load low-frequency/heavy product routes rather than creating a permanently resident workbench stack;
- make Core subprocess/service lifetime explicit and inspectable when an installable host uses one;
- measure actual idle CPU/RAM, first-interaction latency, route chunk cost and Core-process lifetime before calling Phase 2C production-ready.

The repository deliberately does **not** infer runtime performance from framework reputation alone.

### Typed operations

Creator actions call explicit Core queries/commands/transactions with preconditions. Solid components, browser adapters and Tauri commands do not mutate Canon or runtime databases directly.

Publication build/validation is also Core-owned. Studio may package inputs, dispatch supported compiler operations, and display typed result/provenance; it does not silently rewrite Accepted text or substitute browser rendering for Core publication validation.

### Host decision

**Tauri remains selected as the optional installable desktop host.** It is not the primary architecture layer and not required for Local Web. A Tauri package must still prove filesystem/subprocess/CLI/Git/MCP/offline/updater/signing/WebView behavior plus idle CPU/RAM/process lifetime before it is production-ready.

Changing the application framework or host later requires an explicit Product decision; it must never silently fork Core/product semantics.

---

## 09 · Delivery roadmap

**Phase 1 — Product architecture + read-only Inspector**

- IA, product modes and data-honesty grammar;
- Run / Context Inspector prototype;
- synthetic fixtures and responsive visual QA;
- Core consumer gaps recorded as dependencies.

**Phase 2A — Portable Project Hub / Scene workspace**

- Project Hub projection;
- Scene/Chapter read/review prototype;
- one-product/many-host machine contract.

**Phase 2B — Portable host boundary**

- read-only Host Bridge;
- allowlisted typed operations;
- standards-compatible Agent Skill;
- unsafe Core reads/writes remain deferred.

**Phase 2C — SolidJS product shell**

- SolidJS + TypeScript + Vite + `@solidjs/router`;
- Local Web first-class;
- Story Loom v2 + exact-pinned zero-JS WeiUI tokens/CSS foundation;
- responsive/i18n/accessibility machine contract already established;
- route/workspace implementation must preserve no-default-polling and low-idle-overhead constraints;
- optional Tauri packaging after the web/product shell is truthful and measurable.

**Phase 3 — Core workflow operations**

- typed review/compare/run actions;
- safe Context derived controls;
- production-readiness explanation for the exact candidate fingerprint;
- acceptance and settlement handoff surfaces;
- no direct store writes.

**Phase 4 — Publication Studio**

- can begin against merged `quillframe_publication_ir_v1` and deterministic compiler;
- first scope previews/validates only Core-supported outputs: clean text, Web HTML, print-oriented HTML/CSS and EPUB 3.3;
- release EPUB surfaces the external EPUBCheck requirement rather than treating internal validation as full conformance;
- print-oriented HTML is not labeled final print PDF;
- richer IR/profile controls, paged-media PDF and publication authoring wait for remaining Issue #16 contracts;
- publication output stays derived/non-Canon and cannot silently rewrite Accepted manuscript text.

**Phase 5 — Integrations / MCP**

- capability-first integration browser, permission scope, health and provenance;
- only after a stable MCP registry/manifest contract exists.

---

## 10 · Decision ledger

### KEEP

- Story Loom brand, product semantics and visual grammar;
- exact-pinned WeiUI zero-JS token/CSS foundation;
- existing documentation and design-system QA discipline;
- Core Run Receipt, Context Inspector, native Project resolution, capability and Control Plane substrates;
- Core production-readiness and minimum Publication contracts as the authoritative basis for those product surfaces;
- #8 as the Studio/MCP umbrella and #16 as the broader remaining Publication/Typesetting scope;
- one product truth model across CLI, Local Web, optional Tauri, hosted UI and Agent Skill.

### REFINE

- extend Story Loom from documentation into the real SolidJS application through the merged `wui-theme` mapping;
- split creator-facing and inspector-facing density through responsive progressive disclosure;
- make “semantic support” vs “actually loaded” a first-class Context interaction;
- expose readiness as exact conjunctive gate evidence rather than invented quality percentages;
- measure runtime overhead instead of assuming stack choice proves it.

### ADD

- SolidJS + TypeScript + Vite + `@solidjs/router` product shell;
- Local Web as first-class delivery surface;
- optional Tauri package over the same product shell;
- responsive/i18n/accessibility and runtime-overhead acceptance measurements;
- Creator Mode / Inspector Mode;
- current Core Publication preview/validation surfaces.

### DEFER

- write-capable Studio operations until stable typed Core commands exist;
- MCP marketplace/manager until the owning Core contracts exist;
- richer Publication authoring, paged-media PDF and advanced typesetting UI until remaining #16 contracts exist;
- production cloud/auth/collaboration infrastructure not required by the local product contract.

### REJECT

- `@weiui/react` or `@weiui/headless` as Phase 2C runtime dependencies;
- a second Canon/Memory/quality/session/publication-truth store;
- a second bespoke Studio design system competing with WeiUI CSS/tokens + Story Loom semantics;
- making SolidJS/Vite/Tauri prerequisites for Generic Core correctness;
- default polling or idle decorative animation;
- fake engagement, consistency or readiness percentages;
- UI-authored semantic truth;
- UI-side mutation of Accepted manuscript text during publication;
- provider brand as capability proof;
- chain-of-thought exposure;
- giant everything-dashboard;
- graph-database-first Story Loom.
