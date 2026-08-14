<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="54" />
  <p><strong>Runtime & Integrations · choose execution by proven capability, then bind results back to the same contract</strong></p>
  <p><kbd>CAPABILITY</kbd>&nbsp;&nbsp;<kbd>ROUTE</kbd>&nbsp;&nbsp;<kbd>CHECKPOINT</kbd>&nbsp;&nbsp;<kbd>RECEIPT</kbd>&nbsp;&nbsp;<kbd>VALIDATE</kbd></p>
  <p><a href="integrations.zh-CN.md">简体中文</a> · <a href="README.en.md">Docs Home</a></p>
</div>

# Runtime & Integrations

NovelForge is provider-neutral, but **provider-neutral does not mean transport-agnostic magic**.

A runtime is eligible only when the current host can prove the capability the task actually needs under the current permission, availability, user-interaction, model-execution, and usage constraints.

Then the Harness keeps the semantic identity of the work stable while execution may move across chat, local agents, provider APIs, MCP, GitHub jobs, local models, or humans.

> **Runtime name ≠ capability proof. Capability ≠ authority. Transport retry ≠ a new semantic question.**

---

## 01 · The integration model

Most external or semantic work follows the same sequence.

**Classify the work.** Determine whether the current step needs filesystem access, Git, web / GitHub discovery, a semantic model, independent review, durable external work, or another explicit capability.

**Resolve capabilities.** Undeclared capability is unavailable. A provider name alone does not prove anything.

**Checkpoint before consequential waits / writes.** Preserve Project authority, artifact fingerprints, pending work, and side-effect state before execution leaves the current bounded run.

**Choose an eligible route.** Prefer the least complicated transport that satisfies the contract, independence requirement, user constraints, and usage policy.

**Package the exact contract.** Semantic work binds subject, bounded input, rubric, output contract, permissions, and fingerprint independently of transport lineage.

**Execute and record provenance.** Provider / worker / session / attempt information remains execution lineage, not semantic identity.

**Validate the returned result.** Reject stale fingerprints, malformed output, wrong contract binding, or unauthorized side effects.

**Consume once and route the outcome.** A successful result feeds the owning workflow; a semantic rejection routes repair; an infrastructure failure may route to another eligible transport.

---

## 02 · Current chat

The current chat can be the manager runtime and can also perform ordinary bounded semantic work when the active contract does not require independence.

It cannot satisfy a mandatory independent gate by writing the candidate and then role-playing a fresh reviewer inside the same invocation.

Persistent chat history may help maintain conversational continuity, but it does not become Canon, Project state, or a durable semantic receipt automatically.

---

## 03 · Peer chat

A separate peer chat is useful when the user wants or the rubric requires a genuinely separate model invocation without introducing provider API billing.

The peer receives a bounded packet and returns typed fingerprint-bound evidence through the relay protocol.

### Repository ownership rule

Project-hosted peer review belongs to the **consuming Project repository**, not the generic NovelForge framework repository.

The Framework provides the reusable workflow / composite action / bridge runtime, but:

- the issue / relay surface is owned by the consuming Project repo;
- a Framework-repo issue listener for Project review packets is forbidden;
- the caller must bind the job to the exact Framework commit it is using;
- provenance must bind both the Project repository and Framework revision.

This prevents an independent-review queue for one novel from becoming shared mutable state inside the generic Framework repo.

Reference implementation: `.github/workflows/novelforge-chat-semantic-bridge.yml`, `.github/actions/project-peer-semantic/`, and `harness/semantic_workers/peer_chat_relay.py`.

---

## 04 · Local Codex and Claude Code

Local coding-agent runtimes can run either the full Harness or a bounded specialist / semantic worker when the host exposes the required capability.

Useful cases include:

- repository-aware Project / Framework maintenance;
- semantic work executed in a separate local invocation;
- deterministic validation around a semantic result;
- local file / Git operations that should not be tunneled through a provider API.

NovelForge does not require a second API credential merely because a supported local agent already has its own authenticated runtime.

For independent review, use a genuinely separate invocation / session with the same bounded packet and fingerprint contract.

Repository hooks may capture deterministic lifecycle or file-change telemetry, but telemetry is not semantic review.

---

## 05 · Provider APIs

Provider APIs are optional semantic execution transports.

The adapter must preserve the same NovelForge contract boundaries as any other route:

- exact contract ID and pack;
- bounded input;
- rubric and output contract;
- semantic fingerprint;
- authority / permission restrictions;
- typed result validation;
- execution provenance;
- consume-once semantics.

The provider is not allowed to become an authority source just because it produced the answer.

Normal CI uses contract tests / dry runs and does not silently spend provider inference usage. Live provider-backed semantic work requires an explicit execution path and configured secret.

---

## 06 · MCP and service workers

The reference local MCP transport is stdio. Remote service deployment may use Streamable HTTP under normal authentication, origin, session, and transport-security rules.

The Control Plane exposes **operational** capabilities: external events, handoffs, leases, result receipts, and durable work lifecycle.

It deliberately does not expose raw “make this Canon” power as a generic MCP capability.

A worker can return a result; the Harness still decides whether that result satisfies the semantic contract, and the Project / Settlement layer still owns any high-authority mutation.

---

## 07 · GitHub Actions and service jobs

GitHub is useful for several different jobs that should remain distinct.

**Deterministic CI** validates code, schemas, project / Framework contracts, documentation, bundles, and eval queue hygiene without live model execution.

**Reusable contract workflows** let consuming Projects run the Framework's deterministic checks against a pinned revision.

**Typed event ingress** can normalize external events into a shared lifecycle instead of inventing provider-specific resume semantics.

**Project-hosted peer-chat bridge** carries independent semantic packets without putting Project review state in the Framework repo.

**Optional live semantic workflow** can run model-backed evaluation only when explicitly dispatched with the required secret / usage policy.

**Scheduled maintenance** may advance deterministic maintenance / learning state or prepare queues, but it does not receive model execution, web access, or promotion authority simply because a clock triggered it.

Current workflow surfaces include:

- `.github/workflows/novelforge-ci.yml`
- `.github/workflows/novelforge-contracts.yml`
- `.github/workflows/novelforge-semantic-contract-packs.yml`
- `.github/workflows/novelforge-release-bundle.yml`
- `.github/workflows/novelforge-event-router.yml`
- `.github/workflows/novelforge-chat-semantic-bridge.yml`
- `.github/workflows/novelforge-semantic-live.yml`
- `.github/workflows/novelforge-weekly-maintenance.yml`

A GitHub workflow event is a transport / trigger, not authority elevation.

---

## 08 · Provider-neutral semantic run receipts

Longer semantic workflows can emit `novelforge_semantic_run_receipt_v1`.

The receipt is a **non-authoritative trace**, not a replacement for Session / Control Plane state and not a reasoning dump.

It can bind:

- run / session / task identity;
- Context Manifest reference + fingerprint + authority snapshot;
- capture policy;
- activated contract packs and why they were selected;
- individual semantic steps and their input / result fingerprints;
- worker execution lineage;
- artifact and finding references;
- non-authoritative decisions;
- overall workflow status.

Its capture policy explicitly forbids private reasoning and hidden gold. Semantic payloads can be bounded or fingerprint-only.

Every step and decision remains `authority=false`; receipt permissions forbid Canon, Framework, and durable-user-taste writes.

Reference: `harness/semantic_workers/semantic_run_receipt.schema.json`.

---

## 09 · Web / GitHub / Corpus discovery

Network access is not inferred from “the model is online.”

A discovery step requires a proven host capability such as web search, GitHub search, an authorized connector, or another explicit source tool.

Semantic contracts such as `corpus.discovery_plan` may decide **what should be searched and why**. Deterministic runtime / rights layers decide whether the host can execute that plan and what may be stored.

Scheduled jobs or local runtimes must not fabricate source access when the capability is unavailable.

Discovery is also not ingestion: source provenance and rights remain separate gates.

---

## 10 · Human review

A human reviewer is a first-class runtime.

When used for an independent gate, the human should receive the same bounded artifact / rubric contract, exact fingerprint, and relevant provenance as a model reviewer.

The return path should preserve typed evidence or an equivalent structured result so the manager can validate what artifact was actually judged.

Human judgment still does not grant Canon-write authority by itself.

---

## 11 · Webhooks and external events

Provider-specific webhooks should normalize into the generic typed event contract before the Harness acts on them.

A good adapter preserves:

**provider event → normalized NovelForge event → provenance / idempotency validation → Harness classification → owning workflow**

Do not build a separate resume, retry, or authority model for every provider.

A webhook, connector event, schedule, or MCP message can trigger work. It cannot authorize Canon mutation by itself.

---

## 12 · Fallback semantics

Fallback is allowed for **infrastructure failure**, not for disliked judgment.

Examples of transport failure:

- worker unavailable;
- provider outage;
- lease expired;
- required local binary missing;
- explicit capability disappeared;
- malformed transport response before a valid semantic result exists.

A valid semantic result—especially `semantic_reject`—is not transport failure. It must route to the owning repair mechanism.

If the artifact / rubric / output contract materially changes during repair, it becomes a new semantic fingerprint and usually a new review job.

---

## 13 · Secrets and credential boundaries

Provider credentials belong to host / runtime configuration.

Do not store secrets in:

- Project Canon;
- semantic job payloads;
- Corpus records;
- committed runtime SQLite state;
- Framework source;
- review issues / relay packets;
- learning evidence.

Capability records may say that a provider/API capability is available, but should not embed the secret that makes it available.

---

## 14 · Choosing a route

Prefer the simplest route that satisfies the actual contract.

**Current chat** — low-friction manager or ordinary semantic work when independence is not required.

**Peer chat** — separate user-relayed model judgment; especially useful when no API model execution is desired.

**Local Codex / Claude** — repository-aware execution using an already authenticated local runtime.

**Provider API** — explicit programmatic semantic execution and structured automation.

**MCP / service worker** — durable operational delegation across process or host boundaries.

**GitHub job** — deterministic CI, event-driven integration, or explicitly configured service workflow.

**Local model** — privacy / cost / offline tradeoffs when capability is sufficient.

**Human** — high-value judgment, policy, or acceptance work where human evidence is required.

The route may change. The contract and authority boundary must not.

---

## 15 · Exact references

- [Runtime Capabilities](../harness/session_runtime/RUNTIME_CAPABILITIES.en.md)
- [Runtime Routing](../harness/session_runtime/RUNTIME_ROUTING.en.md)
- [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.en.md)
- [Control Plane](../harness/control_plane/CONTROL_PLANE.en.md)
- [Semantic Worker Protocol](../harness/semantic_workers/SEMANTIC_WORKER_PROTOCOL.en.md)
- [Semantic Execution Runtime](../harness/semantic_workers/SEMANTIC_EXECUTION_RUNTIME.en.md)
- [Project SDK](project-sdk.en.md)
- [Corpus Intelligence](../corpus/README.en.md)

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom mark" width="48" />
  <br />
  <sub>Move execution when needed. Never move the authority boundary with it. ✦</sub>
</div>
