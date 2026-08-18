# Runtime Routing · Choose the execution path from evidence, not provider folklore

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>ELIGIBILITY</kbd>&nbsp;&nbsp;<kbd>INDEPENDENCE</kbd>&nbsp;&nbsp;<kbd>COST-AWARE</kbd></p>

Runtime Routing selects **where a specific unit of work should execute** after capability evidence has been resolved. It ranks eligible paths by permission, independence, availability, resumability, interaction requirements, cost preference, and operational friction—not by provider brand.

> **Boundary ✦** Routing may choose an execution transport. It cannot weaken the semantic, authority, fingerprint, or context-isolation contract that made the work eligible in the first place.

## 01 · Routing starts after capability resolution

The routing sequence is:

```text
classify task / gate
→ derive capability requirements
→ resolve current host capabilities
→ filter by permission / auth / connection
→ filter by semantic independence / isolation
→ filter by interaction / model-execution / cost constraints
→ filter by resumability / locality / security needs
→ rank remaining eligible paths
→ checkpoint if execution leaves current invocation
→ dispatch
```

A route that fails a mandatory requirement is not a lower-ranked option. It is ineligible.

## 02 · Runtime classes are possibilities, not availability claims

Typical execution families include:

- current chat;
- separate peer chat;
- local Codex / Claude Code / other agent process;
- provider API;
- local model endpoint;
- MCP worker/service;
- GitHub or service job;
- human reviewer.

Any of these may host a manager, specialist, semantic worker, or external task **only if the current invocation proves the required capability**.

The same family can be suitable for one role and invalid for another. The current manager chat can draft; it cannot satisfy its own mandatory independent-review gate by role-playing a reviewer.

## 03 · Manager path

The current chat or local agent may remain manager even when it cannot directly execute every required subtask.

The manager may:

- freeze work;
- package bounded jobs;
- checkpoint;
- route to another runtime;
- await user/external relay;
- validate and consume results;
- resume the owning workflow.

Do not declare the whole Harness blocked merely because one direct adapter is unavailable. Re-resolve all actually connected/declared routes first.

## 04 · Independent semantic path

When a gate requires independent judgment, eligible routes must provide a **genuinely separate invocation/session** plus the same bounded semantic contract.

Possible paths include:

- a separate local agent invocation;
- a provider model call through an isolated adapter;
- an MCP/control-plane worker;
- a GitHub/service worker;
- a separate peer chat;
- an isolated local-model invocation;
- a human reviewer.

The transport is secondary. The invariants are:

- separate execution identity;
- bounded/blind context appropriate to the rubric;
- exact semantic fingerprint;
- truthful worker provenance;
- typed result;
- consume-once binding;
- no reviewer shopping.

## 05 · Chat and peer-relay semantics

A current chat can coordinate work even without subprocess capability.

A separate peer chat can act as an independent reviewer if it receives the frozen blind packet and returns the expected typed result. If the user must manually relay the packet/result, the workflow becomes `awaiting_user` while that handoff is outstanding.

Do not call this `semantic_pending` merely because the relay is manual; the distinction matters for truthful workflow state.

## 06 · Local agent path

An authenticated local Codex/Claude/other agent can often run the full Harness or bounded semantic jobs without requiring Quillframe to introduce a second provider API key.

However:

- executable presence does not prove login/model entitlement;
- manager and reviewer require distinct invocation/session identities when independence matters;
- the reviewer receives only bounded job material, not the manager's entire working directory/chat by default;
- a local process failure is infrastructure failure, not a semantic rejection.

## 07 · Provider/API path

Provider APIs are optional transports rather than framework authority.

A provider adapter must preserve:

- job identity and semantic fingerprint;
- bounded input/rubric/output contract;
- permission restrictions;
- truthful model/provider provenance;
- typed result validation.

Provider-specific convenience must not change the generic semantic meaning of the job.

## 08 · MCP / Control Plane / service-job path

Longer-running or distributed work may use a handoff:

```text
manager checkpoint
→ bounded handoff/job
→ worker claims lease / attempt
→ execution
→ result + hash
→ manager validates binding
→ named consumer records receipt
→ owning workflow resumes
```

Lease expiry or queue retry is infrastructure behavior. It must never be interpreted as a literary verdict.

## 09 · Research / Corpus routing

Research and corpus discovery should express source capabilities, not provider preferences.

Examples:

- `web_search`;
- `github_search`;
- `user_files`;
- `file_library`;
- `mcp_client`;
- local repository/filesystem access.

After discovery, provenance, rights, storage permission, and semantic interpretation remain separate checks.

Search success does not grant ingestion rights or Canon authority.

## 10 · Cost and user preference

User preferences may reorder eligible paths:

- avoid paid APIs;
- prefer local models;
- prefer current subscription/CLI usage;
- prefer no user relay;
- prefer lower latency;
- prefer stronger isolation;
- prefer human review for selected gates.

Preferences cannot make an ineligible route eligible. They may not weaken independence, capability proof, permissions, context isolation, fingerprint binding, authority, or mandatory quality gates.

## 11 · Failure and fallback

Distinguish transport failure from semantic outcome.

```text
infrastructure failure + unchanged semantic fingerprint
→ checkpoint / re-resolve capabilities / try another eligible transport

invalid or mismatched typed result
→ reject result / repair or rerun transport

valid semantic reject
→ consume as semantic judgment / route repair
```

Never switch reviewers simply because a valid reviewer disliked the artifact.

## 12 · Resume

On resume, routing must re-resolve capabilities for any pending external work. Availability, permissions, cost constraints, and connections may have changed independently of the persisted session.

An already completed/consumed result does not rerun merely because a different route would now be preferred.

## 13 · Invariants

1. Route only among currently proven eligible capabilities.
2. Provider family does not determine role or independence.
3. One missing direct adapter does not prove the whole Harness is blocked.
4. Manual peer relay is a real route with truthful `awaiting_user` state.
5. Cost preference reorders eligible paths but never weakens contracts.
6. Infrastructure failure may fallback; semantic rejection may not be reviewer-shopped.
7. Resume re-resolves pending routes.

## 14 · Related contracts

- [Runtime Capabilities](RUNTIME_CAPABILITIES.en.md) — what makes a path eligible.
- [Session Runtime](SESSION_RUNTIME.en.md) — checkpoint/resume identity.
- [Semantic Execution Runtime](../semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md) — semantic-specific execution boundary.
- [Control Plane](../control_plane/CONTROL_PLANE.en.md) — queued/distributed work.
