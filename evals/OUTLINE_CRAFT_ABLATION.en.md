# Outline craft ablation · Six held-out pairs

This is an isolated realization experiment, not a production release. The [six original tasks](fixtures/outline_craft_ablation.json) differ from the library's miniature examples. Each contains private coverage hypotheses, three planning levels, fixed facts, an explicit viewpoint and a reader declaration. There is no expected winner or validated gold label.

> At the author's explicit request, the active craft-improvement chain now uses [one fresh chapter per iteration](CRAFT_CHAPTER_REVIEW.en.md) for absolute review. This document and its code preserve the verifiability of existing pairwise artifacts; they are no longer the current author-review path, and unreviewed batches cannot be used to fill in a conclusion.

## Controlled difference

Each case has one registered scene-contract/context-composition result shared by both arms. Each arm then runs one direct Surface Writer with the same Scene Realization Contract, selected ordinary context, current author objectives, Director Note, reader declaration, model settings and output budget. Only the guided arm receives the frozen foundation and AI-selected positive cards nested in its Writer pack; neither arm has a prose seed.

This does not measure whether a catalog changes planning, prove correct selection, validate independent-review reliability or evaluate the entire production pipeline. Review method applicability separately, after blind reading. Individual calls remain stochastic; provider-managed sampling defaults are unpinned.

## Preparation and execution

Run `python -m evals.outline_craft_ablation prepare` with explicit `--output`, `--run-id`, private `--order-seed`, `--service-id`, `--model-id` and `--reasoning-effort`. Keep output in ignored local runtime storage. Preparation freezes six registered jobs, positive resources, source-file fingerprints, instructions and settings. It calls no model, creates no project or budget authorization, and never overwrites an existing artifact.

Before live work, verify host capability, packet-only isolation and the existing cumulative ledger. The full experiment needs 18 calls: six context-composition selections and twelve direct Surface Writer candidates. Failed attempts count. There is no automatic retry, ledger reset or self-authorized extension.

An authorized operator sends each `selector_job` through the existing `RegisteredSemanticExecutor.execute_prepared` path and retains the exact binding. `writer_job` builds the tool-free writing jobs; use fresh packet-only sessions, archive actual host outputs and call `record_generation` with each matching result and host receipt. The host must really configure and attest reasoning effort: AgentJob alone does not set this service-level property.

The [helper](outline_craft_ablation.py) is not another model host or background dispatcher. Records bind requests, results and declared host settings. Host attestation is not independent proof of isolation. Synthetic fixtures are explicitly marked and cannot be exported as live blind evidence.

## Human reading

After all 12 generation records are complete, `blind_batches` exports three batches of two pairs. Its whitelist contains only an opaque pair ID, the explicit reader declaration and A/B prose. Model identity, scene contracts, context selections, methods, reasons, hypotheses and arm mapping stay out. Orientation is balanced and salted separately from case order.

Show one batch at a time. Allow A, B, a tie, both bad or insufficient evidence, with passage-based reasons. `human_observation` binds the response to exactly what was shown and records prior exposure. Never fill choices for the author, infer measured retention, or turn six local preferences into universal quality scores. These observations activate neither taste nor General Craft.

The prose is an evaluation specimen, not a Core-released production candidate. Author acceptance, Canon and settlement gates are unchanged. Real execution and human reading remain pending when capability, budget or a response is missing.
