# Anonymous Public General Corpus

This directory is Quillframe's repository-visible publication root for anonymous, source-free craft evidence. It is not a mirror of the local novels, an author-style collection, or a promise that abstraction alone resolves copyright questions.

## Current release state

[`registry.json`](registry.json) is intentionally empty and reports `awaiting_first_validated_release`. No work has been represented as studied or published merely because schemas and release machinery now exist. A validated release adds a random `PS-*` directory only after an exact 120-work study is complete and the caller confirms both the preview token and manifest fingerprint. It becomes part of the public library only when that directory and its matching registry entry are reviewed and committed to Git.

The registry contract is [`registry.schema.json`](registry.schema.json). Individual records and release manifests use [`public_work.schema.json`](public_work.schema.json) and [`public_manifest.schema.json`](public_manifest.schema.json).

The prose-style atlas is a separate, stricter publication family. [`style_registry.json`](style_registry.json) is also intentionally empty; its contracts are [`style_atlas.schema.json`](style_atlas.schema.json), [`style_atlas_preview.schema.json`](style_atlas_preview.schema.json) and [`style_atlas_registry.schema.json`](style_atlas_registry.schema.json). Its source-free craft artifact is built only from an exact completed StyleStudyRunner receipt; preview does not confer release authority. A release additionally needs independently trusted and exact-artifact-bound provenance/rights, semantic-leakage, blind-evaluation, promotion and human-approval receipts, plus a rollback-safe registry transition. Self-reported booleans and caller-computed hashes are not evidence. No style atlas has passed these gates.

The fixed [`style_publication_trust_policy.json`](style_publication_trust_policy.json) stores only each signing role's key identifier and domain-separated secret fingerprint, never a secret. All five roles require distinct secrets, and the publisher must exactly match this sibling policy. The committed policy is deliberately `unconfigured`, so the default public directory cannot perform a real release. A successful release writes the complete claims, signatures and human-confirmation challenge to a content-addressed receipt governed by [`style_atlas_release_receipt.schema.json`](style_atlas_release_receipt.schema.json); rollback and other registry transitions use separate receipts governed by [`style_registry_transition_receipt.schema.json`](style_registry_transition_receipt.schema.json). The registry keeps only the ordered event receipt fingerprints. Every trusted load replays that chain from the empty registry and rechecks all signatures, base revisions and target-path bindings.

## What a release may contain

A version-1 bundle has exactly 120 randomized `public_work_id` records. It may contain numeric derivatives; controlled sentence, scene, chapter, pacing, dialogue, point-of-view, tension and sensory profiles; cross-work controlled mechanisms; applicability boundaries; counterexample states; failure modes; and integrity fingerprints.

It must not contain source paths, filenames, titles, creators, source prose, quotations, close paraphrases, source-reconstructive summaries, character or setting identities, or arbitrary schema extensions. `unresolved` is a valid evidence boundary. These fields describe an anonymous three-window sample; they are not generation quotas and do not support named-author imitation.

A style atlas, if later released, is smaller and contains no per-work record. Its craft cards may expose only a controlled style axis, operation, effect, applicability/avoidance conditions, failure boundary, `general` content zone and bounded confidence, with integrity fingerprints. Evaluation and approval receipts remain separate governance artifacts rather than fields in the Writer-safe atlas.

## Source and profile boundaries

Original novels remain in user-controlled local storage. Private ledgers may retain identifiers, file locations, fingerprints and evidence lineage, but not source prose. Each selected logical work contributes one confirmed edition and three ephemeral windows—opening, middle and closing—of no more than 4,000 Unicode characters each.

While confirming the checklist, the user explicitly selects `general` or `adult_explicit`; Quillframe does not infer the profile from prose. A study, all 120 work records and its aggregate remain inside that one profile. `adult_explicit` evidence cannot be mixed into a general release or injected into ordinary writing tasks.

Body shape, anatomy, clothing and appearance descriptions—including the isolated term `巨乳`—remain ordinary `general` style evidence and do not by themselves create an explicit-content classification. Actual explicit sexual context remains separately governed.

## License and legal boundary

Repository-owned derived artifacts in this directory inherit the repository's [Quillframe Proprietary Source-Available License](../../LICENSE). “Public” here means visible as part of the public repository; it does not mean an open-data or permissive redistribution license. No third-party source text is relicensed by this directory.

Rights and publication suitability still require source-specific review. Non-commercial intent and abstraction reduce neither that responsibility nor the need for a leakage check; Quillframe's deterministic gate validates the declared policy and closed schema, not the law.
