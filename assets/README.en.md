# Quillframe Visual Assets · Story Loom in the repository

This directory contains the maintained Story Loom presentation and application-token foundation for Quillframe documentation and product surfaces. It is deliberately small: a coherent brand system, high-value product diagrams, machine-readable product semantics, exact dependency provenance, and deterministic design-system QA—not a stock-art library or a second UI framework.

> **Boundary ✦** Visual assets and tokens improve comprehension, recognition, interaction consistency, and product theming. They never become a second authority for Framework behavior, Canon, Settlement, semantic truth, production readiness, or workflow state.

---

## 01 · Live asset map

```text
assets/
├── README.en.md / README.zh-CN.md
├── DESIGN_SYSTEM.en.md / DESIGN_SYSTEM.zh-CN.md
├── provenance.json
├── brand/
│   ├── quillframe-mark.svg
│   ├── quillframe-lockup.svg
│   ├── story-thread.svg
│   ├── tokens.json
│   ├── weiui.integration.json
│   └── story-loom.weiui.css
└── ui/
    ├── home-comparison.en.svg / .zh-CN.svg
    ├── home-architecture.en.svg / .zh-CN.svg
    ├── home-pipeline.en.svg / .zh-CN.svg
    ├── home-quality.en.svg / .zh-CN.svg
    └── home-fit.en.svg / .zh-CN.svg
```

Machine integration QA lives in the [product-site quality gate](../site/scripts/quality.mjs) and is enforced by the Story Loom workflow.

---

## 02 · Brand and product-semantic authority

`brand/tokens.json` is now schema **`quillframe_brand_tokens_v2`** and remains the Quillframe-side product-token authority.

It contains:

- stable Story Loom brand/domain semantics;
- light/dark application theme roles;
- interaction budgets such as 44px minimum touch targets and focus geometry;
- mobile-first responsive rules;
- `en-US` + `zh-CN` i18n constraints;
- reduced-motion / no-idle-animation rules;
- performance constraints such as no default polling and no heavy default component import.

A generic UI foundation does not get to redefine what Project, Runtime, Editorial, Evidence, Accepted/Validated, Rejected, Canon authority, or execution state mean in Quillframe.

---

## 03 · WeiUI foundation · merged and pinned

The Story Loom → WeiUI bridge is now a real repository artifact, not only a future direction.

[`brand/weiui.integration.json`](brand/weiui.integration.json) records:

- WeiUI repository: `xiaooye/weiui`;
- exact commit: `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`;
- license: MIT;
- allowed packages: `@weiui/tokens`, `@weiui/css`;
- forbidden Phase 2C runtime packages: `@weiui/headless`, `@weiui/react`;
- WeiUI runtime JavaScript required: `false`;
- theme layer: `wui-theme`;
- CSS order: WeiUI tokens → WeiUI CSS → Story Loom theme.

[`brand/story-loom.weiui.css`](brand/story-loom.weiui.css) is the live application theme bridge. It maps Story Loom light/dark roles into WeiUI `--wui-*` variables while keeping Quillframe-specific `--qf-*` product semantics separate. It must not fork WeiUI `.wui-*` component selectors or use `!important` to win the cascade.

The product dependency therefore stays one-way:

```text
Story Loom v2 product tokens
→ exact-pinned WeiUI tokens/CSS
→ Story Loom wui-theme aliases
→ SolidJS product surfaces
→ Local Web / optional Tauri host
```

WeiUI is a zero-JavaScript styling/token foundation for Phase 2C, **not** the application runtime and not Quillframe product authority.

---

## 04 · Phase 2C product-stack boundary

The selected application stack is SolidJS + TypeScript + Vite + `@solidjs/router`.

- Local Web is first-class and preferred when minimum incremental CPU/RAM matters.
- Tauri is an optional/installable host over the same product, not the center of product architecture.
- `@weiui/react` and `@weiui/headless` are deliberately excluded from the Phase 2C runtime.
- Generic Core correctness, CLI, Framework bundle, and Agent Skill must remain independent of SolidJS/Vite/Tauri and WeiUI runtime JavaScript.

The full product boundary lives in [`../studio/PRODUCT_ARCHITECTURE.en.md`](../studio/PRODUCT_ARCHITECTURE.en.md).

---

## 05 · Machine-checkable application design contract

Run:

```bash
pnpm --filter @quillframe/product-site quality
```

The checker verifies, among other things:

- exact WeiUI source pin and MIT provenance;
- Story Loom v2 / integration schema IDs;
- only `@weiui/tokens` + `@weiui/css` allowed;
- React/headless WeiUI runtimes forbidden;
- `runtime_javascript_from_weiui=false`;
- mobile-first and phone `focus-first` behavior;
- minimum 44px touch target;
- baseline locales exactly `en-US`, `zh-CN`;
- logical properties required and fixed-width locale assumptions forbidden;
- reduced motion required and idle animation forbidden;
- no default polling;
- required light/dark contrast ≥ 4.5:1 for primary/destructive/success/warning role pairs;
- `wui-theme`, light/dark definitions, required `--wui-*` / `--qf-*` variables;
- no `!important` and no Story Loom fork of WeiUI component selectors;
- complete design-system provenance IDs.

This deterministic gate validates machine-checkable design contracts. It does not replace real responsive rendering, accessibility testing, native-copy review, or runtime CPU/RAM measurement.

---

## 06 · Product UI diagrams

`ui/` contains high-value static SVG modules used on product/landing surfaces. They explain comparison, architecture, production pipeline, quality model, and fit/tradeoffs.

They are presentation assets. Maintained Markdown/contracts remain the semantic source of truth.

Tier-A SVGs still require real 820px + narrow render inspection, visible-copy review, bilingual parity, and `pnpm --filter @quillframe/product-site quality` before integration.

---

## 07 · Story Loom rules

Core rules:

- professional technical/product clarity first;
- one coherent original identity rather than unrelated visual styles;
- restrained anime-editorial warmth, not mascot noise;
- no consumer-novel characters or project-specific Canon in generic Framework assets;
- no copyrighted franchise characters, logos, or direct living-artist imitation;
- color never carries authority or PASS/FAIL meaning alone;
- generic `success` styling never proves Accepted Canon or production readiness;
- no external/embedded font files in documentation assets;
- no parallel hand-maintained Studio palette beside the token/theme contract.

The fuller static-visual grammar remains in [Documentation Design System](DESIGN_SYSTEM.en.md).

---

## 08 · Provenance and derived artifacts

[`provenance.json`](provenance.json) records maintained asset provenance. The WeiUI integration now has explicit source commit/license records plus IDs for the Story Loom v2 token contract and application theme.

Directory placement never implies authority. For generated or mapped artifacts, provenance should state:

- authoritative source;
- exact upstream dependency where applicable;
- generated-vs-source status;
- mapping contract;
- validation mechanism;
- whether the artifact is presentation-only or consumed by product runtime.

**The asset system is successful when Quillframe looks distinctive, Studio reuses one source of product semantics, and neither presentation tooling nor the generic UI foundation becomes a competing source of truth.**
