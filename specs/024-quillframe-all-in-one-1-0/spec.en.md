# Quillframe 1.0 All-in-One Product Specification

Status: implementation authority  
Primary mode: `SYSTEM-IMPROVE`  
Release target: `1.0.0`  
Acceptance unit: `CH001` only

## 1. Product thesis

Quillframe 1.0 is one fiction-governance system with one author-facing mental model:

> The host runs the agent. Quillframe governs the novel.

The product has three delivery surfaces, not three products:

1. a public Homepage and task-oriented Docs with an account-free CH001 quick demo;
2. a local-first Studio launched by one canonical command and backed by the Python Core plus local SQLite;
3. an explicitly chosen Hosted Studio using the same product shell and contracts, with SSO, isolated sessions, encrypted project bundles, and user-supplied model credentials.

All surfaces share Story Loom design tokens, product language, workflow stages, schemas, and author actions. They may deploy independently because their trust and execution boundaries differ.

## 2. Clean-break decision

There are no production users and no retained production data. The 1.0 cutover is destructive by design.

- No compatibility layer, legacy adapter, old database migration, dual read/write, route redirect, CLI alias, protocol negotiation, or legacy feature flag is permitted.
- Existing development fixtures may be deleted and rebuilt against the 1.0 contracts.
- Historical specifications remain historical evidence; they do not define current runtime behavior.
- Current product code must fail closed when given a pre-1.0 schema, Host Bridge version, MCP version, route, or launch receipt.
- Useful behavior from 0.9 may be re-declared as a native 1.0 contract, never retained solely to preserve an old caller.

## 3. Authority and truth boundaries

- Project authority owns Canon and project-specific facts.
- Models own semantic fiction judgment.
- Deterministic runtime owns identity, permissions, fingerprints, budgets, stage visibility, persistence, transactions, idempotency, and typed validation.
- Model output is evidence or a proposal; it never grants Canon, settlement, publication, durable taste, or Framework write authority.
- `Accept`, `Settlement`, `Delete`, and `Publish` always require explicit author action.
- Local is the default. Cloud never auto-uploads, auto-imports, or auto-syncs a project.
- Secrets never enter project storage, model context, run events, receipts, logs, analytics, R2 bundles, or exported artifacts.

## 4. Canonical author workflow

`NovelWorkflowEngine` owns the typed, resumable graph:

```text
Intent
→ Story / Canon
→ Planning Horizon
→ Character Intent
→ Event Plan
→ Context Freeze
→ Raw Draft
→ Deterministic Checks
→ Reader / Continuity / Style Critics
→ Local Repair
→ Candidate Freeze
→ Pre-independent Qualification
→ Independent Review
→ Human Review
→ Accept
→ Settlement
→ Publish
```

Raw Draft and private character state are never user-visible release artifacts. CH001 is the only allowed chapter in projection, context assembly, model invocation, drafting, criticism, review, acceptance, settlement, and publication for 1.0 acceptance.

The engine exposes typed pause, resume, and cancel at safe points. A material candidate mutation invalidates all fingerprint-bound critic and review evidence. A valid semantic reject routes repair and never reviewer shopping.

## 5. Core contracts

The 1.0 runtime defines these machine-readable schemas:

- `quillframe_scene_intent_v1`
- `quillframe_character_intent_v1`
- `quillframe_transition_constraints_v1`
- `quillframe_risk_signals_v1`
- `quillframe_repair_plan_v1`
- `quillframe_generation_packet_v1`
- `quillframe_author_run_event_v1`
- `quillframe_model_task_profile_v1`
- `quillframe_model_route_receipt_v1`
- `quillframe_cloud_project_manifest_v1`
- `quillframe_secret_lease_receipt_v1`
- `quillframe_launch_receipt_v1`

Every state-changing operation binds exact project, run, artifact, before-state, idempotency key, and authority evidence. Receipts are safe projections and must not contain manuscript text unless the operation is the Core-owned visible release boundary.

## 6. Author profiles

`guided` is the default and presents only the next meaningful author decision. `expert` reveals plan, story, research, context, model routing, evidence, and runtime diagnostics. Profile selection changes presentation density, not authority, quality gates, or persisted truth.

Primary navigation is `Start · Write · Review · Publish`. Supporting work appears as `Plan · Story · Research`. Advanced technical routes remain discoverable from an explicit Advanced area, never as the default landing experience.

## 7. Model routing

Every semantic task resolves a `ModelTaskProfile` declaring role, required capabilities, context budget, output schema, independence class, privacy class, latency preference, and quality floor.

- Quality floor and hard spend/context budgets are enforced before invocation.
- `model.route.preview` explains the selected route without invoking a model.
- Fallback requires an explicit, typed receipt naming the failed route and the bounded replacement. No silent fallback is allowed.
- Mandatory independent review uses a distinct eligible invocation/session and exact frozen candidate fingerprint.
- Stable, non-secret prompt prefixes may use provider prompt caching.
- Cross-project semantic-output caching is forbidden.
- Provider credentials are memory-only leases; durable state stores at most a non-secret reference and capability evidence.

## 8. Canonical launch flow

The only user launch surface is:

```text
quillframe launch [PROJECT]
  --new
  --profile local|cloud
  --id PROJECT_ID
  --title TITLE
  --language LANGUAGE
  --port PORT
  --no-browser
  --json
```

With no arguments, the command resolves the current project, then the last opened project, then offers a new-project wizard on an interactive terminal. Non-interactive ambiguity fails with a typed error. `local` is the default. `cloud` begins an explicit authentication/upload flow and never uploads merely because the command was run.

Success emits `quillframe_launch_receipt_v1`, including the loopback URL, profile, project identity, process identity, storage boundary, and whether a browser was opened. The receipt contains no token or model secret.

## 9. Host Bridge v11

Host Bridge v11 is the only supported bridge. It exposes the canonical author run/candidate/review/accept/settlement operations plus:

- `author.run.resume`
- `author.run.cancel`
- `model.route.preview`
- `BridgeClient.subscribeAuthorRun(run_id, cursor)`

The subscription is cursor-based and resumable. It transports `quillframe_author_run_event_v1`; it does not grant mutation authority. Any request declaring another bridge version is rejected.

## 10. MCP surface

The only protocol version is `2026-07-28`, with stdio locally and Streamable HTTP remotely. Initialization must match exactly. There is no version negotiation or fallback. MCP exposes bounded novelist operations; privileged authority operations remain behind explicit local/hosted product actions.

## 11. Public demo truth contract

The Homepage demo runs in a Web Worker using Pyodide and a fixed, distributable CH001 fixture. It calls the real deterministic Core contract path for validation, context freeze, checks, candidate fingerprinting, and receipt projection. Model-owned semantic output is a versioned recorded fixture and is labelled as recorded, not live AI.

The demo must show what is deterministic and what is recorded. It cannot imply Canon settlement, independent live review, cloud persistence, or provider invocation. It is account-free and API-key-free.

## 12. Local Studio

Local Studio binds loopback only, runs the Python Core, and persists to project-local SQLite. The browser is a thin product shell; it does not reimplement Canon or workflow authority. Local custom model endpoints may use loopback or explicitly approved private addresses under the existing endpoint security policy.

## 13. Hosted Studio and SSO

Hosted Studio uses:

- WorkOS AuthKit with a hosted custom auth domain;
- email OTP, GitHub, Google, and passkeys;
- a Cloudflare Worker BFF;
- host-only opaque `HttpOnly; Secure; SameSite=Lax` session cookies;
- one personal workspace per identity for 1.0;
- `WorkspaceCoordinator` and `SessionVault` Durable Objects;
- a Python Core Cloudflare Container;
- encrypted project bundles in R2.

SessionVault encrypts leased secrets using AES-GCM. Sessions expire after 30 minutes idle or 8 hours absolute. Logout, explicit session end, and project deletion destroy server-side session/lease state. Hosted custom model endpoints must be public HTTPS and pass DNS/redirect SSRF and rebinding defenses; localhost and private ranges are forbidden in hosted mode.

### Native backup proof attempt semantics

For a correctly framed native backup request with a valid identity-bound core proof, the one-shot nonce is consumed before the C3A ZIP verifier runs. The attempt is therefore consumed even when the bundle is malformed or fails strict C3A validation. A retry must carry a newly signed proof and a newly issued nonce; reusing the proof or nonce is rejected. This is a native 1.0 security contract, not a compatibility or retry shim.

Teams, billing, collaboration, background sync, and old-project imports are out of scope.

## 14. UI/UX quality

Story Loom remains the visual language: approximately 70% technical editorial precision and 30% restrained anime-literary warmth. The UI uses pinned WeiUI primitives, SolidJS, and Vite under one pnpm workspace.

- Minimum interactive target: 44 CSS px.
- Keyboard-visible focus: 3 px with 2 px offset.
- WCAG 2.2 AA contrast and semantics.
- No idle animation, surprise polling, or hidden network activity.
- Reduced motion is respected.
- English and Simplified Chinese are first-class and structurally paired.
- Mobile, tablet, desktop, empty, loading, error, offline, and long-content states are acceptance states.

Homepage sections are `Thesis · Quick Demo · Workflow · Evidence · Privacy · Start`. Docs are task-oriented. Studio opens on the next author action, not a framework dashboard.

## 15. Acceptance gates

1. Gate 0 — paired specification, research register, task plan, and explicit disposable-data decision.
2. Gate 1 — clean foundation cutover: pnpm workspace, Bridge v11, MCP 2026-07-28, no duplicate current contracts.
3. Gate 2 — workflow engine, model routing, typed events, pause/resume/cancel, CH001 enforcement.
4. Gate 3 — launch flow, local Studio, Homepage, Docs, and truthful quick demo.
5. Gate 4 — hosted SSO/BFF/session/BYOK/persistence implementation with local deterministic tests.
6. Gate 5 — runtime/product legacy scan and deletion of current compatibility surfaces.
7. Gate 6 — full deterministic, E2E, accessibility, security, build, and CH001 acceptance evidence.

`1.0.0` may be declared only after every gate is green. External-account deployment checks may remain explicitly `awaiting_external`; in that state the implementation is not a released 1.0 product.

## 16. Required verification

- clean install and build from declared lockfiles;
- exact rejection of legacy Bridge, MCP, schema, CLI, URL, and database fixtures;
- deterministic workflow and receipt replay;
- local launch and browser E2E;
- public demo truth and offline behavior;
- model route, budget, fallback, secret, timeout, and independence fault tests;
- SSO callback, cookie, CSRF, session expiry, logout, deletion, SSRF, and BYOK isolation tests;
- encrypted cloud persistence and restore tests;
- keyboard, screen-reader semantics, contrast, responsive, reduced-motion, and Core Web Vitals budgets;
- one real CH001 chain through candidate-visible release, explicit human acceptance, settlement, and publication.

## 17. Non-goals

- CH002 or later chapter execution;
- teams, roles, billing, marketplace, collaboration, or social features;
- autonomous Canon mutation or autonomous publication;
- author imitation or copyrighted-corpus mirroring;
- generic multi-agent orchestration as a product feature;
- migration of any pre-1.0 runtime or user data.
