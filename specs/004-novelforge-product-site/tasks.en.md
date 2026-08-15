# Tasks · NovelForge Product Site

## T0 · Structural contract

- [x] Open tracking issue #34.
- [x] Define bilingual Product Site specification.
- [x] Define bilingual implementation plan.
- [ ] Commit spec / plan / tasks as one structural-intent checkpoint.

## T1 · Application scaffold

- [ ] Create `site/package.json` with exact SolidJS/Vite/router/TypeScript versions.
- [ ] Create TypeScript and Vite configuration.
- [ ] Create semantic `index.html` metadata shell.
- [ ] Add `src/main.tsx` and router/AppShell.
- [ ] Add host-neutral static build output to `site/dist/`.

## T2 · Story Loom application foundation

- [ ] Consume the repository Story Loom application theme without copying the product palette.
- [ ] Keep `assets/brand/tokens.json` as source authority.
- [ ] Keep `assets/brand/weiui.integration.json` as exact WeiUI upstream contract.
- [ ] Do not introduce `@weiui/react` or `@weiui/headless`.
- [ ] Add site-only layout/marketing CSS that references semantic variables rather than redefining product colors.

## T3 · Global UX shell

- [ ] Responsive top navigation with Product / Studio / Architecture / Publication / Docs.
- [ ] Secondary Changelog / GitHub / locale / appearance controls.
- [ ] Mobile navigation with >=44px controls and keyboard operation.
- [ ] Visible focus states.
- [ ] Footer with product/status/deep-document links.
- [ ] `en-US` / `zh-CN` locale architecture.

## T4 · Product Home

- [ ] Hero-Centric section with one primary thesis and two honest next-step CTAs.
- [ ] Problem section explaining prompt-only failure modes without competitor FUD.
- [ ] “The Forge” story section showing Project → Context → Simulation → Draft → quality/semantic gates → candidate.
- [ ] “Proof, not promises” modules backed by current machine contracts.
- [ ] Studio product section.
- [ ] Publication section with exact current scope boundary.
- [ ] Architecture bento with one message per card.
- [ ] Delivery / one-product-many-hosts section.
- [ ] 0.8.x release-truth section.
- [ ] Final CTA to Docs / Architecture / GitHub.

## T5 · Destination routes

- [ ] `/product` — product model / why NovelForge.
- [ ] `/studio` — Creator/Inspector/portable-host product story.
- [ ] `/architecture` — subsystem map and deep links.
- [ ] `/publication` — current deterministic compiler and remaining #16 scope.
- [ ] `/docs` — curated canonical documentation portal.
- [ ] `/changelog` — release truth and canonical changelog links.

No route may be a blank placeholder or duplicate the home page verbatim.

## T6 · Accessibility / responsive / motion

- [ ] Mobile-first layout with no required horizontal scroll.
- [ ] Minimum interactive target 44×44px.
- [ ] Semantic landmarks/headings.
- [ ] Focus-visible state for every interactive control.
- [ ] `prefers-reduced-motion` fallback preserving complete content/final state.
- [ ] No idle animation loop.
- [ ] No default polling.
- [ ] No hover-only or drag-only interaction.
- [ ] English and Chinese layouts reviewed independently.

## T7 · Deterministic site quality

- [ ] Add `site/scripts/quality.mjs`.
- [ ] Reject forbidden WeiUI runtime dependencies.
- [ ] Check required routes/locales/source references.
- [ ] Check known fake-marketing placeholders (`10K+`, fake SLA, fake logos/testimonials/trial/pricing copy).
- [ ] Check required reduced-motion/focus/touch source contract.
- [ ] Check no Core private-runtime import from `site/`.
- [ ] Add dedicated model-free GitHub Actions workflow for install/build/quality.

## T8 · Product review

- [ ] Desktop render inspection.
- [ ] Narrow/phone render inspection.
- [ ] English copy/product-flow review.
- [ ] Simplified Chinese native-copy/product-flow review.
- [ ] Keyboard/focus review.
- [ ] Reduced-motion review.
- [ ] Verify every machine/product claim against latest `main`.

## T9 · Deployment

- [ ] Keep Vite output host-neutral.
- [ ] Document Cloudflare Pages root/build/output configuration.
- [ ] Connect/deploy only when an authorized hosting account/tool is available.
- [ ] Do not put Cloudflare-specific product logic in the SPA.

## T10 · Later extensions

- [ ] Build-time Markdown renderer from maintained repository docs.
- [ ] Documentation-manifest-driven navigation/freshness metadata.
- [ ] Build-time full-text search.
- [ ] Interactive architecture explorer.
- [ ] Publication sample previews.
- [ ] Social/OpenGraph assets.
- [ ] Analytics only after a separate privacy/product decision.