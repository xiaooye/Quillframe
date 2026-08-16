# Product Godot Migration · Visual Parity Contract

## Status

This is the migration contract for moving the NovelForge Product Site from the Solid/Vite shell to Godot Web. It does not change the Story Loom Kawaii Atelier product visual specification; it changes only the implementation technology stack.

## Source of truth

During the migration there is exactly one visual and behavioral baseline: the Solid/Vite Product Site on current `main` that has passed Browser QA. Godot has no authority to redesign the product.

Baseline evidence:

- desktop: 1440×900 Home Browser Proof;
- mobile: 390×844 Home Browser Proof;
- Product Site source and quality contracts;
- Story Loom Kawaii Atelier v5 spec;
- current bilingual copy, routes, Docs hard-navigation, Hosted Studio external handoff, and accessibility behavior.

## Hard rules

1. **Implementation migration, not redesign.** Preserve the same information architecture, section order, copy, hierarchy, density, and approximately pixel-equivalent geometry.
2. **Production stays Solid until parity passes.** Build and capture Godot first as a shadow runtime; do not replace the production shell merely because Godot can run.
3. **Typography is deterministic.** The Web export must not depend on Godot default fonts or host system fonts. The migration uses content-pinned open-source CJK fonts and explicit `FontVariation` weights.
4. **No 3D.** Permitted 2.5D comes only from 2D layers, shadows, slight rotation, parallax, or other depth cues; `Node3D`, `Camera3D`, and mesh scenes are prohibited.
5. **No ambient perpetual motion.** Preserve the Product Experience v5 reduced-motion and idle-motion constraints.
6. **Mobile is a first-class composition.** 390×844 must be accepted independently and cannot be a scaled desktop canvas.
7. **Browser semantics remain explicit.** Product internal routes use browser history; `/docs/**` uses hard navigation; Hosted Studio remains an external handoff.
8. **No authority expansion.** The Product Site, shadow runtime, and generated visual evidence all remain `authority=false`.

## Cutover gate

Godot may become the production root only when all of the following are true:

- Godot source, smoke, and Web export checks are green;
- desktop and mobile Home screenshots have passed human visual review;
- there are no CJK missing glyphs or tofu;
- typography hierarchy, headline wrapping, header, CTAs, workspace card, and above-the-fold vertical rhythm align with the baseline;
- route-specific Browser QA passes for the major Product routes;
- keyboard focus, locale, reduced motion, and the Docs boundary pass;
- the hosting asset policy is resolved without reducing visual quality as a workaround;
- immediately before cutover, same-size Solid baseline and Godot candidate evidence is regenerated.

Until this gate passes, the Godot workflow may only produce shadow artifacts and must not deploy to `novelforge.wei-dev.com`.
