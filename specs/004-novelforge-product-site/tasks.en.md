# NovelForge Product Site — Godot Replacement Tasks

**Scope:** public site `site/**`. The separate `studio/app/**` remains outside this migration.

Implementation status is recorded here; final release truth comes from the current-HEAD GitHub Actions and deployed site, not from manually copied CI status.

## Runtime replacement

- [x] Make Godot Web the sole public Product runtime.
- [x] Preserve Astro/Starlight as the exclusive `/docs/**` application.
- [x] Remove the legacy `site/src` Solid Product tree and Product Vite entry/config.
- [x] Remove Product browser-framework runtime dependencies and Vite preview from `site/package.json`.
- [x] Preserve Product deep-link fallback without allowing missing Docs paths to become Product routes.
- [x] Keep Product visuals 2D + controlled 2.5D with no 3D nodes.

## Browser/runtime integration

- [x] Synchronize Product navigation through browser `pushState`.
- [x] Bind `popstate` into the live Godot scene through a retained JavaScriptBridge callback.
- [x] Keep Docs navigation as a hard document boundary.
- [x] Publish scene/runtime/layout/history markers for browser QA.
- [x] Provide explicit desktop, compact, and phone layouts.

## Product contract preservation

- [x] Add `en-US` / `zh-CN` Product localization.
- [x] Persist locale and honor browser locale on first run.
- [x] Route English Product users to `/docs/en/` and Chinese users to `/docs/`.
- [x] Enforce canonical 44px touch targets.
- [x] Add keyboard focusability and visible focus styling.
- [x] Honor reduced-motion preferences.

## Story Loom integration

- [x] Treat `assets/brand/tokens.json` as Product visual authority.
- [x] Generate a deterministic Godot token projection and reject stale generated output.
- [x] Derive Product semantic route accents and interaction styling from Story Loom tokens.
- [x] Remove perpetual decorative idle processing.
- [x] Retain 2.5D depth/parallax and bounded route/interaction packet motion.
- [x] Expose applied theme/token schema to browser QA.

## Build/deploy evidence required for completion

A release is complete only when the **same current HEAD** proves all of the following:

- Product-site quality and Story Loom token checks pass.
- Starlight Docs build passes.
- Pinned Godot editor/template setup passes.
- Godot scene instantiation and release Web export pass.
- All Cloudflare Pages production assets satisfy the hard individual-file ceiling.
- Production deployment and custom-domain post-condition pass.
- Browser QA proves root/deep Product routes and the Docs boundary.
- Browser QA proves desktop/phone layouts, both locales, accessibility markers, Story Loom theme markers, and no-reload browser history.
- Browser QA screenshots provide representative visual evidence.
- The live custom domain serves the Godot Product runtime and Starlight Docs split.

## Cleanup condition

The public Product migration must not leave a tracked lockfile or build artifact that falsely declares the retired Solid/Vite Product implementation as a current `site/**` dependency. If a lockfile is retained, it must be regenerated from the final Godot + Starlight package manifest.
