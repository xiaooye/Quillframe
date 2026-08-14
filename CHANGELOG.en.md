# NovelForge Changelog

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
