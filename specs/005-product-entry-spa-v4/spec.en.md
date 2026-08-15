# Specification · NovelForge Product Entry SPA v4

## Baseline

- Framework development baseline: latest `main`.
- Change class: Product Web surface / structural feature.
- Primary mode: `SYSTEM-IMPROVE`.
- Parent Product Site contract: `specs/004-novelforge-product-site/`.
- v4 is a Product Entry architecture, not a visual patch over v3.

## Product identity

The NovelForge public site is a first-class **Product Entry SPA**. It attracts prospective users, demonstrates real product capabilities, provides actionable entry points, hosts product knowledge navigation, and routes people into Studio / Publication / Architecture / Docs / GitHub.

It is not a docs skin, README mirror, static marketing brochure, fake SaaS dashboard, or Generic Core / Canon authority.

## Foundation authority

The dependency direction is fixed:

`SolidJS application shell → WeiUI tokens/CSS primitives → Story Loom v2 semantic theme → NovelForge Product Entry composition/motion`.

Hard requirements:

- WeiUI continues to own the base UI contract.
- `assets/brand/tokens.json` remains NovelForge product-token authority.
- `assets/brand/weiui.integration.json` remains the exact WeiUI consumption contract.
- `assets/brand/story-loom.weiui.css` remains the live semantic theme.
- No second palette, focus, touch, spacing, or component foundation.
- No `@weiui/react` or `@weiui/headless`.
- Site-only composition variables must derive from Story Loom / WeiUI semantic variables.

## Visual direction · premium cute

The target is **premium cute creative-tech**: professional, precise, friendly, collectible, and playful without becoming juvenile. It must not regress to austere luxury-magazine black/white or generic purple AI SaaS.

Story Loom lane colors must become the material system: project blue, runtime violet, editorial pink, evidence gold, validated mint, and rejected rose.

Allowed:

- small kawaii mascots / stickers / emoji / kaomoji;
- tiny stars, hearts, ribbons, sparkle, paper/glass/candy material reactions;
- charming empty and success states;
- kawaii as product-state language, never fake customer/avatar social proof.

Forbidden:

- giant decorative anime hero art that overwhelms the product;
- fake testimonials, users, usage stats, or ratings;
- glass-card soup;
- giant monochrome editorial headlines plus empty space as the main layout language;
- generic purple-gradient SaaS styling.

## Product Entry surfaces

### Home

The first two screens must expose real next steps: Open Studio, Search / Command Palette, Product capabilities, Architecture, Publication, and Knowledge / Docs. Brochure narrative is secondary to operable product surfaces.

### Studio

`/studio` must expose the current hosted/read-only Studio boundary, a prominent hosted Studio CTA, and actual capability entry points without pretending Core is bound. Host capability never grants Canon / Settlement / Framework-write authority.

### Knowledge Explorer

`/docs` becomes an in-product Knowledge Explorer.

Build pipeline:

`docs/documentation_manifest.json → maintained Markdown source → safe structured AST + search index → static Product Entry assets`.

Requirements:

- repository Markdown remains content authority;
- no second CMS;
- no runtime GitHub API dependency;
- never inject raw unsanitized Markdown HTML;
- expose source path / tier / status / authority metadata;
- build en/zh from manifest pairings;
- support search, document open, TOC, code, lists, quotes, tables, and core document structure;
- `/docs/:docId` must deep-link.

### Architecture / Publication / Product

These routes must become interactive product surfaces: focusable/expandable system map, capability/detail popovers, publication profile explorer, source/boundary drill-down, keyboard and touch operation.

## Global interaction model

Provide a Command Palette / global search, `⌘K` / `Ctrl+K`, mobile equivalent, route-aware results, unified navigation across docs/product/architecture, visible focus, and ≥44×44px touch targets. Popover/dialog/anchor positioning may progressively enhance, but fallback remains operable.

## Modern CSS / Web UI enhancement budget

Progressive enhancement may use container size/style queries, subgrid, `:has()`, `color-mix()` and relative semantic color derivation, cascade layers, nesting, `@scope`, masks, clip-path, filters, blend modes, layered conic/radial/mesh-like gradients, 3D transforms, small motion-path decorations, scroll/view timelines, View Transitions, Popover + Anchor Positioning, `@starting-style`, `transition-behavior: allow-discrete`, container-driven density, `content-visibility`, and semantic native top-layer controls.

Hard limits: no scroll-jacking, no default polling, no infinite idle decorative loops, no mandatory pointer-only interaction, full reduced-motion final state, and unsupported experimental syntax cannot be the only content/navigation path.

## Information density

v4 must not use “giant headline + giant empty field” as the dominant rhythm. Desktop viewports should contain multiple understandable or operable information points. Mobile uses progressive disclosure rather than compressing into an unusable dashboard.

## Content truth

Static product proof comes from maintained current contracts. Illustrative state is marked illustrative/derived. Hosted Studio must represent its unbound-Core state honestly. Documentation AST/search is a build-time derivative with `authority=false`. Publication/Readiness/Canon truth stays with the owning Core contracts.

## Acceptance

1. Product Site presents as a Product Entry SPA, not a docs site.
2. WeiUI / Story Loom foundation is provable by deterministic QA.
3. Home first two screens expose at least four real operable product entry points.
4. Global command/search works with keyboard and touch.
5. `/docs` consumes build-time generated repository documentation data.
6. At least one real document is fully readable inside the SPA without GitHub navigation.
7. `/docs/:docId` deep links work.
8. Architecture / Publication / Studio each have at least one real interactive affordance.
9. zh-CN uses native copy; technical identifiers remain English only where needed.
10. Premium-cute visuals derive from Story Loom semantic colors, not a parallel palette.
11. Emoji / kaomoji / kawaii sticker state language is allowed; fake social proof is not.
12. Modern CSS enhancements preserve complete function under reduced-motion / unsupported features.
13. TypeScript/Vite build, Product Site quality, and Cloudflare deployment remain deterministic green.
