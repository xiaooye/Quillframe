# Quillframe Architecture / Docs UI Consistency Bugfix · Plan

## Authority

Implement only against frozen main `4e1945f9ba7604891713d4584f47b71b8077bdfc` on `fix/architecture-docs-ui-consistency`.

## 1. Architecture layout owner

1. Change the execution-path markup in `site/src/ProductApp.tsx` so each semantic step owns its node plus connector.
2. Move all pipeline sizing/reflow behavior into `site/src/styles/architecture-explorer.css`.
3. Remove the later `.architecture-entry .architecture-flow` / node sizing override from `unified-product-app.css`.
4. Use seven equal semantic steps at wide desktop, four columns at tablet, and one column on phone.
5. Remove per-node left margins, absolute connector positioning, current-node translate offsets, forced horizontal scrolling, ellipsis, and line clamping from the pipeline.
6. Preserve the same `architectureNodes` data source for the hero and main path.

## 2. Docs identity audit/fix

1. Correct current landing copy from NovelForge to Quillframe in both locales.
2. Replace live `/why-novelforge` links with `/why-quillframe` / `/docs/en/why-quillframe`.
3. Correct the stale route section slug in `QuillframePageTitle.astro`.
4. Retain canonical GitHub and Hosted Studio destinations already present in the current shell.
5. Do not touch historical specs merely because they legitimately contain NovelForge.

## 3. Foreground ownership

1. Add semantic foreground aliases backed by existing Product and Docs palette tokens.
2. Explicitly assign Product desktop/mobile nav and footer foreground ownership in `product-shell.css`.
3. Make child navigation icon spans inherit their semantic parent foreground.
4. Apply Docs semantic nav/link/action tokens to current shell, sidebar/TOC, inline links, link rows, and CTA roles where those owners already exist.
5. Remove the GitHub child-span muted override that causes icon/text divergence.
6. Preserve visible focus and mobile touch targets.

## 4. Quality hardening

1. Rewrite `architecture-explorer-quality.mjs` checks that currently require the faulty horizontal-scroll/min-width mechanism.
2. Extend `docs-platform-quality.mjs` with current identity/link and semantic color ownership assertions.
3. Extend `product-shell-quality.mjs` with Product nav/footer color ownership and destructive override guards.
4. Keep existing tests; do not weaken unrelated gates.

## 5. Verification and publish

Run the repository's current CI/build authority, including Product quality, Docs quality/build, Studio quality when invoked by the full repo workflow, TypeScript, Vite, Astro/Starlight, and namespace hygiene. Inspect failures and repair real regressions. Open a draft PR to `main`; do not merge.

Rendered browser acceptance is separate from deterministic code/build completion.