# Spec 012 · AI-Native Adaptive Production Refoundation

Status: implementation candidate
Scope: Generic NovelForge only
Primary mode: `SYSTEM-IMPROVE`

## 1. Problem

NovelForge needs a stable boundary between **execution truth** and **narrative truth**. Earlier production layers accumulated deterministic helpers around context, Reader evaluation, repair depth, telemetry, learning, planning and simulation. Some protect real authority and durability; others risk freezing literary judgment into code because code is easier to test.

This candidate tests, rather than assumes, the working hypothesis:

> **Code provides capabilities and constraints; models provide intelligence.**
>
> **Deterministic code enforces execution truth; AI agents evaluate narrative truth.**

The goal is not “less Python”. The goal is to keep Python only where objective enforcement is required and remove deterministic mechanisms that pretend to understand literary meaning.

## 2. Current architecture decision

NovelForge adopts a **thin deterministic kernel + model-owned semantic runtime**.

### Deterministic kernel

Owns only mechanically provable behavior such as:

- authority / permission / Project isolation;
- exact artifact identity, hashes and fingerprints;
- provenance and exact-source references;
- session/run/checkpoint persistence;
- before-state / CAS / idempotency / transactions;
- capability and credential boundaries;
- stage visibility and private-state isolation;
- hard resource/context budgets;
- typed envelope validation and receipt binding;
- required semantic execution presence, exact candidate binding and independent-worker provenance.

Its question is: **did the authorized operation actually happen against the correct state?**

### Semantic runtime

Models own work that requires meaning:

- search intent, query formulation, retrieval continuation and stopping;
- narrative relevance and context sufficiency;
- planning depth and uncertainty decisions;
- character motivation, plausible inference and action;
- scene causality and dramatic realization;
- Reader experience;
- semantic hard-rule applicability and violation;
- repair mechanism and repair depth;
- preference interpretation and learning hypotheses.

Its question is: **what does this story/text/context mean, and what should happen next?**

## 3. Current owner map

| Subsystem | Live owner | Decision | Boundary |
|---|---|---|---|
| session / checkpoint / resume | `harness/session_runtime/**` | KEEP | durability, stale-state rejection, capability re-resolution |
| Control Plane / write intent | `harness/control_plane/**` | KEEP | permission, exact action/target/before-state, idempotency |
| context eligibility / stage isolation | `harness/context_inspector.py` | KEEP | mechanical eligibility only; `relevance` is forbidden |
| Context Assembly | `harness/context_assembly.py` | THIN | exact selected refs, stage/fingerprint/private boundary; no literary sufficiency |
| semantic context/search | `context.select` | MIGRATE_TO_AGENT (implemented) | model decides missing evidence, query, relevance, reformulation and stopping |
| hard-budget packing | `harness/memory_tiers.py` | KEEP | whole-item budget enforcement after semantic selection |
| planning commitment authority | `harness/planning_horizon.py` | KEEP / ADAPT | code enforces declared depth/commitment/CAS; Planner decides useful depth |
| character action | `character.action_propose` | MIGRATE_TO_AGENT (implemented) | private state is causal evidence, not prose serialization |
| scene collision | `scene.resolve_actions` | MIGRATE_TO_AGENT (implemented) | compact causal trace, not a deterministic story engine |
| writer-safe realization | `scene.realization_project` | THIN | privacy boundary; no Realization-Sheet serialization requirement |
| Blind Reader | `reader.engagement_audit` | MIGRATE_TO_AGENT (implemented) | reader-visible evidence only; no taxonomy/HF/telemetry priming |
| semantic hard rules | `quality.semantic_rule_audit` | MIGRATE_TO_SEMANTIC_RULE (implemented) | model judges PASS/FAIL/N/A/insufficient evidence |
| Editor repair | `editor.repair_spec` + `quality/repair_policy.py` | MIGRATE_TO_AGENT + THIN | Editor chooses owner/mode; Python only enforces chosen writer-context boundary |
| prose telemetry | `quality/prose_telemetry.py` | OPTIONAL_TOOL | metrics on demand; never literary truth/default Reader context |
| readiness/release | `quality/production_readiness.py`, `production_release.py` | KEEP | exact semantic binding + conjunctive structural receipts only |
| feedback interpretation | `learning.preference_interpret` | MIGRATE_TO_AGENT (implemented) | model interprets meaning/scope candidate |
| durable learning | `learning/learning_store.py`, `promotion_gate.py`, `author_model.py` | KEEP / THIN | persistence/write authority/CAS; model selects relevant active hypotheses |
| HF taxonomy | `quality/taxonomy.json` | MIGRATE_TO_SKILL | diagnostic vocabulary/regression labels, not default Reader checklist |

No second context store, Reader, simulator, release authority or durable preference database is introduced.

## 4. Deterministic Overreach Audit

| Former/current mechanism | Why suspicious | Current disposition |
|---|---|---|
| required literary context class/purpose gates | deciding that a class is semantically required is meaning-dependent | REMOVED from Context Assembly v2; exact higher-authority required refs remain deterministic |
| fixed last-N / similarity threshold as relevance | recency/similarity is not narrative relevance | REJECTED as semantic truth; retrieval primitives may still return candidates |
| Reader quality taxonomy/HF exposure | primes the evaluator and can manufacture checklist findings | REMOVED from production Blind Reader inputs |
| prose telemetry preloaded into Reader/Editor | anchors semantic judgment on mechanical statistics | default-disabled; OPTIONAL_TOOL |
| owner/scope → repair-depth mapping | repair depth is literary judgment | REMOVED; Editor selects `generation_mode` |
| Python “contradicted/unknown means unusable support” | character belief/inference requires semantics | REMOVED; runtime checks only evidence identity/story-time eligibility |
| numeric evidence-count promotion thresholds | evidence sufficiency/stability is semantic | REMOVED; semantic promotion review supplies evidence judgment |
| auto-inject all active Author Model preferences | active authority does not imply current relevance | REMOVED; model/manager explicitly selects active hypothesis IDs |
| structured Reader dimensions that must all be filled | forces observations that may not matter | THIN Reader report + salient evidence only |
| detailed scene/realization JSON slots | risks Character Sheet → Realization Sheet → prose serialization | THINNED to compact interaction/observable trace plus optional evidence |

Remaining deterministic rules must answer an objective execution question. Any new Python condition that asks whether prose, dialogue, motivation, relevance, continuity meaning, Reader experience or planning quality is “good” is presumed architectural regression until justified.

## 5. Rule architecture

### A. Deterministic invariants

Examples: stale fingerprint, wrong Project, unauthorized write, malformed receipt, missing capability, CAS conflict, invalid independent identity, stale semantic result.

### B. Semantic hard rules

Examples: inaccessible character knowledge, unjustified character-integrity break, POV leakage, Canon contradiction, agenda-to-dialogue serialization, Project-declared narrative hard constraints.

Hard means a **confirmed semantic FAIL can block**. It does not mean Python determines the violation.

`quality.semantic_rule_audit` receives the authoritative rule index and authorized evidence, decides applicability itself, and returns `PASS | FAIL | NOT_APPLICABLE | INSUFFICIENT_EVIDENCE` per rule.

### C. Guidelines / craft knowledge

Remain skills, profiles, references and model instructions. They do not become deterministic gates merely because they are useful craft principles.

## 6. Blind Reader != Rule Auditor != Editor

**Blind Reader** reads naturally with reader-visible information. It does not receive author intent, future plan, private character state, full taxonomy, expected HF codes, telemetry, or semantic-rule prompts.

**Semantic Rule Auditor** receives the authoritative hard-rule index and may request/fetch authorized evidence. It performs explicit semantic compliance judgment.

**Editor** integrates Reader, Rule Auditor, Canon/story evidence and Project constraints, then decides mechanism, repair owner, `local_or_bounded_repair | fresh_realization`, and whether incumbent/challenger comparison is needed.

These roles are separate because their information boundaries conflict, not because multi-agent diagrams are desirable.

## 7. Search and context architecture

Search is a capability, not a precomputed literary-context pipeline.

The model decides:

1. what is missing;
2. what to search;
3. the query;
4. whether results are relevant;
5. whether to reformulate/broaden/narrow;
6. what to retain;
7. when evidence is sufficient.

The runtime exposes authorized search/fetch/extract/index primitives, provenance, exact refs, visibility and resource limits. Context Assembly v2 verifies exact selected refs and stage/fingerprint constraints after model selection; it does not score relevance or declare narrative sufficiency.

## 8. Planning, character and realization

Planning commitment authority remains deterministic because committed depth, promoter class, evidence refs, before-state and fingerprints are execution state. **Which depth is useful now remains a Planner decision.** No universal chapter/volume/time horizon is introduced.

Character/scene flow is:

`private state → model action proposal → model scene/world collision → compact observable interaction trace → Writer`

Private state is causal evidence. It is not dialogue/exposition payload. Writer-safe realization remains deliberately thin so it does not become a second Character Sheet.

## 9. Learning / Author Model

Models interpret feedback and propose the narrowest scope/mechanism. Deterministic infrastructure persists evidence and enforces activation authority.

`active` means **durably eligible**, not “relevant to every future task”. Production receives only explicitly selected active hypothesis IDs. User-taste activation requires both explicit write authority and a current bound promotion prerequisite; General Craft promotion remains SYSTEM-IMPROVE-only and requires stronger evidence/eval/version/rollback/CI controls.

## 10. Current research ledger

Research was re-opened against current primary sources during this candidate, not inherited from an old chat.

| Source family | Mechanism | Decision | NovelForge use |
|---|---|---|---|
| Anthropic current agent/context/harness guidance | simple composable agents, iterative context curation, durable handoff/context reset | ADAPT | keep harness stable while model capability evolves; avoid context bloat and stale transcript authority |
| OpenAI Agents SDK + current GPT model guidance | model-driven tool choice, sessions, guardrails, agents-as-tools/handoffs | ADAPT | let model choose semantic tool/search actions inside deterministic guardrails; refresh stale evaluator pins by current eval evidence |
| LangGraph | checkpoints, persistence, interrupts, durable replay | ADAPT | validates Session/Checkpoint/receipt separation; no dependency needed |
| AutoGen | start single-agent, add teams only when collaboration/specialization helps | ADOPT | multi-agent discipline |
| CrewAI Flows / agents | structured state vs autonomous teams | ADAPT | stateful execution ideas; REJECT org-chart agent proliferation |
| PydanticAI | dependency/toolset/capability separation, optional durable runtime | ADAPT | capability-scoped hands; DEFER new durable dependency |
| Google ADK | Session/Event state and tool-using ReAct agents | ADAPT | supports durable session != model context |
| AWS AgentCore | isolated runtime, identity, gateway, memory | ADAPT | brain/hands/session and credential isolation |
| DSPy | declarative LM programs optimized against evals | ADAPT | keep evaluation separate from implementation; REJECT schema inflation as pseudo-rigor |
| ReAct / Self-RAG / Adaptive-RAG | agentic action/retrieval and adaptive retrieve/skip | ADOPT / ADAPT | model-owned retrieval continuation/stopping; REJECT fixed retrieval horizon as truth |
| WriteHERE / DOME | dynamic hierarchical long-form planning | ADAPT | Planner-owned depth and iterative decomposition |
| MAGNET/ATLAS and related character simulation | persona/private state drives actions before prose | ADAPT | preserve causal private-state boundary; REJECT sheet-to-prose serialization |
| Sudowrite / Novelcrafter | explicit story state, selective context, revision history | ADAPT | explicit state/context visibility; REJECT fixed recency as semantic authority |
| current LLM-as-judge / creative-writing eval research | auxiliary-information bias, position bias, imperfect human agreement, value of decomposed checks | ADOPT / ADAPT | Blind Reader isolation, order-swapped pairwise eval, separate decomposed hard-rule audit |
| Rust/Go/WASM/Starlark/Zig/C++/Temporal/DBOS/etc. | alternate runtime/extension stacks | DEFER | no current owner/performance/packaging evidence justifies a dependency/language migration in PR #90 |

## 11. Ablation contract

Substantial semantic simplifications are not accepted because they look cleaner. The same candidate/authority must be compared where possible.

Required families include:

- remote context outside recent horizon;
- irrelevant semantic match rejection;
- autonomous search continuation and stopping;
- Blind Reader agenda-dialogue experience vs taxonomy-primed Reader;
- legitimate formal completeness;
- inaccessible knowledge vs plausible inference;
- dynamic planning profiles;
- character embodiment without agenda serialization;
- holistic vs decomposed hard-rule audit;
- Reader/Editor with vs without preloaded telemetry;
- unauthorized-state and stale-candidate deterministic rejection;
- long-horizon resume with authority revalidation.

`evals/ai_native_ablation_manifest.json` binds the paired semantic ablations. A model-independent manager may validate packets and deterministic invariants, but may not invent semantic results. If no eligible independent model transport exists, semantic outcomes remain `PENDING_MODEL`.

## 12. Security

AI-owned search does not imply unrestricted access. Tools remain capability-scoped; credentials/tokens are never semantic context; external source text cannot redefine runtime authority; private character/creator/Reader boundaries remain explicit; semantic output cannot grant itself write authority; stale or wrong-candidate receipts fail closed.

## 13. Compatibility and rollback

- no consuming Project lock, manuscript, Canon or Settlement mutation;
- no Framework version bump/release/promotion in this candidate;
- additive semantic contracts remain progressively disclosed;
- Context Assembly v2 intentionally removes semantic class/purpose obligations while preserving exact-ref/stage/fingerprint safety;
- legacy callers that relied on removed semantic obligations must move that decision into `context.select`/Manager and pass exact required authoritative refs when mechanically mandatory;
- each refactor slice remains revertible on PR #90; downstream consumers remain pinned to their existing lock.

## 14. Acceptance

`READY_FOR_HUMAN_REVIEW` requires:

1. live owner/docs/manifest synchronization;
2. deterministic self-tests and exact-head CI for candidate-owned surfaces;
3. blind queue + ablation packets without hidden-gold leakage;
4. exact-candidate independent semantic execution for the required semantic cases;
5. security/compatibility review and rollback evidence.

A green workflow that merely records missing model capability is not semantic PASS. Missing independent capability is reported as `PENDING_MODEL`.
