# Product Experience v5 · Story Loom Kawaii Atelier

## Status

Candidate implementation contract for the NovelForge public Product Entry SPA.

This spec supersedes the **presentation and composition** direction of Product Entry v4. It does **not** supersede v4's shipped product capabilities: SolidJS routing, WeiUI foundation, Story Loom semantic tokens, command palette, interactive product labs, hosted Studio entry, build-time Knowledge Explorer, documentation AST rendering, architecture explorer, publication explorer, release truth, accessibility, or authority boundaries.

## Product outcome

The public site must feel like a complete creative-tool product entry point that can attract a prospective user, not a documentation portal and not a static SaaS brochure.

The signature visual direction is **Story Loom Kawaii Atelier**:

- premium creative-tool finish;
- warm paper / atelier surface rather than default dark-dashboard chrome;
- dense but legible product information;
- playful editorial composition with distinct section shapes;
- restrained kawaii personality through stickers, rounded/tactile controls, tiny kaomoji/emoji states, paper tabs, soft shadows, tape/ribbon motifs, and small illustrative product objects;
- Story Loom lane colors are visible and useful instead of being buried under grey glass;
- cute details never replace product clarity, evidence, accessibility, or professional credibility.

Target balance: **90% premium professional product design + 10% kawaii personality**.

## Foundation and authority

The dependency stack remains:

```text
SolidJS application shell
→ generated WeiUI tokens + CSS primitives
→ Story Loom v2 semantic theme
→ NovelForge Product Experience composition
→ progressive modern-CSS enhancement
```

Hard constraints:

- no parallel design-token authority;
- no React / `@weiui/react` / `@weiui/headless`;
- no WeiUI runtime JavaScript;
- no private Core imports;
- Product Site / generated docs remain `authority=false`;
- no fake customers, fake usage counts, fake trial/pricing, or fake runtime screenshots;
- no default polling or decorative frame loop;
- no infinite idle animation;
- reduced-motion must produce a complete static final state;
- mobile remains first-class and touch targets derive from `--nf-touch-target-min`.

## Customer journey

The home route must support this journey without forcing users through documentation first:

1. recognize NovelForge as a creative fiction product;
2. understand the core promise in one compact hero;
3. see and interact with a believable product workspace;
4. touch real product mechanisms;
5. choose a real entry door: Studio, Knowledge, Architecture, Publication;
6. inspect credible implementation evidence and current release truth.

Documentation is a product capability and destination, not the visual center of gravity.

## Visual grammar

### Surface

Default presentation is light/warm. Dark remains user-selectable but uses Story Loom chroma rather than an OLED/black SaaS aesthetic.

Use existing semantic lanes:

- Project blue → context/project objects;
- Runtime violet → Studio/runtime;
- Editorial pink → reader/editorial;
- Evidence gold → knowledge/evidence;
- Validated mint → accepted/pass/readiness;
- Rejected rose → failed/rejected state.

### Shape language

Allowed signature devices include:

- scalloped or perforated paper edges;
- sticker tabs and tape corners;
- notebook / atelier windows;
- asymmetric bento and overlapping paper layers;
- soft clay-like controls using WeiUI primitive semantics;
- squircle/corner-shape progressive enhancement;
- tiny stars, hearts, ribbons and kaomoji as secondary state language;
- illustrated product objects built from CSS/SVG where useful.

Avoid uniform rounded-rectangle glass cards across the whole page.

### Typography

- Hero titles are compact; they must not occupy an entire viewport.
- Chinese receives independent geometry and native copy.
- Display personality may be stronger in labels/headings, while body text remains a highly readable system/sans stack.
- Dense sections should use typographic hierarchy instead of empty space for separation.

## Interaction grammar

Every major home section must contain a meaningful interaction or real navigation target.

Existing functional interactions remain:

- `Cmd/Ctrl+K` command palette;
- context budget lab;
- same-candidate readiness lab;
- Product capability browser;
- Studio hosted entry;
- Architecture explorer;
- Publication profile switcher;
- Knowledge search/filter/full-document routes.

Visual interaction may enhance these through tactile press, layered focus, hover depth, scroll-linked reveals, anchored tooltips/popovers, View Transitions, container-responsive composition and progressive CSS effects.

Effects must pause when user interaction/scroll stops; no ambient perpetual motion.

## Home composition

Required v5 composition:

- **Atelier Hero**: compact promise + real entry actions + interactive workspace/desk composition;
- **Story Loom strip**: lane-colored capability objects/tabs with immediate state feedback;
- **Workbench spread**: context/readiness labs presented as one authored notebook/workbench composition, not two generic dashboard cards;
- **Product shelf**: asymmetric product doors where Studio is the primary surface and Knowledge/Architecture/Publication have distinct visual identities;
- **Knowledge shelf**: real compiled docs/search preview with visible source truth but without turning the page into docs chrome;
- **Trust/footer**: current release state, GitHub/source path and no-authority truth kept compact.

## Route composition

`/product`, `/studio`, `/architecture`, `/publication`, `/docs`, `/docs/:docId`, and `/changelog` must feel like parts of the same application shell. They must not begin with giant brochure headlines.

Use compact product toolbars, side/inline controls, dense interactive panels, and route-specific visual objects.

`/docs` remains the full Knowledge Explorer and `/docs/:docId` remains the structured AST reader.

## Modern CSS policy

Progressive enhancement may use, when guarded appropriately:

- `color-mix()` / OKLCH;
- container size/style queries;
- scroll-state queries where supported;
- scroll/view timelines;
- View Transitions;
- `:has()`;
- `@property`;
- `@scope`;
- `@starting-style` + discrete transitions;
- CSS anchor positioning / position fallbacks;
- masks, gradients, blend modes and filter effects;
- motion paths for interaction-driven decorative objects;
- `corner-shape` / newer shape primitives when supported.

The base product must remain fully usable without any one enhancement.

## Acceptance

v5 is accepted only when:

- current Product Site quality gate passes;
- TypeScript and Vite production build pass;
- Cloudflare production deployment passes;
- WeiUI exact generated foundation remains verified;
- generated Knowledge corpus remains available;
- desktop and mobile layouts do not horizontally overflow;
- keyboard focus and reduced-motion remain correct;
- default first-load presentation is the warm Story Loom Atelier, not v4 dark glass;
- homepage section rhythm is visibly non-uniform and substantially denser than v4;
- Studio / Knowledge / Architecture / Publication remain directly actionable;
- no product claim exceeds current implementation truth.
