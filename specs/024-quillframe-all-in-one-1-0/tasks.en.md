# Quillframe 1.0 Task Ledger

Legend: `[ ]` pending, `[~]` in progress, `[x]` verified, `[!]` blocked by external evidence.

## Gate 0

- [x] T000 Confirm no production users/data and authorize destructive clean break.
- [x] T001 Write paired product specification.
- [x] T002 Write paired implementation plan.
- [x] T003 Record adopt/adapt/reject research decisions and primary sources.
- [x] T004 Validate YAML and bilingual pair integrity.

## Gate 1

- [x] T100 Add root pnpm workspace and one lockfile.
- [x] T101 Align Site, Docs, Studio, and Cloud TypeScript/tooling.
- [x] T102 Add canonical 1.0 schema catalog and validator tests.
- [x] T103 Replace Host Bridge with version 11 only.
- [x] T104 Add `author.run.resume`, `author.run.cancel`, and `model.route.preview`.
- [x] T105 Add cursor-based run subscription contract.
- [x] T106 Hard-cut MCP to `2026-07-28`.
- [x] T107 Add old Bridge/MCP/schema rejection tests.
- [x] T108 Remove root host-hook correctness dependency.

## Gate 2

- [x] T200 Write failing workflow transition and CH001 boundary tests.
- [x] T201 Implement core typed dataclasses/schema validation.
- [x] T202 Implement `NovelWorkflowEngine` and append-only event stream.
- [x] T203 Implement pause/resume/cancel safe points and replay.
- [x] T204 Implement candidate fingerprint invalidation.
- [x] T205 Write failing model route/budget/fallback tests.
- [x] T206 Implement `ModelTaskProfile` and route preview.
- [x] T207 Implement explicit fallback receipt and independent-route integrity.
- [x] T208 Wire Core operations through Bridge v11.

## Gate 3

- [x] T300 Write failing CLI launch resolution/receipt tests.
- [x] T301 Implement local project resolution/new-project wizard.
- [x] T302 Implement loopback launch server and lifecycle.
- [x] T303 Add cloud opt-in boundary without implicit upload.
- [x] T304 Recompose Studio primary/support/advanced navigation.
- [x] T305 Build Homepage six-section information architecture.
- [x] T306 Add Worker/Pyodide deterministic CH001 demo.
- [x] T307 Add labelled recorded semantic fixture and truth receipt.
- [x] T308 Rebuild Docs task navigation.
- [x] T309 Add responsive, offline, error, and reduced-motion states.
- [x] T310 Run local browser/accessibility/visual E2E; production fail-closed browser evidence passed.

## Gate 4

- [x] T400 Create Cloudflare Worker BFF package and bindings.
- [x] T401 Implement WorkOS authorize/callback/logout adapters.
- [x] T402 Implement opaque cookie, CSRF, origin, and security headers.
- [x] T403 Implement `WorkspaceCoordinator` Durable Object.
- [x] T404 Implement AES-GCM `SessionVault` leases and expiry.
- [x] T405 Implement encrypted R2 project bundle adapter.
- [x] T406 Bind Python Core Container contract.
- [x] T407 Implement hosted public-HTTPS endpoint validation.
- [x] T408 Test logout/delete destruction and secret redaction.
- [!] T409 Verify real WorkOS/Cloudflare deployment with account credentials.

## Gate 5

- [x] T500 Delete current legacy routes, package files, constants, and adapters.
- [x] T501 Rebuild current fixtures against 1.0.
- [x] T502 Add history-aware clean-break scanner.
- [x] T503 Prove absence of redirects, migrations, dual paths, and compatibility flags.

## Gate 6

- [x] T600 Run complete Python suite and compile checks.
- [x] T601 Run frozen pnpm install, tests, types, and builds.
- [x] T602 Run contract, legacy rejection, and secret scans.
- [x] T603 Run local launch and public demo E2E.
- [x] T604 Run hosted deterministic/security tests.
- [x] T605 Run accessibility and responsive visual QA; production fail-closed browser evidence passed.
- [!] T606 Execute real CH001 candidate→accept→settle→publish chain; deterministic transitions pass, but fresh independent model evidence is `PENDING_MODEL`.
- [!] T607 Promote version identities only after T409 and T606 pass; identities remain aligned at `1.0.0-dev.0`.
- [x] T608 Produce and read back the release acceptance report with unresolved external evidence recorded.
