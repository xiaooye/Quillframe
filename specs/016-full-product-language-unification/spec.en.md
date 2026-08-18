# Quillframe Full Product Language Unification · Specification

## Status

- Primary task mode: `SYSTEM-IMPROVE`
- Base main: `e49304bde7fb0c5ba0822deb3823f960c6425804`
- Working branch: `ui/homepage-product-language-unification`
- Visual authority: current Product Homepage
- Architecture boundary: SolidJS + TypeScript + Vite / Tauri 2 / Python Core / SQLite / Astro + Starlight

## Goal

Unify Product Site, Docs, and Studio under one Quillframe product language while preserving the different information densities and jobs of each surface. The Homepage remains the visual reference. Other surfaces move toward its design DNA; the Homepage is not redesigned to match legacy route styling.

Core composition model:

`PAGE == CANVAS`

Hero eyebrow, title, lede, actions, and visual participate directly in page composition. The hero itself is not a card. Only real content objects—manuscript sheets, previews, diagrams, tool surfaces, code, and bounded artifacts—may be contained surfaces.

The default light canvas is white / warm ivory / near-white. Semantic colors are reserved for small states, icons, nodes, labels, selections, annotations, and focus/hover, not route wallpaper.

## Product language

Hierarchy priority:

`whitespace → typography → alignment → composition → tint/color → decoration → border only when needed`

Avoid card soup, giant hero cards, universal 1px borders, nested panels, route rainbow backgrounds, generic admin-dashboard composition, late override CSS, `!important` specificity hacks, infinite idle animation, and default polling.

Kawaii personality comes from proportion, soft touch targets, tiny labels, index/tape/stitch/sparkle motifs, slight asymmetry, and friendly microcopy—not broad pastel wallpaper or emoji density.

## Shared shell contract

Top navigation, mobile navigation, footer, and command palette must derive from one traceable navigation model rather than drifting hard-coded copies.

Primary product entries include Product, Studio product landing, Architecture, Publication, Docs/Knowledge, and GitHub repository. Utility entries include Project Inspector, Local Playground, Agents, Changelog, and Hosted Studio.

GitHub is a real external entry to the repository root with safe new-window semantics. The footer primary product section must stay synchronized with top navigation, and mobile navigation must expose the same primary entries. The command palette must reach Changelog, GitHub, and Studio landing while distinguishing Hosted Studio from the Studio product landing.

Visible version identity must align with the current 0.9.x development line; stale 0.8.x shell copy is not allowed.

## Public routes

Audit and reconstruct `/`, `/product`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, and `/changelog`.

Homepage stays the reference. Product and Studio landing use borderless editorial heroes and avoid mechanical card grids. Architecture becomes a clean ivory execution-paper workspace with restrained semantic node accents. Publication becomes a proofing/typesetting desk whose formats differ through paper/device objects, typography, and metadata rather than wallpaper color. Inspect, Playground, and Agents remain real tools with bounded tool surfaces but no enclosing hero/tool-card nesting. Changelog becomes an editorial release notebook/timeline rather than a release-card grid.

## Docs

Keep Astro + Starlight. Docs inherit the shared semantic foundation with reading-first composition: article/title live directly on canvas; sidebar is not a card stack; code/table/callout can be bounded where necessary. Search, locale, theme, TOC, mobile sidebar, CJK reading rhythm, and accessibility must not regress.

## Studio

Studio remains authoring-environment-first. The overall workstation is warm ivory/white, not pastel dashboard wallpaper. `.nf-page-intro` or equivalent page intro places title/eyebrow/actions directly on the workspace canvas instead of a generic rounded admin card.

All Writer and Inspector functionality, Core Bridge behavior, settings, model configuration, runtime/session/semantic inspection, and truthful Core state remain intact. Desktop may be multi-column, tablet uses progressive reduction/overlay, phone is focus-first.

## Responsive and accessibility

Verify approximately 1440 / 1024 / 768 / 430 / 375 widths. Minimum interactive target is 44px. Preserve semantic HTML, keyboard navigation, visible focus, logical focus order, `aria-expanded`, dialog semantics, skip links, reduced motion, sufficient contrast, and no hover-only or color-only state.

## Quality contract

Update stale visual tests rather than deleting gates. Gates protect Homepage authority, canvas-first heroes, white kawaii baseline, restrained semantic color, no card soup, responsive behavior, touch targets, accessibility, real interactions, single style ownership, no specificity hacks, no infinite animation/polling, Docs readability, and Studio authoring density.

The old 28px-radius + shadow + dashed-frame `ProductSurfaceHero` treatment is explicitly not an invariant. Shared-shell quality must add GitHub-entry and header/footer/mobile synchronization checks.

## Completion truth

Only after deterministic builds/tests, responsive/accessibility verification, and actual visual QA may the candidate move to `review / awaiting_user`. Do not declare design acceptance and do not merge main.