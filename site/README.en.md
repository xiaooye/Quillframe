# NovelForge Product Site

NovelForge's public Product surface is a **Godot Web control room** with a separate Astro/Starlight documentation application.

## Runtime boundary

- Product routes (`/`, `/product`, `/studio`, `/architecture`, `/publication`, `/inspect`, `/playground`, `/agents`, `/changelog`) run inside one Godot Web scene.
- `/docs/**` is owned exclusively by Astro/Starlight and remains semantic HTML.
- Crossing into Docs is a real document navigation.
- Browser back/forward is bridged into the live Godot scene; Product history does not intentionally reboot the runtime.
- The Product runtime is 2D-first with controlled 2.5D depth cues. It does not use Godot 3D nodes.

The former SolidJS/Vite Product SPA has been retired. It is no longer built, previewed, or kept as a fallback Product implementation.

## Stack

- Godot `4.7.1` / GDScript / Compatibility renderer for Product Web runtime
- Astro `7.1.6` + Starlight `0.41.5` for `/docs/**`
- Node.js 24.x for static staging, verification, and local dist serving
- Cloudflare Pages for the composed deployment

There is no browser-framework runtime dependency in `site/package.json` for Product.

## Build

Install Node dependencies:

```bash
cd site
npm install
npm run quality
npm run build
```

`npm run build` prepares `site/dist/` and builds Starlight Docs. Product is then exported with Godot:

```bash
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

The composed output is:

```text
site/dist/
  index.html       # Godot Web host shell
  index*.wasm      # Godot Web runtime
  index*.pck       # Product resources
  docs/            # Astro/Starlight semantic HTML app
  _redirects       # canonical Docs roots
```

The repository CI compiles a pinned, single-threaded, 2D-specific Godot Web export template and verifies every Cloudflare Pages asset remains below the platform's individual-file deployment ceiling.

## Product routing

Product routes are browser-addressable but rendered by the same live Godot runtime. The browser bridge synchronizes `pushState` and `popstate` with scene navigation. Local QA proves that back navigation changes the scene without a document reload.

Missing `/docs/**` paths never fall through to the Product canvas. Product deep links do fall back to the Godot host document, matching the Cloudflare Pages deployment model.

## Design contract

The Product surface uses 2D UI plus limited 2.5D spatial language: layered topology, parallax, animated packets, glow, elevation, and camera-like composition without a 3D scene stack. Mobile uses a dedicated portrait topology rather than a scaled desktop graph.

Docs deliberately stay web-native for long-form reading, link semantics, indexing, selection, and accessibility.

## Authority boundary

The public Product surface and Docs are presentation/navigation layers. They have no Canon, Memory, Settlement, Framework-write, production-readiness, or Publication authority. Visual projections can explain runtime state; they never become a second source of truth.
