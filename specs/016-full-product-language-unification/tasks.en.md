# Tasks

## Shared shell

- [x] Derive ProductShell top/mobile/footer navigation from shared `primaryNav` / `utilityNav` sources.
- [x] Add the real GitHub repository to primary navigation.
- [x] Keep mobile navigation and footer primary section synchronized with top navigation.
- [x] Add Studio landing, Changelog, and GitHub to command-palette reachability; distinguish Hosted Studio.
- [x] Synchronize visible shell version identity to 0.9.x.
- [x] Add GitHub and navigation-sync checks to `product-shell-quality`.

## Shared primitives

- [x] Make `ProductSurfaceHero` a borderless canvas composition.
- [x] Remove the hero root 28px radius, shadow, broad tone gradients, and dashed inset frame.
- [x] Keep route visual artifacts independently containable without recreating a giant hero card.
- [x] Replace the stale framed-hero invariant in `surface-audit-quality`.

## Public Product Site

- [x] `/product`: editorial sequence, no mechanical card grid.
- [x] `/studio`: editorial landing sequence with real Hosted Studio action.
- [x] `/architecture`: white execution-paper canvas, restrained rainbow/card chrome.
- [x] `/publication`: proofing/typesetting desk, restrained format color.
- [x] `/inspect`: remove hero-card + tool-card nesting.
- [x] `/playground`: preserve scratch/tool surfaces with canvas-first page composition.
- [x] `/agents`: preserve Host Bridge truth while reducing host card soup.
- [x] `/changelog`: release notebook/timeline.

## Docs

- [x] Align global header/search/locale/theme with Quillframe product language.
- [ ] Complete rendered visual audit of landing/article/sidebar/TOC/code/table/callout/pagination/mobile/404.
- [x] Preserve reading-first composition and CJK readability in static/build contracts.
- [x] Update docs-specific quality contracts.

## Studio

- [x] Remove generic rounded-admin-card treatment from `.nf-page-intro`.
- [ ] Complete rendered visual audit of Writer routes: Desk / Manuscript / Plan / Story / Review / Research & Corpus / Learning / Publish.
- [ ] Complete rendered visual audit of Settings and global AI Dock / Search / Command Palette surfaces.
- [ ] Complete rendered visual audit of Inspector routes: Sessions / Runs / Checkpoints / Context / Agents & Models / Semantic Jobs / Control Plane / Capabilities / Receipts / Diagnostics / Architecture.
- [x] Preserve real Core Bridge and state truth; introduce no fake runtime or mock authority.
- [x] Update Studio product-language quality gate.

## Verification

- [x] Product / Docs / Studio deterministic builds and quality tests (all GitHub Actions jobs green).
- [ ] Rendered responsive verification at 1440 / 1024 / 768 / 430 / 375.
- [ ] Browser-level keyboard / visible focus / dialog / aria-expanded / reduced-motion / 44px touch-target checks.
- [x] Static gates: no new `!important`, late override layer, infinite idle animation, or polling.
- [ ] Desktop + phone screenshots for all Product routes.
- [ ] Desktop + phone representative Docs screenshots.
- [ ] Desktop + phone representative Studio Writer / Inspector screenshots.
- [ ] Visual-family audit: hiding the logo must still leave one recognizable Quillframe product family.
- [x] Stop on branch for user visual acceptance; do not merge main.
