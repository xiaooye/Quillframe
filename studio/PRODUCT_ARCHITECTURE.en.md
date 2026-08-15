# NovelForge Studio · Product Architecture

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>READ-ONLY CORE</kbd>&nbsp;&nbsp;<kbd>PRODUCT SHELL DIRECTION</kbd></p>

This document records the Studio product architecture against live NovelForge Core contracts. It is a consumer specification, not a competing runtime specification. The future installable shell direction is now selected as **Tauri + React + WeiUI**; that product choice does not make the application a shipped capability.

> **Invariant ✦ `UI CONSUMES CORE STATE. UI DOES NOT INVENT CORE STATE.`**

---

## 01 · Live-repo audit

### Existing side-goal substrate

NovelForge already has more Studio substrate than a first glance suggests:

- Session / Run / Checkpoint identity and a durable Control Plane;
- typed host capability evidence with `capability != authority`;
- Project Adapter resolution for logical project domains;
- `novelforge_context_inspector_v2` for authority-aware, stage-aware context views and safe derived controls;
- `novelforge_run_receipt_v1` for metadata-only execution evidence;
- semantic contract IDs, input/result fingerprints, worker references and typed statuses;
- Quality Evolution, Reader Expectations, State Graph, scenario branches and settlement receipts as non-Canon evidence/state machines;
- deterministic docs QA and release CI.

This is enough to prototype useful observability without creating a Studio database.

### Existing product / visual work

The Story Loom documentation work is a foundation, not a discarded experiment. It already provides:

- an original mark and lockup;
- a machine-readable token source at `assets/brand/tokens.json`;
- semantic visual families for Project, Runtime, Editorial, Evidence, Validated and Rejected states;
- diagram lane, node, edge and motif grammar;
- bilingual product visuals under `assets/ui/`;
- mandatory desktop + narrow render inspection for Tier-A visuals;
- documentation lifecycle and QA governance.

Studio should extend this system from static documentation into interaction design rather than starting a second visual language.

### Current Core interfaces Studio can consume directly

| Core contract | Studio use | Authority note |
|---|---|---|
| `novelforge_run_receipt_v1` | Run summary, actual context loading, semantic jobs, guard outcomes | execution evidence only |
| `novelforge_context_inspector_v2` | context item source, authority, stage eligibility, explicit derived controls | overlay/proposal; not Canon |
| Session / Run identity | navigation, history, resume affordances | operational identity |
| Control Plane | event/handoff/result/consume lineage | operational evidence |
| `novelforge_host_capabilities_v1` | integrations/capability health | capability is not authority |
| `novelforge_project_adapter_resolution_v1` | Project Hub logical domains and paths | path classification only |
| semantic contract catalog | Semantic Pack Inspector labels and deep links | contract metadata |
| settlement receipts | settlement review and failure explanation | settlement semantics remain Core-owned |

### Core consumer gaps

Studio must not paper over these gaps locally:

1. the merged Run Receipt tool/schema is not yet discoverable from `HARNESS_MANIFEST.yaml`;
2. `run_receipt.py` emits `run.receipt_recorded`, while the current event schema enum does not advertise that event type;
3. Studio needs a stable read/query boundary for receipts and Control Plane views rather than reading SQLite internals;
4. Publication / Typesetting is currently an issue-level contract target; no official Publication IR/Profile implementation is assumed here.

These are Core consumer requirements. Read-only Studio adapters stay thin until the owning workstream exposes the formal primitive.

---

## 02 · Product model

Studio is a **fiction creation workbench**, not a runtime dashboard with a manuscript tab attached.

The default hierarchy is:

```text
Creator intent
→ creative object or blocker
→ evidence / comparison / approval
→ optional Inspector detail
→ Core command or transaction
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

**Review** — Reader evidence, Quality Evolution, Context Inspector, branches, continuity findings and pending gates.

**Publish** — profile-based preview, validation and deterministic build/export when Core Publication contracts exist.

**Library** — Corpus and Learning evidence. Lower-frequency than the manuscript path, so it should not compete with daily writing navigation.

### Inspector Mode

Inspector Mode expands the same project with engineering views:

- Runs / checkpoints;
- Context grounding;
- semantic packs / fingerprints / workers;
- handoffs / attempts / consume receipts;
- capabilities / integrations;
- settlement transaction details;
- build / export provenance.

It does not reveal private chain-of-thought, hidden regression gold, secret prompts, or unbounded context dumps.

### Command palette

The command palette becomes the high-frequency cross-cutting navigation layer: Open Chapter, Open Character, Inspect Context, Compare Candidates, Show Run Receipt, Check Capabilities, Preview Publication, Build Export.

Search results must retain their source domain and authority class; manuscript text, Canon facts, plans, runs, findings, Corpus and docs are not flattened into one unlabeled vector result.

---

## 04 · Scene / Chapter workspace

One permanent four-pane layout is too rigid. The same underlying scene should support task-specific modes:

**Focus** — manuscript dominates; contextual signals collapse to small, actionable badges.

**Analysis** — manuscript plus reader/character/context evidence.

**Compare** — incumbent/challenger pairwise comparison, repaired findings, preserved strengths and regressions.

**Review** — user-visible gate, unresolved findings and acceptance/reject actions once typed Core commands exist.

A bottom activity rail can reveal run/branch/revision lineage on demand. It should not become an always-visible CI console.

---

## 05 · Run / Context Inspector vertical slice

Phase 1 proves the most distinctive observability promise:

> **“The model thought this evidence supported the question” is different from “this evidence actually entered the model context.”**

`novelforge_run_receipt_v1` supports this distinction directly through:

- `support_block_ids` — support identified by the semantic selection result;
- `loaded_support_block_ids` — support actually loaded;
- `dropped_support_block_ids` — support identified but excluded by the hard budget;
- `visibility_excluded_block_ids` — items excluded before semantic selection;
- `grounding_incomplete_due_budget` — questions whose support could not fully enter the packet.

The UI must preserve these as different visual channels. A single “Relevant context” list would destroy information.

The receipt does **not** include each block's authority, source, inclusion reason, lifecycle tier or full text. Phase 1 therefore says “details unavailable in this receipt; open Context Inspector projection” instead of inferring them.

---

## 06 · Data-honesty grammar

Studio visual semantics need four orthogonal dimensions. Never overload one color with all of them.

**Domain** — Project / Runtime / Editorial / Evidence. Existing Story Loom colors own this dimension.

**Authority** — locked / accepted / active_plan / review / proposal / derived / runtime. Authority must be written as a label or badge; a mint card is never sufficient evidence of Canon status.

**Execution status** — ready / running / pending / blocked / failed / complete / unsupported. Use label + icon/shape + color.

**Provenance** — source run, contract, worker, artifact fingerprint, receipt or settlement transaction. Truncation is allowed in the surface; full values remain one click away.

Never invent calibrated-looking percentages when the Core does not define a calibrated measurement.

---

## 07 · Design-system direction

**KEEP `assets/brand/tokens.json` as the current NovelForge brand/product token authority.** Do not create an unrelated `studio-colors.json`.

The future interactive token layer will be converted into a **WeiUI-compatible W3C Design Tokens Community Group representation** and consumed through a deterministic theme adapter. WeiUI is the selected generic component/CSS substrate; it does not replace Story Loom as NovelForge's product visual language.

The ownership split is explicit:

- NovelForge owns Story Loom domain semantics, product-specific authority/status/provenance encodings, typography roles and visual personality;
- WeiUI owns generic component primitives, reusable interaction/accessibility behavior, CSS mechanics and its public token/component contracts;
- the adapter owns the deterministic NovelForge-token → WeiUI-compatible token mapping.

WeiUI's token package uses W3C-style `$value` tokens, emits CSS/TypeScript/JSON, and its CSS generator uses the `--wui-*` custom-property namespace. The NovelForge theme should target that public shape instead of maintaining a hand-written parallel palette.

The interactive token layer should add only interaction concerns:

- appearance: light / dark / system;
- density: comfortable / workstation;
- typography roles: manuscript, UI, metadata/mono;
- focus ring and keyboard states;
- elevation / border / interactive surface states;
- motion durations and reduced-motion behavior;
- viewport/breakpoint semantics;
- authority and execution-status encodings kept separate from domain colors.

A generic WeiUI `success` state must never become shorthand for Accepted Canon. Product authority remains a separate labeled channel.

The visual personality remains editorial, warm and precise: paper-like surfaces, soft radii, thread/bookmark/card motifs, small intentional delight. No gradient-card SaaS dashboard and no faux-skeuomorphic writing desk.

---

## 08 · Technical delivery direction

### Portable product boundary

Every delivery surface consumes the same product semantics through typed projections/query/command boundaries. UI frameworks and packaging do not become Core authority.

```text
Studio surface
→ Studio projection/query adapter
→ stable NovelForge Core CLI/schema/query/command contracts
→ Core persistence
```

The projection adapter may normalize presentation shape, but it never becomes a source of truth and never reaches into random Python internals.

### Local / installable Studio shell

The future installable shell choice is now explicit:

```text
Core public boundary
→ Studio view models
→ React 19 shell
→ @weiui/react + @weiui/css + WeiUI-compatible NovelForge theme
→ Tauri host
```

This is a **Product implementation choice**, not a Generic Framework runtime dependency. CLI, Agent Skill, Core tests, and the Framework bundle must remain usable without Tauri, React, or WeiUI unless a product artifact explicitly requests them.

WeiUI heavy surfaces should remain route/feature scoped. Its React package exposes separate editor/chart/data-table entry points and declares `sideEffects: false`; the default shell should preserve that tree-shaking boundary instead of eagerly loading everything.

### Typed operations

Creator actions call explicit Core commands/transactions with preconditions. UI components and Tauri commands do not mutate Canon or runtime databases directly.

### Desktop shell decision

**Tauri is selected for the future installable application.** The previous Electron/Tauri/hybrid decision gate is closed by product direction. Implementation must still measure filesystem, subprocess/CLI, Git, MCP, offline, updater, signing, sandbox/WebView behavior, idle CPU/memory and process lifetime before the shell is called production-ready.

If implementation evidence later proves the choice cannot meet the product constraints, changing the shell requires an explicit product decision rather than silently forking delivery semantics.

### UI-shell acceptance gate

The shell direction becomes an implemented product capability only when applicable evidence lands on `main`:

- exact Tauri / React / WeiUI dependency pins in the app lockfile;
- deterministic NovelForge → WeiUI-compatible token conversion;
- light / dark / system theme validation;
- Story Loom semantic mapping preserved without collapsing authority into generic status colors;
- desktop + narrow responsive tests and English / Simplified Chinese locale smoke tests;
- accessibility, font scaling, keyboard, contrast and reduced-motion checks;
- bundle/chunk inspection proving optional editor/chart/data-table surfaces are not eagerly loaded;
- idle CPU/memory, first-interaction latency and Core-process-lifetime measurements;
- host-bridge tests preserving `authority=false` for read-only operations;
- no new Generic Core correctness dependency on Tauri, React or WeiUI.

Until those artifacts exist, Tauri + WeiUI is the **selected product direction**, not a shipped Studio app.

---

## 09 · Delivery roadmap

**Phase 1 — Product architecture + read-only Inspector**

- IA, product modes and data-honesty grammar;
- Run / Context Inspector prototype;
- synthetic fixtures and responsive visual QA;
- Core consumer gaps recorded as dependencies.

**Phase 2 — Read-only Studio shell**

- Project Hub from Project Adapter projection;
- Scene/Chapter read/review surface;
- Runs, Context and capability inspection;
- command palette + domain-aware search;
- portable host bridge + Agent Skill;
- visual regression harness.

**Phase 3 — Core workflow operations**

- typed review/compare/run actions;
- safe Context derived controls;
- acceptance and settlement handoff surfaces;
- no direct store writes.

**Phase 4 — Publication Studio**

- begins only after official Publication IR / Typesetting Profile contracts exist;
- screen/mobile/ebook/print previews consume deterministic renderer output or a contract-faithful preview adapter;
- publication-only text transforms require visible non-Canon diff/approval semantics when Core requires them.

**Phase 5 — Integrations / MCP**

- capability-first integration browser, permission scope, health and provenance;
- only after a stable MCP registry/manifest contract exists.

**Phase 6 — Installable Tauri distribution**

- Tauri + React + WeiUI app shell;
- deterministic WeiUI-compatible Story Loom theme;
- exact dependency pinning and updater/signing strategy;
- responsive/i18n/accessibility regression coverage;
- idle CPU/memory and process-lifecycle acceptance measurements;
- no new Generic Core correctness dependency on the desktop stack.

---

## 10 · Decision ledger

### KEEP

- Story Loom brand, tokens, assets and diagram grammar;
- existing documentation overhaul and visual QA discipline;
- Core Run Receipt, Context Inspector, Project Adapter, capability and Control Plane substrates;
- #8 as umbrella and Publication work as a separate dependency;
- one product truth model across CLI, local app, hosted UI and Agent Skill.

### REFINE

- extend Story Loom from documentation into an interactive product grammar through a WeiUI-compatible theme layer;
- split creator-facing and inspector-facing density through progressive disclosure;
- make “semantic support” vs “actually loaded” a first-class context interaction;
- bring documentation onboarding toward task-oriented entry paths without discarding the new visual work.

### ADD

- Tauri installable shell direction;
- React + WeiUI component substrate;
- deterministic NovelForge → WeiUI token adapter;
- responsive/i18n/accessibility and runtime-overhead acceptance gates;
- Studio product architecture and view-model boundary;
- Creator Mode / Inspector Mode;
- read-only Inspector vertical slice;
- synthetic public demo fixtures.

### DEFER

- write-capable Studio operations until stable typed Core commands exist;
- MCP marketplace/manager until the owning Core contracts exist;
- Publication editor/preview implementation before Core IR/Profile;
- production cloud/auth/collaboration infrastructure that is not required by the local product contract.

### REJECT

- second Canon/Memory/quality/session stores;
- second bespoke Studio component/design system that competes with WeiUI + Story Loom;
- making Tauri/React/WeiUI prerequisites for Generic Core correctness;
- fake engagement or consistency scores;
- UI-authored semantic truth;
- provider brand as capability proof;
- chain-of-thought exposure;
- giant everything-dashboard;
- graph-database-first Story Loom.
