# Product Site Visual Rewrite v3 Plan — Superseded

**Status:** historical implementation plan; superseded by `plan.en.md`.

The original v3 plan targeted the former browser DOM/CSS/Vite Product shell. The public Product runtime is now Godot Web, so those implementation steps must not be resumed.

## Carried-forward design work

The surviving visual work is executed inside the current Godot architecture:

1. project Story Loom tokens into generated GDScript;
2. build the Product stage with `Control`/Canvas surfaces;
3. represent system relationships as connected topology and inspector surfaces;
4. use semantic route accents for Product, Studio, Architecture, Publication, Inspect, Playground, and Agents;
5. use bounded 2.5D motion and input-driven parallax without an idle frame loop;
6. provide a dedicated portrait topology for phone layouts;
7. preserve bilingual and accessibility contracts;
8. validate the actual exported WebAssembly runtime with screenshot/browser evidence.

Current execution and acceptance are defined by `plan.en.md` and `tasks.en.md`.
