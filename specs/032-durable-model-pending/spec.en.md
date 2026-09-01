# Durable model pending specification

2026-08-31 · implemented `SYSTEM-IMPROVE` contract · deterministic engineering evidence is complete; the CH001 live REVISE and fresh independent review remain a separate production gate.

This specification forward-supersedes the synchronous lifetime rules in specification 027 for keyed local production requests. It does not change Quillframe Project 1.0, any semantic contract, literary rubric, candidate fingerprint, independent-review boundary, or Core release authority.

## 01 · Observed failure

The earlier transport used one absolute deadline for five different things: HTTP waiting, queue admission, worker lifetime, result publication, and production-stage confirmation. A slow but live API could therefore be killed and recorded as a terminal failure merely because an interactive waiter ended. Retrying was unsafe because the first attempt might still complete, while refusing to continue made normal model slowness block production.

These states are now distinct:

- the HTTP waiter ended while the exact worker is still running;
- the worker heartbeat is current;
- the heartbeat is stale and execution is unconfirmed;
- the worker exited without a valid result;
- a result exists but fails identity, schema, or semantic validation;
- a valid semantic result rejects the candidate.

Only the last three are terminal for that attempt. A waiter ending is not a model failure.

## 02 · Fixed decisions and invariants

1. A durable request has one stable idempotency key derived from the frozen `AgentJob` and model-call ordinal.
2. That key binds one immutable relay packet, one charged stage intent, and at most one CLI process launch.
3. HTTP may return `202 model_pending` after a short wait. The worker continues and the production run becomes `semantic_pending`.
4. Resume may poll only the same request. Polling never inserts another stage-call row and never consumes another call from the budget.
5. The initial deadline still bounds malformed input handling and admission before launch. Once launch is durably evidenced, API slowness does not impose an arbitrary worker lifetime.
6. Exact terminal output may be consumed after the original HTTP/admission horizon. Wrong identity, changed bytes, confirmed cancellation, or a terminal worker failure remains blocked.
7. A missing or stale heartbeat is an unknown state, not permission to dispatch again.
8. Transport changes do not alter prompts, semantic fingerprints, output schemas, literary gates, independence, or authority.

## 03 · Objective and non-goals

The objective is resumable, consume-once model execution for slow local production calls, with no duplicate dispatch or charge.

Non-goals:

- semantic retry, JSON repair, or quality-gate bypass;
- extra model-call authorization;
- treating deterministic tests as literary review;
- changing Canon, acceptance, settlement, or user-taste authority;
- reconstructing historical v2 failures as live v3 workers;
- claiming that a stale heartbeat proves either success or failure.

## 04 · Identities and authority

The following identities are related but never interchangeable:

```text
logical AgentJob request
≠ production stage-call intent
≠ relay request packet
≠ charged CLI attempt
≠ worker process / heartbeat
≠ HTTP waiter
≠ response bytes
≠ confirmed stage result
≠ independent review
≠ Core release
```

The production journal owns call intent and consume-once confirmation. The relay owns immutable transport packets. The CLI driver owns launch evidence and worker state. Semantic Runtime validates the returned result. Core alone releases a Review Draft. None of these artifacts grant Canon or Settlement authority.

## 05 · Current v3 contracts

The forward execution route uses:

- relay packet/result schema `quillframe_chat_host_relay_v3`;
- CLI attempt ledger schema `quillframe_codex_cli_relay_v3`;
- worker state schema `quillframe_codex_cli_worker_state_v1`;
- AgentJob/AgentResult schema v1 with `model_pending` as a typed non-terminal result;
- production journal schema `quillframe_production_execution_journal_v1`, encoding a pollable dispatched row with `error_code=idempotent_model_request|model_pending`.

The request-key header is `X-Quillframe-Model-Request-Key`. Only a literal loopback POST receives its SHA-256 value. The message body is unchanged. A v3 durable packet contains the exact request, request-key fingerprint, initial timing fields, `durable_pending=true`, manager-only provenance, and `authority=false`.

The current database schema is not rewritten for this feature. Pollable state is an explicit compatibility encoding inside the native 1.0 stage journal; projections expose `pending_call_ids`, `hard_unconfirmed_call_ids`, and `safe_to_poll_pending` separately.

## 06 · Lifecycle

```text
frozen stage intent
→ pollable intent persisted
→ immutable packet published
→ CLI attempt charged once
→ worker running + heartbeat
→ result published OR terminal worker state
→ exact result validated
→ stage confirmed once
→ production graph continues
```

An HTTP waiter may leave the path at any point after packet publication:

```text
waiter ends → 202 model_pending → semantic_pending → same-request poll
```

It does not change the worker state. A crash after packet dispatch but before the first 202 is also recoverable because the stage was marked pollable before transport dispatch.

## 07 · Admission, worker, and heartbeat

The caller, relay, and packet retain finite timing fields so DNS, request parsing, queue preparation, and pre-launch admission cannot hang forever or start an already-invalid request. The CLI driver must start before a new packet and records a charged `cli_started` event before process launch.

For keyed durable packets, the default CLI route has no arbitrary `worker_seconds` timeout. An operator may explicitly configure a finite emergency limit; doing so is operational policy, not semantic retry authority. While the process runs, the driver atomically refreshes its heartbeat. On normal exit it publishes `finalizing`, then `completed` or `failed`.

A stale or missing heartbeat after admission is `execution_unconfirmed`. No second launch is permitted. Recovery requires the same worker/result evidence, explicit cancellation, or operator reconciliation.

## 08 · HTTP pending and result binding

The relay waits briefly for an interactive response. If no terminal evidence is ready, it returns:

```json
{"status":"model_pending","same_request_poll_only":true}
```

Subsequent identical POSTs join the existing packet. A changed body with the same key returns an idempotency conflict. Concurrent first publishers join the exact winning packet; they do not create two requests.

The relay checks the response before terminal worker state, validates request and response identity, and returns terminal worker failure only when the worker explicitly reports `failed`, or `completed` without response. A transport interruption while polling remains pending because it cannot prove worker termination.

## 09 · Budget and consume-once

The production stage row is created before external dispatch and counts once against `max_model_calls`. The CLI ledger charges the actual launch attempt once. Repeated HTTP waits, production resumes, heartbeat updates, and result reads are not model calls.

The production journal accepts only a result bound to the original job, session, run, input fingerprint, and Model Service. A confirmed result is immutable. A pending row stays pollable even after its original waiter deadline; that expiry cannot create a replacement row.

Independent review remains a separate reserved call and separate invocation. Increasing wait time never increases either budget.

## 10 · Cancellation and late results

Core cancellation marks the run and unresolved stage rows cancelled. It does not pretend that the external process was killed. A later response may remain as transport evidence but cannot be consumed by the cancelled run. Until cancellation is confirmed at Core, the request remains pending or unconfirmed and cannot be replaced.

Late publication is accepted only for an already-launched durable request with exact identity and unchanged bytes. Results are rejected when the request is confirmed cancelled, terminally failed, stale under a conflicting attempt, malformed, or fingerprint-mismatched.

## 11 · Production and review isolation

Durable pending applies to manager transport only. Writer and registered semantic stages retain their existing contracts and inputs. Blind Reader and independent reviewers do not receive style-selection data or old judgments. A REVISE candidate must still pass fresh Reader, continuity, self-audit, comparison, and independent review before Core may expose it as an unaccepted Review Draft.

## 12 · Compatibility and supersession

Specification 027 remains historical evidence for v2 synchronous requests. This specification supersedes, for new keyed v3 execution only:

- the 600-second Model/Agent hard cap as a worker lifetime;
- the 170/590-second relay cap as a worker lifetime;
- the 150/570-second CLI cap as a default production worker lifetime;
- HTTP timeout as proof of terminal model failure;
- rejection of every result published after the first waiter deadline;
- the statement that asynchronous durable execution is a non-goal.

It retains 027's finite ordinary synchronous default, pre-admission validation, no automatic retry, single charging, immutable historical evidence, fingerprint binding, normal-CI model prohibition, and separate independent-review budget.

Historical v2 packets and receipts are read-only evidence. They are not upgraded, replayed, or converted into v3 pending jobs. A confirmed old terminal failure requires a fresh authorized run.

## 13 · Rollback

Rollback disables the keyed durable route for new runs, drains or reconciles every active v3 worker, and restores synchronous defaults. It must not delete packets, worker states, stage rows, ledger entries, candidates, or budget evidence. Rollback cannot occur while two writers could claim the same request.

## 14 · Normative requirements

- `DMP-001`: persist the keyed stage intent before dispatch.
- `DMP-002`: publish at most one immutable packet per request key and exact body.
- `DMP-003`: charge at most one launch for that packet.
- `DMP-004`: return pending rather than failure when only the HTTP waiter ends.
- `DMP-005`: never dispatch a replacement while worker outcome is unknown.
- `DMP-006`: poll with the same AgentJob input fingerprint and stage-call ID.
- `DMP-007`: accept only exact, identity-bound terminal output.
- `DMP-008`: preserve terminal failure, cancellation, and malformed output as blocking evidence.
- `DMP-009`: keep manager transport distinct from independent review and Core release.
- `DMP-010`: do not run live models in normal CI.

## 15 · Acceptance and completion truth

Deterministic acceptance requires tests for pending/result polling, dispatch-crash recovery, concurrent publication, transient poll failure, terminal worker state, no-timeout keyed execution, expired waiter acceptance, stable stage identity, and no duplicate charge.

Live acceptance additionally requires one real slow production path, exact budget reconciliation, a completed REVISE, a fresh independent review, and a Core-visible unaccepted candidate. Engineering completion alone does not claim literary success or production release.
