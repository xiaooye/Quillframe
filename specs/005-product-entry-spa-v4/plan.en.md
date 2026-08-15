# Plan · NovelForge Product Entry SPA v4

## Phase 0 · Authority / evidence freeze

- latest `main` is the development baseline.
- Preserve WeiUI / Story Loom v2 authority; do not fork it.
- UI/UX Pro Max is design evidence only.
- Product claims must match current implementation.

## Phase 1 · Build-time knowledge compiler

- `site/scripts/build-content.mjs` reads `docs/documentation_manifest.json`.
- Use an exact-pinned Markdown parser to compile paired Markdown into safe structured AST; never emit untreated raw HTML.
- Generate metadata, TOC, plain-text excerpt, search terms, source path, tier, and status per document.
- Generate a unified product/docs search index.
- Compile before Vite build; runtime never calls GitHub API.

## Phase 2 · Product Entry shell

Refactor the global shell around:

- WeiUI-backed command/search trigger;
- `⌘K` / `Ctrl+K` command palette;
- mobile search sheet/dialog;
- appearance / locale / GitHub / Studio actions;
- compact high-density premium navigation;
- kawaii state language.

## Phase 3 · Premium-cute home

Replace brochure narrative with an interactive entry surface:

- dense hero/product launcher;
- live capability dock;
- product-surface focus panels;
- Studio launch;
- Architecture explorer teaser;
- Publication profile explorer teaser;
- Knowledge search teaser;
- release/status capsule;
- Story Loom chromatic materials.

## Phase 4 · Knowledge Explorer

`/docs` provides search + filters, tier/status/source metadata, responsive document library, curated product docs, `docs/:docId` article routes, generated TOC, code/list/table/quote rendering, and optional source provenance links without requiring GitHub navigation.

## Phase 5 · Interactive product routes

- `/studio`: hosted Studio CTA + capability explorer + unbound-Core truth.
- `/architecture`: focusable subsystem map / detail popovers.
- `/publication`: profile switcher + accepted-text flow + current limits.
- `/product`: interactive capability inventory / boundaries.
- `/changelog`: release timeline/status rather than a giant static title page.

## Phase 6 · Modern CSS enhancement

Progressively layer container/style queries, subgrid, `:has()`, semantic `color-mix()` derivation, masks, clip-path, filters, blend modes, gradients, perspective, small motion paths, scroll/view timelines, View Transitions, Popover + Anchor Positioning, `@starting-style`, discrete transitions, and `content-visibility` for document content.

No infinite idle loops. Reduced-motion exposes the complete static state.

## Phase 7 · Quality / visual QA

- deterministic Product Site quality gate;
- exact dependency pins;
- generated content and stale-data checks;
- native zh-CN leakage gate;
- no fake social proof;
- keyboard/touch/focus/reduced-motion checks;
- desktop/mobile browser render QA;
- Cloudflare deployment post-condition.

## Rollback

The v4 knowledge compiler, interaction shell, and visual/product rewrite land as independently revertible commits. Rolling back Product Entry must not change Generic Core or Studio Core authority.
