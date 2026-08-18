<div align="center">
  <img src="brand/quillframe-lockup.svg" alt="Quillframe — Adaptive Fiction Agent Framework" width="620" />
</div>

# Quillframe Story Loom Design System

> **One visual language across documentation and product UI.**
>
> Story Loom treats **Project → Runtime → Story → Reader → Evidence → Validated Result** as one continuously woven story thread. Professional technical structure is the skeleton; anime-editorial warmth is the recognition layer. 🌸

**Ratio:** `70% professional technical / 30% anime-editorial warmth`.

This file explains the human-facing design contract. Machine authority lives in [`brand/tokens.json`](brand/tokens.json), [`brand/weiui.integration.json`](brand/weiui.integration.json), [`brand/story-loom.weiui.css`](brand/story-loom.weiui.css), and [`../scripts/design_system_quality.py`](../scripts/design_system_quality.py). Documentation render/review requirements remain in [`../docs/DOCUMENTATION_QA.en.md`](../docs/DOCUMENTATION_QA.en.md).

> **Authority boundary ✦** Story Loom can encode product domain, authority labels, execution status, provenance, focus, hierarchy, and interaction state. It never creates Canon, semantic truth, production readiness, or workflow authority.

---

## 01 · Brand DNA ✦

Quillframe should hold four qualities at once:

| Trait | Design meaning |
|---|---|
| **Precise** | hierarchy, spacing, interaction states, and diagram semantics stay rigorous |
| **Editorial** | feels like a fiction-production studio, not a generic DevOps dashboard |
| **Warm** | sakura / lavender / paper-like surfaces add human and anime-editorial character |
| **Engineered** | tokens, dependency pins, provenance, accessibility rules, and QA are inspectable |

Landing pages may naturally use `🌸 ✦ ✨ 📖`; dense contracts, schemas, command surfaces, and machine inspectors stay quieter.

### Logo system

<img src="brand/quillframe-mark.svg" alt="Quillframe Story Loom brand mark" width="120" />

The mark combines book pages, a woven N/story thread, and a forge spark. Use the lockup on major landing surfaces and the mark at small sizes. Do not rotate, glow, arbitrarily recolor, or use the logo as an architecture/status icon. System-font fallbacks only; no committed external font files.

---

## 02 · Product-token authority · Story Loom v2

Machine source: [`brand/tokens.json`](brand/tokens.json), schema **`quillframe_brand_tokens_v2`**.

The token contract now covers both documentation semantics and application constraints. It is the Quillframe-side source of truth for:

- Story Loom domain families: Project, Runtime, Editorial, Evidence, Validated, Rejected, Neutral;
- application light/dark theme roles;
- typography and density roles;
- focus geometry and minimum touch target;
- mobile-first responsive behavior;
- `en-US` + `zh-CN` i18n constraints;
- reduced-motion behavior;
- runtime-overhead rules such as no default polling, no idle decorative animation, and no heavy default import.

### Semantic discipline

- Pastels are fill/accent colors, not low-contrast body text.
- Color never carries PASS/FAIL or authority alone.
- Generic `success` styling does **not** mean Accepted Canon, production-ready, or valid publication output.
- Authority, execution state, provenance, and domain color remain orthogonal channels.
- Exact machine identifiers remain untranslated in localized UI.
- Spacing follows a 4/8 rhythm unless an explicit product token says otherwise.

---

## 03 · WeiUI integration boundary · merged

WeiUI is the generic **zero-JavaScript token/CSS foundation**, not Quillframe product authority and not the Phase 2C application runtime.

Machine contract: [`brand/weiui.integration.json`](brand/weiui.integration.json).

Current dependency truth:

```text
Story Loom v2 product tokens
→ exact-pinned xiaooye/weiui
→ @weiui/tokens + @weiui/css
→ story-loom.weiui.css (`wui-theme`)
→ SolidJS product surfaces
→ Local Web / optional Tauri host
```

The integration contract pins WeiUI to exact commit `d84d1cd365fb5f90cbbab794d2358f7a13b29b79` and requires:

- allowed packages: `@weiui/tokens`, `@weiui/css`;
- prohibited Phase 2C runtime packages: `@weiui/react`, `@weiui/headless`;
- `runtime_javascript_from_weiui=false`;
- import order: WeiUI tokens → WeiUI CSS → Story Loom theme;
- Story Loom overrides only through `@layer wui-theme`;
- no `.wui-*` component-selector forks;
- no `!important` as a cascade escape hatch.

[`brand/story-loom.weiui.css`](brand/story-loom.weiui.css) maps product roles into `--wui-*` variables and keeps Quillframe-specific semantics in `--qf-*` variables. A WeiUI upgrade may change generic implementation detail, but it cannot silently redefine Quillframe concepts.

---

## 04 · Application visual/runtime contract

Phase 2C product code is directed toward **SolidJS + TypeScript + Vite + `@solidjs/router`**. Local Web is first-class; Tauri is an optional installable host over the same product model.

The design system deliberately separates presentation/runtime responsibilities:

- **Story Loom** owns product semantics and visual meaning;
- **WeiUI** owns generic reusable CSS/token primitives;
- **SolidJS** owns application behavior and reactive UI composition;
- **Studio adapters / Core** own typed product data and commands;
- **Tauri** may host the installable build but gains no story/runtime authority.

### Machine-enforced app invariants

[`../scripts/design_system_quality.py`](../scripts/design_system_quality.py) checks at least:

- exact WeiUI pin and provenance;
- SolidJS/TypeScript/Vite product-stack contract;
- zero WeiUI runtime JS;
- minimum touch target `44px`;
- focus ring `3px` with `2px` offset;
- mobile-first breakpoints and phone `focus-first` workspace;
- baseline locales exactly `en-US` and `zh-CN`;
- logical properties required and fixed-width locale assumptions forbidden;
- reduced motion required;
- idle decorative animation forbidden;
- default polling forbidden;
- heavy default component import forbidden;
- required light/dark contrast ≥ 4.5:1;
- required theme variables/layers and no forbidden selector forks.

Passing deterministic design-system QA does **not** prove real CPU/RAM performance or visual usability. Phase 2C still needs actual responsive, accessibility, localization, bundle/chunk, idle CPU/RAM, first-interaction, and host-process measurements.

---

## 05 · Responsive, i18n, accessibility, motion

Mobile is a first-class product constraint, not a later desktop shrink pass.

- **Phone:** focus-first manuscript/workspace; Inspector becomes route/overlay.
- **Tablet:** richer split surfaces are allowed, but Inspector remains overlay-or-route when space is constrained.
- **Desktop:** persistent Inspector is allowed when space permits.
- **Touch:** interactive targets meet the machine token minimum.
- **i18n:** layout survives Chinese/English expansion; prefer logical CSS properties; never assume English-width labels.
- **Accessibility:** focus remains visible, contrast is measurable, color is not the sole semantic channel, screen-reader names remain explicit.
- **Motion:** reduced-motion support is mandatory; no idle decorative animation merely to make the product feel “alive.”

Story Loom can be warm without being continuously animated.

---

## 06 · Markdown and documentation chrome

GitHub Markdown cannot depend on arbitrary product CSS, so documentation continues to use portable Story Loom primitives:

1. brand lockup on major landing pages;
2. `<kbd>` metadata chips for stable concepts;
3. story-thread dividers for breathing space;
4. numbered H2 rhythm such as `01 · System map`;
5. semantic callouts such as `Boundary ✦` and `Why it matters`;
6. compact reference matrices only when tabular lookup is genuinely the job;
7. branded Mermaid for inspectable source diagrams;
8. small mark/footer only when it adds useful rhythm.

Brand identity comes from hierarchy and consistency, not repeated Hero blocks or decoration density.

---

## 07 · Typography and information hierarchy

- exactly one H1 per document/product page;
- manuscript, UI, and metadata/mono roles remain distinct;
- headings establish scan order before visual decoration;
- body paragraphs stay short and readable;
- monospace is for IDs, schemas, paths, commands, fingerprints, and state machines;
- tables do not carry essay-length prose;
- decorative Unicode/emoji never replace labels;
- never solve overflow by shrinking type below readability;
- localized copy may use different geometry when language expansion demands it.

The repository does not distribute font files as part of documentation assets.

---

## 08 · Mermaid · Story Loom grammar

Mermaid remains the inspectable source chart for technical documentation.

### Lane grammar

- **Project · sky** — inputs, Project SDK, Context;
- **Runtime · lavender** — Harness, Session, Control Plane, workers;
- **Story / Editorial · neutral + sakura** — Story core, simulation, draft, reader quality;
- **Evidence · amber** — feedback, Corpus, learning, eval;
- **Validated · mint** — validated result only, never implicit Canon;
- **Reject · danger** — actual reject/invalid/failed gate states only.

### Shape and edge grammar

- stadium: boundary/input/output;
- hexagon: decision/manager/semantic gate;
- database: durable state/runtime store;
- subroutine: reusable core mechanism;
- rounded node: ordinary processing;
- solid edge: primary execution/dependency;
- dashed edge: feedback/evidence/resume/reference.

One chart answers one core question. Nuance belongs in nearby prose, not oversized node labels.

---

## 09 · Tier-A static visual contract

Homepage/product SVGs are a presentation layer over maintained semantics:

```text
claim/copy freeze
→ information architecture
→ Story Loom layout
→ SVG source
→ real render inspection
→ deterministic lint
→ integration
```

Hard expectations:

- design around a `1200px`-class viewBox unless another size is justified;
- inspect at roughly **820px** GitHub content width and **420px** narrow width;
- projected body text at 820px must remain at least **12px**;
- long measurable text carries explicit width budgets where the checker can measure them;
- no clipping, overflow, collisions, or tiny-text “fixes”;
- English and Chinese are written and laid out natively;
- root `data-doc-tier="A"`, non-empty `<title>` and `<desc>`, system-font fallbacks only;
- meaningful images have alt text and nearby prose preserves meaning if SVG fails.

Before integration, run `python scripts/docs_quality.py` and inspect real renders. **Generated is not reviewed; XML-valid is not visually correct.**

---

## 10 · Definition of Done

A Story Loom documentation or product surface is complete only when:

- the information hierarchy works before decoration;
- domain, authority, execution state, and provenance are not collapsed into one color;
- English and Chinese communicate the same claims naturally;
- phone/narrow behavior is deliberate rather than accidental;
- keyboard/focus/contrast/reduced-motion behavior is credible;
- the product uses the exact-pinned WeiUI boundary rather than a parallel hand-maintained palette;
- deterministic docs/design-system QA is green;
- real render and, for application work, real runtime measurements have happened;
- presentation code never becomes a second authority for Core or story truth.

**Story Loom succeeds when Quillframe feels engineered, editorial, recognizable, and unusually light without sacrificing semantic honesty. ✦**
