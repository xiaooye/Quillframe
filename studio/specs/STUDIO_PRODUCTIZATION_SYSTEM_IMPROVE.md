# Quillframe Studio Productization · SYSTEM-IMPROVE

Status: implementation plan frozen before framework writes  
Primary task mode: `SYSTEM-IMPROVE`  
Authority base: `xiaooye/Quillframe@c363631585fc0dc13cd948db7f60790cf9d4cfae`  
Work branch: `agent/studio-productization-20260818`

## Goal

Turn Studio from a partial product shell into an authoring-first product that consumes Quillframe Core through one typed operation boundary. The same operation semantics must serve Hosted Web and a fully local Tauri 2 host. UI state is never Canon, Accepted state, Settlement authority, or a second persistence authority.

North-star flows:

- Web: Studio → New Project → Endpoint → Token → Connected → Start Writing.
- Desktop: installed Tauri → local Core sidecar → native SQLite → New Project → Endpoint → Token → Start Writing.

## Non-negotiable invariants

1. `UI → BridgeClient → typed transport → Core operation → SQLite / deterministic derived build`.
2. Browser code never reads SQLite, arbitrary Python internals, Cloudflare bindings, or local filesystem directly.
3. `autosave != Accepted`, `Accepted != Settled`, `persistence != authority`.
4. A model credential value never enters SQLite, project state, semantic context, receipts, logs, backup/export, or `.qfproject`.
5. Missing Core contracts are exposed as `unsupported` / `semantic_pending` / `awaiting_external`, never simulated with fixtures.
6. Hosted and Tauri surfaces share operation names and result envelopes; host adapters own transport only.
7. Tauri local authoring must not depend on Cloudflare or any hosted Quillframe service.
8. No default polling and no idle decorative animation.

## Baseline findings

- `studio/app/src/bridge.ts` hard-codes `fetch('/api/bridge/invoke')` and `surface: local_app`; its TypeScript contract omits `authority_command` and its surface enum drifts from the machine contract.
- `studio/app/src/productProjection.ts` calls obsolete `runtime.*` / `run.receipt.*` operations and sends `project_root` where current product Core uses `project_id`.
- `Start.tsx` explicitly describes Desktop as planned and project creation as CLI-only.
- No `src-tauri` application exists at the frozen base.
- Native SQLite already supplies WAL, foreign keys, busy timeout, synchronous FULL, checksummed migrations, optimistic revision parent checks, verified snapshot backup/restore, and doctor/integrity checks.
- Model Runtime already owns endpoint normalization, model discovery/probing/selection and secret-reference semantics, but only memory/env secret stores exist; OS credential storage is still a host responsibility.
- Candidate acceptance and Settlement are already separate Core authority commands with exact fingerprint and independent-review requirements.

## Reference-pattern research

### ADOPT

- **Scrivener:** binder → editor → optional Inspector; index cards/outliner as alternate views of the same project objects; tools disappear when not needed.
- **NovelCrafter:** durable revision history adjacent to the field being edited; restore is explicit.
- **Sudowrite:** AI assistance stays anchored to the manuscript cursor and story context rather than becoming the main application shell.
- **Cursor / VS Code:** editor-first center, optional right-side AI dock, command palette, reviewable diffs before changes become durable accepted work.
- **LangSmith:** project → trace/run → focused details; provenance stays attached to the selected execution rather than flooding the main authoring surface.
- **Temporal:** resumable execution identity and event/history semantics; operational recovery remains distinct from business/story truth.
- **Dagster:** graph/lineage and run observability are inspector views, not the primary day-to-day authoring IA.
- **SillyTavern:** connection profiles hide endpoint/model complexity, while context/lore controls are progressive and budget-aware.

### ADAPT

- AI connection becomes Endpoint + Token first; discovered models/capabilities become advanced controls after connection.
- Binder/card planning patterns are adapted to Quillframe authority labels: `locked | accepted | active_plan | review | proposal` must remain textual, not implied by card color.
- Diff review is adapted to Candidate → Review → Accept → explicit Settle. Accepting a candidate cannot silently mutate Canon.
- Workflow/trace graphs become the Architecture/Inspector lenses `SYSTEM | EXECUTION | AUTHORITY | PROJECT`.

### REJECT

- Generic admin-dashboard IA, card soup, universal 1px borders, dense runtime telemetry as the default Writer view.
- Browser-owned project truth in localStorage/IndexedDB.
- A Cloudflare-shaped Core contract.
- Automatic acceptance/settlement after AI generation or inline edit.
- Hiding pending/unsupported Core work behind generated fixture data.

## Product IA target

Creator navigation:

`DESK | MANUSCRIPT | PLAN | STORY | REVIEW | RESEARCH & CORPUS | LEARNING | PUBLISH`

Global:

`AI ASSISTANT DOCK | SEARCH | COMMAND PALETTE | SETTINGS`

Inspector progressive disclosure:

`SESSIONS | RUNS | CHECKPOINTS | CONTEXT | AGENTS/MODELS | SEMANTIC JOBS | CONTROL PLANE | CAPABILITIES | RECEIPTS | DIAGNOSTICS | ARCHITECTURE`

## Route → Core operation baseline/target

| User action | Required operation | Product state |
|---|---|---|
| New Project | `project.create` | implement/wire |
| Project list/open | `project.list`, `project.inspect` | add public op |
| Delete/remove project | `project.delete` | add guarded op |
| Portable export/import | `project.export`, `project.import` | add `.qfproject` ops |
| Backup | `project.backup` | already Core-backed; wire |
| New manuscript | `document.create` | already Core-backed; wire |
| Binder/list/open | `document.list`, `document.get` | add public ops |
| Autosave revision | `document.revision.save` | already CAS-backed; wire |
| History | `document.revisions.list` | add public op |
| Compare | `document.revision.compare` | already Core-backed; wire |
| Restore | `document.revision.restore` | add as a new proposal revision |
| Connect Endpoint+Token | `model.connect` | add host/Core op over Model Runtime |
| Model list/capability | `model.list`, `model.get` | add query ops |
| Author AI request | `author.run.start` | real run registration; currently may return `awaiting_semantic` |
| Candidate list/review | `candidate.list`, `candidate.get` | add projections |
| Accept | `candidate.accept` | existing authority command |
| Settle | `settlement.apply` | existing authority command |
| Publication preview/build | `publication.preview`, `publication.build` | existing Accepted-only Core |
| Inspector | `inspector.*.list` | current Core-backed persisted projections |
| Doctor | `database.doctor` | existing |

Plan/Story mutation is deliberately not fabricated in this change unless a matching Core authority contract exists. Unsupported edit affordances stay disabled/deferred.

## Portable `.qfproject` contract

`.qfproject` is a deterministic portable project package, distinct from operational `.qfbackup`:

- ZIP container.
- `manifest.json` with schema/version/project identity/DB fingerprint/blob fingerprints and compatibility metadata.
- consistent SQLite snapshot created through SQLite backup after WAL checkpoint.
- `project.sqlite` plus referenced `blobs/**`; no global DB, model service table, credential ref, token, environment secret, host config, cache, or exports.
- validate archive paths before extraction; reject traversal/absolute paths/symlink-style entries.
- verify checksums + SQLite integrity + embedded `project_identity` before installation.
- import is stage-then-atomic-replace only when explicitly requested; normal import fails closed if project exists.
- Web↔Tauri portability is file export/import, not live SQLite synchronization.

## Host Bridge target

```text
BridgeClient.invoke(operation, args)
├─ LocalHttpTransport   # loopback Core host
├─ HostedHttpTransport  # authenticated remote Quillframe API; provider-neutral
└─ TauriTransport       # Tauri invoke → thin Rust host → local Python Core sidecar
```

Every request contains a declared surface and `authority:false`. `authority_command` means the *Core operation* enforces explicit authorization; the Bridge itself never gains authority.

## Tauri thin-host target

`Solid/Tauri → Tauri command → packaged Quillframe Python sidecar → Core operations → ~/.quillframe SQLite + blobs`

- Tauri 2 only.
- Python sidecar is packaged as an external binary; Rust does not duplicate Quillframe business logic.
- Desktop credential remembrance is delegated to an OS credential facility. Until that secure host implementation is proven, Desktop connection may remain session-only; never fall back to SQLite or plaintext files.
- A missing packaged sidecar/credential backend must fail visibly, not fall through to Cloudflare.

## Web host target

`Solid hosted UI → HostedHttpTransport → authenticated durable Quillframe Core API → Core → durable SQLite host/volume`

Cloudflare Pages/Workers may serve/adapt the UI boundary, but Workers ephemeral filesystem is not canonical SQLite storage. A static/browser-only deployment is therefore not allowed to claim the full Web vertical slice.

## Implementation tasks

1. Add portable project + project/document query operations to Core/persistence.
2. Add Model Runtime lifecycle operations with session-only secret storage by default and secret-sanitized results.
3. Version Host Bridge contract and dispatch for new operations; close surface/type drift.
4. Replace frontend transport hard-coding with `BridgeClient` + three transports.
5. Rebuild onboarding/project/manuscript paths around real operations and optimistic revision state.
6. Add Review acceptance/explicit settlement surfaces and truthful pending semantics.
7. Add/repair Inspector/Publication projections and remove obsolete operation calls.
8. Add Tauri 2 thin-host source/config with a strictly local bridge command and sidecar contract.
9. Add deterministic unit/integration tests for persistence, bridge, secret leakage, revision conflicts and portability.
10. Update architecture/portable product docs and machine contracts.
11. Run CI on exact branch HEAD; repair deterministic failures.
12. Report Web and Tauri vertical-slice status separately. A source/config implementation without executed desktop verification is not a PASS.

## Acceptance matrix

Phase-1 sequence is tracked independently for Web and Tauri:

1. Open Studio
2. Create Project
3. Project persists
4. Endpoint + Token
5. model discovery
6. create/open manuscript
7. type
8. autosave revision
9. restart/reload
10. text persists
11. AI Dock has correct project context
12. real Agent run
13. Candidate returned
14. Review diff
15. Accept
16. explicit Settle
17. restart
18. state correct
19. export `.qfproject`
20. remove project
21. import `.qfproject`
22. exact recovery

A step can only be PASS when exercised against the corresponding real host. `awaiting_semantic`, `awaiting_external`, `unsupported`, and `failed_gate` remain valid truthful outcomes.
