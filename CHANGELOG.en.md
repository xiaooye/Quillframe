# NovelForge Changelog

## Unreleased · Development architecture toward 8.0

> This section is a development ledger, **not an 8.0 release declaration**. `HARNESS_MANIFEST.yaml` remains the release authority until the Core acceptance/release workflow explicitly promotes a new release.

### Release truth

- The current release authority still reports **7.2.0** in `HARNESS_MANIFEST.yaml`.
- The top-level CLI currently reports **7.3.0** through `novelforge.py`, while the Project SDK default remains **7.2.0**. This is implementation/release metadata drift and must remain visible until the owning Core/release workflow resolves it.
- Documentation rebuilt against current `main` remains a review candidate unless the documentation manifest explicitly marks it `reviewed_current` against the release authority.
- NovelForge **8.0 is not released** merely because 8.0-oriented mechanisms or documentation are present on `main`.

### Merged development changes

- The semantic runtime has moved to a small model-contract catalog with progressive disclosure of exact contract packs. Semantic fiction judgment belongs to the model; deterministic code owns authority, permissions, fingerprints, persistence, routing, hard budgets, typed validation, transactions, and reproducibility.
- The live machine namespace migrated from `NOVEL_OS_*` / `novel_os_*` / `.novel-os/` surfaces to `NOVELFORGE_*` / `novelforge_*` / `.novelforge/` without compatibility aliases. This is a pre-release breaking migration.
- Context selection now supports task-aware grounding with explicit question-to-evidence mapping and deterministic perspective/visibility filtering before model context is assembled. Ineligible pinned evidence fails closed rather than being shown to the model with a warning.
- A metadata-only `novelforge_run_receipt_v1` observability primitive has been merged. It binds run/context/semantic-job/guard metadata and grounding evidence without storing candidate prose, granting Canon authority, or becoming a second state database.
- Current settlement/runtime work keeps Accepted-artifact mutation behind explicit acceptance, exact before→after intent, checkpoint/write authorization, compare-and-swap, post-condition checks, and required projection receipts. Derived projections remain non-Canon.
- Documentation governance now tracks audience, tier, authority sources, freshness ownership, rewrite policy, lifecycle state, bilingual pairing, local-link integrity, release drift, and deterministic visual/documentation checks. Semantic documentation review remains a separate human/model judgment layer.

### Breaking-change and migration ledger

- The machine namespace migration above is **already implemented on live `main`**. Historical 7.0 notes below describe the state of that release and should not be read as current machine guidance.
- The separate permission-schema rename `os_behavior_write` → `framework_behavior_write` is **not complete on live `main`**. Closed PRs #14/#15 are not release authority and must not be treated as a successful migration.
- Projects pinned to an older NovelForge commit remain bound to that exact dependency. Do not silently switch an existing project lock to `main`; use an explicit framework-upgrade/migration workflow and revalidate the project, bundle fingerprint, contracts, and any affected runtime state.
- Final 8.0 migration instructions must be generated from the accepted Core contracts and release bundle, not inferred from issue descriptions or intermediate development commits.

### Product / publication status

- Publication / Typesetting is an active Core workstream tracked by issue #16. Until its schemas/runtime are present in live release authority, documentation must describe it as planned/in development rather than as a released capability.
- NovelForge Studio / observability UX is an active Product Experience workstream tracked by issues #8 and #17. A merged Core receipt or inspector primitive does not by itself mean Studio is shipped.
- Studio must consume Core state through stable read interfaces; UI state never becomes Canon, Memory, semantic truth, or write authority.

## 7.0.0 · Adaptive Fiction Framework

### Architecture
- Repositioned the repository as a fully project-agnostic fiction agent framework.
- Established one-way dependency: consuming Project → NovelForge Framework.
- Added standard and mapped Project Adapter support so mature fiction repositories can migrate without destructive directory rewrites.
- Added `novelforge.toml` project manifest and `novelforge.lock.json` framework dependency lock contract.

### Fiction Core
- Added generic Story Architecture, Character/Relationship, Canon/State, dependency, settlement, and continuity contracts.
- Promoted recurring anti-AI prose corrections into framework-level Surface Fundamentals (HF-01..HF-29).
- Added generic Reader Engagement positive quality model (RG-01..RG-15), including SAFE-BUT-FLAT detection.

### Runtime
- Preserved session-native Harness with manager/specialist/reviewer separation.
- Added durable SQLite Control Plane for sessions, events, handoffs, leases, result hashes, and logical consume-once receipts.
- Added provider-neutral runtime routing across chat sessions, local Codex/Claude, MCP, provider APIs, GitHub/service jobs, local models, and humans.
- Kept mandatory independent semantic judgment fingerprint-bound and fresh-per-fingerprint by default.
- Added typed GitHub event ingress and a no-API peer-chat semantic bridge.
- Added optional manually dispatched provider-backed semantic eval workflow; it requires an explicit secret and is never part of normal CI.
- Added weekly deterministic maintenance that observes/tests/queues work without LLM execution or automatic Framework promotion.

### Adaptive Learning
- Added durable Learning Store for preference evidence, revisable hypotheses, contradictions, Corpus gaps, promotion candidates, and rollback records.
- Added autonomous preference-dimension discovery and Corpus-gap generation.
- Enforced evidence hierarchy: model inference alone cannot become durable user taste or General Craft.

### Corpus Intelligence
- Added provider-neutral Corpus Scout and rights/storage gate.
- Added rights classes `redistributable | analysis_only | unknown`.
- Added question-bounded analysis, counterexample search, cross-work generalization, and named-author imitation boundaries.
- Migrated eight generic cross-work mechanism benchmark seeds without raw source text or consumer-project facts.
- Scheduled maintenance can generate typed Corpus discovery queues, while actual Web/GitHub/MCP discovery still requires an authorized host connector and is never fabricated.

### Evals
- Added generic deterministic + semantic eval runner.
- Added blind semantic queue builder that strips expected/gold/release labels before reviewer dispatch.
- Added v7 Surface/Reader/Character/Canon/Corpus fixture suite.
- Normal CI reports semantic cases as `PENDING_MODEL` when no independent judgment exists rather than fabricating PASS.

### Project Engineering
- Added executable Project SDK: `init`, `validate`, `spec-new`, `build`, `self-test`.
- Added generic mapped Project Adapter for legacy/mature repositories.
- Adopted engineering discipline for structural changes: `spec → plan → tasks → implementation → verification → acceptance`.
- Added deterministic compact project bundle/fingerprint build model.

### Documentation / Repository Quality
- Added paired English and Simplified Chinese authoritative documentation.
- Added Mermaid architecture/learning/runtime/project diagrams.
- Added agent-framework adopt/adapt/reject research matrix.
- Added CI hard gates for consumer-project leakage, bilingual pairing, relative links, manifests, Project SDK, Learning/Corpus, Runtime/MCP, Semantic transport, Evals, and authority boundaries.
- Normal CI does not invoke paid/login-bound model inference.

### Migration note
- Old internal compatibility identifiers may still use pre-v7 `novel_os_*` names inside stable executable schemas/environment variables. They are implementation compatibility details, not consumer-project dependencies. A future schema migration can rename them behind a dedicated structural-change spec without destabilizing v7 release behavior.