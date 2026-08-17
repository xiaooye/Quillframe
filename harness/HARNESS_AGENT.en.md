# Harness Agent · One manager, model-owned meaning, deterministic execution truth

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>ONE MANAGER</kbd>&nbsp;&nbsp;<kbd>ONE PRIMARY MODE</kbd>&nbsp;&nbsp;<kbd>AI-NATIVE</kbd></p>

The NovelForge Harness coordinates a validated fiction Project plus a declared task into a bounded, resumable run. It owns execution policy, not story truth.

> **Project authority owns Canon and project-specific facts. Models own semantic fiction judgment. Deterministic runtime owns identity, power, persistence and exact execution state.**

## 01 · AI-native does not mean model-authoritative

Model-owned work includes, when needed:

- search intent, query formulation, relevance, continuation and stopping;
- story/scene/planning interpretation;
- character action, motivation, plausible inference and integrity;
- Reader experience;
- semantic hard-rule applicability/violation;
- repair mechanism/depth;
- research interpretation;
- whether a turn is learnable feedback, plus feedback meaning, scope, contradiction and hypothesis reconciliation.

Deterministic code owns only what can be proved mechanically:

- Project/resource/session/run/checkpoint identity;
- permissions and capability boundaries;
- exact artifacts, hashes and fingerprints;
- provenance and exact-source binding;
- stage/private-state visibility;
- persistence, CAS, transactions and idempotency;
- hard budgets/resource limits;
- typed envelope/result/receipt validation;
- required semantic execution presence and exact candidate binding;
- settlement and release-role invariants.

A semantic result is evidence/proposal unless a separate authority mechanism explicitly grants more.

## 02 · One manager by default

Use one capable manager/agent unless separation has a concrete benefit:

- mandatory independent evaluation;
- information/context isolation;
- private per-character state;
- genuinely different permissions/tools/runtime;
- useful parallel work over immutable inputs;
- human review.

Do not create multi-agent round-tables merely to mirror a software organization chart.

## 03 · Exactly one primary task mode

Every user-visible run has exactly one primary mode:

`DESIGN-BOOK | DESIGN-VOLUME | PLAN-UNIT | PLAN-CHAPTER | DRAFT | REVISE | RESEARCH | SETTLE | AUDIT | CORPUS-INGEST | LEARN | SYSTEM-IMPROVE`

A mode may invoke shared internal subroutines, but it may not silently perform another mode's user-visible side effect. DRAFT does not SETTLE; AUDIT does not rewrite by surprise; LEARN does not self-promote durable behavior.

**Basic feedback Learning intake is a bounded internal subroutine, not a second primary mode.** Feedback in REVISE/DRAFT/PLAN/etc. can become Learning evidence without requiring an explicit LEARN mode switch. LEARN remains the dedicated mode for deeper learning analysis, Corpus expansion, hypothesis evaluation and promotion work.

## 04 · Bootstrap live authority before semantic work

A fresh manager resolves:

1. current/pinned Framework manifest/identity;
2. consuming Project manifest + exact lock/fingerprint;
3. Project Adapter/logical paths;
4. exactly one task mode;
5. manager session/run identity;
6. authority cutoff + permissions;
7. sparse Context Manifest/candidate set;
8. current host capabilities.

Old chat/provider session state is not bootstrap authority. Resume revalidates Framework/Project compatibility, current fingerprints, approvals/write preconditions and pending capabilities before continuing.

## 05 · Search/context: semantic selection, deterministic boundary

The manager/model decides what it lacks, what to search, how to query, which result matters, whether to reformulate/continue, what to retain and when it has enough evidence.

The runtime may expose search/fetch/extract/index primitives and generate candidates. Recency, fixed last-N windows, vector similarity, top-k and item classes are not narrative truth.

`context_inspector.py` verifies mechanical eligibility/stage/protected-edit state and intentionally rejects a `relevance` field.

`context_assembly.py` v2 runs **after** semantic selection. It validates exact selected/source refs, receiving stage, hidden/private/invalidated state, fingerprints and exact higher-authority refs when an operation mechanically requires them. It does not enforce literary class/purpose obligations or claim semantic sufficiency.

Hard-budget packing may enforce whole-item resource limits after selection. Persistent storage never implies automatic prompt injection.

## 06 · DRAFT / REVISE production responsibilities

The adaptive production path is approximately:

```text
authority/session bootstrap
→ agent-owned context/search
→ deterministic exact-set/stage/fingerprint verification
→ Story / Canon + planning preflight
→ private character state
→ character.action_propose
→ scene.resolve_actions
→ compact writer-safe realization
→ Reader Pressure
→ event-first Raw Draft
→ Surface realization
→ freeze candidate fingerprint
→ Blind Reader (`reader.engagement_audit`)
→ Semantic Rule Auditor when required (`quality.semantic_rule_audit`)
→ Editor repair spec (`editor.repair_spec`)
→ repair / challenger comparison as warranted
→ continuity/state checks
→ required independent semantic gate
→ user-visible Review Draft
```

Important boundaries:

- Raw Draft is internal.
- Regression bad examples remain post-generation until Raw Draft/candidate freeze.
- Private character state is causal evidence, not Writer exposition payload.
- Surface-clean prose is a floor, not production readiness.
- Blind Reader is not a hard-rule checklist executor.
- Rule Auditor sees authoritative rules Reader should not see.
- Editor chooses repair owner and generation mode semantically.
- `repair_policy.py` only enforces the resulting writer-context boundary.
- Any material candidate change invalidates stale fingerprint-bound review results.
- Explicit acceptance and SETTLE remain separate.

When the user gives feedback during production, the current explicit instruction constrains the current run immediately; the same turn may independently enter automatic Learning intake. Current compliance never waits for durable promotion.

## 07 · Model-readable semantic contracts

Catalog authority: `harness/semantic_workers/model_contract_catalog.json`.

Semantic work resolves exact contract IDs through that progressive-disclosure catalog. A job binds kind/subject/version, bounded input/context, rubric, output contract, permissions, semantic fingerprint and execution provenance.

The model owns judgment. Runtime validates identity/fingerprint/permissions/type/provenance and consumes results once. Internal semantic work is not automatically independent.

`learning.preference_interpret` first decides semantic `capture | skip`; capture then determines the narrowest scope, mechanism and exact hypothesis relation. Never replace this with keyword/regex feedback classification. The contract is `independent_gate=false`, so Learning does not automatically require another costly reviewer.

## 08 · Capability broker

Every tool/external action must be resolved against current host capabilities. Undeclared capability is unavailable.

A provider name, executable on PATH, remembered prior session, network primitive, documentation page or model assertion is not proof of authorization.

Capability never grants authority: filesystem write capability does not grant Canon write.

Credentials/authority tokens stay outside ordinary semantic context.

## 09 · Durable session != model context

Execution identities remain distinct:

```text
Project/resource
→ session
→ run
→ checkpoint
→ event/handoff/job
→ result
→ validated consume-once receipt
→ resume
```

Checkpoint before external waits, required independent review and consequential writes. Context-window loss is recoverable because authoritative state lives in durable artifacts/events/checkpoints, not in the transcript.

`feedback.observed` follows the same model: Author Steering and Learning Intake consume the same durable event under distinct logical consumers. Missing semantic capability leaves Learning in durable `awaiting_semantic`; resume revalidates event/hash/job fingerprint before continuing.

## 10 · Independent semantic integrity

When a gate requires independence, the manager may:

`freeze → package → checkpoint → dispatch → await → validate → consume → route repair`

It may not perform the judgment itself under a different role label.

A materially changed candidate needs fresh bound review unless the contract explicitly permits reuse. Transport failure may route to another eligible transport; a valid semantic reject routes repair and must not trigger reviewer shopping.

No eligible independent provider/model means `PENDING_MODEL`, never PASS.

## 11 · LEARN / CORPUS / SYSTEM-IMPROVE

Learning separates:

```text
feedback observation
!= semantic interpretation
!= evidence
!= hypothesis
!= promotion review
!= write authority
!= active eligibility
!= current relevance
```

### Automatic feedback intake

For user/authorized-human semantic feedback about existing outputs or working behavior:

```text
feedback.observed
├→ Author Steering for the current run when applicable
└→ learning/feedback_intake.py
   → learning.preference_interpret
   → capture | skip
   → Author Model evidence/hypothesis candidate
   → consumer-specific receipt
```

The consumers are independent. Steering consumption never starves Learning; Learning retry cannot duplicate the same evidence.

Automatic intake always keeps activation/write authority false. It does not auto-edit Project Profile, activate durable user taste, promote General Craft, mutate Framework behavior, or write Canon.

Same-event retry uses stable evidence identity. Distinct user turns may supply independent evidence; the model decides whether to strengthen, contest, supersede or split a supplied hypothesis. Python does not infer semantic merge from string/embedding similarity.

Rejected output stores only bounded refs/fingerprint plus negative meaning; rejected prose is not a positive exemplar and is not fed into Writer pre-draft context.

`learning/feedback_query.py` is the side-effect-free observability surface and does not expose whole conversation/private reasoning/hidden gold.

### Durable activation and General Craft

LearningStore/Author Model persist evidence/hypotheses under authority/CAS. Promotion Gate validates exact bound semantic review plus objective prerequisites; it does not use arbitrary evidence-count thresholds as semantic truth and cannot grant write authority.

Active preferences are not automatically injected: the manager/model selects relevant active hypothesis IDs for the current task. Current explicit request outranks older active preference.

General Craft changes remain `SYSTEM-IMPROVE` work with current research, counterexamples/evals, compatibility, rollback and explicit promotion authority. A universal claim in ordinary production feedback is candidate evidence only.

## 12 · Writes and settlement

Every consequential side effect needs least privilege, exact target, before-state/precondition, idempotency, checkpoint/write intent where required, postcondition verification and trace/rollback semantics.

Canon settlement is legal only after explicit Project acceptance/authorized Canon intent. Connectors, schedules, webhooks, model results, learning state, feedback intake, CI or corpus evidence do not grant write authority by arrival alone.

## 13 · Truthful states

Valid workflow states include:

`complete · review · awaiting_user · awaiting_external · semantic_pending · semantic_invalid · failed_gate · blocked · settlement_incomplete`

Feedback intake may internally record `observed | awaiting_semantic | skipped | persisted | blocked | failed`; these are not primary task modes.

A green deterministic workflow cannot replace a required semantic judgment. A semantic job that did not execute remains pending. Never label an artifact production-ready while a required gate is unresolved.

## 14 · SYSTEM-IMPROVE execution discipline

Material Framework work follows:

```text
live bootstrap
→ candidate/owner reconciliation
→ current research
→ overreach audit
→ spec/plan/tasks
→ incremental implementation
→ ablations + deterministic tests
→ independent semantic evidence when required
→ CI/security/compatibility/docs synchronization
→ human-review readiness
```

Every consequential write revalidates current branch/HEAD/before-state. Long operations are bounded; repeated pending without new evidence routes to job/log diagnosis rather than blind waiting. Candidate-owned failures are separated from pre-existing unrelated repository debt.

## Related contracts

- [Orchestration Protocol](ORCHESTRATION_PROTOCOL.en.md)
- [Session Runtime](session_runtime/SESSION_RUNTIME.en.md)
- [Runtime Routing](session_runtime/RUNTIME_ROUTING.en.md)
- [Control Plane](control_plane/CONTROL_PLANE.en.md)
- [Semantic Worker Protocol](semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md)
- [Context & Memory](../docs/context-and-memory.en.md)
- [Production Pipeline](../docs/production-pipeline.en.md)
- [Adaptive Learning](../docs/adaptive-learning.en.md)
- [Canon & State Model](../core/CANON_STATE.en.md)
