# Production Pipeline

A Quillframe DRAFT or REVISE run is an adaptive production graph. The graph has hard boundaries, but it does not force every chapter through the same number of model calls.

<img src="assets/architecture/production-graph.en.svg" alt="Production graph from sparse context and simulation through internal candidate, qualification, repair loops, independent review, and the user-visible gate" width="100%" />

## 1. Freeze authority and sparse context

Resolve the exact framework/project authority for the run, establish session/run identity, select only task-relevant context, and verify stage/fingerprint boundaries. Future Plan outcomes cannot leak into current state. Regression bad examples and hidden expected labels stay out of first-pass generation.

## 2. Simulate before prose

Story/Canon preflight, scene simulation, private character state, character action proposals, scene action resolution, and Reader Pressure establish causes, agendas, knowledge boundaries, pressure, reward, and forward pull before surface realization.

## 3. Generate an internal candidate

Event-first Raw Draft material is private. Surface realization turns the simulated event structure into prose. The candidate is then frozen and fingerprinted. Raw Draft is never the user-visible artifact.

## 4. Qualify before spending independent review

`quality/candidate_qualification.py` expects registered non-independent semantic evidence for candidate self-audit and reader engagement, plus continuity evidence. A repair-cycle candidate also needs a `quality.compare` preservation check against its objective envelope.

The result is one of `awaiting_semantic`, `repair_required`, or `qualified_for_independent`. Qualification is not independent review and cannot replace it.

## 5. Repair the owning mechanism

Local surface defects can receive local rewrite. A surface cluster can require scene realization again. SAFE-BUT-FLAT returns to Reader Pressure and Scene Simulation. Character failure returns to Character Simulation. Story/plan failure returns upstream. Context failure returns to Context/Memory.

Every repair cycle follows FIX + PRESERVE. A successful local repair that damages the objective envelope, reader value, or relationship energy is not a successful overall repair.

<img src="assets/concepts/objective-preserving-repair.en.svg" alt="Objective-preserving repair: target defect improves while the objective envelope stays intact" width="100%" />

## 6. Evolve candidates without contaminating fresh regeneration

Quality Evolution compares an incumbent with a challenger through registered semantic comparison. Candidate Lineage records whether the challenger is a repair, fresh regeneration, or user edit. A repair derives prose from its comparison parent; a fresh regeneration keeps a comparison parent but has no prose parent.

## 7. Run independent review on the exact candidate

When required, freeze and package the qualified candidate, checkpoint, dispatch to a genuinely separate eligible invocation/session, validate the returned typed result against the exact candidate fingerprint, consume it once, and route any valid rejection back to repair.

<img src="assets/concepts/independent-semantic-review.en.svg" alt="Separate manager and reviewer invocations connected only by a fingerprint-bound candidate artifact" width="100%" />

## 8. Cross the user-visible gate

Only a candidate whose applicable semantic, continuity, lineage, and independence gates resolve may be called a Review Draft or production-ready according to the current contract. Acceptance remains a separate user/editorial decision; settlement remains a separate authorized state mutation.
