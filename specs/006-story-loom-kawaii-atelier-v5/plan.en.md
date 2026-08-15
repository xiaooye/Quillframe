# Product Experience v5 · Implementation Plan

## Goal

Replace the v4 dark-glass presentation with the Story Loom Kawaii Atelier while preserving all shipped Product Entry capabilities and authority boundaries.

## Phase 1 · Freeze current capability surface

- Keep current routes and runtime behavior.
- Keep WeiUI generated foundation and exact pin.
- Keep Story Loom semantic lane variables as the only brand color authority.
- Keep build-time documentation ingestion and structured AST renderer.
- Keep Command Palette, context/readiness labs, hosted Studio entry, architecture explorer and publication switcher.
- Treat current main at implementation start as the write before-state.

## Phase 2 · Recompose the product shell

- Compact the sticky app bar and make it feel like an atelier tool strip rather than dashboard chrome.
- Add a warm, paper-like page foundation.
- Version the appearance migration so first v5 load returns stale v4 dark preference to light once.
- Preserve explicit user dark-mode control after migration.

## Phase 3 · Rebuild home composition

- Convert the hero into a compact atelier desk with layered product objects and direct launch actions.
- Turn the capability ribbon into tactile lane tabs/stickers.
- Recompose the two labs as a single notebook/workbench spread.
- Recompose product doors into an asymmetric shelf/bento with Studio visually primary.
- Keep real documentation preview but present it as a knowledge shelf/library object rather than a documentation section.
- Reduce vertical dead space and avoid repeated section-heading/card formulas.

## Phase 4 · Unify route surfaces

- Make InteractiveRouteFrame a compact application toolbar rather than a brochure hero.
- Re-style Product/Studio/Architecture/Publication as dense work surfaces.
- Preserve Knowledge Explorer and document reader functionality while giving them the same atelier material language.
- Preserve keyboard navigation and mobile bottom-nav behavior.

## Phase 5 · Progressive CSS showcase

- Build a dedicated v5 enhancement layer using modern CSS only as progressive enhancement.
- Include interaction-driven material response, view/scroll timelines, View Transitions, container queries, `:has`, `@scope`, `@property`, `@starting-style`, discrete transitions, masks/blends and guarded anchor/corner-shape support.
- No infinite idle animation and no decorative `requestAnimationFrame` loop.
- Reduced motion resolves to static final states.

## Phase 6 · Quality contract

Update Product Site QA so it verifies:

- v5 appearance migration;
- warm atelier identity markers;
- Story Loom lane-token consumption;
- WeiUI primitives remain present;
- Knowledge build/runtime remains present;
- v5 CSS capabilities are progressive and reduced-motion safe;
- no dark-dashboard-only regression;
- no fake product/social-proof claims;
- no authority bleed.

## Verification

Run current Product Site workflow through:

`foundation sync → documentation build → Product Site contract → tsc → Vite build → Cloudflare Pages deploy → custom-domain post-condition`

Then perform user-visible visual review on desktop and mobile. CI success is necessary but not sufficient for visual acceptance.
