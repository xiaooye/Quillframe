# NovelForge Product Site — Godot Replacement Plan

**Scope:** `site/**` public Product Site only. `studio/app/**` remains a separate local Studio application.

## Target architecture

```text
Browser
├─ Product routes
│  └─ Godot 4.7.1 Web / GDScript / Compatibility renderer
│     ├─ responsive Control scene
│     ├─ browser route/history bridge
│     ├─ deterministic typography + Kawaii geometry parity
│     └─ locale / appearance / command / mobile interaction bridge
└─ /docs/**
   └─ Astro 7.1.6 + Starlight 0.41.5 semantic HTML

Repository-only QA fixture
└─ site/src/** SolidJS/Vite Story Loom / Kawaii Atelier golden baseline
   └─ never shipped as the Product runtime
```

The Product and Docs applications are composed into one `site/dist/` deployment. Product-to-Docs navigation intentionally remains a document boundary.

## Phase 1 — Replace the Product runtime

- Introduce the Godot Web project rooted at `site/godot/Main.tscn`.
- Implement Product route surfaces in one live Godot runtime.
- Keep real browser URLs with `pushState` and bridge `popstate` back into the live scene.
- Preserve `/docs/**` as a separate Starlight application.
- Add the branded Web shell and runtime-ready browser markers.
- Compile a pinned single-thread slim Web export template suitable for the Product's 2D feature set and hosting ceiling.

## Phase 2 — Retire Solid/Vite from production, not from parity evidence

- Remove Solid/Vite from the **production runtime path** and default Product `dev`/`build` commands.
- Retain `site/src/**` and its exact browser dependencies only as an explicitly named golden visual-and-behavior fixture for parity QA.
- Keep baseline commands under `baseline:*`; they have no production authority.
- Keep one parity-proven Godot Web exporter and make production assembly consume that exact artifact.
- Keep `studio/app/**` untouched because it is not the public Product Site runtime.

## Phase 3 — Preserve product contracts in Godot

- Implement explicit `desktop`, `compact`, and `phone` scene layouts.
- Preserve Product deep links and no-reload browser back/forward.
- Implement `en-US` / `zh-CN`, locale persistence, explicit toggle, appearance state, command palette, mobile menu, and locale-aware Docs handoff.
- Preserve touch-target, focus, and reduced-motion behavior.
- Keep visuals strictly 2D + controlled 2.5D; never introduce a 3D scene stack.

## Phase 4 — Preserve Story Loom / Kawaii Atelier exactly enough to prevent redesign drift

- Keep canonical Story Loom brand primitives/assets under `assets/brand/**`.
- Use the retained Solid/Vite site only as the rendered golden parity fixture.
- Pin Latin, CJK, symbol, Thai, and Arabic fallback fonts used by browser/Godot comparison.
- Encode page-grid, typography, wrapping, margins, alignment, responsive-flow, and route-identity parity in Godot source contracts.
- Run route-pair screenshot evidence and blocking interaction QA against the golden fixture.
- Do not treat visual-diff metrics as permission to reinterpret the approved layout.

## Phase 5 — Production evidence

The final current HEAD must pass all of the following:

- baseline fixture + Godot source + production assembly contracts;
- Starlight Docs staging/build;
- Godot scene instantiation and release Web export through the single exporter;
- Cloudflare individual-file ceiling check;
- Cloudflare Pages production deployment + custom-domain API post-condition;
- production Browser QA for runtime, routes, interactions, Docs boundary, desktop/phone rendering, and screenshots;
- route parity evidence against the retained golden fixture;
- live HTTP checks proving `/` and a direct Product route are Godot while `/docs/` remains Starlight.

## Repository responsibilities

- `site/godot/**`: sole public Product runtime source.
- `site/src/**`: non-production Story Loom / Kawaii Atelier golden parity fixture.
- `site/docs-site/**`: Docs application.
- `site/scripts/godot-shadow-source-quality.mjs`: production Godot source/parity contract (historical filename retained for compatibility).
- `site/scripts/build-godot-shadow.sh`: single parity/size-proven Godot Web exporter (historical filename retained for compatibility).
- `site/scripts/build-godot-web.sh`: production root assembler preserving `/docs/**`.
- `site/scripts/godot-shadow-browser-shot.mjs`: deterministic browser screenshot driver used by parity and production QA.
- `site/scripts/godot-interaction-qa.mjs`: blocking browser interaction evidence.
- `.github/workflows/product-godot-route-parity.yml`: golden-fixture visual/interaction parity evidence.
- `.github/workflows/product-site.yml`: composed build/deploy + live-domain verification.
- `.github/workflows/product-site-browser-qa.yml`: production visual/runtime acceptance evidence.

## Non-goals

- No Unity/Unreal parallel UI.
- No 3D Product scene stack.
- No tiny-bundle/first-load optimization target beyond hard hosting constraints.
- No migration of the separate `studio/app/**` local application as part of this public-site replacement.
- No deletion of the golden browser fixture while it remains the regression oracle for approved Kawaii layout.
- No presentation-layer authority over Canon, Memory, Settlement, or Framework state.
