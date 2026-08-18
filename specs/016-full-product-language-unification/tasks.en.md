# Tasks

## Shared shell

- [ ] Derive ProductShell top/mobile/footer navigation from shared `primaryNav` / `utilityNav` sources.
- [ ] Add the real GitHub repository to primary navigation.
- [ ] Keep mobile navigation and footer primary section synchronized with top navigation.
- [ ] Add Studio landing, Changelog, and GitHub to command-palette reachability; distinguish Hosted Studio.
- [ ] Synchronize visible shell version identity to 0.9.x.
- [ ] Add GitHub and navigation-sync checks to `product-shell-quality`.

## Shared primitives

- [ ] Make `ProductSurfaceHero` a borderless canvas composition.
- [ ] Remove the hero root 28px radius, shadow, broad tone gradients, and dashed inset frame.
- [ ] Keep route visual artifacts independently containable without recreating a giant hero card.
- [ ] Replace the stale framed-hero invariant in `surface-audit-quality`.

## Public Product Site

- [ ] `/product`: editorial sequence, no mechanical card grid.
- [ ] `/studio`: editorial landing sequence with real Hosted Studio action.
- [ ] `/architecture`: white execution-paper canvas, restrained rainbow/card chrome.
- [ ] `/publication`: proofing/typesetting desk, restrained format color.
- [ ] `/inspect`: remove hero-card + tool-card nesting.
- [ ] `/playground`: preserve scratch/tool surfaces with canvas-first page composition.
- [ ] `/agents`: preserve Host Bridge truth while reducing host card soup.
- [ ] `/changelog`: release notebook/timeline.

## Docs

- [ ] Align global header/search/locale/theme with Quillframe product language.
- [ ] Audit landing/article/sidebar/TOC/code/table/callout/pagination/mobile/404.
- [ ] Preserve reading-first composition and CJK readability.
- [ ] Update docs-specific quality contracts.

## Studio

- [ ] Remove generic rounded-admin-card treatment from `.nf-page-intro`.
- [ ] Audit Writer routes: Desk / Manuscript / Plan / Story / Review / Research & Corpus / Learning / Publish.
- [ ] Audit Settings and global AI Dock / Search / Command Palette surfaces.
- [ ] Audit Inspector routes: Sessions / Runs / Checkpoints / Context / Agents & Models / Semantic Jobs / Control Plane / Capabilities / Receipts / Diagnostics / Architecture.
- [ ] Preserve real Core Bridge and state truth.
- [ ] Update Studio product-language quality gate.

## Verification

- [ ] Product / Docs / Studio deterministic builds and quality tests.
- [ ] Responsive verification at 1440 / 1024 / 768 / 430 / 375.
- [ ] Keyboard / visible focus / dialog / aria-expanded / reduced-motion / 44px touch-target checks.
- [ ] No new `!important`, late override layer, infinite idle animation, or polling.
- [ ] Desktop + phone screenshots for all Product routes.
- [ ] Desktop + phone representative Docs screenshots.
- [ ] Desktop + phone representative Studio Writer / Inspector screenshots.
- [ ] Visual-family audit: hiding the logo must still leave one recognizable Quillframe product family.
- [ ] Stop on branch for user visual acceptance; do not merge main.