# Outline-driven scene craft

2026-08-28 · `SYSTEM-IMPROVE` · Implementation candidate; no quality improvement or default promotion established.

The existing realization guidance remains the production baseline. This change adds a versioned, bilingual library of positive writing methods: a common foundation and six combinable packs for progression/confrontation, relationships/emotion, mystery/information, everyday/professional scenes, comedy, and worldbuilding/wonder. Each method has application choices, an original miniature example, and separately stored diagnostic counterexamples. These are options, not universal beat, sentence, viewpoint, or gratification quotas.

## Runtime contract

An optional `craft_guidance_mode=outline_driven` on execution explicitly enables the candidate; omitted mode retains `baseline` for new runs and the frozen mode for resumed runs. No author must select cards or fill new story fields. The exact library content is frozen in the execution request before model dispatch. Resume consumes that snapshot, never replacement files. Revision inherits its source snapshot unless a different mode is explicitly requested on the new run.

The existing `scene.realization_project` call selects methods using the current authorized book/ancestor/chapter plans, detailed scene material and resolved trajectory. Only eligible frozen scene-stage plans are supplied; superseded plans are excluded, and plans remain future intentions. The model receives a compact catalog and returns `craft_selection` entries with card IDs, source references and concise applicability reasons. Empty selection is valid. Deterministic code validates identities, bounds and hashes; it neither classifies genres nor chooses methods.

Only the selected positive method texts and the common foundation reach Raw Draft and Surface, bound to the same selection and snapshot. Planning evidence and selection reasons stay outside the Writer craft projection. Diagnostic examples and hidden evaluation material are not loaded by the runtime. Blind Reader and independent review receive no craft selection, method text, private planning evidence or anticipated answer.

`production-loop` advances from version 6 to 7, retaining the exact version-6 registry for immutable evidence. The native Project format stays 1.0. Existing release, acceptance, settlement and review gates are unchanged. The library ships in both source bundles and installed wheels.

## Evaluation and rollout

Six original held-out scene briefs support paired baseline/treatment generation. Both variants use the same frozen story, writer-safe trajectory, model settings and output budget; selection relevance is examined separately from prose quality. Anonymous A/B batches contain two pairs, allow ties and rejection of both, and hide treatment identity and planning explanations. Human feedback is evidence, never automatic taste activation or General Craft promotion.

Deterministic tests and preparation spend no model usage. Live execution requires verified host capability and the remaining explicitly authorized cumulative budget. Missing authority or insufficient budget leaves generation pending; it does not create sample prose or reset an old ledger. Candidate methods remain opt-in until capability/regression evidence and the existing promotion prerequisites support an authorized default change.

Rollback: disable the opt-in mode and retain the original guidance. Source baseline: `22a9b21dc93099882f87ce546c3ed8abb31abd76`. Never rewrite historical runs or review evidence.
