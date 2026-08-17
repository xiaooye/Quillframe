# Adaptive Learning

Quillframe learning begins automatically when meaningful feedback arrives, but nothing about automatic intake grants automatic promotion.

<img src="assets/concepts/automatic-learning-intake.en.svg" alt="Learning intake from automatic feedback capture through interpretation and scoped hypothesis to governed validation and promotion" width="100%" />

## Automatic capture

A durable `feedback.observed` event can be consumed by the Learning Intake independently of current-run author steering. `learning/feedback_intake.py` packages the feedback for `learning.preference_interpret`; the model decides `capture | skip`, the narrowest supported scope, mechanism, contradiction, and hypothesis relation.

There is no keyword or regex shortcut for deciding whether feedback is meaningful.

Retrying the same durable event does not create new evidence. A genuinely new user turn can provide independent evidence that strengthens, contests, supersedes, or splits an existing hypothesis.

## Four scopes

`one_off` serves the current request/run. `project` is limited to one fiction Project. `user_taste` is a durable cross-project preference hypothesis. `general_craft` is a candidate for generic framework behavior.

Evidence always takes the narrowest scope it actually supports.

## Governed promotion

Automatic intake defaults all protected write permissions to false. It does not automatically edit Project Profile, activate durable user taste, promote General Craft, modify framework source, or write Canon.

Durable activation requires evidence, contradiction review, relevant eval evidence, provenance, and whatever authority the target scope requires. General Craft has the highest bar: cross-work evidence, a counterexample/profile boundary, capability and regression evaluation, version/rollback, green deterministic CI, and explicit engineering authority.

## Rejected output

A rejected artifact can become negative regression evidence by reference/fingerprint and meaning. It is not a positive prose exemplar and must not leak back into pre-draft writer context.

## Research and Corpus

Learning may create a Corpus gap and search for rights-safe contrast evidence. Discovery is not ingestion; ingestion is not preference; analysis is not promotion; Corpus is not Canon.
