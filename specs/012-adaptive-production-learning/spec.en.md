# Spec 012 · Adaptive Production Learning and Realization Boundary

Status: implementation candidate
Scope: Generic NovelForge only
Primary mode: SYSTEM-IMPROVE

## Problem

Real production evidence shows an intent–execution gap: NovelForge can have correct Framework rules and Project profiles while a run still assembles a formally legal but quality-poor context, exposes private character state too directly to prose generation, accepts a semantic review as if it were the whole release decision, and then loses useful user feedback after the revision.

This is not solved by adding more prose instructions. The production runtime needs explicit state and interfaces connecting author intent, context assembly, simulation, realization, reader/editor feedback, and future runs.

## Design influences

The candidate adapts mechanisms visible across mature writing tools and agent systems rather than copying their product surfaces:

- persistent, editable creative intent / story-bible state instead of relying on chat memory;
- task-aware sparse context assembly instead of injecting all stored knowledge;
- hierarchical or bounded planning with room for emergence;
- character/world simulation before prose realization;
- evaluator/editor revision loops rather than one-shot generation;
- pairwise incumbent/challenger comparison for subjective revisions;
- episodic feedback that informs future work without silently granting durable authority.

NovelForge keeps its stronger authority, fingerprint, session, settlement, rights, and independent-review boundaries.

## Invariants

### I1 · Author intent is first-class state

Production may consume an Author Model projection containing only explicitly authorized and applicable intent/preference state. Priority is:

`current explicit request > explicit Project intent/profile > active scoped preference > candidate/inferred hypothesis`.

A hypothesis is evidence, not behavior. Model inference alone cannot activate durable user taste or General Craft.

### I2 · Review feedback creates evidence, not automatic rules

Material user review feedback must be classifiable as `one_off | project | user_taste | general_craft` and may create a typed observation plus a proposed preference delta. Activation remains governed by scope authority.

Project-authorized preferences may affect future Project runs. User-taste hypotheses require their existing learning/activation prerequisites. General-craft observations enter SYSTEM-IMPROVE evidence only.

### I3 · Context assembly must prove required context classes are satisfied

The semantic selector decides relevance. Deterministic runtime proves only that declared required obligations are satisfied by eligible, stage-safe, non-invalidated context with suitable authority/provenance.

A required obligation with no eligible selected item blocks the assembly. Optional context may be absent.

### I4 · Private character state is not prose payload

Character agenda, fear, goal, risk, private knowledge and simulation reasoning are causal control state. They are not writer exposition obligations.

Pre-draft character/scene simulation can consume private character state. Prose generation should normally consume a writer-safe realization projection containing observable actions/events, permitted POV state, interaction tactics, shared context, withheld/compressed information, social cost, task/object carriers, turn pressure, and any justified formal-completeness reason.

### I5 · Agenda drives dialogue; agenda is not dialogue

`AGENDA-TO-DIALOGUE LEAKAGE / CHARACTER-SHEET-TO-DIALOGUE SERIALIZATION` is a Framework quality failure when private character state is realized in near-isomorphic, over-complete dialogue without sufficient transformation by immediate tactic, listener model, shared knowledge, relationship/social cost, omission, distortion, interruption, task action, or other interaction pressure.

Complete speech is valid when the speech act itself requires completeness (for example testimony, briefing, instruction, formal risk explanation, record-making, or explicit full-account requests).

### I6 · Reader → Editor is the creative repair loop

The Reader judges the actual reading experience holistically and returns multidimensional semantic evidence. The Editor converts those findings into a bounded repair specification: preserve/change priorities, owning mechanism, local/global depth, invalidation needs, and whether incumbent/challenger comparison is required.

Do not create a committee of redundant literary agents when one structured Reader plus one Editor role is sufficient.

### I7 · Revision is not improvement by default

Material repairs to scene realization, reader grip, voice, paragraph rhythm, dialogue embodiment or platform fit require evidence that the challenger is not worse than the incumbent when policy marks comparison required. Pairwise results may be A, B, or tie.

### I8 · Deterministic code does not decide literary truth

Metrics such as one-sentence-paragraph ratio, sentence-length distribution, fragment density and consecutive short-paragraph runs are telemetry. They are not universal pass/fail rules unless an explicit Project profile supplies a hard threshold.

Semantic evaluation owns profile-sensitive judgments such as pseudo-speed fragmentation, paragraph-function failure, commercial/platform fit and agenda-dialogue leakage.

### I9 · Structural release evidence remains conjunctive

A semantic reviewer PASS cannot satisfy a missing required structural receipt. If a run policy requires a current context-assembly receipt, that receipt must bind the candidate/run and be present before user-visible readiness can be true.

### I10 · Consequential writes must match typed intent

A write intent must bind resource class, operation class, exact target, authority/precondition and idempotency. A connector action for another resource/operation/target must fail closed with `BLOCK_RESOURCE_ACTION_MISMATCH`.

## Compatibility

- No Canon or downstream Project state is changed by this Framework candidate.
- Existing Author Steering, Learning Store, Context Inspector, Character Action Proposal, Scene Action Resolution, Production Readiness, Reader Engagement and Quality Evolution remain owners; this work connects and narrows interfaces instead of replacing them.
- Existing DRAFT/REVISE behavior can remain compatible when new obligations are not declared by policy. New required obligations fail closed only when explicitly required.
- No generic Project-specific genre or platform is hard-coded.

## Non-goals

- no automatic General Craft promotion;
- no automatic consumer lock migration;
- no named-author imitation profile;
- no deterministic literary scoring engine;
- no mandatory retrieval of Corpus on every Draft;
- no requirement that dialogue be short, fragmented, colloquial or incomplete;
- no replacement of planning-commitment-horizon semantics in this candidate.

## Acceptance

The feature is ready for human review only after deterministic self-tests, catalog/schema/reference checks, generic eval queue construction, exact-head CI evidence, and required independent semantic capability/counterexample evidence are available for the candidate fingerprint. Promotion/activation remains a separate authorized decision.
