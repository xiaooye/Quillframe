# Chinese fiction canary authorization packet

2026-08-31 · one source-free A/B authorized and dispatched · author decision pending.

## Purpose and source-free AI boundary

The canary asks one narrow question: does the new near-generation instruction improve one Chinese scene relative to the ordinary Writer baseline enough for the author to prefer it? It does not revise, accept, settle or overwrite the frozen failed candidate.

This canary tests 100% AI-generated candidate prose, not author-voice learning. Fixed input contains only abstract author objectives, project-neutral character/relationship/world facts, one shared Scene Realization Contract, and versioned general craft instructions. Each Writer generates its entire candidate from the first character to the last.

No positive Chinese prose sample is supplied or retrieved, no Author Voice Sheet is compiled, and no accepted prose tail, rejected prose, reviewer analysis, repair explanation or private Character Enactment state is used. The run must record `source_free_voice_baseline=true` and must not claim that Quillframe has learned the author's style.

## Authorized calls

| Phase | Model ID | Planned calls | Purpose |
| --- | --- | ---: | --- |
| Ordinary Writer baseline | `gpt-5.6-sol` | 1 | Generate a complete candidate from the shared source-free scene contract and ordinary Writer instruction |
| AI-native treatment | `gpt-5.6-sol` | 1 | Generate a complete candidate from the same scene contract and the new near-generation instruction |

This experiment authorizes exactly two prose calls. There is no model Reviewer, swapped model review, extra sample or automatic replacement call. Tools and web search are disabled so the candidates do not receive different external information. The author, not another model, makes the only literary comparison.

Before dispatch, the provider model ID, protocol and available provider-visible metadata are frozen into the execution receipt. A missing service, changed ID or unverifiable request identity stops before the first Writer call and requires a new authorization packet.

## Token and cost policy

The author sets no canary token ceiling or provider-cost ceiling and does not require `run_cost_budget` to stop dispatch. Each request is constrained only by the selected model/protocol's own context window and output capability, provider account state, and Quillframe's safeguards against invalid or duplicate dispatch. Exact input, output, billing and model-version receipts are still recorded for reconciliation after the run; recording cost is not limiting cost.

## Rights and confirmation gate

This plan ingests no third-party prose and requires no user prose sample, so there is no voice-sample rights gate. The abstract scene facts and author objectives are still bound to this canary receipt and may be used only for this test. Any later Author Voice learning experiment requires a separate source, rights and author-confirmation packet; this approval cannot be reused.

## Blind decision rule

1. Both Writers receive the same fingerprint-bound Writer Pack and symmetric non-price settings; neither candidate is truncated merely to force equal token counts.
2. Export labels and model identities are hidden; A/B mapping is sealed.
3. The author sees the two prose arms in randomized order without model or instruction identity, and chooses A, B or neither.
4. The selection is one-off instruction evidence only. It cannot promote General Craft, write Canon, qualify a model or claim literary success by itself.
5. “Neither” records that this instruction treatment did not pass the author canary; it does not trigger more calls.

## Execution record

The user explicitly authorized one sample A/B on 2026-08-31. Exactly two Writer calls completed; the first checkpoint was reused after relay validation stopped, so it was not dispatched twice. The two outputs contain 3,720 and 2,560 Chinese characters in blind order. Recorded usage totals 27,936 input tokens, 6,894 output tokens and 1,393 reasoning-output tokens. No provider monetary-price receipt was exposed.

Both Codex CLI 0.151 calls returned exit code 0, one exact final message and usage, but also emitted sanitized error-type lifecycle items that the v3 relay preserved as `forbidden_cli_item` / `invalid_cli_item`. The blind prose is available for author review; clean transport validation is not claimed. No Reviewer or further model call was made.
