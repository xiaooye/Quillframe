# NovelForge Product Site — Godot Replacement Tasks

**Scope:** public site `site/**`. The separate `studio/app/**` remains outside this migration.

Implementation status is recorded here; final release truth comes from the **same current HEAD** GitHub Actions and deployed site, not from manually copied CI status.

## Runtime replacement

- [x] Make Godot Web the sole public Product runtime.
- [x] Preserve Astro/Starlight as the exclusive `/docs/**` application.
- [x] Remove Solid/Vite from the production Product path and default Product `dev`/`build` commands.
- [x] Retain `site/src/**` plus exact Solid/Vite dependencies only as a named golden visual-and-behavior fixture for parity QA.
- [x] Keep baseline commands explicitly namespaced under `baseline:*` with no production authority.
- [x] Preserve Product deep-link fallback without allowing missing Docs paths to become Product routes.
- [x] Keep Product visuals 2D + controlled 2.5D with no 3D nodes.

## Browser/runtime integration

- [x] Synchronize Product navigation through browser `pushState`.
- [x] Bind `popstate` into the live Godot scene through retained JavaScriptBridge callbacks.
- [x] Keep Docs navigation as a hard document boundary.
- [x] Publish scene/runtime/layout/history markers for browser QA.
- [x] Provide explicit desktop, compact, and phone layouts.
- [x] Preserve command palette, locale, appearance, mobile menu, and browser history interactions.

## Visual parity preservation

- [x] Keep Story Loom brand primitives/assets as the canonical design foundation.
- [x] Treat the retained Solid/Vite Kawaii Atelier page as a non-production golden rendered fixture.
- [x] Pin deterministic Inter, CJK, symbol, Thai, and Arabic fallback fonts for cross-renderer evidence.
- [x] Encode page-grid, typography, wrap, margin, alignment, responsive-flow, and route-identity parity in Godot source contracts.
- [x] Keep font fallback scoped so decorative glyph coverage cannot alter normal text line metrics.
- [x] Run route-pair screenshot evidence and blocking interaction QA against the golden fixture.
- [x] Prevent migration work from reinterpreting the approved Kawaii layout.

## Build/deploy evidence required for completion

A release is complete only when the **same current HEAD** proves all of the following:

- Golden-baseline fixture quality, Godot source quality, and production assembly contracts pass.
- Starlight Docs build passes.
- Pinned Godot editor/template setup passes.
- The single parity/size-proven Godot exporter completes release Web export.
- All Cloudflare Pages production assets satisfy the hard individual-file ceiling.
- Production deployment and custom-domain API post-condition pass.
- Production Browser QA proves runtime readiness, Product routes, interactions, responsive layouts, screenshots, and the Docs boundary.
- Route parity QA remains green against the retained golden fixture.
- Live HTTP verification proves `/` and a direct Product route serve the Godot shell while `/docs/` serves Starlight without the Godot shell.

## Cleanup condition

- [x] Default Product `dev`/`build` commands identify Godot as production.
- [x] Solid/Vite dependencies are explicitly retained only for baseline fixture QA, not as a shipped fallback runtime.
- [x] Product source-quality output identifies `production_cutover: true`.
- [x] The Product specification distinguishes public Godot runtime from the separate `studio/app/**` application.
- [x] Live-domain content verification is part of the deployment workflow rather than an external/manual assumption.

The golden fixture may retain its exact browser-framework dependencies and a lockfile if needed for deterministic regression evidence; that does not make it a production runtime.
