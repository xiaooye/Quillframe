# Framework Self-Improvement Protocol · v7

## Goal

NovelForge may learn and improve autonomously, but durable behavior changes must remain evidence-backed, testable, scoped, and rollbackable.

```text
Capture → Classify → Distill → Counterexample → Test → Promote → Observe → Roll back
```

## Learning scopes

- `one_off`: current response/run only.
- `project`: one consuming novel/project.
- `user_taste`: cross-project preference for one user, stored outside generic source control by default.
- `general_craft`: candidate generic mechanism for NovelForge itself.

Always choose the narrowest scope supported by evidence.

## Evidence hierarchy

Strong evidence includes explicit user rules, direct edits, explicit acceptance/rejection reasons, repeated consistent corrections, project conventions, cross-work corpus mechanisms, and external primary/framework evidence.

Model inference alone is weak evidence and cannot promote durable user taste or General Craft.

## User preference learning

User feedback becomes traceable evidence, then a revisable hypothesis. The system may autonomously detect contradictions, create Corpus gaps, search contrast/counterexamples through authorized tools, generate personalized evals, and strengthen/narrow/deprecate hypotheses.

Do not turn rejected model output into a positive exemplar.

## General Craft promotion

A framework behavior promotion requires:
1. mechanism independent of one project/user;
2. provenance/evidence;
3. counterexample or profile-boundary analysis;
4. capability + regression evals;
5. conflict check against existing fundamentals/profiles;
6. smallest sufficient change;
7. version/rollback reference;
8. green post-change deterministic CI;
9. observation after promotion.

No amount of repeated self-agreement replaces new evidence.

## Corpus-derived learning

Corpus observations become general guidance only through cross-work synthesis and rights/provenance governance. Do not create modern named-author imitation profiles.

## External framework learning

Changes in OpenAI Agents SDK, LangGraph, ADK, AutoGen, Claude Code, MCP, or other frameworks produce an `adopt | adapt | reject` candidate. Newer upstream behavior is not automatically better for fiction production.

## Rollback

If later evidence shows harm or invalid provenance:
- mark hypothesis/promotion contested or deprecated;
- invalidate dependent benchmarks/evals;
- restore prior behavior/profile;
- record rollback evidence;
- rerun relevant regressions.

## Boundary

Framework self-improvement may change generic mechanisms. It may never absorb a consuming novel's characters, Canon facts, plot outcomes, or private project state into generic source.
