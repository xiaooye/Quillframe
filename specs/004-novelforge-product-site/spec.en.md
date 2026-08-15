# NovelForge Product Site — Godot Web Specification

**Status:** current implementation contract  
**Scope:** public Product Site under `site/**`. The separate local Studio application under `studio/app/**` is out of scope.

## 1. Product boundary

NovelForge exposes two deliberately different browser applications:

- **Product surfaces:** `/`, `/product`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, `/changelog`.
- **Documentation:** `/docs/**`.

Product surfaces are rendered by one live **Godot 4.7.1 Web** runtime. Documentation is rendered by **Astro 7.1.6 + Starlight 0.41.5** as semantic HTML. The former SolidJS/Vite implementation under `site/**` is retired and must not be reintroduced as a fallback Product runtime.

## 2. Runtime contract

### G1 — Godot-first Product UI

The Product runtime MUST use GDScript, the Compatibility renderer, an adaptive Web canvas, and a single-threaded Web export unless hosting requirements are intentionally changed. Product UI uses Godot `Control`/Canvas primitives.

### G2 — 2D + controlled 2.5D

The public Product runtime MUST NOT introduce `Node3D`, `Camera3D`, meshes, 3D physics, or a 3D scene stack. Spatial character comes from layered topology, elevation, parallax, glow, route accents, and bounded execution-packet motion.

Continuous decorative idle animation is not allowed. Motion may run briefly in response to route changes or user interaction. `prefers-reduced-motion: reduce` MUST freeze decorative motion while keeping the final state legible.

### G3 — Real browser routes without Product reloads

Each Product route MUST be directly addressable. Internal Product navigation MUST synchronize `history.pushState`. Browser back/forward MUST route the existing Godot scene through a retained `JavaScriptBridge.create_callback` instead of intentionally reloading the document.

Crossing into `/docs/**` MUST be a hard document navigation. Missing Docs pages MUST NOT fall through into the Product canvas.

### G4 — Responsive scene composition

The runtime MUST derive layout from the real browser viewport. It MUST provide explicit `desktop`, `compact`, and `phone` states. Phone topology is a dedicated portrait composition, not a scaled desktop graph.

## 3. Visual authority

### G5 — Story Loom token projection

`assets/brand/tokens.json` is the visual token authority. The Product build MUST deterministically project it into Godot through `site/scripts/generate-godot-theme.mjs` and `site/godot/generated/story_loom_tokens.gd`.

The runtime MUST expose browser evidence that `Story Loom v2` and token schema `novelforge_brand_tokens_v2` are applied. Route accents MUST come from semantic token families rather than independent hard-coded brand systems.

## 4. Language and accessibility

### G6 — Bilingual Product contract

Product supports `en-US` and `zh-CN`, provides an explicit in-scene locale toggle, persists the choice in browser storage, and honors a Chinese browser locale on first run. Docs handoff follows Product locale: English to `/docs/en/`, Chinese to `/docs/`.

### G7 — Interaction accessibility

Interactive Product controls MUST have at least a 44px target, keyboard focusability, and a visible focus ring derived from canonical Story Loom interaction tokens. Browser QA MUST expose and verify the accessibility markers.

## 5. Documentation contract

`/docs/**` remains web-native for long-form reading, semantic links, selection, indexing, accessibility, and localization. Starlight owns Docs routing and output. Godot MUST NOT claim Docs paths.

## 6. Build and deployment contract

The composed build is:

1. stage and build Starlight Docs into `site/dist/docs/`;
2. export Godot Web into `site/dist/index.html` plus WebAssembly/resource artifacts;
3. preserve root static files such as `_redirects`;
4. verify each production asset is below the hosting platform's individual-file ceiling;
5. deploy the composed directory to Cloudflare Pages.

Product bundle size is not a UX optimization objective. Size work is justified only where necessary to satisfy a hard hosting/deployment constraint.

## 7. Browser acceptance evidence

Current-HEAD Browser QA MUST prove:

- Godot engine starts and the scene reaches `ready`;
- root and deep Product URLs resolve to the Godot host;
- `/docs/` remains Starlight HTML;
- desktop and phone responsive states render;
- Story Loom token/theme markers are present;
- both Product locales apply in the live runtime;
- 44px/accessibility and motion markers are present;
- browser history changes the live Product scene without a document reload;
- representative desktop screenshots are materially distinct across Product routes.

## 8. Authority boundary

The public Product Site and Docs are presentation/navigation surfaces only. They do not gain Canon, Memory, Settlement, Framework-write, production-readiness, or Publication authority. A visualization or browser projection never becomes a second source of truth.
