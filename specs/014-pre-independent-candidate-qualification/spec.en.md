# Spec 014 · Pre-Independent Candidate Qualification

## Problem

NovelForge already has a Blind Reader, Semantic Rule Auditor, Editor repair routing, continuity checks, and independent `quality.production_review`, but it lacks a mandatory fingerprint-bound manager qualification receipt before independent dispatch. A half-clean candidate can therefore reach the expensive independent reviewer before the manager has exhausted obvious Surface, regression, semantic-ownership, Reader-Grip, or realization defects.

The consuming Project also documents a stale order that places independent review before rewrite, Reader Engagement, and continuity. Generic execution authority belongs to the pinned Framework, not to the stale consumer adapter sequence.

## Target graph

```text
Raw Draft
→ Surface Realization
→ freeze diagnostic candidate fingerprint
→ manager/internal semantic quality loop
   → Surface + project regression + semantic ownership/natural-realization audit
   → Blind Reader / Reader Engagement
   → Editor repair diagnosis
   → continuity/state check
→ repair owning mechanism when blocked
→ new candidate fingerprint after material repair
→ repeat bounded loop
→ pre-independent qualification receipt
→ independent production review dispatch
→ independent PASS → user-visible Review Draft
→ independent FAIL → owning repair layer → new fingerprint → qualify again → fresh independent review
```

Manager/internal audit is explicitly `independent=false`: it may block, diagnose, and qualify; it never satisfies mandatory independence.

## Diagnostic vs qualified candidate

No new Canon lifecycle authority class is introduced. Runtime distinguishes:

- **diagnostic candidate**: exact fingerprint frozen after Surface Realization; post-generation regression/rule evidence may now be loaded;
- **qualified release candidate**: that exact fingerprint has passed required manager self-audit, Reader Engagement, and continuity with no unresolved blocking finding.

Any material prose change creates a new candidate fingerprint and makes old qualification/review results stale.

## Semantic vs deterministic responsibility

Models judge narrative function, Delete Test results, micro-action function, explanation-after-evidence, synthetic coolness, AI explanation tone, regression applicability, semantic ownership, Reader Grip, repair ownership/depth, and functional-but-over-authored realization.

Deterministic runtime owns subject identity, fingerprints, typed contract/result validation, qualification receipt presence/status, blocking-finding state, receipt/provenance binding, dispatch refusal, stale invalidation, role separation, replay safety, and no-live-model normal CI.

There is no deterministic ban on words such as “look”, “smile”, “not”, fragments, punchlines, complete sentences, or witty dialogue. Optional lexical tooling may highlight candidate spans only; it cannot make a literary verdict.

## `quality.candidate_self_audit`

Add a non-independent semantic contract that binds `candidate_fingerprint`, `candidate_text`, bounded authoritative Surface/regression material, and bounded project/profile/voice constraints where relevant. It evaluates sentence/utterance, local block, and scene/cluster scales.

Diagnostics include Delete Test, micro-action/action-tag function, explanation-after-evidence, artificial punch/synthetic coolness, AI explanation tone, procedural chronology/SAFE-BUT-FLAT interface, semantic ownership, cluster failure, and Project regression applicability.

Typed findings carry scope, severity, repair owner, evidence refs, and blocking state. Overall result is `pass | fail | insufficient_evidence`. `independent_gate=false`.

## Functional-but-over-authored realization

`FUNCTIONAL != NATURAL != CHARACTER-OWNED != PRODUCTION-READY`.

Delete Test only rules out prose with no meaningful function. For salient narrator sentences and dialogue turns the semantic audit must continue through three layers:

1. **FUNCTION** — does deletion lose action, information, relationship, pressure, humor, timing, or voice?
2. **OWNERSHIP** — does the wording/understanding actually belong to the POV, narrator profile, or speaker?
3. **NATURAL REALIZATION** — even if functional and owned, would this person at this moment plausibly use this degree of completeness, symmetry, cleverness, or quote-readiness?

Risk mechanisms include narrator clever reframing of ordinary facts, punchline-first speech, unusually polished/complete character lines, repeated witty comebacks, punchline stacking, and humor/charisma optimization that dominates the current social purpose.

Prefer the existing vocabulary (`HF-27`, `HF-29`, `HF-25`, `HF-30`, Character Integrity, `RG-08`) rather than adding a new HF code in this change. A future General Craft promotion may add a narrow mechanism only if cross-case evidence proves the existing taxonomy cannot describe it reliably.

**Character-owned humor** grows from relationship, agenda, status, misunderstanding, pressure, history, and self-interest. Removing the evaluation “funny” should still leave a social move that character would make for the current purpose. **Author-optimized wit** starts from “this beat needs charm/a joke” and reverse-engineers a quote-ready line.

A punchline-stacking cluster routes to Character Simulation + Dialogue/Scene Realization + Surface Realization, not synonym-level patching. Legitimately witty or charismatic characters remain allowed.

## Qualification receipt

Add `novelforge_candidate_qualification_v1` containing at least candidate fingerprint, subject id, repair cycle, self-audit semantic binding, Reader Engagement semantic binding, continuity state/receipt, blocking findings, qualification status, provenance, `independent=false`, and no Canon/Framework/taste write authority.

Statuses:

- `awaiting_semantic`
- `repair_required`
- `qualified_for_independent`

The qualification runtime composes exact evidence; it does not re-judge prose.

## Independent dispatch guard

Construction/dispatch of any `quality.production_review` job requires the exact current candidate plus a valid qualification receipt whose candidate/subject/fingerprint matches, status is `qualified_for_independent`, blocking findings are empty, and `independent=false`.

Missing, stale, failed, or pending qualification is a hard refusal. Qualification metadata is runtime-only dispatch proof and must not contaminate the independent reviewer semantic payload.

## Final release defense-in-depth

Final readiness/release still verifies the exact independent result plus the exact qualification receipt. Independent PASS cannot override unresolved self-audit failure, and a material candidate change invalidates both qualification and review.

## Regression isolation

First-pass Writer cannot see rejected bad-example text or hidden expected labels. After the diagnostic candidate is frozen, Auditor/Editor may read directly relevant regression evidence. Fresh realization receives mechanism/scene/character/reader constraints and writer-safe repair projection, not rejected exact prose. Rejected output is never a positive exemplar.

## Cost boundary

Default architecture remains `single manager + bounded semantic quality loop + mandatory independent reviewer`. Self-audit does not require an independent invocation. Only the mandatory release reviewer does.

## Observability

Expose high-level states such as:

`raw_generated | surface_realized | self_audit_failed | repairing | qualified_for_independent | awaiting_independent | independent_failed | review_ready`

A user may see blocking families (Surface cluster / Reader Grip / continuity) without chain-of-thought, hidden regression gold, or private worker chatter.

## Compatibility

This change does not alter Canon/Settlement authority, does not modify or repin the consumer Project, and never stores Project characters, chapter text, or private user material in Generic Framework fixtures. `quality.production_review` keeps the same reviewer-visible bounded packet; qualification is runtime-only dispatch proof.

Old runtimes that do not produce a qualification receipt fail closed after upgrade and must migrate their production-review job construction. Consumers pinned to an older Framework remain unchanged until an explicit repin.

## Current research: adopt / adapt / reject

**Adopt**: OpenAI Agents SDK blocking guardrail/tripwire principle before consequential/expensive execution; Anthropic evaluator-optimizer for writing-like iterative improvement; Anthropic 2026 guidance on deterministic graders where possible, model graders for nuance, balanced positive/negative controls, isolated trials, Unknown/insufficient-evidence escape hatches, and separate capability/regression suites; Google Agents CLI/ADK staged generate→grade→compare eval-fix loop.

**Adapt**: the evaluator does not have to be an independent agent. Manager self-audit stays `independent=false`; only release review is separate. The guardrail validates semantic receipts rather than using lexical literary rules. Self-audit may see post-generation regression/rule material while independent review stays blind to manager audit findings.

**Reject**: paid independent critique on every sentence, lexical hard bans, reviewer voting/shopping until PASS, same-session self-review treated as independent evidence, or promotion of one Project failure directly into a universal HF rule.

## Acceptance criterion

A candidate with known Surface / Project-regression / AI-explanation / Reader-Grip / functional-but-over-authored defects cannot be packaged or dispatched to mandatory `quality.production_review` until the manager repairs it and the exact new fingerprint receives a valid qualification receipt. Clean or legitimately witty prose is not rejected by deterministic keyword logic.

## Repair objective preservation addendum

A repaired candidate is not qualified merely because a targeted Surface/AI-realization failure disappears. Material repair uses a compact, fingerprint-bound `objective_envelope` selected semantically from current authorized request/plan/profile/state evidence. Rejected prose is not an objective source.

`quality.compare` is the single repair-outcome comparator. It distinguishes `target_not_fixed`, `objective_regression`, `successful_repair`, and `inconclusive` using separate target, objective-preservation, reader-value, and character/relationship-energy axes. Runtime validates binding and internal consistency; it does not score literature. Only a semantically successful repair can normally advance as challenger.

`editor.repair_spec` emits **FIX + PRESERVE**. Fresh realization receives reconstructed current state + objective envelope + distilled repair plan and hides rejected prose, full critique trajectory, raw complaint chain and regression bad examples. Context reconstruction is selected semantically when warranted; there is no fixed repair-cycle reset threshold.

For `repair_cycle > 0`, pre-independent qualification requires exact passing repair-preservation evidence in addition to self-audit, Reader and continuity. `repair_induced_objective_regression` is QA observability, not Canon or a deterministic literary verdict.

Research basis and inference boundaries: [research-objective-preservation.en.md](research-objective-preservation.en.md).
