# Specification · NovelForge Product Site

## Baseline

- Framework development baseline: latest `main`.
- Tracking issue: #34.
- Change class: Product Web surface / structural feature.
- Primary mode: `SYSTEM-IMPROVE`.
- Rollback: parent commit of the Product Site implementation.

## Problem

NovelForge now has enough real product, runtime, publication, design-system, and documentation surface that GitHub README pages alone no longer provide a coherent public introduction.

A newcomer currently has to infer the product from architecture-heavy documentation. That creates three problems:

1. the value proposition appears after implementation detail;
2. product proof is scattered across Core, Studio, Publication, quality, and release documents;
3. the repository has no first-class public surface where Story Loom can operate as an interactive product language rather than static documentation decoration.

The Product Site solves this with a standalone SaaS-like SPA whose primary job is **product understanding and trustworthy navigation**, not documentation rendering.

## Product role

The site must communicate in this order:

`value → problem → mechanism → proof → product surfaces → deep documentation`.

It is presentation-only. It never becomes Canon, Memory, semantic truth, production-readiness truth, Publication truth, Settlement authority, Framework-write authority, or another runtime.

## Design evidence

UI/UX Pro Max is used as external design evidence, not repository authority. The applicable pattern is a bounded hybrid of:

- Hero-Centric Design;
- Scroll-Triggered Storytelling;
- Product Demo + Features;
- Bento Grid Showcase;
- Trust & Authority.

Repository Story Loom v2 tokens and Product contracts always override generic palette/style recommendations.

## Goals

### G1 · SaaS-like Product Home

The home page is a product narrative, not a docs index.

Required narrative:

1. Hero: concise NovelForge thesis, primary CTA, secondary proof/navigation CTA.
2. Problem: explain why prompt-only/one-shot fiction generation loses authority, continuity, context discipline, evidence, and repeatability.
3. The Forge: visually explain Project → Context → Simulation → Draft → Reader/Continuity/Semantic gates → User-visible candidate.
4. Proof, not promises: show real machine-backed distinctions from `main`.
5. Studio: Creator/Inspector and portable delivery story.
6. Publication: deterministic Accepted-text publication core and its current boundary.
7. Architecture: subsystem bento with deep links.
8. Delivery: CLI / Local Web / hosted / Agent Skill; host capability != story authority.
9. Release truth: current pre-1.0 identity and development status.
10. CTA: Docs / Architecture / Studio / GitHub.

No fake testimonials, customer logos, usage metrics, prices, uptime, ratings, or scarcity.

### G2 · Long-lived Route Model

Initial routes:

- `/`
- `/product`
- `/studio`
- `/architecture`
- `/publication`
- `/docs`
- `/changelog`

The site is an SPA with deep links. Hosting must remain replaceable static infrastructure.

### G3 · One Content Truth

The Product Site must not create a second CMS or semantic copy of Framework contracts.

- Product marketing copy may summarize maintained contracts.
- Technical claims link to or are generated from maintained repository sources.
- Docs route initially provides curated navigation; future Markdown rendering/search must consume repository source files at build time.
- Dynamic runtime truth is not fabricated from static site state.

### G4 · Story Loom / WeiUI Foundation

- `assets/brand/tokens.json` remains NovelForge product-token authority.
- `assets/brand/weiui.integration.json` remains the exact upstream WeiUI consumption contract.
- `assets/brand/story-loom.weiui.css` remains the live mapping/theme surface.
- No parallel hand-maintained product palette.
- No `@weiui/react` or `@weiui/headless` runtime dependency.
- Until WeiUI packages have a stable cross-repository distribution surface, the Product Site may consume the merged Story Loom application theme directly without claiming an unavailable npm package import.

### G5 · Low-overhead SolidJS Surface

Application stack:

- SolidJS;
- TypeScript;
- Vite;
- `@solidjs/router`.

Local Web is the primary public form. No Tauri dependency is needed for this public site.

The Product Site must not add runtime dependencies to Generic Core, CLI, Framework bundle, Agent Skill, or Studio host bridge.

### G6 · Bilingual Architecture

Baseline locales are `en-US` and `zh-CN`.

- Locale is explicit and switchable.
- Layout cannot depend on fixed English label widths.
- Simplified Chinese copy is native product copy, not literal sentence-by-sentence translation.
- Exact machine identifiers remain untranslated.

### G7 · Accessibility / Responsive / Motion

Hard requirements:

- mobile-first;
- minimum 44×44px interactive targets;
- visible focus states;
- keyboard-accessible navigation and controls;
- no horizontal-scroll requirement;
- semantic headings and landmarks;
- contrast aligned with Story Loom design QA;
- reduced-motion preserves complete content and final state;
- no idle animation loop;
- no default polling;
- content remains understandable without JS-driven animation.

### G8 · Product Proof Modules

Proof surfaces must come from real current contracts, for example:

- semantic support vs actually loaded Context;
- story-order/perspective-safe evidence;
- same-candidate-fingerprint production-readiness conjunction;
- Character visible-evidence discipline;
- exact Accepted-text Publication fingerprint preservation;
- portable Host Bridge `authority=false` boundary;
- deterministic Story Loom/WeiUI design-system checks.

A proof module may simplify presentation, but may not invent a metric, score, customer result, or authority claim.

### G9 · Static Hosting

The build output is a host-neutral `dist/` directory.

Cloudflare Pages is a preferred deployment target because it can serve a Vite SPA directly, but Cloudflare is not product authority and the site must remain deployable to another static CDN/host.

No database, Pages Function, analytics SDK, authentication, or server runtime is required for the first slice.

### G10 · Deterministic Quality Gate

Normal CI must verify at least:

- dependency/version contract;
- TypeScript/Vite production build;
- required route/source presence;
- no forbidden WeiUI runtime package;
- no obvious fabricated social-proof placeholders;
- locale structure;
- Story Loom theme/source references;
- required reduced-motion/focus/mobile contracts in source;
- no Core runtime import from the site.

CI performs no model execution.

## Information Architecture

### Global navigation

Primary: Product, Studio, Architecture, Publication, Docs.
Secondary: Changelog, GitHub, locale, appearance.

### Home composition

The home page should use editorial pacing rather than equal-sized feature-card repetition. Alternate narrative, proof, diagram/product-preview, and bento sections.

### Docs

Docs remain a major destination but not the home-page identity. The first slice can provide curated deep links to canonical source documents while the build-time renderer/search layer is developed separately.

## UX / visual constraints

- Story Loom: precise, editorial, warm, engineered.
- Avoid generic purple-gradient SaaS treatment.
- Avoid glass-card soup and giant everything-dashboard layouts.
- Avoid fake terminal windows used only as decoration.
- Use diagrams/provenance/fingerprints only where they explain product behavior.
- Motion must explain continuity/state transition or stay subtle.
- No scroll-jacking.
- No interaction whose only accessible path is hover or drag.

## Non-goals · first slice

- user accounts / auth;
- billing / pricing;
- analytics / tracking;
- collaboration;
- server database;
- write-capable Studio;
- Tauri packaging;
- complete Markdown full-text search;
- customer case studies without real customer evidence.

## Acceptance criteria

1. `site/` is independently buildable to static `dist/`.
2. The home page is a finished product narrative with real NovelForge claims, not placeholder/lorem ipsum content.
3. All initial routes exist and can be deep-linked through an SPA host.
4. `en-US` and `zh-CN` are represented by an explicit locale architecture.
5. Product visual semantics reuse Story Loom v2; no parallel token palette is created.
6. No forbidden WeiUI runtime package is introduced.
7. Mobile/narrow reading order is coherent and interactive targets respect the 44px contract.
8. Keyboard focus and reduced-motion behavior are present.
9. Product proof uses current repository contracts and contains no fabricated social proof.
10. Site build/quality CI is deterministic and model-free.
11. Generic Core remains independent of the site stack.
12. The first slice is visually/product-reviewable before any hosting account is required.