# Plan 012 · Adaptive Production Learning and Realization Boundary

## Goal

Connect existing NovelForge primitives into a stateful co-creative production loop without creating duplicate subsystems or weakening authority boundaries.

## Live candidate reconciliation · 2026-08-16

This plan was re-audited against PR #90 at exact pre-write HEAD `0a1679b315366c4a42bda17eff9dffd04ad76db0`. The branch already contains a partial adaptive-production candidate, so this work extends existing owners rather than creating parallel stores, registries, routers, simulators, or release authorities.

| Existing mechanism | Current owner / files | Coverage before stabilization | Decision | Reason / migration risk |
|---|---|---|---|---|
| planning commitment horizon | `harness/planning_horizon.py`, schema, dedicated CI/evals | deterministic + independent semantic workflow PASS on pre-write HEAD | KEEP | mechanism is bounded, non-authoritative and already proven; do not entangle later runtime work with its semantics |
| durable preference evidence / hypotheses | `learning/learning_store.py` | existing self-test + normal contracts CI | KEEP | already owns durable learning state; a second Author Model database would create duplicate truth |
| promotion prerequisites | `learning/promotion_gate.py` | existing self-test + normal contracts CI | KEEP + BIND | the new Author Model must consume this prerequisite result before durable user-taste activation; a caller boolean alone is insufficient |
| Author Model projection | `learning/author_model.py` | local self-test only; not yet normal-CI/manifest integrated | REFACTOR | preserve Learning Store ownership, but close the activation-authority gap and register the runtime |
| context stage isolation | `harness/context_inspector.py` | existing self-test, but manifest schema metadata drifted | EXTEND | current owner already separates stage visibility; keep semantic relevance outside deterministic code |
| required context assembly | `harness/context_assembly.py` | local self-test only | EXTEND | typed satisfaction receipt belongs beside existing context owner; no second relevance engine |
| character / scene simulation | `character.action_propose`, `scene.resolve_actions` contracts | registered semantic contracts | KEEP | existing action→collision boundary is the correct simulation owner; do not build a parallel simulator |
| writer-safe realization | `scene.realization_project` in `production-loop.json` | registered contract; typed CI fixtures incomplete | EXTEND | projection is the needed privacy boundary between private simulation state and prose |
| Reader / Editor loop | `reader.production_audit`, `editor.repair_spec` | registered contracts; typed CI fixtures incomplete | EXTEND | reuse existing quality/readiness/compare owners instead of proliferating literary agents |
| structural release composition | `quality/production_release.py` + existing `production_readiness.py` | local self-test only | EXTEND | structural receipts are conjunctive evidence only; no alternate release authority |
| prose telemetry | `quality/prose_telemetry.py` | local self-test only | KEEP + INTEGRATE | signals-only design is compatible; it must remain non-verdict-bearing |
| HF-30 taxonomy | `quality/taxonomy.json` | registry entry exists; Surface docs + semantic regression family missing | EXTEND | synchronize human contract and add semantic counterexamples; never replace semantics with lexical heuristics |
| write-intent guard | `harness/control_plane/write_intent_guard.py` | local self-test only | EXTEND | belongs in existing Control Plane; exact action/resource/target/before-state match remains non-authoritative |
| semantic registry integrity | `scripts/semantic_reference_integrity.py` | local tool only | EXTEND | add normal-CI coverage rather than creating a new registry |

### Candidate-owned failures found during reconciliation

- Spec 012 bilingual docs were not registered in `docs/documentation_manifest.json`.
- The four new `production-loop` contracts were registered, but generic semantic-contract workflow fixtures were not migrated with the registry.
- HF-30 existed in `quality/taxonomy.json` without the canonical bilingual Surface heading/name.
- `HARNESS_MANIFEST.yaml` did not yet register the new Author Model / context assembly / write guard / telemetry / structural release runtimes, and still declared the old Context Inspector schema id.
- The generic eval manifest did not yet contain the required HF-30 capability/counterexample family.
- `learning/author_model.py` allowed `durable_user_taste_write_authorized=true` to activate a user-taste hypothesis without binding the existing `promotion_gate` prerequisite result.

Pre-existing Product/Godot documentation and Studio/Product CI debt are tracked separately and are not evidence against this candidate.

## Branch / PR architecture decision

PR #90 remains the only active general/agent branch and must first become a coherent planning + adaptive-production review unit. Repository branch-budget guidance prefers at most one active general/agent branch; the Master execution prompt also forbids hiding a future polyglot rewrite inside an unrelated planning PR. Therefore:

1. **Current review unit:** stabilize only the adaptive-production work that is already present on PR #90, including authority, registry, docs, deterministic CI, HF-30 semantic evidence, and rollback completeness.
2. **No history rewrite / no force push / no merge:** preserve the current nine-commit history and use `0a1679b3…` as the rollback checkpoint for this stabilization slice.
3. **Polyglot implementation:** DEFER from this PR. A Rust/Go/WASM/Starlark implementation requires a separate review unit after PR #90 is closed/merged/superseded or an explicit branch-budget exception exists. The architecture research may be recorded now; production source in new languages must not be added decoratively to PR #90.
4. **No second Core:** any later polyglot slice must begin with a fingerprint/canonicalization authority audit and golden vectors from the existing Python behavior before moving an implementation boundary.

This is a reviewability constraint, not a rejection of the long-term polyglot direction.

## Research adoption snapshot

Primary-source revalidation for this stabilization produced the following mechanism decisions:

- **ADAPT — LangGraph / OpenAI Agents SDK / AutoGen / CrewAI / PydanticAI:** retain explicit session/run state, typed handoffs, bounded specialist context, interrupts/resume, and inspectable graph state as runtime mechanisms; reject provider/session memory as Project authority and reject multi-agent role proliferation.
- **ADAPT — Temporal / Dapr durable execution:** retain replay-aware checkpoint thinking, deterministic workflow-side decisions, idempotent side-effect boundaries, typed failure/retry classes, and upgrade caution; do not introduce Temporal or Dapr as a NovelForge dependency for this candidate because existing Session Runtime + Control Plane already own these semantics.
- **ADAPT — SQLite:** formalize the existing embedded WAL-backed Learning/Control Plane stores and their migration/backup semantics; do not create a second operational database. WAL remains a same-host substrate, not a distributed authority plane.
- **ADAPT — Sudowrite / Novelcrafter:** explicit editable project state, selective AI context, prompt/context visibility, revision history, and project/series scoping validate NovelForge's explicit Project state + sparse Context Assembly direction. NovelForge keeps stronger authority separation between evidence, derived state and Canon.
- **ADAPT — MAGNET / StoryBox / StoryWriter / Generative Agents:** preserve `private state → action proposal → shared-world collision → event trajectory → writer-safe realization`; keep dynamic history selection and bounded planning. Reject `character sheet → prose/dialogue paraphrase` and reject simulation state as automatic story truth.
- **DEFER — Rust / Go / WASM / Starlark / Zig / C/C++ production ownership in PR #90:** no current performance or packaging evidence justifies crossing the reviewability boundary. Rust remains the preferred future deterministic-kernel candidate only after existing fingerprint semantics and golden vectors are mapped. Go remains a future execution-fabric candidate only if it does not duplicate the Python Control Plane. Starlark remains a future restricted extension candidate under deny-by-default capabilities. Zig/C/C++ remain interop/portability-only candidates with no current production owner.

## Workstream 1 · Author Model and review feedback

1. Add a deterministic Author Model projection runtime backed by the existing Learning Store.
2. Add a semantic `learning.preference_interpret` contract for bounded interpretation of explicit review feedback.
3. Separate observation, hypothesis, activation, and production projection.
4. Support contradiction/supersession and scope-aware activation rules.
5. Connect existing `feedback.observed` Author Steering to the review-learning lifecycle by contract/documentation, not by automatic mode switching.

## Workstream 2 · Adaptive Context Assembly

1. Extend context stages so private simulation state can be visible to simulation but not to prose generation.
2. Add typed required-context obligations and deterministic satisfaction receipts.
3. Add a context-assembly runtime that validates selected IDs against stage, authority, invalidation state, required class/purpose, and provenance/fingerprint requirements.
4. Preserve semantic relevance ownership in `context.select`.
5. Keep Corpus retrieval conditional; benchmarks are one possible context class, not a universal pipeline stage.

## Workstream 3 · Simulation-before-Prose

1. Reuse `character.action_propose` and `scene.resolve_actions`.
2. Add a semantic `scene.realization_project` contract that converts private simulation evidence into a writer-safe interaction/event projection.
3. Block raw private-character/simulation classes from `writer_pre_draft` by default.
4. Document the interface: private state controls behavior; realization projection controls writer-visible event/dialogue opportunity.

## Workstream 4 · Reader → Editor closed loop

1. Add a structured Reader production audit focused on actual reading experience, profile fit, paragraph rhythm and dialogue realization without exposing creator-private state.
2. Add an `editor.repair_spec` contract that translates Reader evidence into preserve/change priorities and owning repair layers.
3. Reuse `reader.compare` / `quality.compare` for material incumbent/challenger comparison.
4. Extend Production Readiness only for structural receipts that deterministic runtime can actually prove; do not create one deterministic gate per literary dimension.

## Workstream 5 · Quality mechanisms

1. Register HF-30: Agenda-to-Dialogue Leakage / Character-Sheet-to-Dialogue Serialization.
2. Add profile-sensitive prose telemetry as signals only.
3. Add semantic counterexamples for formal-completeness dialogue and legitimate selective short paragraphs.
4. Extend surface/character/reader contracts so the architecture and backstop diagnosis agree.

## Workstream 6 · Safety and integrity

1. Add a write-intent/action guard for resource/operation/target mismatch.
2. Fix stale `model_contracts.json` references and add deterministic semantic-reference integrity checking.
3. Improve semantic-bridge failure classification where Framework code owns the distinction; report repository-setting/configuration owners separately.

## Workstream 7 · Integration and verification

1. Register new tools/contracts in `HARNESS_MANIFEST.yaml` and model contract catalog.
2. Update Harness/Orchestration/production/context/adaptive-learning docs in both languages.
3. Add deterministic self-tests to reusable release contracts CI.
4. Add generic semantic fixtures without hidden expected labels in reviewer queues.
5. Run exact-head CI; distinguish candidate failures from pre-existing repository debt.
6. Obtain independent semantic capability/counterexample evidence for the exact candidate fingerprint when an eligible independent transport is available.
7. Keep PR Draft until evidence is complete enough for human review; no merge, release, or downstream lock migration in this run.

## Compatibility strategy

Prefer additive schemas and optional policy requirements. Existing projects that do not declare new required context/structural receipts remain compatible. Material release identity/version changes are decided only after exact diff and verification.

## Rollback

Each workstream should land in a coherent commit. Any workstream can be reverted independently. The downstream consumer remains pinned to NovelForge 0.8.0 throughout this run, so candidate rollback never changes the book's runtime authority.