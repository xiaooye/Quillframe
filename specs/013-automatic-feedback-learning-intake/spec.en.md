# Spec 013 · Automatic Feedback Learning Intake

## Problem

NovelForge 0.8 already has durable `feedback.observed` events, Author Steering, `learning.preference_interpret`, an Author Model, Learning Store, and durable learning cycles. What it lacks is mandatory wiring from ordinary production feedback into Learning. Current-run steering can succeed while the same feedback evaporates at session end unless a manager explicitly invokes Learning.

This is a wiring/lifecycle gap, not a reason to build a second memory system.

## Goal

Within exactly one user-visible primary task mode, make user/authorized-human feedback flow through:

```text
user turn
→ manager semantic judgment: feedback candidate?
→ feedback.observed
├→ author_steering:<session>        # when current-run steering applies
├→ learning_feedback:<scope owner>  # automatic learning intake
└→ read-only observability
```

Automatic means evidence intake: capture → interpret → narrow scope → evidence → hypothesis/candidate → optional validation queue. It never means automatic promotion, Project Profile mutation, durable user-taste activation, Framework mutation, Canon write, or SETTLE.

## Authority invariants

1. A feedback event is transport evidence, not preference authority.
2. A current explicit user instruction applies immediately and outranks old active preferences.
3. Persistence does not activate future behavior.
4. Existing project/user/general-craft promotion gates remain authoritative.
5. Canon acceptance and learning evidence remain separate domains.
6. Rejected model output is negative evidence only, never Canon or a positive exemplar.
7. Personal learning state is not committed to the Generic Framework by default.
8. Active remains eligibility, not automatic prompt relevance.

## Semantic / deterministic split

The model decides whether a candidate turn is learnable feedback; whether to `capture` or `skip`; the narrowest scope; mechanism, polarity and applicability; and whether evidence should create, strengthen, contest, supersede, or split a hypothesis.

Deterministic runtime owns event identity/hash, provenance, consumer-specific consume-once, semantic fingerprints and typed validation, pending/resume state, stable event-derived evidence identity, referenced hypothesis existence/scope compatibility, CAS/versioning, persistence, observability, and authority checks.

No keyword or regex heuristic may decide literary feedback meaning.

## `learning.preference_interpret` v2

Every semantic result requires only:

```yaml
capture_decision: capture | skip
skip_reason: string | null
confidence: 0..1
```

A `capture` result is additionally validated by the intake owner for scope, dimension, mechanism, statement, polarity, feedback/evidence type, desired/avoid behavior, applicability and a model-selected hypothesis action:

`create | strengthen | contest | supersede | split`.

New semantic evidence types include `reasoned_acceptance`, `comparison`, and `correction`; deterministic legacy `acceptance` remains supported for compatibility. A `skip` result never fabricates a preference record.

## Event compatibility and fan-out

Keep shared `novelforge_event_v1`. Learning intake accepts both the existing `novelforge_author_steering_request_v1` payload and a generic `novelforge_feedback_observation_v1` payload for feedback that does not need current-run steering.

Control Plane already scopes logical consumption by consumer. Learning uses a distinct `learning_feedback:<project-or-resource>` consumer. Steering and Learning therefore consume the same event independently, and each consumer remains replay-safe.

## Intake lifecycle

Add an intake projection table to the existing Learning DB:

`observed → awaiting_semantic → interpreted → skipped | persisted`, with `blocked | failed` exits.

Missing semantic capability leaves a durable `awaiting_semantic` item. Resume must revalidate exact event hash, semantic fingerprint, Project/Framework authority supplied by the manager, and consume state before applying a result.

## Idempotency and hypothesis reconciliation

Automatic intake supplies a deterministic evidence ID derived from exact feedback event identity/hash and logical learning consumer. Same-event retries cannot write duplicate evidence.

Hypothesis reconciliation is model-directed, runtime-validated. `strengthen` adds genuinely distinct evidence to one existing hypothesis; `contest` marks a target contested; `supersede` creates the narrower/new candidate and supersedes the old target; `split` creates a narrower candidate while contesting the broader target. Runtime does not use keyword similarity, embedding nearest-neighbor rules, elapsed time, or evidence counts as semantic truth.

## Activation

Automatic intake always captures with project preference activation, durable user-taste activation, Framework behavior write and Canon write authority set false. Project feedback therefore becomes a project candidate by default, not an active Project Profile rule.

No new Project manifest flag is required for this first version because candidate persistence is runtime Learning state rather than Project/Profile mutation. Host privacy/capability policy may disable or redirect persistence; future explicit Project opt-out can be additive.

## Rejection, privacy and context

For rejected artifacts, store only bounded target metadata, fingerprint, feedback reference and semantic rejection meaning plus `artifact_disposition=rejected_negative_only`. Do not copy rejected prose into the store or Writer pre-draft context.

Persist only minimum sufficient feedback, target refs/fingerprints, semantic interpretation, scope/mechanism and provenance. Generic fixtures are synthetic/anonymized. User/project content does not enter Generic Framework source.

## Observability

Provide side-effect-free recent-feedback queries exposing status, event/fingerprint binding, capture/skip decision, evidence/hypothesis refs, reconciliation action and timestamps, while excluding secrets, private reasoning, hidden eval gold and whole conversation history.

## Cost and independence

`learning.preference_interpret` remains `independent_gate=false`. The current manager model may execute the bounded interpretation while already handling the request. No extra provider call is required merely because this is Learning. If no semantic route is eligible, persist pending state.

## Compatibility

- shared event schema stays v1;
- author-steering v1 payload stays valid;
- Author Model v1 capture remains accepted, with optional new event-id/merge fields;
- legacy acceptance source stays accepted;
- Learning Store is extended additively with `CREATE TABLE IF NOT EXISTS`;
- LEARN mode remains for dedicated learning research/eval/promotion.

## Acceptance

All 17 requested deterministic controls must be covered. Paired semantic ablations must test automatic intake, non-feedback skip, authority isolation, dual consumption and contradiction. Where the registered rubric requires independent execution and none is available, the truthful result is `PENDING_MODEL`, never manager self-approval.
