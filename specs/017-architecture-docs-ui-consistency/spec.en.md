# Quillframe Architecture / Docs UI Consistency Bugfix · Specification

## Status

- Primary task mode: `SYSTEM-IMPROVE`
- Frozen base main: `4e1945f9ba7604891713d4584f47b71b8077bdfc`
- Working branch: `fix/architecture-docs-ui-consistency`
- Scope: follow-up bugfix after the product-language reconstruction; no redesign or architecture migration
- Hosting: Cloudflare only; no Vercel configuration or deployment

## Problem A — Architecture execution path

The `/architecture` seven-step execution path must preserve the semantic order:

`Project → Manager → Context → Worker → Gate → Settlement → Publication`

The current implementation mixes a seven-column Grid with per-node left margins and absolutely positioned connectors. A later route stylesheet also redefines node width and horizontal scrolling. Cards and connectors therefore have separate layout ownership, causing drift, narrow text columns, ellipsis, and a horizontal-scroll mobile experience.

Required mechanism:

- one route-owned layout system in `architecture-explorer.css`;
- node and connector spacing are modeled together;
- no per-card margin/translate positioning hacks;
- no absolute connector positioning;
- no late architecture rail override in `unified-product-app.css`;
- shared card height/inner rhythm and natural word wrapping;
- desktop seven-step editorial strip;
- tablet semantic 4+3 reflow;
- phone vertical sequence;
- no horizontal page overflow;
- hero path and execution path consume the same `architectureNodes` order.

## Problem B — Docs current-product identity

Current Docs runtime/build surfaces must use `Quillframe`. `NovelForge` is allowed only in explicit historical/migration records, never current chrome, nav, CTA, title, metadata, or live destination links.

The current Docs landing still exposes NovelForge product identity and `/why-novelforge` links even though the active Starlight manifest/config uses `why-quillframe`. These current-product references must be corrected without global replacement.

Canonical current destinations:

- GitHub: `https://github.com/xiaooye/cn_webnovel_agent`
- Hosted Studio: `https://studio.quillframe.wei-dev.com`
- product/docs identity: `Quillframe`

## Problem C — semantic foreground ownership

Product and Docs foreground colors must be owned by semantic components rather than incidental inheritance or decorative child selectors.

Requirements:

- reuse existing palette tokens through semantic aliases where useful;
- normal nav, active nav, body/link, hover/focus, action foreground, and muted text remain distinct;
- nested icon/text spans normally inherit the owning anchor/control foreground;
- no global `a { color: ... }` or `span { color: ... }` patch;
- no new `!important`;
- visible focus remains intact and contrast is not weakened for kawaii styling.

## Responsive / accessibility contract

Verification targets: 1440, 1024, 768, 430, 375 CSS viewport behavior. Interactive navigation targets remain at least 44px on mobile/touch surfaces. Preserve semantic anchors/buttons, keyboard access, visible focus, `aria-expanded`, reduced-motion behavior, and logical reading order.

## Deterministic quality contract

Quality must prevent regressions by asserting:

- exact architecture semantic order;
- one architecture layout owner;
- desktop/tablet/phone execution-path strategies;
- absence of per-node margin/translate and absolute-connector hacks;
- absence of late architecture rail ownership in shared route CSS;
- current Docs landing/title/shell use Quillframe and `why-quillframe`;
- canonical GitHub and Hosted Studio destinations;
- stale current-product NovelForge identity is forbidden in current Docs runtime components;
- semantic color ownership exists for Product/Docs navigation and nested link spans inherit parent foreground;
- no new destructive global anchor/span color rule and no `!important` in modified style owners.

## Completion truth

Code-complete requires deterministic quality/build checks to pass. If a real rendered browser is unavailable, the truthful status is:

`code-complete / rendered visual acceptance pending`

Static CSS inspection must not be presented as rendered visual acceptance.