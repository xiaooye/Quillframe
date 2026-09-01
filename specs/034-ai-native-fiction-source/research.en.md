# AI-native fiction-source research

2026-08-31 · SYSTEM-IMPROVE research record · primary papers and official mechanism documentation checked through 2026-08-31 · no live fiction generation performed.

The evidence does not support a promise that prompting can mathematically eliminate an “AI voice.” It does support a narrower engineering claim: an instruction-tuned model has a persistent default register, and a pipeline can amplify that register by drafting explanatory prose first, exposing rejected prose and planning explanations as near context, then asking another model to polish it. Quillframe should stop manufacturing that failure mode, preserve author-specific objectives through the Writer and review graph, and report a model-capability boundary when an author canary still fails.

## 01 · Evidence boundary

This review prefers peer-reviewed papers, proceedings pages, official documentation and official repositories. Product documentation is used only to verify a product mechanism, not to prove literary quality. A preprint is labeled as frontier evidence. Popular plotting systems are treated as optional planning lenses, never universal chapter formulas.

The implementation decision for every source is:

- Adopt: the mechanism fits Quillframe’s authority and evidence boundaries.
- Adapt: retain the useful mechanism while changing its scope or representation.
- Reject: do not put it in the production quality path.

## 02 · Model default style and capability limits

The PNAS study “Do LLMs write like humans?” finds a stable, informationally dense, noun-heavy register in instruction-tuned model output, including under informal prompting. This supports treating default voice as a model-and-pipeline problem rather than a list of forbidden words. It does not prove that every model or Chinese fiction sample behaves identically.

Fiction-Writing Mode shows that specialized training can improve human preference for creative writing in its evaluated setting. The result supports fiction-capable routing and controlled auditions; it does not establish a universal best model for Chinese web fiction.

Decision:

- Adopt a fiction-writing capability requirement, exact model/version fingerprinting and author-blind auditions.
- Adapt prompt guidance into short, positive, scene-local direction near generation.
- Reject claims that one prompt guarantees zero AI voice.
- Stop prompt stacking when all authorized audition arms fail; report the capability boundary and consider a separately authorized specialized model or training path.

## 03 · Character action before prose

ConPer converts persona information into character-centered events before surface generation. Character-centric story generation and the psychological-depth work likewise support modeling character goals, beliefs and relations as causal state rather than decorative adjectives.

Decision:

- Adopt a private Character Enactment artifact: belief, misperception, desire, feared loss, expectations of others, two or three viable strategies, tradeoffs, selected action and relationship-specific interaction tactics.
- Keep that private reasoning out of Writer context. The Writer receives enacted choices, observable constraints and consequences, not a psychology essay.
- Reject personality labels as a sufficient character plan and reject deterministic “character uniqueness” scores.

## 04 · Hierarchical planning without prose templates

DOC and DOME support progressive, hierarchical outline refinement and long-range memory. Snowflake explicitly presents iterative expansion and says writers should discard methods that do not work for them. Story Grid offers useful choice, complication and consequence lenses. None of these sources establishes a universal per-chapter beat quota.

Decision:

- Adapt these methods into a Scene Realization Contract covering available choices, action strategies, counterforce, lost options or rising costs, required facts, information gaps, a concrete source of friction and the new constraint at scene end.
- Separate causal content from prose shape.
- Reject mandatory fifteen-beat, five-commandment, reversal, hook, sensory-detail, joke or tension-peak counts.

## 05 · Minimal context and near-generation direction

Novelcrafter documents ordered Codex context and writing samples; Sudowrite documents a style field that directly affects generated prose and selective Story Bible visibility; NovelAI distinguishes durable Memory from the near-generation Author’s Note and activates Lorebook entries conditionally; SillyTavern documents example messages, dynamic World Info and late prompt instructions.

These are product mechanism descriptions, not comparative quality studies. Together they establish that selective context, demonstrations and near-generation instructions are common controllable mechanisms.

Decision:

- Adapt a model-owned Context Composer that chooses the minimum sufficient eligible items from a Core-validated inventory.
- Permit two to four author-owned or explicitly authorized positive anchors with provenance, rights, version, fingerprint and author confirmation.
- Permit only accepted or author-approved recent prose as a prose tail.
- Keep rejected prose, reviewer analysis, repair explanations, private character deliberation, unrelated lore and unknown future facts out of fresh Writer context.
- Merge scene projection, context selection and Director Note production in one semantic call where their inputs coincide.
- Reject automatic top-k raw corpus retrieval and named living-author imitation.

## 06 · Review evidence and judge bias

G-Eval explicitly notes potential bias by LLM evaluators toward LLM-generated text. Personalized evaluation shows that evaluation can be conditioned on user preferences rather than a generic aggregate. These findings do not turn any model judge into literary truth.

Decision:

- Adopt atomic author-objective judgments with met, not_met or uncertain, exact candidate evidence, scope and recommended repair route.
- Make each current hard objective conjunctive: not_met cannot be averaged away by fluency, completeness or a global score.
- Keep model review as evidence and the author’s explicit current-work feedback as the highest semantic authority.
- For A/B review, blind model identity, swap candidate order, prefer different model families and mark order-conflicted results uncertain.
- Reject a single overall PASS as sufficient evidence that author objectives were met.

## 07 · External implementation survey

The surveyed open repositories contain useful orchestration ideas but also mechanisms outside Quillframe’s boundary.

| Source | Adopt or adapt | Reject |
| --- | --- | --- |
| Oh Story | Separate planning, drafting and review responsibilities | Forbidden-word and AIGC-style quality gates |
| Chinese Novelist Skill | Explicit phase boundaries and author checkpoints | Fixed hook, rhythm and formula claims |
| AI Novel Writer | Human-edit comparison and staged provenance | Any implication that workflow completion proves literary quality |
| Novel Studio | POV-scoped state, sealed chapter contracts, leases and checkpoints | AIGC metrics as a literary guard |
| Fanqie creator course | Platform context as optional authoring evidence | Universalizing platform advice into Framework quotas |

Discovery of a repository does not grant ingestion, dependency or Framework-write authority.

## 08 · Failure evidence and overreach audit

The frozen failed revision establishes these pipeline facts without using the rejected prose as a positive example:

- the author objective reached the Repair Editor and Surface Writer;
- the Surface Writer also received the entire incumbent prose, repair explanation, repeated plans and substantial planning context;
- the route selected bounded surface repair rather than fresh realization;
- later self-audit and independent review did not receive the active author objectives;
- a returned Writer response was discarded by an after-response token-budget check;
- once a coordinator was active, model stages followed each other with sub-second gaps, while the dominant wall-clock gaps were outside model execution.

The evidence does not establish that an English counter or prose telemetry decided release. Current prose telemetry is optional and is not imported by the production runtime. Run-specific helper scripts existed, but their unavailable contents cannot be represented as proven literary counters.

Overreach rejected:

- treating fewer English characters as proof of natural Chinese;
- treating any deterministic test as a literary verdict;
- inferring precise database or validation milliseconds when the event schema did not record them;
- treating reviewer confidence as author acceptance;
- treating research on English or short fiction as a guaranteed Chinese-web-fiction effect size.

## 09 · Resulting engineering hypothesis

Quillframe can remove a known source of systematic contamination by replacing full Raw Draft rewriting with direct Surface Writer realization from a compact causal contract, verified author voice assets and model-selected relevant context. It can preserve author objectives through every applicable reviewer, route systemic contamination to fresh realization, and make valid returned results durable regardless of a soft budget crossing.

This remains an engineering hypothesis until an authorized, paid Chinese canary is blind-reviewed by the author. The canary is a separate gate and is not run by this change.

## 10 · Primary and official sources

- PNAS, “Do LLMs write like humans?”: https://doi.org/10.1073/pnas.2422455122
- ConPer: https://aclanthology.org/2022.naacl-main.245/
- DOC: https://aclanthology.org/2023.acl-long.190/
- DOME: https://aclanthology.org/2025.naacl-long.63/
- Character-centric generation: https://aclanthology.org/2025.findings-acl.82/
- Psychological Depth: https://aclanthology.org/2024.emnlp-main.953/
- Fiction-Writing Mode: https://aclanthology.org/2023.eacl-main.128/
- G-Eval: https://aclanthology.org/2023.emnlp-main.153/
- Personalized evaluation: https://aclanthology.org/2024.emnlp-main.737/
- Chinese web-fiction homogeneity preprint: https://arxiv.org/abs/2603.14430
- Snowflake Method: https://www.advancedfictionwriting.com/articles/snowflake-method/
- Story Grid 101: https://store.storygrid.com/wp-content/uploads/sites/3/2020/07/STORY-GRID-101-Print.pdf
- Novelcrafter context and writing samples: https://www.novelcrafter.com/help/faq/ai-and-prompting/codex-context-in-prompting and https://www.novelcrafter.com/help/faq/write/writing-samples
- NovelAI Memory, Author’s Note and Lorebook: https://docs.novelai.net/en/text/editor/storysettings/ and https://docs.novelai.net/en/text/lorebook/
- SillyTavern prompts and World Info: https://docs.sillytavern.app/usage/prompts/ and https://docs.sillytavern.app/usage/core-concepts/worldinfo/
