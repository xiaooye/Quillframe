# Quillframe Studio · Core Consumer Handoff

## Authority snapshot

- Core authority consumed by this Studio workstream: `main@6ee7299f81b92e11b67da32d16abf73e7ace1ccd` (merge of Core PR #131).
- Host Bridge: **v8**.
- Studio consumer PR: #130.
- Dependency direction remains `Studio → typed Host Bridge → Python Core → SQLite`.
- Browser state is convenience only. It never becomes Project, manuscript, Review, Canon, Acceptance, Settlement, Context, Model Service, or credential authority.

## Closed Core blockers

The six blockers previously reported by Studio are now implemented by Core v8 and consumed by Studio:

1. `project.list` — canonical global Project registry.
2. `document.list` — canonical Binder/document list with latest revision identity/fingerprint.
3. `candidate.review.get` — exact Candidate-bound Review projection with incumbent/diff and safe Reader/Character/Continuity/Independent/readiness evidence.
4. `candidate.reject` — explicit exact-fingerprint idempotent Reject; no Canon/Settlement write.
5. `candidate.revision.request` — durable Request Revision; old Candidate becomes non-acceptable; Core returns an explicit REVISE next action with `auto_started=false`.
6. `settlement.preflight` — read-only authoritative Acceptance/current-Canon before-state validation; `settlement.apply` consumes its exact `expected_before_fingerprint`.

No fallback browser authority is retained for these paths.

## Current Studio operation map

### Project / Binder / manuscript
- `project.create`
- `project.list`
- `project.inspect`
- `document.create`
- `document.list`
- `document.open`
- `document.revisions.list`
- `document.revision.save`
- `document.revision.compare`

Manuscript autosave creates proposal revisions only and uses `expected_parent_revision_id` CAS. Reload/open always hydrates the exact persisted Core revision. Local storage may remember the last selected Project/document id only; manuscript text is never stored there.

### AI Assistant / production runtime
- `author.run.start`
- `author.run.status`
- `author.run.execute`
- `inspector.context.runtime`

The UI separates run registration from model execution. DRAFT/REVISE production execution is explicit and passes the current user instruction only as `current_request` rule material; Studio does not forge Framework or Project rule authority.

The normal production state machine is:

```text
register run
→ execute production
→ Context Freeze / mandatory production graph
→ awaiting_external
→ genuinely independent review transport
→ author.run.independent.submit
→ Review Draft Candidate
```

Studio does **not** synthesize independent provenance/result and does not substitute same-runtime self-review. If no independent transport is available, the truthful state is `awaiting_external`.

### Review lifecycle
- `inspector.candidates.list` for Candidate index metadata
- `candidate.review.get` for exact Review evidence
- `candidate.accept`
- `candidate.reject`
- `candidate.revision.request`
- `settlement.preflight`
- `settlement.apply`

Review, Accepted, and Settled remain visibly distinct. Request Revision does not auto-start REVISE. Settlement always performs preflight immediately before apply and uses the exact Core-returned before fingerprint.

### Model Service
- `model.service.add`
- `model.service.list`
- `model.service.get`
- `model.service.discover`
- `model.service.test`
- token lifecycle commands
- `model.capabilities`

Ordinary setup remains Endpoint + Access Token. Provider/protocol/capability identity is Core observation, not a browser-owned setup taxonomy. Token values are never persisted by Studio.

## Explicitly deferred Core operations

Studio continues to reflect Core truth rather than inventing features:
- `project.delete`: unsupported until a reversible Core transaction exists.
- portable `project.export/import`: awaiting external transport contract.
- free-floating `candidate.review.request`: unsupported; mandatory semantic review belongs to production execution.

## Host boundaries

### Hosted Web
The consumer is implemented. Production deployment still requires a real authenticated durable Core endpoint with server-side secure credential/session storage and durable SQLite hosting. An unbound static site remains read-only/unbound rather than falling back to browser authority.

### Tauri Desktop
The TypeScript `TauriTransport` consumer is implemented and invokes a single `bridge_invoke` command. The actual Tauri 2 thin host / OS-keychain-backed SecretStore / packaged Python Core sidecar is **not part of PR #130** and remains a separate host implementation workstream. Desktop must not be called production-ready until that host is built and verified.

## Verification contract for PR #130

The Studio build must prove:
- product-language-quality PASS;
- hardening-quality PASS;
- authoring-boundary-quality PASS;
- TypeScript PASS;
- Node authoring/bridge tests PASS;
- Vite production build PASS;
- real browser smoke PASS for Desk, Manuscript desktop, Review, Context Inspector, AI & Models, phone 390×844 and dark preference;
- no browser SQLite/IndexedDB authority;
- no secret Vite env consumption;
- no fabricated Core operation names;
- no fake run progress/private CoT/raw-draft visibility.
