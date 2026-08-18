# Spec 014 — Semantic Context Runtime

Status: Implemented for Quillframe 0.9.x branch validation
Primary task mode: `SYSTEM-IMPROVE`
Frozen Quillframe main: `0d211675fd9f545b83d02ab4102563f0c67e11b9`
Frozen Shujuku main studied: `12fec85bae325cacd8370b4dd0f4aff0dfd6da0e`

## 1. Problem

Quillframe already separates persistent Project State from sparse injected context and already makes semantic relevance a model-owned decision. The missing layer is a durable, inspectable runtime between those concepts. A model can choose context today, but the Framework does not yet expose one typed end-to-end contract for lifecycle eligibility, derived semantic indexing, stage-specific greenlights, hard-budget packing, freeze reproducibility, and SQLite-backed inspection.

This feature turns the Context path into:

```text
AUTHORITATIVE PROJECT STATE
→ deterministic eligibility / lifecycle / visibility gate
→ fingerprint-bound Semantic Context Profiles
→ mechanically eligible candidate universe
→ Agent semantic context decision
→ exact-id/fingerprint validation
→ stage-specific Context Greenlights
→ hard-budget packing
→ Context Freeze
→ frozen stage payloads
→ production runtime
→ receipts / Inspector projections
```

The dependency direction remains `Project → Quillframe`. Semantic metadata is derived and never becomes a second truth model.

## 2. Non-negotiable invariants

1. `stored ≠ injected`; `relevant ≠ authoritative`.
2. `Plan ≠ Canon`; `Review ≠ Accepted`; `Accepted ≠ Settled`.
3. `Corpus ≠ Canon`; `Research ≠ Character Knowledge`; `Memory/Telemetry/AI inference ≠ Canon`.
4. Eligibility is evaluated before semantic relevance. A relevance decision never repairs an ineligible lifecycle or visibility state.
5. Model-returned identifiers are mechanically validated against a frozen candidate universe. Unknown, stale, wrong-stage, or out-of-universe ids are invalid, not guessed.
6. Semantic Context Profiles carry no authority and are fingerprint-bound to one exact source-object version.
7. Runtime hard budgets never create a minimum-quota obligation. Irrelevant objects are not selected merely to fill tokens.
8. A Context Freeze is immutable input to later stages. A stage cannot perform an untracked Project DB lookup to expand its own context.
9. Refresh/extension is explicit and creates a new context fingerprint/checkpoint.
10. Context selector ≠ independent literary reviewer. Existing independent semantic integrity remains unchanged.
11. The contract is host-neutral: local Tauri/Python/SQLite and hosted Core adapters implement the same typed boundary. No Cloudflare assumption enters the Context schema.
12. Inspector explanations are bounded provenance/reason codes, never private chain-of-thought.

## 3. Semantic Context Profile

`quillframe_semantic_context_profile_v1` is derived semantic metadata, not a source object.

Required semantics:

- `profile_id`
- `source_object_id`
- `source_object_type`
- `source_fingerprint`
- `description`
- `trigger_when`
- `estimated_tokens`
- `semantic_tags`
- `stage_affinities`
- `generated_at`
- `generator_provenance`
- `status`
- `stale_reason`
- `profile_fingerprint`
- optional manual override projection
- `authority=false`

Supported generic source families include Character, Relationship, World Fact, Location, Timeline Event, Story Node, Plan, Research, Accepted manuscript context, previous scene/chapter, Canon claim, Corpus evidence, Review artifact, Character Knowledge, Candidate, runtime state, and derived memory.

Profile identity is source-version-specific. If `source_fingerprint` changes, the existing profile becomes `stale`; a new profile version receives a new `profile_id`. The Framework may regenerate semantic metadata automatically through `context.profile_derive`, but regeneration never promotes authority. Manual overrides are stored separately and reapplied to regenerated metadata unless explicitly changed.

## 4. Semantic indexing / automatic regeneration

The semantic worker contract `context.profile_derive` receives an exact source id, source type, source fingerprint, a bounded model view, and optional stage hints. It returns only semantic metadata. It cannot return authority, Canon state, acceptance, settlement, or source mutation.

A runtime indexing pass may queue derivation when:

- no current profile exists;
- the source fingerprint changed;
- a caller explicitly requests regeneration;
- a generator version requires re-indexing.

The automatic part is indexing work creation and derived metadata persistence. It is not automatic Canon mutation, Learning promotion, or Project-profile write.

## 5. Eligibility gate

Eligibility is deterministic and stage-specific. It evaluates source existence, lifecycle, authority class, visibility, invalidation, allowed stage, source/profile fingerprint consistency, protected/private classes, and domain boundaries before the model sees a candidate.

Examples:

- a rejected Candidate is lifecycle-excluded even if semantically perfect;
- Research can be eligible as research evidence while remaining ineligible as Character Knowledge;
- a source can be eligible for Continuity and ineligible for Draft;
- hidden regression material remains unavailable to writer stages;
- an `accepted_manuscript` projection without accepted/locked authority is invalid;
- a stale semantic profile is not eligible until regenerated or explicitly refreshed.

Stage affinity in a Semantic Context Profile is a relevance hint, not an authority/eligibility override.

## 6. Agent Context Decision

`context.stage_select` receives only the mechanically eligible candidate universe for one stage. The model returns:

- `profile_id`
- exact `stage_id`
- bounded priority
- short `reason_code`
- short provenance-safe explanation
- optional `required_for_grounding`

The runtime validates every selected id against the candidate universe and exact source/profile fingerprints. Any invalid selection makes the semantic result `semantic_invalid`; the Framework does not silently repair it by choosing a nearby id.

Selection reasons are short public explanations. Fields such as hidden analysis, scratchpad, or chain-of-thought are rejected by the runtime result contract.

## 7. Stage Context Greenlights and budget packing

`quillframe_context_stage_greenlight_v1` records, per stage:

- candidate count;
- semantically selected object/profile ids;
- actually loaded object/profile ids after packing;
- short selection reasons;
- estimated and optional actual token costs;
- hard budget;
- budget drops;
- authority classes (descriptive only);
- source fingerprints;
- selector identity/provenance;
- candidate-universe fingerprint;
- selection fingerprint;
- `grounding_incomplete_due_budget` when a required grounding item cannot fit.

Packing is deterministic. Selection priority and requirement semantics outrank quota filling. `hard_budget=0` means zero positive-cost context, not “fill until useful.”

## 8. Context Freeze

`quillframe_context_freeze_v1` binds:

- run id and task mode;
- candidate-universe fingerprints by stage;
- stage selection fingerprints;
- all participating source fingerprints;
- all participating profile fingerprints;
- frozen profile projections required to build stage payloads.

The `freeze_fingerprint` is computed from those bindings, not from wall-clock `created_at`, so identical inputs produce an identical fingerprint.

After freeze, `stage_context(freeze, stage)` has no persistence dependency and returns only the frozen loaded profiles for that stage. If Project state changes, `validate_freeze` returns `stale_conflict` and requires a fresh context fingerprint. Explicit extension/refresh supersedes the old freeze instead of mutating it in place.

## 9. Character context vs persona

Fictional Character Context remains a Project-domain projection of independent actors. A character projection may include identity, agenda/current desire, knowledge boundary, current task, location, relationship state, emotional carryover, stakes, misbeliefs, scene presence, known facts, and unknown facts.

Author persona, user taste, narrative preferences, or provider personality are different domains and cannot substitute for fictional character state. Semantic profiles summarize retrieval relevance only; they do not collapse the Character System into a single chat persona.

## 10. Adaptive routing

Quillframe keeps mandatory production graph constraints separate from adaptive mechanisms. An Agent may select or reorder only within the Framework-defined decision space. It cannot disable mandatory mechanisms such as Context Freeze, Story/Canon Preflight, Character Simulation, Reader Pressure, Continuity, independent semantic gate, or the user-visible gate.

`validate_adaptive_graph` mechanically rejects plans that omit or disable mandatory mechanisms.

## 11. Typed Context Query

Quillframe does not import Shujuku/SillyTavern-style prompt SQL templates. `quillframe_context_query_v1` describes:

- `domain`
- typed `filters`
- `projection`
- `limit`
- optional `authority_requirement`

It contains no SQL, table names, DB paths, or physical storage assumptions. A native SQLite adapter or hosted persistence adapter may implement the same query contract behind Core.

## 12. Persistence

Migration `002_semantic_context_runtime.sql` adds only derived/runtime tables:

- `semantic_context_profiles`
- `context_profile_overrides`
- `context_stage_selections`
- `context_freezes`

Existing `context_manifests` remains a compatibility/runtime summary projection. No new table grants authority. All new tables carry `authority=0`; stage selection and freeze rows bind to `runs` through foreign keys. Existing ordered/checksummed migration, WAL, backup/restore, integrity, FK and doctor mechanisms continue to own durability.

## 13. Inspector public projection

`quillframe_context_inspector_projection_v4` supports the Studio/Core boundary with states:

- Eligible / Considered / Selected / Loaded
- Dropped due budget
- Visibility excluded
- Lifecycle excluded
- Stale
- Invalid

Each item may expose source object id/type/domain, authority/lifecycle labels, stage, bounded reason code/explanation, estimated/actual token cost, source/profile fingerprints, selector provenance, and receipt fingerprint. It explicitly exposes no private chain-of-thought.

The Studio Host Bridge gains one read-only operation for this projection. No Studio visual design is changed.

## 14. Shujuku Agent Worldbook vs Quillframe Context Runtime

| Dimension | Shujuku current-main pattern studied | Quillframe decision |
|---|---|---|
| Worldbook Skill meta | `description`, `triggerWhen`, `tk`, update provenance | Adopt the semantic indexing idea; store typed derived profiles in SQLite rather than source comments |
| Skillify | AI derives retrieval metadata from worldbook entries | Adopt as `context.profile_derive`; no source mutation or authority promotion |
| Greenlights | plot-task and final-generation worldbook refs | Adopt as generic per-stage Context Greenlights across production mechanisms |
| Worldbook snapshot/takeover | snapshot records candidates and manipulates enabled/constant entries during takeover | Adopt freeze/snapshot intent; reject mutation of source entries as runtime isolation mechanism |
| Strict runtime reads | scoped lorebook reads and failure classification | Adopt strict Core-owned reads before freeze; reject arbitrary post-freeze DB discovery |
| Candidate-id validation | model refs are normalized against allowed keys | Adopt and strengthen with profile/source fingerprint validation and fail-closed invalid result |
| Token budget | deterministic max-token packing | Adopt; explicitly reject minimum-token quota filling |
| Sharded/concurrent semantic decision | candidate shards permit concurrent decision calls | Adopt as an optional execution optimization only; merged results must validate against one frozen universe |
| Task plan | Agent can choose run/effective stage/order for selectable tasks | Adopt only inside allowed adaptive mechanisms; mandatory Quillframe graph constraints cannot be skipped |
| Persona/current character | chat-centric persona/current-character concepts may drive prompting | Reject as fiction-state architecture; Quillframe preserves multi-character simulation and knowledge boundaries |
| Prompt SQL/query templates | prompt-level DB/SQL expansion is possible in the broader host pattern | Reject; use typed Context/Projection Query through Core |
| Fallback | Shujuku contains fallback summaries and task-plan fallbacks | Use explicit typed failure states (`semantic_invalid`, stale, incomplete); do not silently convert ineligible data into context |
| Authority | worldbook relevance is principally retrieval/runtime state | Quillframe preserves explicit Canon/lifecycle authority classes ahead of relevance |
| Candidate/acceptance/settlement | not Quillframe's staged Canon pipeline | Preserve Quillframe Candidate → explicit Acceptance → Settlement separation |
| Semantic review | context decision is an Agent concern | Preserve separate genuinely independent literary review; context selector never counts as reviewer independence |

### Ideas adopted

Semantic metadata, auto derivation/regeneration, allowed-candidate validation, stage greenlights, snapshot/freeze semantics, strict runtime reads, deterministic token packing, optional sharded decisions, and bounded adaptive task routing.

### Ideas rejected

Worldbook/comment-block metadata as canonical storage, source-entry takeover as Context isolation, prompt SQL, minimum-token quotas, single-persona substitution for fictional characters, model-created authority, and Agent-created mandatory production graphs.

## 15. Backward compatibility

- `context.select` remains registered and unchanged for callers using the existing generic memory-block selector.
- Existing `context_manifests` stays readable; new freezes write a compatible summary row.
- Existing Agent Runtime and Model Runtime contracts are not replaced.
- No consumer Project migration or Framework repin is part of this task.
- Existing Canon/Acceptance/Settlement tables and precedence are unchanged.
- Studio receives an additive read-only projection operation; no UI route or layout is changed.

## 16. Acceptance

The implementation is acceptable only if deterministic and integration tests prove:

A. semantic profiles can be derived and persisted as non-authoritative metadata;
B. eligibility precedes semantic relevance;
C. model selection cannot create authority or escape the candidate universe;
D. stages can receive different greenlights;
E. freezes are reproducible and fingerprint-bound;
F. budget, visibility, lifecycle, stale and invalid states remain distinguishable;
G. public receipts contain no hidden reasoning;
H. no Project-specific story data enters Generic Framework;
I. local SQLite runtime remains Cloudflare-independent;
J. no consumer repo repin occurs.
