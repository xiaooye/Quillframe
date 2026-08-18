# Implementation Plan

## Phase 1 · Authority and shared shell

1. Use `e49304bde7fb0c5ba0822deb3823f960c6425804` as the sole base authority.
2. Keep `ui/homepage-product-language-unification` as the single implementation branch; do not merge main.
3. Reconcile ProductShell navigation ownership so top nav, mobile nav, footer, and command palette derive from shared navigation models.
4. Restore the real GitHub repository entry, Changelog, and Studio landing reachability while keeping Hosted Studio a distinct external action.
5. Synchronize stale 0.8.x shell identity to the 0.9.x development line.

## Phase 2 · Shared visual primitives

1. Refactor the `ProductSurfaceHero` style owner back to canvas composition: remove frame, radius, shadow, broad tone gradients, and dashed inset.
2. Preserve the optional visual slot; route-specific artifacts become contained surfaces only when the information object needs a boundary.
3. Review ProductSectionHeading, shared shell, and small object surfaces without adding a late override layer.

## Phase 3 · Public routes

1. Product / Studio landing: replace card-grid explanation with editorial sequence, rail, or asymmetric composition.
2. Architecture: remove broad radial rainbow treatment and reduce node/card chrome while emphasizing execution path and inspector hierarchy.
3. Publication: reconstruct as proofing/typesetting desk; preserve real profile switching and preview behavior with color limited to semantic accents.
4. Inspect / Playground / Agents: preserve real tool objects while removing enclosing hero-card and nested-surface syndrome.
5. Changelog: reconstruct as release notebook/timeline.

## Phase 4 · Docs

Audit Starlight chrome, landing, articles, sidebar, TOC, code, tables, callouts, pagination, mobile sidebar, and 404. Share Quillframe product language while remaining reading-first; do not create a second token authority.

## Phase 5 · Studio

Audit all Writer and Inspector routes. Fix `.nf-page-intro` and shell composition first, then route-specific density. Preserve Core Bridge, settings, model/runtime/session/semantic functionality.

## Phase 6 · Quality and verification

Update stale visual invariants in site/studio/docs quality checks; add GitHub-entry and navigation-sync contracts; run deterministic builds and quality tests; verify no new `!important`, late override CSS, polling, or infinite idle animation; verify 1440 / 1024 / 768 / 430 / 375 layouts and accessibility; render representative Product/Docs/Studio routes at desktop and phone sizes for visual-family audit.

## Acceptance

When implementation and deterministic gates pass but user visual acceptance is pending, status is `review / awaiting_user`. Missing mandatory render/visual gates prevent a `complete` claim.