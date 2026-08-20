# Quillframe 1.0 All-in-One Implementation Plan

This plan implements the clean-break specification in gated, test-driven slices. A gate may advance only with fresh evidence. The version remains pre-release until Gate 6.

## Working rules

- Preserve the host/framework/project authority boundary.
- Keep CH001 as the only executable acceptance scope.
- Write a failing contract test before each runtime behavior.
- Keep normal CI deterministic and free of live model or paid external calls.
- Pair human-facing English and Simplified Chinese documentation.
- Do not add compatibility code. A legacy fixture must be rejected, not translated.
- Never claim an external WorkOS/Cloudflare deployment without live account evidence.

## Gate 0 — Authority and research

Deliver:

- paired spec, plan, and task ledger;
- source-level adopt/adapt/reject research register;
- explicit confirmation that pre-1.0 runtime state is disposable;
- a single product topology and trust-boundary decision.

Exit evidence:

- YAML parses;
- paired documents exist;
- no research item silently creates a dependency;
- `compatibility_layer_permitted: false` and `migration_permitted: false` are machine-readable.

Rollback: delete only spec 024 artifacts; no runtime mutation occurs in this gate.

## Gate 1 — Foundation hard cutover

1. Create the root pnpm workspace and align Site, Docs, Studio, and Cloud packages on one package manager and TypeScript baseline.
2. Re-declare the exact 1.0 machine schemas in a canonical schema directory.
3. Replace Host Bridge current contract with version 11 and add run subscription/resume/cancel/route-preview operations.
4. Replace the MCP initialization constant with `2026-07-28` and exact-match rejection.
5. Remove current root-host-hook correctness requirements and make `quillframe launch` the only product bootstrap.
6. Add legacy-rejection and duplicate-contract scans.

Exit evidence:

- contract tests fail on Bridge 10 and MCP 2025 inputs;
- one workspace lockfile installs reproducibly;
- no current product code imports a second bridge or protocol contract;
- root Claude/Codex configuration is not required to launch or test the product.

Rollback: revert Gate 1 as one unit; do not introduce an adapter to preserve a partial cutover.

## Gate 2 — Core workflow and AI routing

1. Add `NovelWorkflowEngine` with an explicit transition table and append-only typed events.
2. Add CH001 scope guard at run creation, generation packet creation, and all release/authority operations.
3. Add typed scene intent, character intent, transition constraints, risk signals, repair plan, and generation packet models.
4. Implement safe-point pause/resume/cancel with exact cursor/idempotency semantics.
5. Add `ModelTaskProfile`, deterministic route preview, hard budget checks, and explicit fallback receipts.
6. Bind critic and independent-review evidence to candidate fingerprint; invalidate it on mutation.
7. Expose new operations through Bridge v11 without giving the bridge Canon authority.

Exit evidence:

- transition/property tests cover legal and illegal edges;
- replay produces byte-stable receipts;
- CH002 is rejected before context or model execution;
- no secret survives schema sanitization or persistence tests;
- an independent reject routes repair and cannot trigger a second reviewer automatically.

Rollback: delete new 1.0 runtime state and code; no old state is migrated or restored.

## Gate 3 — Local product, public site, and docs

1. Implement `quillframe launch` resolution, project creation, loopback server lifecycle, receipt, browser-open behavior, and cloud opt-in boundary.
2. Recompose Studio around `Start · Write · Review · Publish`, with `Plan · Story · Research` support and explicit Advanced routes.
3. Build the Homepage around thesis, truthful quick demo, workflow, evidence, privacy, and start.
4. Run the CH001 deterministic Core in a Web Worker/Pyodide demo; package semantic output as a labelled recorded fixture.
5. Rebuild Docs navigation around author tasks and trust boundaries.
6. Add empty/loading/error/offline/long-content/responsive/reduced-motion states.

Exit evidence:

- local launch E2E creates/opens one CH001 project and never binds non-loopback;
- demo output matches Core fixture fingerprints and discloses recorded semantic evidence;
- no account, key, or network is required for the public demo;
- accessibility and visual snapshots pass at mobile/tablet/desktop sizes.

Rollback: revert product shells and launch server together; Core contracts remain independently testable.

## Gate 4 — Hosted Studio

1. Add a Cloudflare Worker BFF package with strict origin, CSRF, callback, cookie, and security headers.
2. Implement WorkOS AuthKit authorization/callback/logout adapters behind testable HTTP interfaces.
3. Add `WorkspaceCoordinator` Durable Object for per-workspace serialization and project manifest coordination.
4. Add `SessionVault` Durable Object with AES-GCM encrypted secret leases, 30-minute idle expiry, 8-hour absolute expiry, and explicit destruction.
5. Define encrypted R2 project-bundle storage and a Python Core Container binding.
6. Validate hosted custom endpoints as public HTTPS with DNS/redirect SSRF and rebinding defenses.
7. Make upload explicit and one-way per action; do not add sync or import.

Exit evidence:

- local Worker tests cover callback tampering, CSRF, cookie flags, expiry, logout, deletion, SSRF, rebinding, encryption, and log/receipt redaction;
- cloud manifest is personal-workspace-only;
- no model token is persisted outside SessionVault ciphertext;
- live deployment remains `awaiting_external` until account-bound checks succeed.

Rollback: destroy test namespaces/buckets and remove cloud bindings; local product remains complete.

## Gate 5 — Clean-break audit

1. Remove obsolete current routes, READMEs, package-manager files, bridge constants, MCP constants, and runtime adapters.
2. Rebuild fixtures on 1.0 schemas.
3. Add an allowlisted history-aware scan: historical specs may describe old versions, current product/runtime/docs may not expose them.
4. Confirm no redirect, dual read/write, import migrator, or compatibility feature flag exists.

Exit evidence:

- legacy rejection suite passes;
- current-surface scan reports zero unallowlisted matches;
- repository hygiene identifies the one lockfile and canonical contract locations.

Rollback: none through compatibility. Fix the 1.0 source of truth directly.

## Gate 6 — Release acceptance

Run fresh:

- Python unit/integration tests and compile checks;
- Node package tests, type checks, builds, and lockfile install;
- Bridge/MCP/schema contract suites;
- local launch/browser E2E;
- public demo offline/truth checks;
- cloud Worker deterministic/security tests;
- accessibility and responsive visual QA;
- repository hygiene and secret scans;
- an actual CH001 production path through visible candidate, human accept, settlement, and publication.

Release decision:

- Set `VERSION`, Python package, machine manifest, UI metadata, and release docs to `1.0.0` only after all locally controllable gates pass.
- If hosted live verification is unavailable, retain an explicit pre-release version and `awaiting_external` status.
- Any failed mandatory semantic gate remains `semantic_pending` or `failed_gate`, never PASS.

## Dependency order

```text
schemas + exact protocols
→ workflow/events + model routing
→ Bridge v11 + launch server
→ Studio/Site/Docs/demo
→ Hosted BFF/DO/Container/R2
→ clean-break audit
→ CH001 release evidence
```

## Risk controls

- Contract drift: canonical schemas plus cross-language fixture tests.
- UI reimplementation of authority: all mutations pass through Bridge v11/Core.
- Secret leakage: schema allowlists, redaction tests, memory-only local lease, encrypted hosted lease.
- False demo claims: deterministic/recorded labels embedded in the demo receipt.
- Cloud lock-in: BFF and storage adapters depend on internal manifests, while deployment bindings stay Cloudflare-specific.
- Scope explosion: CH001 and personal workspace are hard guards, not roadmap suggestions.
