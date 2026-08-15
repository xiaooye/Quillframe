# NovelForge Godot Product Runtime

This directory is the Godot-first presentation runtime for the public NovelForge product surface.

## Boundary

- Product routes (`/`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, `/changelog`) are rendered by Godot Web.
- Documentation remains the Astro/Starlight application under `/docs/**`.
- Crossing into `/docs` is a hard document navigation. Godot never owns documentation routing.
- The existing Solid product source is retained during migration as reference/fallback source, but the production root export is overwritten by the Godot Web artifact after the normal site build.

## Visual contract

The runtime is intentionally 2D-first with limited 2.5D depth cues:

- Canvas/UI nodes only; no `Node3D`, `Camera3D`, meshes, or 3D physics.
- Compatibility renderer for WebGL 2.
- Depth comes from parallax, layered grids, shadows, animated packets, and lifted panels.
- Browser history remains authoritative for route URLs and back/forward navigation.

## Local export

Install Godot 4.7.1 with matching export templates, then from `site/` run:

```bash
npm run build
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

`npm run godot:build` exports to `site/dist/index.html` and sibling Godot Web artifacts. The already-built `site/dist/docs/` tree is preserved.

## CI

`.github/workflows/product-site.yml` pins Godot `4.7.1-stable`, installs the matching official export templates, runs the existing product/docs build, and then replaces only the product root with the Godot export before Cloudflare Pages deployment.

`site/scripts/godot-web-quality.mjs` locks the cross-app routing boundary, Web renderer, product route contract, and the deliberate absence of 3D nodes.
