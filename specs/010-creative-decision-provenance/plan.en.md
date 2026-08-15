# Plan · Creative Decision Provenance

1. Freeze cross-framework evidence from NeuroBook and GitHub Spec Kit and preserve profile counterexamples.
2. Implement a provider-neutral JSON artifact validator/lifecycle tool; do not add a database or second plan store.
3. Implement `open`, `resolve`, `supersede`, `drop`, and audience projection with exact fingerprint/CAS guards.
4. Keep semantic judgment outside deterministic code. The tool validates actor permission and provenance; it never chooses an alternative.
5. Emit downstream revalidation candidates only. Reuse #63 separately when explicit dependency evidence warrants debt.
6. Add deterministic self-tests and a dedicated CI workflow.
7. After dedicated CI is green, integrate HARNESS discovery, normal/reusable contracts and documentation governance.
8. Add capability/regression evidence required by the Self-Improvement Protocol, review rollback, then consider merge/promotion.
