# Plan 012 · AI-Native Adaptive Production Refoundation

## Goal

Finish the existing PR #90 review unit as a coherent **thin-kernel / model-owned semantic-runtime** candidate. Do not create parallel owners, do not merge/release, and do not mutate downstream Projects.

## Live reconciliation

Live bootstrap for this refoundation is always resolved from the current PR/HEAD, not from the SHAs written in older chat or historical plan text. The rollback checkpoint immediately before this synchronization slice was `b6f13ac97a105221f8ee78d862c4e6f02e4cf9ab`; every later consequential write must re-read PR #90 before-state.

Current owner decisions:

- KEEP Session Runtime, Control Plane, exact identity/fingerprint, CAS, receipts, stage isolation and hard budgets.
- THIN Context Assembly, Writer realization and repair routing to machine-required fields only.
- MIGRATE semantic relevance/search, Reader experience, rule applicability, repair depth, planning quality, character reasoning and feedback interpretation to model contracts.
- OPTIONAL_TOOL prose telemetry.
- MERGE_WITH_EXISTING_OWNER rather than invent second stores/readers/simulators/releases.
- DEFER new languages/runtimes/dependencies until a concrete owner and measurable need exists.

## Phase A · Authority and stale-state cleanup

1. Re-bootstrap PR #90, main base, changed files, workflows and exact Framework authority.
2. Treat PR body/old plan SHAs as historical notes only.
3. Synchronize `HARNESS_MANIFEST.yaml` schema IDs and contract names with live code.
4. Remove stale assertions that Python chooses literary repair depth or semantic context obligations.
5. Keep Framework version `0.8.0`; no release/promotion.

## Phase B · Semantic-role separation

1. Keep `reader.engagement_audit` as the production Blind Reader.
2. Keep `quality.semantic_rule_audit` as a separate hard-rule semantic role.
3. Keep `quality.production_review` as the genuinely independent holistic gate when enabled.
4. Keep `editor.repair_spec` as the semantic repair owner.
5. `quality/repair_policy.py` receives Editor-selected generation mode and enforces only the resulting writer-information boundary.

## Phase C · Agent-owned search/context

1. `context.select` owns missing-information diagnosis, query formation, relevance, reformulation, continuation and stopping.
2. `context_inspector.py` owns eligibility/stage/protected-edit mechanics, never relevance.
3. `context_assembly.py` v2 validates only exact selected refs, exact higher-authority required refs, source fingerprints, stage safety and private-state boundaries.
4. `memory_tiers.py` may pack whole selected blocks under hard budgets; it must not convert priority/top-k into literary truth.
5. Remove documentation that says a deterministic class/purpose obligation proves semantic sufficiency.

## Phase D · Planning / simulation / realization

1. Preserve commitment strength/depth/CAS/fingerprint mechanics in `planning_horizon.py`.
2. Make explicit that the Planner, not the runtime, chooses useful depth/uncertainty.
3. Keep private character state → action → scene collision as semantic work.
4. Keep runtime checks to evidence identity, story-time eligibility, permissions and visibility.
5. Keep writer projection compact; do not re-expand a Realization Sheet.

## Phase E · Learning

1. Semantic `learning.preference_interpret` interprets feedback.
2. LearningStore/Author Model persist evidence/hypotheses under CAS and authority.
3. `active` remains eligibility only; manager/model selects relevant hypothesis IDs.
4. Promotion Gate verifies a bound semantic review plus durable-write prerequisites; no numeric evidence-count literary threshold.

## Phase F · Ablation and regression coverage

Add/retain blind semantic families for:

- remote context outside a recent horizon;
- irrelevant similarity match;
- search continuation;
- search stopping;
- agenda-to-dialogue artificiality without exposing expected HF code;
- legitimate formal completeness;
- inaccessible knowledge and plausible inference;
- dynamic planning profiles;
- character embodiment;
- Reader contamination (unprimed vs taxonomy-primed);
- rule audit (holistic vs decomposed mandatory rules);
- telemetry anchoring (not preloaded vs preloaded);
- deterministic unauthorized-state rejection;
- deterministic stale-candidate rejection;
- long-horizon resume / stale checkpoint authority revalidation.

Pair semantic ablations in `evals/ai_native_ablation_manifest.json`. The ablation manifest must bind the same candidate text/authority across conditions. Deterministic CI validates packet construction; semantic outcomes require a real model worker and remain `PENDING_MODEL` when that capability is absent.

## Phase G · Current evaluator freshness

The independent semantic workflow must not hard-pin a superseded model indefinitely. Current primary-source research identifies the OpenAI `gpt-5.6` alias as the current complex-production baseline, so the workflow should use that alias rather than the older `gpt-5.1` pin. This is an evaluator-infrastructure freshness change, not semantic evidence by itself.

Future model changes must follow the same rule: research current official guidance, run representative evals, and update only with evidence. Model popularity alone is not authority.

## Phase H · Deterministic verification

Run all candidate-owned focused checks, including:

- Python compile;
- context inspector / context assembly;
- semantic router/catalog/reference integrity;
- repair policy, production readiness/release, telemetry;
- promotion gate / Author Model;
- planning horizon;
- bundle/version identity and deterministic double-build where the workflow already owns it;
- blind queue construction and hidden-gold guards;
- exact-candidate receipt/fingerprint/independence validation.

Do not add Python tests that claim to prove prose quality.

## Phase I · CI anti-stall and stale optimization

Adopt the useful execution discipline from the UI completion contract without importing UI scope:

- every poll/build/workflow observation is bounded;
- no `WAITING` state may persist without new evidence;
- if the same workflow remains pending across two observation cycles, inspect jobs/logs rather than sleeping again;
- every consequential write revalidates PR branch, HEAD, base and exact before-state;
- each failed job is classified as candidate-owned, pre-existing/base, external-capability, or transport/configuration;
- retry only after the cause changes; never retry identical failures indefinitely.

## Phase J · Security / compatibility

Verify:

- model can choose searches only inside allowed capability scope;
- source text cannot grant permissions or redefine authority;
- credentials stay outside semantic context;
- Reader/private-character/manager information boundaries remain intact;
- semantic results cannot self-grant Project/Canon/Framework/user-taste authority;
- stale candidate/receipt/session state fails closed;
- no downstream lock/manuscript/Canon/Settlement changes occur.

## Exact CI classification policy

Pre-existing Product/Godot or Studio failures are not evidence that this candidate failed. They must still be reported, but SYSTEM-IMPROVE only repairs them if they directly block this architecture work. Candidate-owned deterministic workflows must be green at the final HEAD.

A workflow that records `PENDING_MODEL` is functioning correctly but does **not** provide semantic PASS.

## Rollback

- rollback base for this synchronization slice: `b6f13ac97a105221f8ee78d862c4e6f02e4cf9ab`;
- each documentation/authority/eval slice lands as a reviewable commit;
- no force-push/history rewrite;
- downstream consumers remain pinned, so reverting PR #90 cannot change their live Framework authority.

## Stop condition

Normal completion requires all executable deterministic, documentation, ablation-packet, CI, security and compatibility work to be complete **and** required independent semantic evidence to exist for the exact final candidate. If independent model capability is unavailable, complete everything else and stop only with the explicit external blocker `PENDING_MODEL`.
