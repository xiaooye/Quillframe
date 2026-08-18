# Why Quillframe?

**Quillframe** is the current product identity and `quillframe` is the current technical namespace.

Quillframe exists because long-form fiction has two simultaneous needs that are easy to collapse into one another: creative interpretation must remain flexible, while authority and execution state must remain exact.

## The system boundary is the product

A useful fiction framework cannot make a deterministic script decide whether a relationship feels alive. It also cannot let a model decide that a plan has become Canon, that a stale review still applies, or that a failed write probably succeeded.

Quillframe therefore separates semantic ownership from deterministic ownership. Models or humans make judgments that require meaning. Code proves identities, permissions, fingerprints, lifecycle, provenance, transactions, and reproducibility.

The same boundary applies to model execution: users connect inference with `API Endpoint + Access Token`; Quillframe owns discovery, capability evidence, model selection, tools, sessions, Context, authority, and the agent loop. Vendor identity is not the product authority.

## Long-form work needs authority, not just memory

A large memory window does not answer which facts are authoritative. Quillframe keeps Project truth, current state, plans, review candidates, derived memory, research, Corpus evidence, and runtime state in different authority classes. Sparse Context Manifests select only what the current task actually needs.

<img src="assets/concepts/authority-ladder.en.svg" alt="Authority ladder from locked to proposal, with Plan not equal to Canon and Accepted not equal to Settled" width="100%" />

## Revision needs lineage, not rewrite churn

Revision can improve the local target while harming the chapter's real objective. Quillframe freezes an objective envelope, compares incumbent and challenger semantically, records repair-induced regression, and separates comparison ancestry from prose ancestry. A fresh regeneration can compete without inheriting rejected wording.

## Independence is a runtime property

A manager changing role labels inside the same invocation is not an independent reviewer. When independence is required, the artifact is frozen, fingerprinted, dispatched to a separate eligible invocation/session, validated against that exact fingerprint, and consumed once.

## Learning is automatic at intake, governed at promotion

Meaningful user feedback can enter a bounded learning intake from any primary task mode. Capture is automatic; promotion is not. `one_off`, `project`, `user_taste`, and `general_craft` remain separate scopes, and none receives durable write authority merely because a model inferred it.

## Persistence is not authority

SQLite is Quillframe's canonical durable product state. That does not mean every persisted value is Canon, Accepted, Settled, or eligible for prompt injection. Persistence answers “what survives”; authority answers “what this fact is allowed to mean.”

## The tradeoff

Quillframe is intentionally heavier than a one-shot writing assistant. It is useful when a project lives long enough for continuity, state, revision provenance, recovery, independent review, and learning discipline to matter. For lightweight ideation or a single rewrite, a smaller tool may be better.

## Naming and historical records

Current-facing product documentation, package metadata, schemas, and active architecture use **Quillframe / `quillframe`**. Historical specifications, migration records, Git history, and legal text may retain earlier terminology when changing it would rewrite provenance or legal meaning. Those historical records do not change the current product identity.
