# Chinese fiction canary authorization packet

2026-08-31 · proposal only · not authorized and not dispatched.

## Purpose and source-free AI boundary

The canary asks one narrow question: can either supported model family realize the same Chinese scene from the new Writer Pack well enough for the author to accept it? It does not revise, accept, settle or overwrite the frozen failed candidate.

This canary tests 100% AI-generated candidate prose, not author-voice learning. Fixed input contains only abstract author objectives, project-neutral character/relationship/world facts, one shared Scene Realization Contract, and versioned general craft instructions. Each Writer generates its entire candidate from the first character to the last.

No positive Chinese prose sample is supplied or retrieved, no Author Voice Sheet is compiled, and no accepted prose tail, rejected prose, reviewer analysis, repair explanation or private Character Enactment state is used. The run must record `source_free_voice_baseline=true` and must not claim that Quillframe has learned the author's style.

## Proposed calls

| Phase | Model ID | Planned calls | Purpose |
| --- | --- | ---: | --- |
| Writer arm A | `gpt-5.6-sol` | 1 | Generate a complete candidate directly from the shared source-free Writer Pack |
| Writer arm B | `claude-opus-5` | 1 | Generate a complete candidate directly from the shared source-free Writer Pack |
| Swapped A/B evidence | `gpt-5.6-terra` | 2 | Review A→B and B→A separately |
| Swapped A/B evidence | `claude-sonnet-5` | 2 | Review A→B and B→A separately |

The baseline experiment plans six calls; this is a call graph, not a token or cost budget. Tools, web search and automatic replacement calls are disabled so the candidates do not receive different external information. An unknown result stops and is reported rather than being called again until uncertainty turns into PASS.

Before dispatch, each provider model ID, protocol and provider-visible metadata are frozen into Quillframe's model-version fingerprint. A missing service, changed ID, changed price or unverifiable fiction-audition receipt stops before the first paid Writer call and requires a new authorization packet.

## Token and cost policy

The author sets no canary token ceiling or provider-cost ceiling and does not require `run_cost_budget` to stop dispatch. Each request is constrained only by the selected model/protocol's own context window and output capability, provider account state, and Quillframe's safeguards against invalid or duplicate dispatch. Exact input, output, billing and model-version receipts are still recorded for reconciliation after the run; recording cost is not limiting cost.

## Rights and confirmation gate

This plan ingests no third-party prose and requires no user prose sample, so there is no voice-sample rights gate. The abstract scene facts and author objectives are still bound to this canary receipt and may be used only for this test. Any later Author Voice learning experiment requires a separate source, rights and author-confirmation packet; this approval cannot be reused.

## Blind decision rule

1. Both Writers receive the same fingerprint-bound Writer Pack and symmetric non-price settings; neither candidate is truncated merely to force equal token counts.
2. Export labels and model identities are hidden; A/B mapping is sealed.
3. Each Reviewer compares A→B and B→A. It reports every current objective as `met`, `not_met` or `uncertain` with exact evidence and repair scope. An order-dependent conflict becomes `uncertain`; no average score chooses a winner.
4. The author sees the two prose arms in randomized order without model identity or Reviewer verdict, and chooses A, B or neither.
5. Only an explicit author acceptance can activate the selected fiction-writing receipt. “Neither” stops prompt stacking and records a model-capability boundary.

## Authorization required

No call may start until the user explicitly asks to start this source-free AI canary. There is no separate token- or cost-ceiling confirmation gate; correcting this document is not itself a start command.
