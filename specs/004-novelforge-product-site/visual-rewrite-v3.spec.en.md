# Product Site Visual Rewrite v3 — Superseded Web-Shell Specification

**Status:** superseded by the Godot Web Product contract in `spec.en.md`.  
**Historical role:** this document originally described the pre-Godot DOM/CSS/Vite visual rewrite. Its surviving design intent is carried forward below; its implementation mechanics are no longer normative.

## Surviving visual thesis

NovelForge should feel like a **cinematic editorial instrument / production control room**, not a SaaS card catalogue or documentation homepage.

The current Godot implementation preserves that intent through:

- a dark Story Loom stage;
- asymmetric control-room composition and negative space;
- connected topology rather than equal-card grids;
- semantically differentiated project/runtime/editorial/evidence/validated surfaces;
- 2D layering, elevation, glow, parallax, animated route packets, and optical depth;
- route-dependent visual emphasis inside one live Product runtime;
- a dedicated phone topology instead of desktop scaling.

## Current implementation rules

1. Product visuals are implemented in Godot Canvas/`Control` nodes, not DOM/CSS layout.
2. `assets/brand/tokens.json` remains the visual authority and is deterministically projected into Godot.
3. Depth is limited to controlled 2.5D. No 3D scene stack is allowed.
4. No perpetual idle animation loop is allowed. Motion is bounded to route transitions/user interaction; pointer parallax is input-driven.
5. Reduced-motion resolves to a static, complete, readable state.
6. Product language and accessibility contracts remain `en-US`/`zh-CN`, 44px minimum targets, keyboard focus, and visible focus rings.
7. `/docs/**` remains a separate Starlight semantic HTML application.
8. Browser acceptance is performed against the exported Godot runtime, not a Vite Product build.

## Authority

For current requirements, use:

- `spec.en.md` / `spec.zh-CN.md` — Product contract;
- `plan.en.md` / `plan.zh-CN.md` — Godot replacement plan;
- `tasks.en.md` / `tasks.zh-CN.md` — implementation and release acceptance.

Any historical DOM, CSS animation, scroll-story, or Vite requirement from earlier revisions is non-authoritative unless it has been explicitly restated in those current contracts.
