# NovelForge Product Site

Standalone public Product / Intro SPA for NovelForge.

This is **not** the Studio application and **not** a replacement content store for the repository documentation. It is the public product narrative and navigation surface around NovelForge Core, Studio, Publication, Architecture, Docs, and release truth.

## Stack

- SolidJS `1.9.14`
- `@solidjs/router` `0.16.2`
- Vite `8.1.5`
- vite-plugin-solid `2.11.14`
- TypeScript `7.0.2`
- Node.js 24.x for CI/build

All direct frontend versions are exact pins. `@weiui/react` and `@weiui/headless` are intentionally absent.

## Story Loom / WeiUI boundary

The site does not own a second palette.

It consumes:

- `../assets/brand/tokens.json` — NovelForge Story Loom v2 product-token authority;
- `../assets/brand/weiui.integration.json` — exact WeiUI upstream pin/consumption contract;
- `../assets/brand/story-loom.weiui.css` — live `wui-theme` application mapping.

The current WeiUI source contract permits `@weiui/tokens` + `@weiui/css` and requires zero WeiUI runtime JavaScript. The WeiUI repository packages do not yet have a stable cross-repository npm distribution contract assumed by this site, so the first public slice consumes the maintained Story Loom theme directly rather than inventing an unavailable package install.

## Local development

```bash
cd site
npm install
npm run quality
npm run dev
```

Production build:

```bash
npm run build
```

Output: `site/dist/`.

## Routes

- `/` — SaaS-like Product Home
- `/product` — product model / boundaries
- `/studio` — Studio phases and product stack
- `/architecture` — subsystem map
- `/publication` — deterministic Publication core
- `/docs` — curated canonical documentation portal
- `/changelog` — release truth

The Docs route links to maintained repository sources; it is not a second CMS.

## Product design contract

The public site follows issue #34 and `specs/004-novelforge-product-site/`.

Key rules:

- Hero-first product value, not architecture-first onboarding;
- real contract evidence instead of fake testimonials / logos / user counts / SLA / pricing;
- mobile-first with >=44px interaction targets;
- visible focus and keyboard-operable navigation;
- `en-US` + `zh-CN` product copy;
- no default polling;
- no idle animation loop;
- reduced-motion preserves complete content;
- no Generic Core runtime dependency on this SPA.

Run:

```bash
npm run quality
```

The quality script verifies stack pins, Story Loom/WeiUI contracts, routes/locales, basic UX invariants, forbidden runtime dependencies, fake-marketing placeholders, and private-Core coupling.

## Cloudflare Pages

The build stays host-neutral. For Cloudflare Pages, configure:

```text
Root directory: site
Build command: npm run build
Build output directory: dist
Production branch: main
```

Do not add a top-level `404.html` unless the hosting strategy changes: Cloudflare Pages treats a site without that file as a single-page application and routes incoming paths to the SPA root.

No Pages Function, database, authentication, analytics SDK, or Cloudflare-specific product logic is required for the first slice.

## Authority boundary

The Product Site is presentation/navigation only.

It has no Canon, Memory, semantic, Settlement, Framework-write, production-readiness, or Publication authority. Product diagrams and UI projections may explain Core state; they never become a second source of truth.
