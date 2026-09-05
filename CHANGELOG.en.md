# Quillframe Changelog

## Unreleased · 1.0.0-dev.0 ultra-long book setup and production closure

- Added a source-fingerprint-bound Book Setup proposal/author-approval lifecycle. Projects targeting at least five million characters must provide a fixed ending, complete volume plots, cross-volume arcs, one climax per volume, character-charm proof beats, progression ladders, rolling-plan policy, and explicit capacity evidence. Character, relationship, and world assets gain no authority before approval.
- Added idempotent Host Bridge creation for volumes, units, and chapters, with a database invariant of one manuscript document per chapter. Setup approval binds the exact active `DESIGN-BOOK` plan; interrupted approval resumes only the same request and reports partial completion truthfully.
- Restored model-owned semantic Context selection, character simulation, and scene resolution for DRAFT/REVISE. Approved character/relationship decision models enter only private pre-prose stages; the Surface Writer receives a bounded, fingerprint-bound Director Note without private reasoning. Only the assembled chapter minimum length is checked deterministically before release, with no prose maximum or mechanical per-scene quota.
- Narrative settlement continues through compact typed deltas and retains only the latest four fully verified snapshots. Production release, author acceptance, and settlement replay the same receipt after response loss; Studio can restore acceptance/settlement state and explicitly choose a production model from an enabled discovered catalog. Automatic mode is described honestly as Core's catalog default.
- Added Project schema fragment 025. This development clean break does not migrate existing databases. Stop runtimes and restore parent commit `638afcf24e6bfc27e26c4906186b2175f02b5bb1` to roll back; Projects created with fragment 025 must be recreated rather than opened by the older Core.
- Model endpoints now preserve explicit `v1`/`v4`/`v4.1` API bases and add the default `v1` only when no version segment is present, preventing model discovery or inference from silently rewriting provider paths. OpenAI Chat production requests explicitly require `json_object` responses and use standard SSE streaming for long reasoning responses. For `glm-5.3`/`glm-5.3-flash`, whose published contract requires thinking, Quillframe sends `reasoning_effort=low` instead of inheriting the provider's `max` default. Core assembles only `delta.content`, never `reasoning_content`, and accepts at most one outer JSON fence, a one-to-three-backtick trailing fragment, or a provider suffix of at most 2,048 bytes containing neither a second JSON value nor non-whitespace control characters. Such suffixes never enter the typed result. `raw_content` is treated as redundant only when byte-identical to `manuscript`, empty, or null. Beyond those cases, `answer` may be isolated as Provider envelope metadata only when the manuscript is at least 512 bytes and the single-line status note is at most 256 bytes and shorter than one eighth of the manuscript; every other non-empty difference remains rejected. When a provider returns plain raw text for the single-field Surface artifact, Core may deterministically wrap exact bytes only when they do not begin as JSON or a fence, contain no control characters or JSON-escape fragments, and stay at or below 512 KiB; mixed escaping and truncated JSON remain rejected. `chapter_id`/`scene_id` are removed as echoes only when they exactly match the frozen target; provider metadata is isolated only when it stays within eight top-level fields, 2 KiB, and bounded nested strings/collections. Differing prose or identity and oversized metadata remain rejected. Per-scene length targets have been removed; the hard minimum applies only to the assembled chapter so mechanical averaging cannot override scene rhythm. If Tracking returns `character_snapshot_updates` as character IDs, Core mechanically projects snapshots only from matching character state deltas in the same result; missing states or duplicate IDs still fail without semantic invention. Production calls use the documented 180-second deadline, character simulation is bounded to 3,000 tokens and action/scene fields paraphrase quotations without quote marks so providers cannot insert unescaped double quotes into JSON; an extra empty `action_note` is isolated as a semantically empty provider field, while non-empty values and every other unknown field remain rejected; scene resolution and per-scene prose receive at least 8,000 tokens so provider reasoning tokens cannot truncate the typed artifact or manuscript. When the Corpus or preference candidate set is empty, Core freezes a verifiable empty-selection receipt instead of spending a semantic call on nonexistent candidates; non-empty sets remain model-selected. Context Query may likewise return zero archive queries when the frozen plan and exact repair evidence are already sufficient, rather than inventing search work for a local edit. Multi-hop bounded-repair lineage now reuses the live Surface normalizer when verifying the original scene evidence, so an already accepted bounded Provider envelope is not rejected during lineage validation.
- Fixed the Surface-rule wiring gap exposed by the live sequential canary. New runs freeze positive Framework Writer guidance, complete `HF-01..HF-30`, the registered semantic rubric, and project guidance materialized through native handles or explicitly supplied from approved prose sources and verified against content fingerprints. Writer receives only the positive projection; a dedicated Surface Auditor must try to falsify release readiness and return one exact-evidence assessment per rule. It explicitly applies cross-paragraph cluster and deletion tests to body signals, process steps, agenda-shaped dialogue, micro-actions, metaphors, and explanations instead of excusing aggregate repetition because each instance has a plausible local function. PASS may omit an example; when a PASS citation is not byte-exact candidate text, Core drops only that unsupported citation while retaining the complete coverage report. FAIL always requires byte-exact evidence. If a complete judgment has an abbreviated or inexact FAIL citation, one evidence-only repair may run while Core freezes every identity, decision, rule status, report, and repair scope; any judgment change is rejected. A provider-echoed `judgment_fingerprint` is isolated only when it exactly matches the frozen value. Revision diagnosis resolves the exact result fingerprint within the semantic mechanism and its controlled repair-stage prefix, preventing a base stage name from being paired with the evidence-repair receipt. Missing coverage, insufficient evidence, or confirmed failure blocks a v2 release. Writer no longer receives duplicate plan-lock/chapter-plan/standalone-scene payloads. An assembled chapter below its minimum now freezes the manuscript and a deterministic length diagnosis before entering a traceable `failed_gate`, rather than leaving the run in `executing`; Blind Reader no longer receives Reader Pressure. REVISE merges rather than replaces inherited rules. If every bounded repair target is a unique byte-exact window but the model returns them out of manuscript order, Core mechanically sorts by source position; missing or repeated windows still fail. For `fresh_realization`, any incumbent excerpt returned by Editor—including null—is replaced with a non-prose sentinel so rejected prose windows never reach Fresh Writer. Every revised candidate reruns the whole-candidate audit. Review projection reports actual typed gate decisions instead of synthesizing PASS from receipt existence. Legacy v1 releases remain readable but do not claim the new audit.
- Per-scene Surface requests no longer repeat the full author instruction, chapter-wide `must_happen` list, request-level rule material, or non-final chapter debt, preventing each scene from reenacting the whole chapter. The final scene still receives the exact stop point and end debt, while every scene retains prohibitions, time anchors, approved project guidance, and its frozen scene contract. When a Surface object contains unescaped newline, carriage-return, or tab characters only inside JSON strings, Core may escape only those controls after proving the complete response is one exact object, then apply the original typed validation. If a provider emits raw prose followed by a complete `{manuscript}` object containing byte-identical prose, Core isolates the duplicate prefix and retains one typed value; any differing prefix still fails. Two narrowly observed Repair Editor key-quoting defects are normalized only when the entire payload remains one exact object and the resulting typed repair contract validates. Bounded replacement arrays may be reordered only by a complete set of unique exact source identities; explicit `无需修改` no-op targets become preserve boundaries, while missing or duplicated real windows still fail. A non-failing Surface assessment's meaningless repair scope is normalized to null without changing its judgment. Trailing `User`/`Assistant` content, a second JSON value, truncated objects, and other controls remain rejected.
- Deterministic gates prove contracts, transactions, isolation, and recovery only. The first sequential canary's prior literary scores are withdrawn. The post-fix canary proves that CH002's HF-18/HF-25 cluster is blocked by real gates, while author-side review still overturned CH001's internal PASS. Single-model review recall, genuinely independent review evidence, and author confirmation remain pending.

## Unreleased · web-novel Corpus analysis v2

- Replaced the current flat ten-axis Corpus dispatch contract with a six-domain, 26-dimension web-novel hierarchy covering reader contract, plot progression, emotion/payoff, character/relationship, scene delivery, and Chinese language rhythm.
- Added closed v2 observation, cross-work candidate, source-free mechanism catalog, evidence-request, and one-to-four-card Writer projection contracts. Raw anchors and source identity remain forbidden.
- Registered five v2 semantic contracts and retired the five v1 style-axis contracts from current dispatch. Completed V5 artifacts remain historical and cannot resume or support v2 promotion.
- The v2 append-only runner, public atlas, rebuilt candidate, and live literary A/B remain pending; no quality uplift is claimed by this structural change.

## Unreleased · 1.0.0-dev.0 constrained simulation responses

- Character action and scene resolution use an explicit native JSON shape containing only the original contract's required fields. Semantic findings and repair routes remain model judgments; original contracts and gates are unchanged.
- An optional, fingerprint-bound `AgentJob.output_schema` reaches OpenAI Chat Completions / Responses and Codex CLI `--output-schema`. Unsupported formats stop explicitly, without probes, fallback or retries. The current Anthropic codec does not implement this profile.
- The CLI ledger preserves the exact schema, output bytes and validation outcome. Malformed, duplicate-key, truncated or refused responses cannot become completed constrained jobs; they are not repaired in place.
- Deterministic fixtures cover transport, failure preservation and unchanged unconstrained fingerprints. These checks do not claim live model or production-chain acceptance.
- Development change only; no Project schema migration. Stop executors before rollback to `b43aaeeb7ab00baab8261f22f7731c59b7853f08`, retain evidence, and do not resume newly constrained calls under the older code.

## Unreleased · 1.0.0-dev.0 internal candidate repair

Studio can register a `REVISE` from an exact, private qualification failure. Core freezes the source and confirmed diagnostics, inherits the original goals and selected preferences, executes registered Editor FIX + PRESERVE and exact-text comparison, and keeps independent review, author acceptance and settlement separate.

- A comparison-losing repair cannot become the next incumbent. Missing or changed ancestor evidence blocks continuation before model execution.
- `quality.compare` now requires both exact candidate texts, including in its CLI text-file arguments. Callers must update together with the contract pack; fingerprints alone are not semantic evidence.
- Deterministic regression fixtures cover source tampering, request inheritance, private draft isolation, comparison failure, budget exhaustion and interrupted execution. They are not evidence that a real manuscript passed review.
- This is a development change, not a published release. No Project schema migration is introduced. Rollback uses the parent commit `d3f1706ff90f8d68621644576a74f4830c8421fa` after stopping executors; preserve run evidence and do not resume new repair runs under older code.

## 0.9.1 · Novel-native host boundary

Quillframe v0.9.1 narrows the product boundary to a novel-contract kernel: **the host runs the agent; Quillframe governs the novel**. Codex/Claude native reviewer adapters consume one exact frozen packet, while Project mapping, bounded Context, candidate visibility, independent review, and Acceptance/Settlement remain Core contracts.

### Included

- Native Codex/Claude reviewer lifecycle hooks with trusted parent/child session separation, reviewer tool denial, exact packet/nonce binding, lease fencing, consume-once evidence, and crash recovery.
- Deterministic mapped-Project projection preview/apply/status/preflight with source fingerprints, transactional CAS, rebuildable SQLite projection state, stage-bounded Context, and zero-model preflight.
- Paired Novel-Native Host Boundary documentation and explicit novelist-facing, internal/ops, and privileged author surfaces.
- v0.9.1 version identity across Framework, CLI, Project SDK, MCP metadata, Host Bridge, Studio, site, and Tauri packaging.

### Known limits

- The embedded Agent/Model Runtime remains an optional/reference implementation; native hosts own generic session, model/tool, sandbox, and subagent execution.
- Acceptance and Settlement remain explicit author-controlled operations and are not exposed as ordinary agent authority.
- Full hosted multi-user, broad Studio redesign, complete benchmark corpus, plugin ecosystem, cloud deployment, and full typesetting remain post-v0.9.1 backlog.

### Release evidence

The v0.9.1 release must be bound to one exact main commit, deterministic Framework bundle fingerprint, CI result, and downloadable checksum manifest. A local build or pending review is not a published release.

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
- PR #27 made Context grounding story-order-aware and question-specific: future/incompatible evidence fails closed, including pinned evidence, and hard-budget drops can leave grounding explicitly incomplete rather than silently under-supported.
- PR #28 separated character epistemic status from acquisition mode and bound proposed character actions to story-ordered, character-visible evidence; future/unknown/invalid evidence cannot be used as positive support merely because the Framework stores it.
- PR #29 strengthened long-horizon reconciliation with story-ordered evidence, complete requirement coverage, explicit uncertainty, and separation between shared relationship state and per-character perceptions.
- PR #31 added `novelforge_production_readiness_v1`, a deterministic same-candidate-fingerprint conjunction gate for Surface, Reader Engagement, required Continuity, and required independent semantic review. Missing/pending/failing required gates block review readiness; `RG-15` SAFE-BUT-FLAT cannot pass Reader Engagement; no numeric literary-score aggregation is introduced.
- PR #31 also added the minimum deterministic Publication core: manifest-discoverable `novelforge_publication_ir_v1`, `publication/compiler.py`, exact Accepted-text fingerprint preservation, and `clean_text`, `web_reflow`, `print_book`, and `epub3` build profiles. Publication output remains derived/non-Canon. EPUB targets W3C EPUB 3.3; internal validation is deterministic, while release conformance requires an explicitly supplied external EPUBCheck command.
- PR #32 upgraded Story Loom to `novelforge_brand_tokens_v2` and merged the WeiUI foundation contract. `assets/brand/weiui.integration.json` pins `xiaooye/weiui` at exact commit `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`, allows only `@weiui/tokens` + `@weiui/css`, forbids `@weiui/react` / `@weiui/headless` as Studio runtime dependencies, and requires zero WeiUI runtime JavaScript. `assets/brand/story-loom.weiui.css` supplies the `wui-theme` Story Loom layer without forking WeiUI selectors.
- PR #32 also made mobile/i18n/accessibility/runtime-overhead expectations machine-checkable: mobile-first responsive rules, 44px minimum touch targets, `en-US` + `zh-CN`, logical properties, reduced motion, no idle decorative animation, no default polling, and deterministic light/dark contrast checks are enforced by `scripts/design_system_quality.py` and CI.
- The selected Phase 2C application framework is **SolidJS + TypeScript + Vite + `@solidjs/router`**, consuming WeiUI only as a zero-JS CSS/token foundation. Local Web remains first-class and preferred for minimum incremental runtime overhead; Tauri remains an optional/installable desktop host rather than the center of product architecture.
- The 0.8.0 normalization aligns the current machine/version identity instead of maintaining parallel “release” and “implementation” development numbers.
- Documentation governance tracks audience, tier, authority sources, freshness ownership, rewrite policy, lifecycle state, bilingual pairing, local-link integrity, version alignment, and deterministic visual/documentation checks. `studio/` is included in bilingual manifest-coverage QA.

### Active gaps and compatibility notes

- Run Receipt still has Core-owned consumer/read-surface work: stable manifest discoverability, event-schema alignment for `run.receipt_recorded`, and a stable query/projection boundary instead of persistence-internal access. PR #25 deliberately does not expose unsafe Control Plane or Run Receipt reads through the host bridge.
- The Publication core is real, but broader Issue #16 scope remains open: richer semantic structure/profile contracts, print-PDF via a paged-media engine, broader typesetting controls, visual-regression hooks, and Studio publication preview/authoring are not implied by the minimum compiler.
- Story Loom/WeiUI foundation integration is now real, but the Phase 2C SolidJS application itself is not implied by those token/CSS artifacts. App-shell code, route implementation, host lifecycle, and measured idle CPU/RAM still need their own implementation evidence.
- Existing projects that intentionally pin an older Framework revision remain bound to that revision until explicitly upgraded. Generic Framework development itself follows latest `main` rather than an internal development lock.
- A future stable migration guide must be generated from frozen contracts and the final bundle, not inferred from issue descriptions or intermediate commits.

### Product / publication status

- Studio currently has merged **read-only** Phase 1, Phase 2A, and Phase 2B product slices: observability, Project Hub, Scene workspace, portable host boundary, and Agent Skill delivery are real on `main`.
- Story Loom v2 + the exact-pinned zero-JS WeiUI CSS/token foundation are also real on `main`. This is a product-foundation implementation, not a completed Studio app.
- Phase 2C is directed toward **SolidJS + TypeScript + Vite + `@solidjs/router`**. `@weiui/react` is explicitly not a planned runtime dependency. Tauri remains an optional installable host; the Local Web surface remains first-class.
- These Studio slices do **not** make Studio a write-capable, collaborative, authenticated, or production-hosted application. Generic invoke/write, project mutation, resume, and broader Control Plane reads remain outside the current bridge contract.
- Publication now has a minimum deterministic Core implementation: exact-text Publication IR plus clean-text, Web HTML, print-oriented HTML/CSS, and EPUB 3.3 outputs. This does **not** mean the full Typesetting Toolkit or Studio Publish experience is complete; Issue #16 remains open for the broader scope.
- Broader MCP registry/management and later write-capable Studio operations remain deferred to their owning workstreams.
- UI, host-bridge, Agent Skill, production-readiness receipts, and publication outputs never become Canon, Memory, semantic truth, settlement truth, or workflow authority merely by existing.

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
