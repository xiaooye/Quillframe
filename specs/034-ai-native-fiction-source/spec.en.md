# AI-native fiction-source architecture specification

2026-08-31 · SYSTEM-IMPROVE contract · engineering implementation does not claim literary success.

## 01 · Outcome

Quillframe shall generate fiction directly from a compact causal scene contract and an eligible, model-composed Writer context. It shall not first create a complete explanatory Raw Draft and then ask a second model to remove its AI voice.

The architecture shall preserve current author objectives through final generation and every applicable review. Deterministic Core code shall enforce identity, rights, provenance, schema, fingerprints, budgets, persistence, idempotency and release invariants only. Literary relevance, voice, character strategy, revision scope and prose quality remain model or author judgments.

## 02 · Author Voice Sheet

An Author Voice Sheet is a versioned, disabled-by-default user or Project asset. It may be compiled by a registered semantic contract only from:

- user-authored or explicitly authorized prose;
- author-edited and explicitly approved passages;
- explicit author feedback;
- lawful, provenance-bound positive evidence that does not request imitation of a living author.

Every source must bind source kind, rights class and basis, storage intent, content fingerprint, version, applicability and author confirmation. Rejected model prose is negative regression evidence and is ineligible as a positive anchor.

The sheet covers narrative distance and POV attention, syntax and paragraph rhythm, information release, dialogue and relationship differences, humor under pressure, emotion through action/judgment/cost, reader inference, language-switching and terminology, positive evidence, boundaries and uncertainty.

Core validates structure and eligibility. It does not infer a voice or score prose. A sheet cannot become active without explicit author confirmation. Absence of an active sheet produces an honest disabled/degraded receipt.

## 03 · Character Enactment

Before prose generation, the character model shall privately describe for each present character:

- current belief and misperception;
- desired gain and feared loss;
- expectations of other present characters;
- two or three viable strategies;
- each strategy’s gain, risk and reason for rejection when not selected;
- the selected choice and its constraint on others;
- relationship-specific ways of speaking, evading, testing, conceding or changing the subject.

The artifact is private planning evidence. Writer context may include the selected enacted behavior and observable constraints, but never the full deliberation or psychological explanation.

## 04 · Scene Realization Contract

The model-owned scene contract contains only:

- what the POV can currently see, know and misunderstand;
- opening choices available to each side;
- enacted character strategies;
- environmental or interpersonal counterforce;
- which option disappears, cost rises or relationship changes;
- required factual outcomes;
- protected subtext or information gaps;
- the new constraint at scene end;
- one concrete object, action or spatial resistance able to carry conflict.

It shall not prewrite themes, aphorisms, complete dialogue, fixed imagery, paragraph shapes, sensory quotas, humor quotas or mandatory beats.

## 05 · Context Composer

The scene projection call shall also select the minimum sufficient Writer context from a Core-prevalidated inventory. Eligible categories are:

- the active Author Voice Sheet;
- two to four function-matched, rights-eligible positive anchors;
- the current Scene Realization Contract;
- situation voice cards for present characters;
- current relevant world facts and state;
- the latest accepted or author-approved prose tail;
- one short, concrete Director Note;
- the current author objectives.

Core materializes only selected identifiers and revalidates rights, source state, version and fingerprint. It does not select relevance.

Fresh realization must exclude:

- author-rejected or otherwise ineligible prose;
- reviewer reports and repair explanations;
- private character deliberation;
- unrelated character encyclopedias or lore;
- future facts outside current POV knowledge;
- duplicate full objects or repeated rule documents;
- script-generated style diagnostics.

## 06 · Direct Surface Writer

There is one prose-generation stage. The Surface Writer receives the compact Writer pack and realizes candidate prose directly.

Its near-generation guidance shall be short, positive and scene-local: place judgments in action, pause, misunderstanding, avoidance and choice; show only what the POV notices; make dialogue contest information, relationship, time, responsibility or resources; let motive be inferred from behavior and cost; stop explaining when evidence is sufficient; end on consequence or constraint; use natural Chinese by default and brief contextual English only when character and situation require it.

The Writer never receives English counts, AI-risk scores, lexical bans or prose telemetry.

## 07 · Revision routing

A registered semantic router shall bind each current author objective to exact candidate evidence and choose:

- isolated_defect: a bounded edit with only the target prose window visible;
- scene_causality_failure: rebuild the affected scene from its causal state;
- voice_contamination: freeze valid facts and perform fresh surface realization without incumbent prose;
- mixed: partition by scene and apply the appropriate route.

Core validates the selected enum, evidence binding and allowed context projection. It never selects the literary route. Systemic voice, explanatory narration, character interchangeability or language contamination cannot default to minimum-change repair.

Repair explanation remains audit evidence and is excluded from Writer context.

## 08 · Objective-bound review

Final self-audit and independent review shall receive the current author-objective envelope. Each applicable objective returns:

- met, not_met or uncertain;
- exact candidate evidence;
- impact scope;
- local_edit, scene_realization or fresh_realization recommendation.

Natural language use, explanatory narration, character-specific choices, relationship-specific dialogue, situated humor and continuity are required default review dimensions when applicable.

Any hard objective marked not_met blocks user-visible readiness. It cannot be overridden by overall fluency, completeness, plot clarity, average score or another objective. Uncertain remains visible and cannot be silently converted to met.

Model review is evidence, not literary truth. Explicit author feedback about the current work has higher semantic priority. A/B evaluation hides model identity, swaps order, prefers different model families and marks order conflict uncertain; final success requires author blind review.

## 09 · Fiction-capable model routing

The Writer profile requires a fiction_writing capability and freezes the selected service, model version, route/profile fingerprint and request identity in the stage receipt.

No generic reasoning rank establishes fiction ability. Formal activation requires a small same-scene audition approved in advance by the author. If all arms fail, the runtime reports a model capability boundary and does not add a humanizer or more prompt layers automatically.

## 10 · Budget and completion semantics

Every model job separates:

- model_context_limit;
- max_output_tokens;
- run_cost_budget.

All known limits are checked before dispatch. A valid completed response is atomically recorded and remains valid even if elapsed time, observed token use or cost crosses a soft run budget while the request was in flight. The crossing may prevent the next dispatch; it cannot rewrite the completed result as budget_exhausted_after_response.

## 11 · Durable checkpoints and event-driven coordination

Every semantic node checkpoint binds:

- input and output fingerprints;
- prompt and semantic-contract versions;
- upstream dependency fingerprints;
- model request identity and model/version fingerprint;
- validation receipt;
- usage and billing receipt;
- immutable Framework build fingerprint.

A provider completion shall atomically confirm the result and enqueue a coordinator wake for that run. The coordinator validates the completed node and immediately dispatches ready successors. HTTP wait expiry may create durable pending only; it cannot kill an active keyed worker or authorize a duplicate request.

Coordinator restart shall reclaim durable wakes and ready nodes without redispatching confirmed or pending requests. Continuing a run under a different build fingerprint fails closed and requires an explicit checkpoint-resume operation after the new build passes regression.

## 12 · Performance objectives

- Serial elapsed time: no more than observed model time plus three minutes.
- Parallel elapsed time: no more than the model critical path plus three minutes.
- Unexplained gap between ready nodes: no more than ten seconds.
- Automatic continuation after coordinator restart: no more than thirty seconds.
- No manual polling requirement, duplicate dispatch, duplicate charge or discarded confirmed node.

Call reduction may come from direct Surface Writer generation, merged context selection, parallel independent review and checkpoint reuse. Required semantic evidence cannot be removed merely to reduce calls.

## 13 · Deterministic exclusions

No production quality decision, retry, revision-scope choice or release gate may depend on:

- English-character or English-word counts;
- banned-word or “AI phrase” lists;
- sentence/paragraph length, dialogue ratio or part-of-speech counts;
- metaphor, adjective, sensory-detail, interruption, joke or hook counts;
- AIGC detector scores;
- regular-expression or frequency-derived human-likeness scores;
- an average that overrides a failed hard author objective.

Optional telemetry may exist only outside the production decision path and must label itself non-authoritative.

DRAFT and REVISE may create structured data, evidence and model requests. They shall not generate one-off Python, PowerShell, shell or other programs for semantic quality work.

## 14 · Compatibility and rollback

Quillframe 1.0 uses a clean graph cut with no legacy Raw Draft adapter or dual dispatch path. Project open may apply only Core-owned, ordered known-prefix schema migrations atomically; it does not semantically rewrite run state. Existing historical runs remain readable as immutable evidence under their frozen build and contract versions. Resuming one under a new build requires the typed checkpoint/build-migration path, reconciled billing, an exact persisted offline-regression receipt and explicit migration authorization.

Rollback disables new run registration under this contract version and preserves all voice assets, source receipts, checkpoints, model results and review evidence. It never reactivates rejected prose as Writer context.

## 15 · Acceptance

Engineering acceptance requires deterministic tests proving context exclusion, rights/fingerprint binding, direct Writer dispatch, revision route isolation, conjunctive author objectives, budget-after-response preservation, wake/idempotency recovery, build binding and absence of runtime-generated quality scripts.

Literary acceptance remains pending until the author approves a separately authorized Chinese blind canary. Code completion, model PASS, confidence or reduced English count is not literary success.
