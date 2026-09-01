# Outline-driven craft · Candidate library

This library helps a Writer choose how to realize an already authorized scene. It is a candidate set of methods, not a genre classifier, a plot generator, a quality gate or a new Canon source. The existing production guidance remains the default.

The current registry is version 4. Version 3 stopped treating greater restraint and polish as the main objective after the author rejected the earlier prose as literary, over-composed and short on lived character pressure. Version 4 preserves those causal craft hypotheses but removes the active Raw Draft-to-Surface instruction: one direct Surface Writer now realizes the selected scene contract. These mechanisms remain candidates for chapter-by-chapter author review, not a claim of literary improvement.

## Foundation and composable methods

Every enabled run includes [serial immediacy, lived character voice and forward motion](cards/core.en.md). In the existing scene projection call, the model may choose a small combination of:

- [Progression and confrontation](cards/confrontation.en.md).
- [Relationship and emotional movement](cards/relationship.en.md).
- [Information, uncertainty and revelation](cards/mystery.en.md).
- [Everyday life and professional pleasure](cards/everyday.en.md).
- [Comedy and lightness](cards/comedy.en.md).
- [Worldbuilding and wonder](cards/wonder.en.md).

A quiet professional scene can also carry relationship movement or wonder. Methods follow the scene's actual function in the available overall outline, chapter outline and scene details; book-category keywords do not select cards. Selecting no additional method is valid. None of the illustrative passages is a mandatory shape, a quota or a validated gold example.

## Execution and rollback

Pass `craft_guidance_mode="outline_driven"` to `ProductionRunExecutor.execute`, or the same field to `author.run.execute`, to opt in. Omission on a new DRAFT keeps `baseline`. REVISE inherits the source's exact snapshot when the mode is omitted or unchanged; explicitly choosing a different mode on a new run freezes that mode. This does not authorize changing the repair's story objective.

When an explicitly authorized run needs registered Craft V4 and a source-free Corpus candidate to cooperate, use `outline_plus_style_contract` with that run's candidate pack. The composite snapshot always retains the V4 `core`; the same registered scene projection may then select applicable registered methods and Corpus mechanisms, with no more than four Corpus cards reaching Writer. The candidate pack is frozen only into that immutable request and does not change the default mode, registry, Framework promotion, or publication state.

The runtime freezes the registry identity and full positive card texts into the immutable execution request before dispatch. The existing `scene.realization_project` call receives only catalog descriptions and current, already selected planning evidence. Its `craft_selection` cites exact source references. Python validates identities, hashes and permissions; it does not decide applicability.

The direct Surface Writer receives the foundation and selected texts with the Scene Realization Contract. Selection reasons, planning-source citations, unselected cards, diagnostics and hidden evaluation labels are excluded from that projection. Blind Reader and independent review receive no craft projection, selection or private planning material. No complete intermediary prose is generated for later cleanup; ordinary release gates still apply.

Resume uses the frozen snapshot, even after resource files change. A mode change on the same execution is rejected. The version-1 and version-2 registries and foundations remain byte-exact under `history/v1/` and `history/v2/` for evidence checks only. Old runs continue to use their own frozen snapshots, and history is never current dispatch authority. Executions predating snapshots require a fresh run. To roll back, use `baseline` on a new run. Candidate methods cannot enable themselves.

The source tree, Python wheel and full framework bundle all carry this single resource directory. There is no second hand-maintained copy.

## Evidence and boundaries

The [one-chapter author-review protocol](../../evals/CRAFT_CHAPTER_REVIEW.en.md) is the current review path. Each iteration exposes one complete fresh chapter generated through the full production runtime, including Character Simulation and Reader Pressure. No next chapter is prepared before the author's feedback is bound, and a returned or rejected edition cannot retry under a new premise without a changed craft snapshot.

The [six-pair ablation protocol](../../evals/OUTLINE_CRAFT_ABLATION.en.md) remains available to verify existing artifacts or run a separately authorized engineering experiment. It is no longer the current author-review path and never dispatches a model automatically.

The [source register](sources.json) pins nine primary repositories, commits, licenses, adapted ideas and deliberately rejected prescriptions. A noncommercial source is analysis-only; none of its wording or code is copied. No external code, installed skill or copied source prose is included. Examples are original, generic microfiction, not a consumer project or a named-author imitation.

[Post-generation diagnostics](diagnostics.en.md) explain failure mechanisms and legitimate exceptions. They are for analysis after prose exists; the resource loader never reads them for a Writer or selects them as examples.

The [version-1 implementation specification](../../specs/028-outline-driven-craft/spec.en.md), [version-2 restraint specification](../../specs/029-prose-restraint-candidate/spec.en.md), [version-3 serial-immediacy specification](../../specs/030-web-serial-immediacy-candidate/spec.en.md) and their verification records separate engineering checks from literary evidence. Passing deterministic tests, a model's confidence or one chapter preference does not establish broad improvement. No automatic promotion follows from any local evaluation.
