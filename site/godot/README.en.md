# NovelForge Godot Product Runtime

This directory contains the Godot-first presentation runtime for the public NovelForge product surface.

## Boundary

- Product routes (`/`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, `/changelog`) are rendered by Godot Web.
- Documentation stays in the Astro/Starlight app under `/docs/**`.
- Entering `/docs` performs a full documentation navigation; Godot never claims docs routes.
- The existing Solid product source remains in the repository as reference/fallback source during the migration, but the production root export is replaced by the Godot Web artifact after the normal site build.

## Visual contract

The runtime is intentionally 2D-first with limited 2.5D depth cues:

- Canvas/UI nodes only; no `Node3D`, `Camera3D`, mesh, or 3D physics.
- Compatibility renderer for WebGL 2.
- Depth comes from parallax, layered grids, shadows, animated packets, and elevated panels rather than 3D scenes.
- Route URLs and browser back/forward behavior remain browser-history authoritative.

## Local export

Install Godot 4.7.1 plus matching export templates, then from `site/` run:

```bash
npm run build
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

`npm run godot:build` exports into `site/dist/index.html` plus sibling Godot Web artifacts. The already-built `site/dist/docs/` directory is preserved.

## CI

`.github/workflows/product-site.yml` pins Godot `4.7.1-stable`, installs matching official export templates, runs the existing product/docs build, replaces only the product root with the Godot export, then deploys to Cloudflare Pages.

`site/scripts/godot-web-quality.mjs` locks the cross-app route boundary, web renderer, product-route contract, and deliberate absence of 3D nodes.
