# NovelForge Changelog

## 0.8.0 · Active pre-1.0 development baseline

> `0.8.0` is the current development identity for the architecture previously discussed as the “8.0” development line. NovelForge is still pre-1.0: latest `main` is the working implementation baseline, and this version does **not** promise a frozen 1.0 compatibility surface.

### Version truth

- Current machine-facing version surfaces are normalized to **0.8.0**: `HARNESS_MANIFEST.yaml`, `SKILL.md`, `novelforge.py`, the Project SDK default, exposed MCP server metadata, and documentation governance metadata.
- This replaces the previous fragmented 7.2 release-metadata / 7.3 implementation-metadata convention. Historical 7.x records below remain historical and are not rewritten.
- During active pre-1.0 development, justified breaking machine-contract cleanup may still land on `main`. Formal compatibility promises belong to a future intentionally frozen release contract.
- Documentation rebuilt against current `main` remains `candidate_review` unless its manifest lifecycle explicitly says otherwise; version normalization does not auto-promote semantic, native-copy, or visual review status.

### Merged development changes

- The semantic runtime uses a small model-contract catalog with progressive disclosure of exact contract packs. Semantic fiction judgment belongs to the model; deterministic code owns authority, permissions, fingerprints, persistence, routing, hard budgets, typed validation, transactions, and reproducibility.
- PR #11 migrated the live machine namespace from `NOVEL_OS_*` / `novel_os_*` / `.novel-os/` surfaces to `NOVELFORGE_*` / `novelforge_*` / `.novelforge/` without compatibility aliases.
- PR #12 added task-aware context grounding with explicit question→evidence mapping and deterministic perspective/visibility filtering before model context is assembled.
- PR #13 added metadata-only `novelforge_run_receipt_v1` observability without candidate prose, Canon authority, or a second state database.
- PR #18 made the Framework bundle release-complete by including the quality runtime and smoke-testing extracted bundles with `novelforge.py doctor` plus the model-free self-test.
- PR #19 merged Studio Phase 1: a read-only Run / Context Inspector driven by Run Receipts.
- PR #21 merged Studio Phase 2A: the portable one-product/many-host contract, safe Project Hub projection, synthetic project/scene fixtures, and a read-only Project Hub + Scene workspace prototype.
- PR #25 merged Studio Phase 2B: a versioned read-only host bridge plus a standards-compatible NovelForge Agent Skill. The bridge exposes an allowlisted read surface (`bridge.describe`, `framework.doctor`, `project.inspect`, `capabilities.inspect`, `context.inspect`, `semantic.catalog`), fails closed on unsupported operations, defaults away from host-private absolute paths, and keeps `authority=false`.
- PR #24 completed the remaining machine-contract rename: `os_behavior_write` → `framework_behavior_write`, semantic job/result IDs moved from `novel-os-*` to `novelforge-*`, the live `.novel-os/` ignore surface was removed, and namespace hygiene now blocks those legacy machine identifiers from returning. No compatibility aliases were added.
- The 0.8.0 normalization aligns the current machine/version identity instead of maintaining parallel “release” and “implementation” development numbers.
- Documentation governance tracks audience, tier, authority sources, freshness ownership, rewrite policy, lifecycle state, bilingual pairing, local-link integrity, version alignment, and deterministic visual/documentation checks. `studio/` is included in bilingual manifest-coverage QA.

### Active gaps and compatibility notes

- Run Receipt still has Core-owned consumer/read-surface work: stable manifest discoverability, event-schema alignment for `run.receipt_recorded`, and a stable query/projection boundary instead of persistence-internal access. PR #25 deliberately does not expose unsafe Control Plane or Run Receipt reads through the host bridge.
- Existing projects that intentionally pin an older Framework revision remain bound to that revision until explicitly upgraded. Generic Framework development itself follows latest `main` rather than an internal development lock.
- A future stable migration guide must be generated from frozen contracts and the final bundle, not inferred from issue descriptions or intermediate commits.

### Product / publication status

- Studio currently has merged **read-only** Phase 1, Phase 2A, and Phase 2B product slices: observability, Project Hub, Scene workspace, portable host boundary, and Agent Skill delivery are real on `main`.
- These slices do **not** make Studio a write-capable, collaborative, authenticated, or production-hosted application. Generic invoke/write, project mutation, resume, and broader Control Plane reads remain outside the current bridge contract.
- Publication / Typesetting remains an active Core workstream tracked by issue #16. Until official IR/profile/runtime contracts land, EPUB/Web/print publication remains planned/in development rather than shipped.
- Broader MCP registry/management and later write-capable Studio operations remain deferred to their owning workstreams.
- UI, host-bridge, and Agent Skill state never become Canon, Memory, semantic truth, settlement truth, or workflow authority.

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