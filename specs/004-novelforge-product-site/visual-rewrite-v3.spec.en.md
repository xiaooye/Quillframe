# Specification · Product Site Visual Rewrite v3

## Baseline

- Parent Product Site contract: `specs/004-novelforge-product-site/spec.en.md`.
- Tracking issue: #34.
- Framework baseline: latest `main` at implementation start.
- Primary mode: `SYSTEM-IMPROVE`.
- Change class: presentation architecture rewrite; no Core/runtime authority change.

## Problem

The current Product Site is structurally correct and truthful, but its visual hierarchy still reads as a polished documentation/SaaS page. Repeated light surfaces, card grids, and a conventional two-column hero do not create the premium, cinematic, editorial product identity expected for NovelForge.

The rewrite must not decorate the current layout. It replaces the homepage composition and visual grammar while preserving product truth, routes, accessibility, i18n, Story Loom authority, low runtime overhead, and deterministic build/deploy contracts.

## UI/UX Pro Max evidence

Use UI/UX Pro Max as design evidence with a high-variance / high-motion / low-density marketing interpretation:

- Gradient Mesh / Aurora Evolved for atmospheric hero/background fields;
- Editorial Grid / Magazine for asymmetric narrative composition;
- Motion-Driven for scroll-linked choreography and state transitions;
- Tactile Digital for restrained press/hover material response;
- Liquid Glass only for navigation/control chrome, never content-card soup;
- Hero-Centric + Scroll Storytelling + Product Demo as the landing-page structure.

Reject skill recommendations that conflict with NovelForge contracts: no idle infinite Aurora loops, no custom cursor requirement, no animation-only content, no heavy default WebGL/Three.js dependency, and no parallel product palette.

## Visual thesis

**Cinematic editorial instrument, not SaaS card catalogue.**

The page should feel like a precision creative tool presented through a premium publication/editorial lens:

- dark cinematic opening stage;
- luminous Story Loom threads / evidence lanes;
- asymmetric typography and negative space;
- alternating dark/light chapters instead of one continuous white document page;
- proof objects integrated into composition rather than boxed as equal feature cards;
- materially differentiated chrome, manuscript, runtime, evidence, and publication surfaces;
- depth from layering, masks, gradients, borders, optical highlights, and scroll choreography rather than gratuitous 3D scenes.

## Homepage architecture

### H1 · Cinematic hero

Replace the conventional left-copy/right-card hero with a full-width stage containing:

- concise product thesis;
- atmospheric mesh/loom field;
- an integrated floating provenance instrument rather than a detached dashboard card;
- a compact contract rail showing real machine-backed proof nouns;
- pointer-responsive lighting as progressive enhancement with no frame loop;
- scroll-linked transition into the next chapter.

### H2 · Editorial problem chapter

Replace three equal cards with an asymmetric editorial composition: one dominant statement plus three indexed failure modes laid out as narrative rails/columns. Desktop may use sticky/asymmetric placement; mobile must retain linear reading order.

### H3 · Forge scroll story

The Forge becomes the primary scroll-story sequence. One visual stage remains sticky while Project → Context → Simulation → Draft → Gates → Review progresses through explicit steps. Scroll effects must be native/progressive and must not hijack scroll.

### H4 · Proof field

Proof modules use varied spans, typography scales, inline machine identifiers, and lightweight diagrams. Avoid a uniform card wall.

### H5 · Studio / Publication feature chapters

Studio and Publication become large immersive chapters with different material identities instead of two-column marketing bands. Their visuals remain illustrative and clearly non-runtime screenshots.

### H6 · Architecture constellation

Architecture is presented as a connected system/constellation rather than a generic bento grid. Every node retains a readable text fallback and explicit ownership label.

### H7 · Release / CTA close

End with a restrained release-truth surface and strong final navigation. Do not imitate pricing/conversion templates.

## Motion contract

- Prefer native CSS `animation-timeline: view()` / `scroll()` progressive enhancement.
- Same-document View Transitions may be used for locale/theme/navigation state changes.
- Pointer response may set CSS custom properties directly on pointer events; no `requestAnimationFrame` or default polling loop.
- Motion explains depth, focus, continuity, or state transition.
- No `animation: ... infinite` in Product Site showcase CSS.
- `prefers-reduced-motion: reduce` resolves to the complete readable final state.

## Material contract

- Story Loom v2 tokens remain color/semantic authority.
- Dark hero may derive deeper shades through `color-mix()` from existing semantic roles; do not add a second brand palette.
- Glass is restricted to header/control/instrument overlays where background context remains legible.
- Main reading surfaces remain opaque enough for stable contrast.
- Texture/noise may be generated with gradients/masks; no large decorative image dependency is required.

## Performance contract

- No new framework/runtime dependency is required for v3.
- No WebGL/Three.js dependency in the default path.
- No idle JS loop.
- CSS effects must degrade to a static composition when unsupported.
- Mobile removes nonessential blur/depth layers before compromising readability or interaction latency.

## Acceptance

1. The homepage DOM composition is materially different from Visual v2 rather than a CSS reskin.
2. Desktop first impression is cinematic/premium/editorial, not documentation/SaaS-card-first.
3. Mobile retains the same content hierarchy without horizontal scrolling or hover dependency.
4. Chinese and English retain independent natural typography geometry.
5. No fabricated social proof or product authority is introduced.
6. No idle animation/default polling is introduced.
7. Reduced-motion exposes full content immediately.
8. Product Site deterministic quality and Vite production build pass.
9. Cloudflare deployment remains host-neutral static output.
10. The rewrite is independently revertible without changing Core/Studio runtime semantics.
