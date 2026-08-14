# NovelForge Documentation Standard

> **Status:** repository-wide authoring contract for customer-facing and human-facing documentation.
>
> **Visual system:** [`assets/DESIGN_SYSTEM.en.md`](../assets/DESIGN_SYSTEM.en.md)
>
> **Agent entrypoint:** [`AGENTS.en.md`](../AGENTS.en.md)

NovelForge documentation is part of the product. It must explain a sophisticated fiction-production framework with the same rigor used to build the framework itself, while preserving a recognizable **Story Loom** identity: professional technical structure with restrained anime-editorial warmth.

This standard applies to root READMEs, docs landing pages, guides, architecture explanations, comparison pages, release-facing documentation, and major subsystem introductions. Deep protocol and schema references may use a quieter presentation, but they still follow the language, authority, and accuracy rules below.

---

## 1 · Product-documentation goals

A first-time reader should be able to understand, in roughly 60–90 seconds on the main landing page:

1. what NovelForge is;
2. what problem it solves for long-form fiction;
3. how it differs from direct novel-writing agents/frameworks;
4. how its architecture and production pipeline work;
5. why its QA and independence claims are trustworthy;
6. what the framework costs in ceremony and where it is a poor fit;
7. how to start and where to go deeper.

Do not make users reconstruct the product from source-tree navigation.

Customer-facing documentation should cover capabilities **and** limitations. NovelForge must not be presented as universally superior. Tradeoffs such as extra ceremony, smaller ecosystem, semantic-review latency/cost, early-stage UX, and weaker publishing/export polish than dedicated author products should be stated when relevant.

---

## 2 · Documentation tiers

### Tier A — product / landing surfaces

Examples: `README.md`, `README.en.md`, `README.zh-CN.md`, Docs Home.

Purpose: orientation, positioning, confidence, navigation.

Requirements:
- high information density with strong visual hierarchy;
- branded presentation modules for architecture, pipeline, QA, fit, and primary comparisons;
- no wall of native Markdown tables, raw Mermaid, or arrow-list process dumps as the main product story;
- explanations remain understandable if an image fails to load;
- link to inspectable source/reference docs.

### Tier B — explanatory guides

Examples: Why NovelForge, Production Pipeline, Quality Assurance, Architecture Atlas, Adaptive Learning, Corpus, Integrations, Project SDK.

Purpose: teach mechanisms, boundaries, workflows, and tradeoffs.

Requirements:
- richer prose and source diagrams are appropriate;
- Mermaid is welcome when it is the inspectable technical source;
- native Markdown tables are acceptable when they are the clearest reference structure;
- branded page chrome and Story Loom hierarchy should remain visible.

### Tier C — contracts / reference

Examples: Harness protocols, schemas, runtime contracts, machine-adjacent references.

Purpose: precision and implementation authority.

Requirements:
- correctness beats decoration;
- avoid unnecessary mascot/editorial flourishes;
- preserve exact identifiers, state names, schemas, and normative language;
- still follow bilingual quality and accessibility rules where human-facing editions exist.

---

## 3 · Story Loom visual contract

The canonical visual specification is [`assets/DESIGN_SYSTEM.en.md`](../assets/DESIGN_SYSTEM.en.md) and machine-readable tokens live in [`assets/brand/tokens.json`](../assets/brand/tokens.json).

The target balance is approximately **70% professional technical / 30% anime-editorial warmth**.

Required characteristics:
- original NovelForge branding, not generic GitHub-doc styling;
- warm white/ink technical core with sakura, lavender, sky, mint, and amber semantic accents;
- numbered section rhythm, clear whitespace, branded dividers, semantic callouts, and compact modules;
- emoji such as `🌸 ✦ ✨ 📖` may add editorial character on landing surfaces, but must never be the only structural/status icon;
- do not add external font files; use system-font fallbacks;
- do not mix unrelated visual languages such as glassmorphism, terminal UI, brutalism, and skeuomorphism on one page.

### Primary-surface anti-patterns

On Tier A pages, avoid these as the main representation of an important concept:
- a fenced `text` block containing `A → B → C → D`;
- long arrow lists or pipeline prose pretending to be a diagram;
- generic gray Mermaid as the hero visual;
- a large native Markdown comparison table when a branded matrix is more readable;
- stacks of nearly identical cards that force the reader to open/scan each card to discover differences;
- decorative boxes with little information density;
- walls of bullet points with no hierarchy.

A production pipeline, architecture, QA stack, or competitor matrix deserves a purpose-built presentation module on the landing page.

---

## 4 · Diagram and visual-source policy

NovelForge uses a **presentation-over-source** model.

- Branded SVG/UI modules are the preferred presentation layer for Tier A pages.
- Mermaid remains the inspectable, diffable source/reference layer for technical diagrams.
- A branded rendering must not invent semantics absent from the source/reference documentation.
- Architecture or process semantics change first in authoritative text/source diagrams, then the presentation asset is updated.
- Meaningful visuals require useful alt text and nearby textual explanation.
- Color is never the sole semantic channel.
- Static assets must be original or have explicit license/provenance.

For product comparisons, prefer a high-density custom matrix that exposes actual mechanisms. Avoid star scores and vague marketing grades.

---

## 5 · Comparison standard

The root README compares NovelForge primarily with **direct novel-writing agents/frameworks**, not general-purpose agent runtimes.

Examples of direct comparison class include systems such as NovelClaw, Novel OS, AuthorAgent, and autonovel when they remain relevant and verifiable.

Dedicated author applications such as Sudowrite or NovelCrafter may be discussed separately because their product category, UX, and publishing surface differ from an engineering framework.

LangGraph, OpenAI Agents SDK, AutoGen, CrewAI, and similar general runtimes belong in implementation-influence/adoption documentation, not the homepage's primary competitor matrix.

Comparison rules:
- compare mechanisms, not vibes;
- prefer explicit capabilities such as Canon/truth model, character knowledge/state, resumability, independent semantic QA, reader QA, deterministic QA, failure routing, runtime/provider choice, local execution, and publishing/export;
- state uncertainty or documentation gaps instead of inferring a competitor lacks a feature;
- include snapshot/provenance when comparison claims may become stale;
- current competitor claims require fresh verification before material edits;
- never distort another product to make NovelForge look stronger.

---

## 6 · Bilingual standard

English and Simplified Chinese are **parallel native editions**, not literal mirrors.

### English

Write idiomatic professional technical English. Avoid Chinese sentence structure translated word-for-word. Prefer standard software, editorial, and agent-system terminology.

### Simplified Chinese

Write native professional Chinese. Do not build sentences by gluing English nouns together when a clear Chinese term exists.

Use English identifiers only when they are actual protocol names, schema values, code identifiers, commands, product names, or when the English term is the established industry term and translating it would reduce precision.

Examples:
- prefer “运行时状态”“独立语义审查”“内容指纹”“项目适配器” in explanatory prose;
- preserve exact values such as `semantic_reject`, `task_mode`, `SAFE-BUT-FLAT`, file paths, CLI commands, and schema keys when they are normative identifiers;
- Chinese diagrams use Chinese node/section labels except for exact identifiers and product names.

Do not require the two editions to have identical sentence structure. They must have equivalent meaning, authority, coverage, links, and visual hierarchy.

---

## 7 · Content and authority accuracy

Documentation must preserve NovelForge's authority boundaries:

- Framework mechanisms ≠ consuming-project Canon;
- plan/review/proposal ≠ Accepted Canon;
- runtime/session state ≠ project state ≠ learning state;
- corpus/research/eval evidence ≠ Canon or character knowledge;
- capability ≠ authority;
- a semantic worker result does not gain authority merely because a model produced it.

Never document a planned capability as already implemented. Distinguish current behavior, proposal, roadmap, and experiment.

Technical docs must match live contracts and code. When behavior changes materially, update docs in the same change unless the docs explicitly describe a future proposal.

---

## 8 · Homepage module requirements

The root README should use a coherent set of branded modules rather than switching between polished SVGs and raw text diagrams.

Current expected product-story modules include:
- direct novel-agent comparison;
- system architecture;
- chapter production pipeline;
- quality/QA and repair routing;
- honest fit/tradeoffs.

These modules should share Story Loom tokens, spacing, typography, corner language, and information density.

A core module must not silently regress from branded presentation back to an arrow list, generic table, or default Mermaid without a deliberate design reason.

---

## 9 · Markdown and prose quality

- one H1 per page;
- use numbered H2 rhythm on product/guidance pages where it improves scanning;
- keep paragraphs short enough for GitHub reading widths;
- use bold leads and callouts to expose the argument before detail;
- avoid repetitive “This system provides…” catalog prose;
- explain why a mechanism exists, what it owns, what it does not own, and what failure it prevents;
- compress routine procedure; expand important boundaries, tradeoffs, failure modes, and user decisions;
- use tables for actual multidimensional comparison/reference, not because Markdown makes tables easy;
- use code blocks only for code, commands, schemas, state machines, or genuinely textual representations—not as a substitute for product UI.

---

## 10 · Repository workflow for documentation

For user-authorized routine documentation and visual-system maintenance, **work directly on `main` by default**.

Do not create a branch merely because the task is nontrivial. Use a branch/PR only when one of these applies:
- the user explicitly requests it;
- repository protection requires it;
- the change is risky enough to need isolated review or migration;
- multiple contributors need a coordination boundary;
- an external review/check workflow specifically depends on a PR.

Before consequential writes, re-read current `main` for overlapping changes when another session or contributor may be active. Preserve unrelated concurrent work.

Temporary branches created for exceptional work should be merged/closed and deleted when no longer needed.

---

## 11 · Documentation Definition of Done

A customer-facing documentation change is complete only when:

- the page tells a coherent product story rather than exposing repository structure;
- the main visual hierarchy is recognizable as NovelForge / Story Loom;
- Tier A core concepts are not represented by raw arrow lists or generic placeholder visuals;
- English and Chinese editions are both native-quality and semantically aligned;
- diagrams and comparison claims have appropriate source/reference grounding;
- limitations and tradeoffs are not hidden;
- links and asset paths are valid;
- visuals have alt text and nearby prose fallback;
- no private data, project Canon, credentials, or chain-of-thought leaks into the framework repo;
- documentation reflects implemented behavior and current authority boundaries;
- the change preserves concurrent unrelated `main` work.

A visually clean page that is vague, low-density, misleading, untranslated-in-spirit, or hard to navigate is **not** done.