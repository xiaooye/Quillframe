# Chinese Webnovel Production Closure

Status: implementation in progress. Primary task mode: SYSTEM-IMPROVE. Framework version: 1.0.0-dev.0.

## Objective

Quillframe must support Chinese long-form serial fiction through a real browser-to-Core production flow. Reader engagement is the positive quality objective: meaningful questions, character investment, movement, emotional reward and reasons to continue. Genre and platform emphasis are project choices, not universal quotas.

## Native project boundary

This specification supersedes the earlier development-only CH001 restriction. A native `quillframe_project_v1_0` manifest contains exactly `schema`, `id`, `title` and `language`. Transport projections declare `scope: novel`. A new project atomically creates its initial chapter and manuscript; later chapters have real registered identities. Old five-key manifests and incompatible development databases are rejected without migration, deletion or silent repair.

Author acceptance, independent review, Canon settlement, learning activation and publication remain separate operations. Only an exact Core release exposes production manuscript text. A changed candidate invalidates its old reviews. A changed source invalidates dependent context and derived observations.

## Production and reader experience

Each run binds its actual chapter, document, reading order, declared story order, selected preferences and frozen sources. Character actions cause scene results; Writer receives only the safe projection. Blind readers do not receive future plans, expected payoffs or private character state. Editor diagnosis may compare the plan against the final candidate.

Use existing planning-horizon and reader-expectation mechanisms. Proposed events do not become historical facts. Reader expectations record source-bound opening, reinforcement, partial reward and payoff; observations remain non-authoritative. Source changes preserve history and mark dependent observations stale.

## Persistence and learning

Persist each model request before dispatch and confirm its exact result before downstream consumption. Restart may reuse confirmed results; an unknown outcome never causes an automatic duplicate model call. Cancellation prevents late results from advancing the run. Budgets count actual model dispatches, including supporting work.

Feedback distinguishes author, human reader and model proxy sources. Stable event identity prevents retry inflation. Interpretation yields project-local candidates; evaluation and explicit author activation are required before future production uses a preference. Framework source, learning storage and consumer Canon remain separate domains.

## Acceptance

Acceptance requires Linux non-root storage tests, current Studio/Bridge regressions, clean-package checks and real browser operation. Real GPT evidence must cover a single chapter, three consecutive chapters, then twelve chapters in one external original test project, with author confirmation between chapters. Operational correctness does not prove market retention or million-word consistency.

Experiments use four development cases and six held-out cases. A round is limited to 64 actual model calls including supporting work; insufficient budget is reported as incomplete. No model calls run in ordinary CI. Cloud deployment, automated submission, bulk novel ingestion and weight training are outside this implementation.
