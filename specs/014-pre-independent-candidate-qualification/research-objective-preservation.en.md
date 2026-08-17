# Objective Preservation Under Repair — Research Synthesis

Date: 2026-08-17  
Mode: `SYSTEM-IMPROVE`  
Scope: pre-independent candidate qualification / repair loop

This research note separates **empirical support**, **engineering inference**, and **NovelForge-specific design**. No cited source directly establishes a fiction-writing architecture.

## Research matrix

| Source | Status | Phenomenon / domain | Evidence strength | Relevant result | Limitation | NovelForge applicability | Decision |
|---|---|---|---|---|---|---|---|
| Qi et al., *On the Paradoxical Interference between Instruction-Following and Task Solving* (arXiv:2601.22047, 2026) | preprint | math, multi-hop QA, code; self-evident added constraints | medium; recent multi-model empirical study, not peer reviewed | adding constraints already satisfied by successful outputs can still reduce underlying task performance; failures allocate more attention to constraints | non-fiction tasks; attention analysis does not prove causal mechanism for creative repair | direct warning against treating constraint compliance as the task objective | **ADOPT principle**, not architecture |
| Harada et al., *When Instructions Multiply* (Findings EMNLP 2025, DOI 10.18653/v1/2025.findings-emnlp.896) | peer reviewed | multi-instruction text/code generation across 10 LLMs | strong for instruction-count interference | performance consistently degrades as simultaneous instructions increase | benchmark constraints are more measurable than fiction objectives | supports sparse repair packets instead of accumulating every rule | **ADOPT** |
| Zeng et al., *Order Matters* (Findings ACL 2025, DOI 10.18653/v1/2025.findings-acl.646) | peer reviewed | position bias in multi-constraint instructions | strong for ordering sensitivity | constraint order materially changes performance; hard-to-easy ordering performed better in studied settings | does not justify one universal prompt order | supports avoiding accidental priority changes from repair-history order | **ADAPT** |
| Robinette et al., *We Are What We Repeatedly Do* (Findings EACL 2026, DOI 10.18653/v1/2026.findings-eacl.254) | peer reviewed | multi-turn long-context instruction following | strong for long-context instruction decay | long contexts harm instruction adherence; six mitigations improved compliance up to 79% in studied open models | focuses verifiable instruction compliance, not story quality | supports explicit re-anchoring/compact state experiments | **ADAPT** |
| Singh et al., *MT-OSC* (Findings ACL 2026, DOI 10.18653/v1/2026.findings-acl.1354) | peer reviewed | multi-turn dialogue condensation across 13 LLMs | strong for condensation in tested benchmarks | one-off sequential condensation reduced tokens up to 72% in 10-turn dialogues while improving/preserving accuracy | condensation may lose creative nuance if poorly constructed | supports compact current-state reconstruction rather than indefinite append | **ADAPT** |
| Shen et al., *ACR: Adaptive Context Refactoring* (Findings ACL 2026, DOI 10.18653/v1/2026.findings-acl.155) | peer reviewed | multi-turn contextual inertia / state drift | strong for adaptive context refactoring in tested dialogue tasks | dynamic context refactoring outperformed baselines while reducing tokens | learned refactoring operators were not tested on fiction production | supports model-selected context reconstruction after drift/inertia, not hard cycle-count reset | **ADAPT** |
| Chen et al., *Breaking Contextual Inertia* (Findings ACL 2026, DOI 10.18653/v1/2026.findings-acl.313) | peer reviewed | multi-turn updates and prior-reasoning inertia | strong for contextual inertia | models can cling to prior traces despite later corrections; single-turn anchors improve stability in studied domains | training method is not directly usable as a prompt-time repair mechanism | supports clean current-state anchors and not inheriting failed trajectories | **ADAPT** |
| Menon et al., *Inherited Goal Drift* (arXiv:2603.03258, 2026) | preprint | agent trajectories in stock trading; preliminary ER triage | medium; recent, multi-setting but not peer reviewed | strong models can inherit drift when conditioned on weaker prefilled trajectories; hierarchy following does not reliably predict drift resistance | agentic environments differ from creative writing | supports treating prior trajectory as potentially causal context, not inert history | **ADAPT cautiously** |
| Du et al., *Context Length Alone Hurts LLM Performance Despite Perfect Retrieval* (arXiv:2510.05381, 2025) | preprint | math, QA, code with relevant evidence available | medium | performance can degrade as context length grows even with perfect retrieval | preprint; not multi-turn fiction | supports context minimization as quality protection | **ADAPT cautiously** |
| Stechly, Valmeekam & Kambhampati, *On the self-verification limitations of LLMs on reasoning and planning tasks* (ICLR 2025) | peer reviewed | self-verification in reasoning/planning | strong for tested tasks | self-verification is often unreliable | not prose evaluation | manager self-audit should prefilter, not replace independent review | **ADOPT boundary** |
| Critic-CoT (Findings ACL 2025) and Table-Critic (ACL 2025) | peer reviewed | iterative critique/refinement in reasoning/table tasks | counterevidence | iterative critique can improve outcomes in some domains | domain-specific | rejects a universal claim that iterative repair necessarily degrades | **REJECT blanket anti-refinement** |
| *Monotonic Reference-Free Refinement for Autoformalization* (arXiv:2601.23166, 2026) | preprint | multi-dimensional preservation in formalization | medium/indirect | demonstrates a preservation + improvement acceptance approach in a verifiable formal domain | fiction lacks theorem-prover-style objective ordering | useful analogy, not proof of literary monotonicity | **ADAPT concept; reject strict monotonic claim** |
| Anthropic, *Effective context engineering for AI agents* (2025) and long-running harness engineering guidance (2026) | official engineering, not peer reviewed | context pollution, compaction, structured handoff | practical evidence | long-running systems benefit from compaction/structured current state; separate evaluation remains valuable | vendor engineering observations, not controlled fiction research | informs implementation details and failure recovery | **ADAPT** |

## Empirically supported

1. More simultaneous instructions/constraints can reduce compliance and/or underlying task performance.
2. Constraint placement/order can materially change outcomes.
3. Multi-turn and long-context interaction can degrade instruction adherence and task accuracy.
4. Condensation/refactoring/anchoring can mitigate some long-context and multi-turn failures in studied domains.
5. Prior trajectories can induce contextual inertia; recent preprint evidence also suggests inherited goal drift.
6. Self-evaluation is not a sufficient substitute for independent verification.
7. Iterative critique is not inherently bad: some critique/refinement systems improve performance, so the Framework should detect regressions rather than ban refinement.

## Plausible engineering inference

1. A repair loop that keeps appending negative findings can accidentally increase the salience of local constraints relative to the original creative task.
2. Rejected prose and long critique history are plausible context contaminants for a fresh realization even when they are useful to an Auditor/Editor.
3. A compact current-state reconstruction is likely safer than indefinite repair-history accumulation when contextual inertia or objective regression is observed.

These are engineering inferences from adjacent empirical domains. They are not claimed as proven facts about fiction writing.

## NovelForge-specific design choices

1. Introduce a compact, fingerprint-bound **objective envelope** built semantically from current authorized request/plan/profile/state evidence. Runtime validates provenance/fingerprint only.
2. Treat Surface/AI-realization rules as constraints on acceptable solutions, not as a substitute objective function.
3. Upgrade existing `quality.compare` rather than create a parallel comparator: classify repair outcome as target-not-fixed, objective-regression, successful-repair, or inconclusive, with separate target and preservation axes.
4. Require material repair candidates to carry repair-preservation evidence before pre-independent qualification can pass.
5. Keep incumbent protection: a challenger that fixes the target while materially degrading required story/reader objectives cannot become the current incumbent through a contradictory typed result.
6. Extend `editor.repair_spec` from FIX-only emphasis to **FIX + PRESERVE**, and make fresh realization receive reconstructed current state + objective envelope + minimal repair packet while hiding rejected realization and accumulated critique history.
7. Do not use a universal weighted score, lexical ban, fixed constraint-count cap, or hard repair-cycle reset threshold.
8. Use semantic detection of contextual inertia/objective regression/oscillation to choose fresh reconstructed context; deterministic runtime enforces the selected information boundary.

## Why strict “monotonic quality” is rejected

The repair target can be made monotonic in a narrow semantic sense (the targeted defect should improve), but fiction quality is not a single verifiable scalar. NovelForge therefore adopts **target improvement with blocking semantic non-regression of the current objective envelope**, not a mathematical monotonic-quality claim.
