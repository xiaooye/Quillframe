# NovelForge Godot Product Runtime

This directory is the sole Product runtime for the public NovelForge site.

## Boundary

- Product routes (`/`, `/product`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, `/changelog`) are rendered by Godot Web.
- Documentation stays in the Astro/Starlight app under `/docs/**`.
- Entering Docs is a full document navigation; Godot never claims docs routes.
- The former Solid/Vite Product implementation has been retired rather than retained as a production fallback.

## Visual contract

The runtime is intentionally 2D-first with controlled 2.5D depth cues:

- Canvas/UI nodes only; no `Node3D`, `Camera3D`, meshes, or 3D physics.
- Compatibility renderer for WebGL 2.
- Depth comes from parallax, layered grids, glow, animated packets, and elevated panels rather than a 3D scene stack.
- Mobile uses a dedicated portrait topology.

## Browser contract

Product navigation pushes real browser history entries. A retained `JavaScriptBridge.create_callback` binds `popstate` back into the live scene, so browser back/forward changes the Product route without intentionally reloading the document. Docs remain a hard cross-application navigation.

## Local export

Install Godot 4.7.1 and the matching NovelForge Web export template, then from `site/` run:

```bash
npm run build
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

`npm run build` prepares static host files and Starlight Docs. `npm run godot:build` then exports `site/dist/index.html` plus the sibling WebAssembly/resource artifacts while preserving `site/dist/docs/`.

## CI

`.github/workflows/product-site.yml` compiles the pinned 2D-specific Web template, exports Godot as the Product root, verifies the hosting file-size ceiling, and deploys the composed Godot + Starlight site.

`.github/workflows/product-site-browser-qa.yml` exercises desktop/mobile scenes, Product deep links, the Docs boundary, and live no-reload browser history.
