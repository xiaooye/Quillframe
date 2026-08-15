# Plan · NovelForge Product Site

## Phase 0 · Contract freeze

- Track work in issue #34.
- Preserve latest `main` as implementation baseline.
- Reuse Story Loom v2 / WeiUI zero-JS contracts; do not fork them.
- Keep Product Site isolated from Generic Core runtime dependencies.

## Phase 1 · Site foundation

Create `site/` with:

- exact frontend versions;
- SolidJS + TypeScript + Vite + `@solidjs/router`;
- host-neutral static `dist/` output;
- global AppShell / responsive navigation / footer;
- explicit `en-US` / `zh-CN` locale state;
- Story Loom application theme imported from repository authority;
- base accessibility, focus, touch, responsive and reduced-motion rules.

The first implementation intentionally uses no analytics, backend, auth, CMS, or Tauri runtime.

## Phase 2 · Product Home vertical slice

Build a complete homepage narrative:

1. Hero + product thesis;
2. problem / prompt-only failure model;
3. Forge pipeline story;
4. proof modules based on real contracts;
5. Studio section;
6. Publication section;
7. subsystem bento;
8. one-product/many-host delivery section;
9. release truth;
10. final CTA.

No fake social proof. Product proof comes from current machine contracts and observable architecture.

## Phase 3 · Destination routes

Add real, non-placeholder route pages for:

- Product;
- Studio;
- Architecture;
- Publication;
- Docs;
- Changelog.

The first route versions can be concise, but each must answer a distinct user question and deep-link to canonical repository sources.

## Phase 4 · Documentation portal

Start with curated documentation cards mapped to authoritative sources.

Later structural extension:

- build-time Markdown ingestion;
- generated navigation from documentation manifest;
- build-time search index;
- source/freshness badges;
- no browser-time GitHub API dependency.

This extension must not create a second content store.

## Phase 5 · Deterministic quality

Add a model-free Site CI workflow that:

- installs exact dependencies;
- builds production output;
- runs `site/scripts/quality.mjs`;
- blocks forbidden WeiUI runtime packages;
- checks required routes/locales/Story Loom references;
- checks basic a11y/responsive/motion source invariants;
- rejects known fake marketing placeholders.

CI may later add browser rendering/Lighthouse-style checks, but normal CI should stay deterministic and low-cost.

## Phase 6 · Visual review

Before calling the first slice product-ready:

- render desktop and phone widths;
- inspect English and Chinese independently;
- verify no horizontal overflow;
- verify keyboard navigation/focus;
- verify reduced-motion final state;
- verify section hierarchy and CTA clarity;
- verify marketing claims against current `main`.

## Phase 7 · Hosting

Preferred first deployment: Cloudflare Pages.

Build contract:

- root directory: `site`;
- build command: `npm run build`;
- output directory: `dist`.

Cloudflare remains replaceable. No Cloudflare-specific product logic enters the SPA.

## Phase 8 · Future product growth

After the public site foundation is stable:

- interactive architecture explorer;
- real Studio preview/demo modules;
- Publication sample build previews;
- build-time docs search;
- release/status data generated from maintained manifests;
- social/OpenGraph image generation;
- optional anonymous analytics only after an explicit privacy/product decision.

## Rollback

Every implementation commit must remain revertible without changing Core contracts. Removing `site/` and its dedicated workflow must leave Framework/Studio runtime behavior unchanged.