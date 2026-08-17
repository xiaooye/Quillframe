# Spec 013 · Automatic Feedback Learning Intake

## 1. Problem

NovelForge 0.8 已经分别具备 `feedback.observed`、Author Steering、`learning.preference_interpret`、Author Model、Learning Store 与 durable learning cycle，但 production feedback 进入 Learning 仍依赖 manager 主动调用。结果是 current-run steering 可以生效，而同一反馈未必成为可恢复、可审计的 learning evidence。

本规格把缺口定义为 **wiring / lifecycle gap**，不是重做 memory subsystem。

## 2. Goal

在保持 exactly one primary task mode 的前提下，让 user / authorized human 对既有模型产物、工作方式或行为给出的明确 semantic feedback 自动进入 bounded Learning intake：

```text
user turn
→ manager semantic judgment: feedback candidate?
→ feedback.observed (durable)
├→ author_steering:<session>        # current-run consumer when applicable
├→ learning_feedback:<project/user> # automatic learning consumer
└→ observability                    # read-only projection
```

`automatic` 仅表示：capture → interpret → scope → evidence → hypothesis/candidate → optional further validation queue。

它不表示：automatic promotion、Project Profile write、durable user-taste activation、Framework mutation、Canon write 或 SETTLE。

## 3. Authority invariants

1. `feedback.observed` 是 observation/request transport，不是 preference authority。
2. Current explicit user instruction immediately applies to the current task and outranks previously active preferences.
3. Learning persistence does not activate durable behavior.
4. Project / user_taste / general_craft activation continues through existing authority gates.
5. Canon acceptance and learning acceptance are separate domains even if sourced from the same user turn.
6. Rejected AI artifacts are negative evidence only: never Canon, positive exemplar, or Writer pre-draft corpus.
7. Personal learning data is runtime/user storage and is not committed to Generic Framework by default.
8. Active preferences remain an eligibility index; semantic relevance is selected per future task.

## 4. Semantic vs deterministic boundary

### Model owns

- whether a candidate turn contains learnable feedback;
- `capture | skip`;
- narrowest scope: `one_off | project | user_taste | general_craft`;
- feedback type / polarity / mechanism / applicability;
- whether new evidence creates, strengthens, contests, supersedes or splits an existing hypothesis;
- semantic contradiction and contextual/temporal boundary.

### Deterministic runtime owns

- event identity/hash and provenance;
- consumer-specific consume-once receipt;
- semantic job fingerprint and typed result validation;
- pending/resume state;
- stable evidence identity for an event;
- existence/scope compatibility of referenced hypotheses;
- CAS/versioning, persistence and audit projection;
- write/activation authority.

No keyword/regex classifier may decide literary feedback meaning.

## 5. Feedback interpretation contract v2

`learning.preference_interpret` evolves additively.

Minimum result:

```yaml
capture_decision: capture | skip
skip_reason: string | null
confidence: 0..1
```

When `capture_decision=capture`, the intake layer additionally requires:

```yaml
scope_candidate: one_off | project | user_taste | general_craft
dimension: string
mechanism: string
statement: string
polarity: positive | negative | mixed
evidence_source: explicit_rule | user_edit | rejection | reasoned_acceptance | comparison | repeated_pattern | correction | human_review
hypothesis_action: create | strengthen | contest | supersede | split
target_hypothesis_id: string | null
desired_behavior: []
avoid_behavior: []
exceptions: []
applicability: {}
contradicts_hypothesis_ids: []
```

`skip` MUST NOT require a fabricated scope/mechanism/hypothesis.

Legacy `acceptance` remains accepted by the deterministic Author Model adapter for backward compatibility, while new semantic output uses `reasoned_acceptance` when acceptance carries actual learning signal.

## 6. Feedback event compatibility

The Control Plane event schema stays `novelforge_event_v1`; no breaking event migration is required.

Learning intake accepts two payload shapes:

1. existing `novelforge_author_steering_request_v1` / `kind=author_steering` — its bounded `instruction` is also eligible learning feedback;
2. generic `novelforge_feedback_observation_v1` / `kind=feedback_observation` for feedback that does not need current-run steering.

Thus old steering producers continue to work. New manager implementations may emit the generic observation when steering is irrelevant.

## 7. Consumer fan-out

Control Plane already keys consumption by `(source_type, source_id, consumer)`. The new learning consumer MUST use a distinct logical consumer, e.g. `learning_feedback:<project_id-or-resource_id>`.

A steering receipt MUST NOT consume or delete the event globally. A learning receipt MUST NOT affect steering. Replay of the same event to the same consumer is idempotent; the same logical consumer with a different event hash fails closed.

## 8. Intake lifecycle

A new additive feedback-intake projection lives in the existing Learning DB, not a second preference database.

States:

```text
observed
→ awaiting_semantic
→ interpreted
→ skipped | persisted

observed/awaiting_semantic/interpreted
→ blocked | failed
```

`awaiting_semantic` is durable. Missing semantic capability never drops the event and never triggers heuristic scope classification.

Resume revalidates event hash, semantic fingerprint, Project identity, Framework compatibility supplied by the manager, and consume-once status before applying a result.

## 9. Evidence identity and hypothesis merge

Automatic intake supplies a deterministic evidence ID derived from the exact feedback event identity/hash/learning consumer. Therefore retry cannot create a second evidence row.

Hypothesis merge is model-directed and runtime-validated:

- `create`: create a candidate hypothesis;
- `strengthen`: attach independent new evidence to an existing compatible hypothesis;
- `contest`: mark the target contested and bind contradiction evidence;
- `supersede`: create the narrower/new candidate and supersede the old target;
- `split`: create a narrower candidate and contest the broader target pending further review.

The runtime never performs embedding similarity, keyword matching, evidence-count thresholds or scalar nearest-neighbor merging as a substitute for semantic judgment.

## 10. Activation

Automatic intake always uses:

```text
project_preference_write_authorized = false
durable_user_taste_write_authorized = false
framework_behavior_write_authorized = false
canon_write = false
```

So automatic project feedback becomes a **project candidate**, not an active Project Profile rule. Existing explicit activation/promotion paths remain authoritative.

No new Project manifest flag is required for v1: candidate persistence is Learning runtime state, not Project Profile mutation. A host may disable/redirect personal persistence through capability/privacy policy. Future Project-level opt-out can be added without changing the evidence model.

## 11. Rejected artifacts

For rejection, intake stores only bounded metadata:

- artifact ref/fingerprint;
- feedback event/ref;
- semantic rejection meaning/mechanism;
- `artifact_disposition=rejected_negative_only`.

The failed prose body is not copied into Learning Store and is not injected into Writer pre-draft context.

## 12. Observability

Read-only query surface returns recent feedback intake records with:

- event id/hash/source;
- observed / awaiting_semantic / interpreted / skipped / persisted / blocked / failed;
- semantic fingerprint/result hash;
- capture decision / skip reason;
- evidence/hypothesis refs and hypothesis action;
- contradiction target refs;
- timestamps/version.

It must not expose secrets, private chain-of-thought, hidden eval gold, or whole conversation history.

## 13. Cost model

`learning.preference_interpret` remains `independent_gate=false`.

When the current manager model is already executing the user request, it may perform the bounded interpretation in the same invocation under the formal contract. A separate provider/model is not required merely because the work is called Learning.

If no eligible semantic execution exists, intake persists `awaiting_semantic` for later resume.

## 14. Privacy

Persist minimum sufficient evidence only. Generic Framework tests/evals use synthetic/anonymized fixtures. Project-specific content and user-specific preference records do not enter Generic Framework source.

## 15. Backward compatibility

- `novelforge_event_v1` remains valid.
- existing author-steering v1 payload remains valid.
- existing `author_model.capture` requests remain valid; new merge/evidence-id fields are optional.
- legacy `acceptance` source remains accepted deterministically.
- existing Learning Store tables remain; feedback intake adds a table with `CREATE TABLE IF NOT EXISTS`.
- LEARN mode remains for dedicated analysis/corpus/eval/promotion work.

## 16. Acceptance criteria

The 17 deterministic cases in the user requirement must be represented by self-tests/CI fixtures, including dual-consumer, retry, pending/resume, contradiction, privacy, and current-explicit-instruction priority.

Semantic ablation evidence must cover:

- before: steering works, automatic learning absent;
- after: same feedback becomes bounded learning candidate;
- negative control: non-feedback skips;
- authority control: no auto promotion;
- dual-consumer control;
- contradiction control.

Where the registered ablation rubric requires independent semantic execution, absence of an eligible independent reviewer remains `PENDING_MODEL`, never synthetic PASS.
