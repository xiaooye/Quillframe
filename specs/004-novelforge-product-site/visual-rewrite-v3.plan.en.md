# Plan · Product Site Visual Rewrite v3

## Phase V0 · Freeze the rewrite contract

- Keep existing Product Site routes, authority boundaries, i18n model, Story Loom/WeiUI source authority, and deployment pipeline.
- Treat the current Visual v2 homepage as replaceable presentation, not implementation authority.
- Commit this spec/plan/tasks pair before rewriting application structure.

## Phase V1 · Clean-slate homepage composition

Rewrite `site/src/App.tsx` homepage composition from scratch while preserving shared route shell and truthful content sources.

Target chapters:

1. cinematic full-width hero;
2. editorial problem chapter;
3. sticky Forge scroll story;
4. asymmetric proof field;
5. immersive Studio chapter;
6. publication material chapter;
7. architecture constellation;
8. host/release close;
9. final navigation CTA.

The rewrite must not retain the old three-card problem wall, generic proof grid, ordinary architecture bento, or detached dashboard-card hero as the dominant composition.

## Phase V2 · Rebuild the CSS architecture

Rewrite `site/src/styles/site.css` as the base/reset/layout/accessibility layer and `site/src/styles/showcase.css` as the premium material/motion layer.

Use:

- CSS Grid named/asymmetric layouts;
- `color-mix()` derived Story Loom colors;
- radial/conic gradients and masks;
- SVG/CSS loom/thread visuals;
- restrained backdrop blur for chrome/instrument surfaces;
- perspective and layered transforms where meaningful;
- `animation-timeline: view()` / `scroll()` progressive enhancement;
- View Transition styling;
- pointer-driven CSS variables with event-only updates;
- mobile/reduced-motion fallbacks.

Do not introduce an animation framework for this slice.

## Phase V3 · Native bilingual geometry

- Keep Chinese hero and chapter headings independently tuned from English.
- Do not force English display line lengths onto Chinese.
- Keep machine IDs/contract names visible only where they function as proof/provenance.
- Preserve the current native-copy quality gate.

## Phase V4 · Destination route coherence

Destination routes may remain structurally quieter than Home, but must inherit the new material system, typography, header, transitions, and dark/light chapter identity so navigation does not feel like entering a different product.

## Phase V5 · Deterministic verification

Run current Product Site quality and production build. Extend checks only where necessary to ensure:

- premium rewrite still contains required progressive-enhancement primitives;
- no idle infinite animation;
- no `requestAnimationFrame`/polling decorative loop;
- locale-specific typography remains explicit;
- Story Loom theme remains the source authority;
- routes and host-neutral build remain unchanged.

## Phase V6 · Visual acceptance

Acceptance requires visual review at:

- large desktop;
- ordinary laptop/desktop;
- phone/narrow width;
- `zh-CN` and `en-US`;
- normal and reduced motion.

Review specifically for: first-impression premium quality, section rhythm, excessive card repetition, text readability over gradients, motion coherence, and mobile simplification.

## Phase V7 · Deploy

Use the existing Product Site workflow. Deployment is accepted only after quality/build pass. Cloudflare remains replaceable static infrastructure and does not enter Product Site semantics.

## Rollback

The rewrite implementation should be one independently revertible presentation commit (plus narrowly scoped verification fixes if necessary). Reverting it must restore the previous visual implementation without changing Core, Studio Host Bridge, Publication, or production-readiness contracts.
