# NovelForge Product Site — Godot Replacement Plan

**Scope:** `site/**` public Product Site only. `studio/app/**` remains a separate local Studio application.

## Target architecture

```text
Browser
├─ Product routes
│  └─ Godot 4.7.1 Web / GDScript / Compatibility renderer
│     ├─ Main Control scene
│     ├─ live BrowserRouteBridge
│     ├─ Story Loom ThemeBridge
│     ├─ LocaleBridge
│     ├─ AccessibilityBridge
│     └─ 2D/2.5D responsive topology
└─ /docs/**
   └─ Astro 7.1.6 + Starlight 0.41.5 semantic HTML
```

The two applications are composed into one `site/dist/` deployment. Product-to-Docs navigation is intentionally a document boundary.

## Phase 1 — Replace the Product runtime

- Introduce a Godot Web project rooted at `site/godot/Main.tscn`.
- Implement Product route surfaces in one live Godot runtime.
- Keep real browser URLs with `pushState` and bridge `popstate` back into the live scene.
- Preserve `/docs/**` as a separate Starlight application.
- Add custom branded Web shell and runtime-ready browser markers.
- Compile a pinned single-thread Web export template suitable for the Product's 2D feature set.

## Phase 2 — Retire the legacy public SPA

- Remove `site/src`, Product Vite entrypoints/config, and Product-only Solid/Vite quality scripts.
- Remove Product browser-framework runtime dependencies from `site/package.json`.
- Replace Vite preview with a small static dist server that mirrors Product route fallback while refusing Docs fallback.
- Keep `studio/app/**` untouched because it is not the public Product Site runtime.

## Phase 3 — Preserve product contracts in Godot

- Implement explicit `desktop`, `compact`, and `phone` scene layouts.
- Preserve direct Product deep links and no-reload browser back/forward.
- Implement `en-US` / `zh-CN`, persisted locale, explicit in-scene toggle, and locale-aware Docs handoff.
- Enforce 44px targets, keyboard focus, visible focus ring, and reduced-motion behavior.
- Keep visuals strictly 2D + controlled 2.5D; never introduce a 3D scene stack.

## Phase 4 — Make Story Loom authoritative

- Treat `assets/brand/tokens.json` as visual token authority.
- Deterministically project tokens into generated GDScript before Godot export.
- Derive route accents, focus styling, surfaces, and semantic state colors from that projection.
- Remove perpetual decorative idle loops. Keep only bounded transition/interaction motion plus input-driven parallax.
- Publish theme/token markers for browser acceptance tests.

## Phase 5 — Production evidence

The final current HEAD must pass both deployment and browser evidence:

- static Docs staging/build;
- Godot scene instantiation and release Web export;
- Cloudflare individual-file ceiling check;
- Cloudflare Pages production deployment + custom-domain post-condition;
- browser QA of root/deep routes, Docs boundary, desktop/phone layouts, Story Loom theme, both locales, accessibility markers, and no-reload history;
- representative screenshots for visual regression evidence.

## Repository responsibilities

- `site/godot/**`: sole public Product runtime.
- `site/docs-site/**`: Docs application.
- `site/scripts/generate-godot-theme.mjs`: brand-token projection.
- `site/scripts/godot-web-quality.mjs`: static Product runtime contract.
- `site/scripts/godot-browser-proof.mjs`: real-browser runtime evidence.
- `.github/workflows/product-site.yml`: composed build/deploy.
- `.github/workflows/product-site-browser-qa.yml`: visual/runtime acceptance evidence.

## Non-goals

- No Unity/Unreal parallel UI.
- No 3D Product scene stack.
- No tiny-bundle/first-load optimization target beyond hard hosting constraints.
- No migration of the separate `studio/app/**` local application as part of this public-site replacement.
- No presentation-layer authority over Canon, Memory, Settlement, or Framework state.
