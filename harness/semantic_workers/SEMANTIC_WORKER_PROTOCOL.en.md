# Semantic Worker Protocol · Bounded model judgment with exact identity and no hidden authority

<p><kbd>TIER C · CONTRACT</kbd>&nbsp;&nbsp;<kbd>MODEL-READABLE CONTRACT</kbd>&nbsp;&nbsp;<kbd>FINGERPRINT-BOUND</kbd>&nbsp;&nbsp;<kbd>NO REVIEWER SHOPPING</kbd></p>

Semantic work is where NovelForge deliberately uses a model or human to make a judgment that deterministic rules cannot honestly make. The protocol freezes the semantic question, limits what the worker sees, defines what result may be returned, and binds that result to an exact fingerprint before the owning workflow can consume it.

> **Core invariant ✦** The model owns semantic interpretation. Deterministic infrastructure owns identity, permissions, fingerprints, typed validation, and logical consumption. Neither side silently acquires the other's authority.

## 01 · Generic semantic boundary

```text
frozen subject
→ model contract / rubric
→ bounded input + permissions
→ semantic fingerprint
→ semantic invocation / handoff
→ typed result
→ deterministic binding validation
→ named gate consumes once
```

For a mandatory independent gate, the invocation/session executing the judgment must also satisfy the required independence contract.

## 02 · Model contract catalog and packs

Current semantic behavior is indexed by [`model_contract_catalog.json`](model_contract_catalog.json) and defined in progressively disclosed contract packs, not scattered across dedicated Python “critic engines.”

A model contract defines:

- semantic kind/purpose;
- forbidden input keys or leakage constraints;
- rubric;
- output JSON schema/contract;
- permissions;
- allowed durable result scope;
- whether the contract itself requires an independent invocation.

Examples may include reader reaction/comparison, character integrity, revision diagnosis, reader expectations, narrative-state interpretation, memory consolidation, corpus mechanism analysis, and learning eval judgment.

Adding a semantic capability should normally start by asking whether it belongs in an existing contract pack before adding new specialized runtime code.

## 03 · Semantic job identity

A semantic job should identify:

```yaml
job_id:
contract_or_kind:
subject_id:
created_at:
input_fingerprint:
input:
rubric:
output_contract:
permissions:
provenance:
execution:
```

The semantic question is bound by the subject, bounded input, rubric, and output contract—not by whichever provider happens to execute it.

## 04 · Semantic fingerprint

The semantic fingerprint represents the exact judgment being requested.

Conceptually:

```text
contract/kind
+ subject identity
+ bounded semantic input
+ rubric
+ output contract
= semantic fingerprint
```

Transport/session/attempt lineage is execution metadata rather than semantic identity.

Therefore:

- infrastructure retry with the unchanged frozen question may preserve the fingerprint;
- changing candidate input, relevant context, rubric, or output contract creates a new fingerprint;
- a materially changed artifact normally requires a fresh independent reviewer session when the gate is independent.

## 05 · Bounded context

The worker receives only what the declared judgment needs.

Common exclusions include:

- hidden expected verdict / gold label;
- prior reviewer verdicts when they would bias the current judgment;
- writer private reasoning / chain-of-thought;
- manager scratchpad;
- unrelated project state;
- regression answer keys;
- full raw corpus text when rights-safe bounded evidence is the intended contract;
- future-plan data that would leak into a current-state judgment.

Context minimization is both a quality mechanism and an authority mechanism.

## 06 · Blindness for independent review

An independent reviewer should not be told what answer the manager expects.

A blind packet may contain:

- frozen candidate/artifact;
- bounded current-state/context evidence needed by the rubric;
- rubric and output contract;
- exact fingerprint/job identity;
- provenance sufficient to validate execution.

It should not contain “expected verdict,” hidden regression gold, earlier reviewer outcomes, or instructions designed to push the reviewer toward PASS.

## 07 · Permissions

A semantic worker has no implicit permission to:

- write Canon;
- settle project state;
- change project plans unless the mode separately authorizes that write;
- promote Framework behavior;
- overwrite durable user taste;
- grant itself new capabilities;
- change the meaning of its output contract.

Permissions should explicitly describe the maximum result scope, for example:

`diagnostic_observation | revision_proposal | derived_memory_proposal | learning_observation | eval_observation`

The model result may recommend a change. Recommendation is not mutation.

## 08 · Typed result

A result should repeat enough identity to prove what it is answering:

- job/subject identity;
- semantic fingerprint;
- status/judgment fields required by the output contract;
- evidence / codes / findings / confidence as applicable;
- truthful model/provider/worker provenance;
- execution lineage when required;
- errors when the worker could not complete the judgment.

Private chain-of-thought is not requested, transported, or persisted as part of the contract.

A worker may provide concise evidence or explanation fields required for auditability without exposing private reasoning traces.

## 09 · Deterministic validation

Before consumption, deterministic infrastructure verifies what it can prove:

- job/result schema;
- exact semantic fingerprint match;
- subject/job identity match;
- permission boundary;
- required provenance/lineage;
- output contract fields/types/enums;
- forbidden leakage checks where applicable;
- consume-once identity.

A semantically plausible result with the wrong fingerprint is invalid.

## 10 · Independence

When the workflow requires independent semantic review, independence means a genuinely separate eligible invocation/session or human identity—not “the manager adopts a critic persona.”

Eligible implementations may include:

- separate local-agent invocation;
- isolated provider API call;
- MCP/Control Plane worker;
- GitHub/service worker;
- separate peer chat;
- isolated local-model invocation;
- human reviewer.

The same provider or CLI family can be used if the actual invocation/session identity and context are separate.

## 11 · Internal semantics versus independent gates

Not every semantic contract is an independent gate.

Internal semantic jobs may support:

- scene/character reasoning;
- reader diagnostics;
- revision diagnosis;
- context/memory consolidation;
- research/corpus interpretation.

These can be model-smart while still belonging to the manager's workflow.

A mandatory independent gate is a stronger execution requirement layered on top of semantic judgment. Do not conflate “a different prompt/persona” with independence.

## 12 · Retry semantics

Distinguish three cases:

### Infrastructure failure

Transport crash, unavailable adapter, timeout, lease expiry, or malformed delivery with the semantic question unchanged.

→ checkpoint / retry or fallback to another eligible transport.

### Invalid result

Wrong fingerprint, wrong schema, missing provenance, forbidden leakage, or incompatible output.

→ reject result / repair transport or worker invocation.

### Valid semantic reject/fail

The reviewer completed the correct judgment and rejected the artifact.

→ consume the judgment and route repair to Story / Character / Reader / Surface / Continuity / other owning mechanism.

Never turn case three into case one simply because PASS was preferred.

## 13 · Reviewer shopping prohibition

A valid semantic rejection is evidence.

Do not:

- keep changing reviewer until one passes the same frozen candidate;
- reveal earlier rejections to a fresh blind reviewer in order to steer them;
- change rubric after seeing an unfavorable result without acknowledging a new semantic question/fingerprint;
- call a same-session self-review “independent.”

A repaired artifact may legitimately receive a new fingerprint and a fresh review.

## 14 · Canon / learning / framework boundary

Semantic results may influence planning, repair, learning evidence, or user decisions. They do not become durable authority by themselves.

```text
semantic judgment
→ validated observation / proposal
→ owning workflow gate
→ explicit authority / acceptance / promotion mechanism
→ durable change, if authorized
```

This prevents persuasive model output from bypassing Project/Framework governance.

## 15 · Invariants

1. Semantic intelligence belongs to the model/human judgment layer.
2. Job identity, fingerprint, permission, schema, and consumption remain deterministic.
3. Model contracts are bounded and explicitly permissioned.
4. Independent gates require genuinely separate execution identity.
5. Material semantic-question changes create new fingerprints.
6. Valid semantic reject is not infrastructure failure.
7. Reviewer shopping is prohibited.
8. Semantic result alone never grants Canon/Framework/taste-write authority.

## 16 · Related contracts

- [Semantic Execution Runtime](SEMANTIC_EXECUTION_RUNTIME.en.md) — how a semantic job reaches an eligible runtime.
- [Runtime Routing](../session_runtime/RUNTIME_ROUTING.en.md) — general route eligibility.
- [Control Plane](../control_plane/CONTROL_PLANE.en.md) — queued handoff/lease/result consumption.
- [Quality Evolution](../../docs/quality-evolution.en.md) — model-owned quality semantics with deterministic ledgers.
- [`model_contract_catalog.json`](model_contract_catalog.json) — live catalog for progressively disclosed semantic contract packs.

## Repair-preservation evidence

`quality.compare` may bind a repair challenger to an `objective_envelope`. The semantic worker separately judges target improvement and higher-order preservation. Runtime may reject an internally contradictory typed result (for example, `objective_regression` that also names the challenger as winner) but may not infer the literary classification itself.
