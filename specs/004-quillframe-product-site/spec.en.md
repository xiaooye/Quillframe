# NovelForge Product Site — Godot Web Specification

**Status:** current implementation contract  
**Scope:** public Product Site under `site/**`. The separate local Studio application under `studio/app/**` is out of scope.

## 1. Product boundary

NovelForge exposes two deliberately different browser applications:

- **Product surfaces:** `/`, `/product`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, `/changelog`.
- **Documentation:** `/docs/**`.

Product surfaces are rendered by one live **Godot 4.7.1 Web** runtime. Documentation is rendered by **Astro 7.1.6 + Starlight 0.41.5** as semantic HTML.

The former SolidJS/Vite Product implementation under `site/src/**` is **not a Product runtime**. It is retained only as the non-authoritative Story Loom / Kawaii Atelier golden visual-and-behavior fixture used by screenshot parity QA. Default Product `dev`/`build` commands and production deployment MUST resolve to Godot, never to that fixture.

## 2. Runtime contract

### G1 — Godot-first Product UI

The Product runtime MUST use GDScript, the Compatibility renderer, an adaptive Web canvas, and a single-threaded Web export unless hosting requirements are intentionally changed. Product UI uses Godot `Control`/Canvas primitives.

### G2 — 2D + controlled 2.5D

The public Product runtime MUST NOT introduce `Node3D`, `Camera3D`, meshes, 3D physics, or a 3D scene stack. Spatial character comes from layered 2D surfaces, elevation, bounded parallax, route-specific composition, and interaction feedback.

Continuous decorative idle animation is not allowed. Motion may run briefly in response to route changes or user interaction. `prefers-reduced-motion: reduce` MUST preserve a legible final state without decorative motion.

### G3 — Real browser routes without Product reloads

Each Product route MUST be directly addressable. Internal Product navigation MUST synchronize `history.pushState`. Browser back/forward MUST route the existing Godot scene through retained `JavaScriptBridge` callbacks instead of intentionally reloading the document.

Crossing into `/docs/**` MUST be a hard document navigation. Missing Docs pages MUST NOT fall through into the Product canvas.

### G4 — Responsive scene composition

The runtime MUST derive layout from the real browser viewport. It MUST provide explicit `desktop`, `compact`, and `phone` states. Phone composition is dedicated responsive geometry, not a scaled desktop scene.

## 3. Visual authority and parity

### G5 — Story Loom / Kawaii Atelier preservation

The visual contract has two complementary sources:

1. `assets/brand/tokens.json`, WeiUI integration metadata, and checked-in Story Loom brand assets define canonical design primitives and brand values.
2. The retained SolidJS/Vite Story Loom / Kawaii Atelier implementation under `site/src/**` is the **golden rendered visual-and-behavior fixture** for migration parity only.

Godot MUST preserve the approved baseline's page grid, typography hierarchy, margins, alignment, wrapping, responsive flow, route identity, interactions, and Kawaii Atelier composition. It MUST use deterministic pinned typography/fallback resources so browser/Godot comparisons do not drift with runner fonts.

The golden fixture has no production runtime authority and MUST NOT be shipped as a fallback Product application. A generated GDScript token file is not an independent authority requirement; the current Godot source/parity contracts and current-HEAD browser evidence are the implementation gate.

## 4. Language and accessibility

### G6 — Bilingual Product contract

Product supports `en-US` and `zh-CN`, provides an explicit in-scene locale toggle, persists the choice in browser storage, and honors browser locale on first run. Docs handoff follows Product locale: English to `/docs/en/`, Chinese to `/docs/`.

### G7 — Interaction accessibility

Interactive Product controls MUST preserve the canonical minimum touch target, keyboard focusability, visible focus treatment, and reduced-motion behavior. Source and browser QA MUST fail closed when these interaction contracts regress.

## 5. Documentation contract

`/docs/**` remains web-native for long-form reading, semantic links, selection, indexing, accessibility, and localization. Starlight owns Docs routing and output. Godot MUST NOT claim Docs paths.

## 6. Build and deployment contract

The composed build is:

1. stage and build Starlight Docs into `site/dist/docs/`;
2. export the validated Godot Web runtime through the single parity/size-gated exporter;
3. merge that Product artifact into the root of `site/dist/` while preserving `site/dist/docs/**`;
4. preserve root routing files such as `_redirects`;
5. verify every production asset is below the hosting platform's individual-file ceiling;
6. deploy the composed directory to Cloudflare Pages;
7. verify the public custom domain serves Godot at `/` and a direct Product route while `/docs/` remains Starlight.

Product bundle size is not a UX optimization objective. Size work is justified only where necessary to satisfy a hard hosting/deployment constraint.

## 7. Browser acceptance evidence

Current-HEAD acceptance evidence MUST prove:

- Godot engine starts and the scene reaches `ready`;
- root and deep Product URLs resolve to the Godot host;
- `/docs/` remains Starlight HTML;
- desktop and phone responsive states render;
- Kawaii Atelier geometry/typography remains materially aligned with the retained golden fixture;
- locale, appearance, command-palette, mobile-menu, and browser-history interactions remain functional;
- representative screenshots are captured as visual regression evidence;
- the live custom domain serves the intended Godot/Starlight split after deployment.

Visual diff metrics are evidence, not a license to redesign the approved baseline. Structural layout, typography, and interaction regressions are blocking even when a numerical threshold is not.

## 8. Authority boundary

The public Product Site, its golden visual fixture, and Docs are presentation/navigation/test surfaces only. They do not gain Canon, Memory, Settlement, Framework-write, production-readiness, or Publication authority. A visualization or browser projection never becomes a second source of truth.
