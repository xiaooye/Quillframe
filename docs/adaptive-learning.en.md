<div align="center">
  <img src="../assets/brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="540" />
  <p><strong>Adaptive Learning · models interpret feedback; deterministic state controls durable authority</strong></p>
  <p><kbd>OBSERVE</kbd>&nbsp;&nbsp;<kbd>INTERPRET</kbd>&nbsp;&nbsp;<kbd>EVIDENCE</kbd>&nbsp;&nbsp;<kbd>HYPOTHESIS</kbd>&nbsp;&nbsp;<kbd>EVAL</kbd>&nbsp;&nbsp;<kbd>AUTHORIZE</kbd>&nbsp;&nbsp;<kbd>ROLLBACK</kbd></p>
  <p><a href="adaptive-learning.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Adaptive Learning

NovelForge learns from explicit user/project evidence without letting a model turn an interpretation into durable authority.

```text
runtime/session state != learning evidence != Project Canon
semantic interpretation != promotion judgment != write authorization
```

`learning/author_model.py` remains a projection/capture layer over the existing Learning Store. It is not a second preference database.

## 1. Feedback intake is automatic, but only through evidence/candidate creation

Inside any primary task mode, when a user or authorized human provides evaluative semantic feedback about an existing model output, creative result or working behavior, the manager should treat it as a `feedback.observed` candidate. **Basic Learning intake does not require switching the user-visible mode to LEARN.**

The same durable feedback event can have independent logical consumers:

```text
feedback.observed
├─ author_steering:<session>        → immediate current-run steering
├─ learning_feedback:<project/user> → automatic Learning intake
└─ observability                    → read-only projection
```

Control Plane consume-once is consumer-scoped. Steering consumption does not starve Learning, and Learning retry does not create a second evidence item.

Automatic Learning means:

```text
observe
→ semantic capture | skip
→ narrowest scope + mechanism
→ source-bound evidence
→ candidate / hypothesis reconciliation
→ optional corpus/eval queue
```

It does **not** automatically mutate a Project Profile, activate durable user taste, promote General Craft, modify Framework behavior, write Canon, or SETTLE.

## 2. Not every user message is a preference

`learning.preference_interpret` first returns a semantic `capture_decision`:

`capture | skip`

This is model judgment, not a keyword/regex classifier.

Examples:

- “This dialogue is too bookish” can be learnable feedback.
- “The previous version had livelier characters; this one is more professional but less enjoyable” can be comparison evidence.
- “Continue” and “ok” should normally skip.
- An ordinary factual question or operational command must not become a preference merely because it contains a word such as “should.”

A skip may leave an auditable processed/skipped receipt, but it must not fabricate scope, mechanism or hypothesis fields.

## 3. Semantic interpretation belongs to the model

For `capture`, `learning.preference_interpret` proposes the narrowest plausible scope:

`one_off | project | user_taste | general_craft`

It may also return:

- feedback type/polarity;
- mechanism and desired/avoid behavior;
- applicability, exceptions and uncertainty;
- semantic relation to the supplied compact hypothesis index;
- `create | strengthen | contest | supersede | split`.

The model can only target supplied exact hypothesis IDs. Runtime does not merge because wording or embeddings look similar.

A user saying “all webnovels should...” does not establish General Craft. It can only become candidate evidence; General Craft promotion still requires current research, cross-work evidence, counterexamples/profile boundaries, eval/regression evidence, version/rollback, green CI and authorization.

## 4. Learning Store owns durability, not meaning

The deterministic layer owns:

- feedback event/hash plus evidence/hypothesis identity and provenance;
- stable event-derived evidence IDs;
- versioned state and contradiction/supersession records;
- exact source/target/fingerprint binding;
- persistence and rollback history;
- consumer-specific consume-once;
- Project/user scope isolation.

Retrying the same event cannot count as independent evidence. A genuinely distinct user turn may add a second evidence reference, after which the model can decide whether it strengthens an existing hypothesis.

A durable record can still be tentative or contested. Persistence does not make an inference true.

## 5. Pending/resume is a normal state

When no eligible semantic capability is available:

```text
feedback.observed
→ feedback intake = awaiting_semantic
→ event/job fingerprint remains durable
→ later resume revalidates event + authority + semantic job
→ consume exactly once
```

NovelForge must neither drop the feedback nor classify its scope with keyword heuristics.

`learning.preference_interpret` is not an independent gate. If the manager model is already executing the request, it may perform this bounded formal contract in the same invocation. Separate model/session execution is reserved for contracts that actually require independence.

## 6. Current explicit instruction and durable learning are separate

The same user turn can do two things at once:

1. bind the current task immediately as explicit instruction; and
2. become an automatically captured Learning evidence candidate.

Neither waits for the other.

```text
current explicit instruction > old active preference
current explicit instruction != automatically active durable preference
```

Thus “in this chapter, reduce the professional feel and prioritize humor, charisma and tension” applies now, while future durable Project/user behavior still requires the Learning authority path.

## 7. Promotion Gate binds semantic review to authority

`learning/promotion_gate.py` does not try to prove semantic sufficiency with arbitrary evidence-count thresholds.

Semantic promotion review decides whether supplied evidence supports the proposed scope/mechanism and whether important contradictions/counterexamples remain unresolved.

The deterministic gate verifies objective prerequisites around that review, including exact contract/result/evidence binding, candidate identity/scope, required eval/counterexample artifacts, General Craft version/rollback/CI references, and explicit write authority.

A passing promotion review is a prerequisite. It is **not** permission to write.

## 8. Active != relevant

An `active` Author Model hypothesis means it is durably eligible for future use. It does not mean every production invocation receives it.

The Author Model exposes a compact active index. The manager/model selects relevant active hypothesis IDs for the current task; deterministic code verifies active/scope compatibility before exposing details.

Stronger automatic Learning therefore does not become all-memory prompt injection.

## 9. Scope-specific authority

### One-off

Automatic intake may retain auditable evidence/candidate state for the current repair, but it does not become future active behavior by itself.

### Project preference

Automatic intake produces a Project candidate by default. Only a later Project-authorized activation/write path can activate it; it does not directly edit Project Profile files.

### Durable user taste

Requires both a current bound promotion prerequisite for the same mechanism/scope and explicit durable-user-taste write authorization. Personal learning state stays in user/runtime storage by default rather than Generic Framework source.

### General Craft

General Craft remains a Framework `SYSTEM-IMPROVE` concern. It requires stronger current research, cross-work evidence, counterexample/profile-boundary evidence, eval/regression, compatibility, version/rollback, green CI and explicit Framework promotion authority. Production feedback cannot auto-promote it.

## 10. Rejection, acceptance and Canon authority remain separate

An explicitly rejected AI artifact can provide negative evidence through its artifact ref/fingerprint, feedback event/ref, rejection mechanism and `rejected_negative_only` disposition.

Do not copy failed prose into Learning Store or use capture as a way to turn rejected text into a positive benchmark or Writer pre-draft context.

Reasoned acceptance can be learning evidence; plain “accepted” must not imply that the user permanently prefers every mechanism in the artifact.

Canon acceptance and Learning acceptance are separate authority domains. Canon acceptance may satisfy a Project Settlement prerequisite; Learning acceptance only records a response to an artifact. Neither grants the other's authority.

## 11. Contradiction and rollback are first-class

New feedback may strengthen, contest, supersede or split a hypothesis, or narrow applicability by scene/profile/time context.

For example, “use more professional detail” and “openings should not feel professional; charisma and plot matter more” need not become two blindly active universal rules. The model can scope the latter to openings while runtime preserves the exact target/version/provenance.

Strengthening means genuinely new evidence—not retrying the same event, repeated model agreement, or elapsed time.

## 12. Corpus/research remains evidence gathering

A semantic learning agent may identify evidence gaps and search for lawful contrast/counterexample material inside allowed capabilities. Search/retrieval strategy remains model-owned.

Corpus discovery does not imply ingestion; ingestion does not imply Canon; corpus analysis does not imply promotion. Rights, provenance, source identity and Project/user isolation remain deterministic boundaries.

## 13. Observability and privacy

`learning/feedback_query.py` opens an existing Learning DB read-only. Querying does not create tables, consume receipts, update timestamps, or execute a model.

It can expose observed/awaiting_semantic/skipped/persisted/blocked/failed status, event/hash and target/artifact fingerprints, semantic job/result fingerprints, evidence/hypothesis/action/contradiction refs, and versions/timestamps.

It does not expose whole conversation history, bounded feedback text, private model reasoning, hidden eval gold, or secrets.

## 14. Production use

```text
user feedback in any primary mode
→ current instruction/steering acts now
→ feedback.observed durable
→ automatic Learning intake
→ semantic capture | skip
→ source-bound evidence
→ create / strengthen / contest / supersede / split candidate
→ optional corpus/eval cycle
→ later authorized activation/promotion only when prerequisites pass
→ active eligibility
→ model selects relevant active hypotheses for future task
```

The Writer/Editor never receive a hidden global style profile simply because records exist in `learning.db`.

## Exact implementation boundaries

- `learning/learning_store.py` — durable evidence/hypothesis/candidate/promotion history.
- `learning/feedback_intake.py` — feedback event → semantic job → pending/result validation → Author Model capture → Learning consumer receipt.
- `learning/feedback_query.py` — side-effect-free feedback intake projection.
- `learning/promotion_gate.py` — deterministic binding/authority checks around model-owned promotion review.
- `learning/author_model.py` — bounded capture, exact hypothesis reconciliation, activation binding, active index and explicit selected projection.
- `harness/semantic_workers/contracts/production-loop.json` — `learning.preference_interpret` capture/skip contract.
- `evals/feedback_learning_ablation_manifest.json` / `feedback_learning_ablation.py` — independent semantic BEFORE/AFTER and control packets; no independent reviewer means `PENDING_MODEL`.
- Framework Self-Improvement Protocol — General Craft promotion authority.

<div align="center"><sub>Hear feedback automatically. Persist minimally. Change durable behavior only with evidence and authority. 🌸</sub></div>
