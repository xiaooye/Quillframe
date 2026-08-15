# NovelForge Visual Assets · Story Loom in the repository

This directory contains the maintained Story Loom presentation and token foundation for NovelForge documentation and product surfaces. It is deliberately small: a coherent brand system, high-value product diagrams, machine-readable product semantics, and provenance—not a stock-art library or a second UI framework.

> **Boundary ✦** Visual assets and tokens improve comprehension, recognition, and presentation consistency. They never become a second authority for Framework behavior, architecture, Canon, Settlement, semantic truth, or workflow state.

---

## 01 · Live asset map

```text
assets/
├── README.en.md / README.zh-CN.md
├── DESIGN_SYSTEM.en.md / DESIGN_SYSTEM.zh-CN.md
├── provenance.json
├── brand/
│   ├── novelforge-mark.svg
│   ├── novelforge-lockup.svg
│   ├── story-thread.svg
│   └── tokens.json
└── ui/
    ├── home-comparison.en.svg / .zh-CN.svg
    ├── home-architecture.en.svg / .zh-CN.svg
    ├── home-pipeline.en.svg / .zh-CN.svg
    ├── home-quality.en.svg / .zh-CN.svg
    └── home-fit.en.svg / .zh-CN.svg
```

If a file is not present in the repository, documentation must not describe it as an available asset. In particular, no generated WeiUI theme file is claimed here until the implementation actually lands on `main`.

---

## 02 · Two maintained visual layers

### Brand and product-semantic primitives

`brand/` contains the stable Story Loom identity:

- **mark** — compact NovelForge symbol;
- **lockup** — primary horizontal brand treatment;
- **story thread** — decorative divider / continuity motif;
- **tokens** — machine-readable brand and product-semantic palette.

These assets should change rarely and coherently. `brand/tokens.json` is the current NovelForge-side token authority; a future interactive theme adapter may transform it, but a component library does not get to redefine Story Loom semantics.

### Product UI diagrams

`ui/` contains high-value static SVG modules used on product/landing surfaces. They currently explain:

- direct-system comparison;
- architecture;
- production pipeline;
- quality model;
- fit and tradeoffs.

They are presentation assets. The maintained Markdown/contracts remain the source of semantic truth.

---

## 03 · Interactive product bridge · selected direction

The future installable Studio shell has selected Tauri + React + WeiUI. The intended visual dependency is one-way:

```text
NovelForge Story Loom tokens
→ deterministic WeiUI-compatible W3C token representation
→ WeiUI token / CSS / React component substrate
→ Tauri Studio shell
```

The implementation is still pending. Until a converter/theme artifact is committed, tested, and pinned, `assets/brand/tokens.json` remains the only NovelForge token source documented as present in this repository.

Ownership stays explicit:

- **NovelForge** owns Story Loom domain colors, product semantics, authority/status/provenance grammar, typography roles, density choices, and visual personality;
- **WeiUI** owns generic reusable component primitives, component interaction/accessibility behavior, CSS mechanics, and its public token/component contracts;
- **the adapter** owns deterministic conversion between those two layers;
- **Tauri** hosts the installable product and does not become Core authority.

Do not hand-copy a second Studio palette beside the adapter. Do not map generic `success` styling to Accepted Canon. Do not make Tauri, React, or WeiUI dependencies of Generic Core correctness, CLI, the Framework bundle, or the Agent Skill.

The full product boundary and acceptance gate live in [`../studio/PRODUCT_ARCHITECTURE.en.md`](../studio/PRODUCT_ARCHITECTURE.en.md).

---

## 04 · Story Loom rules

The full visual contract lives in [Documentation Design System](DESIGN_SYSTEM.en.md).

Core rules:

- professional technical documentation first;
- one coherent original identity rather than unrelated visual styles;
- restrained anime-editorial warmth, not mascot noise;
- no consumer-novel characters or project-specific Canon in generic Framework assets;
- no copyrighted franchise characters, logos, or direct living-artist imitation;
- diagrams remain understandable through nearby prose if the SVG does not load;
- color and emoji never carry meaning alone;
- no external/embedded font files.

---

## 05 · Tier-A visual QA

Homepage/product visuals are stricter than ordinary decorative assets.

Before a new or materially redesigned Tier-A SVG is referenced from README, it must pass:

```text
copy freeze
→ information architecture
→ Story Loom layout
→ real render at GitHub-like width
→ narrow render
→ visible-copy review
→ bilingual parity review
→ deterministic docs lint
→ integration
```

Hard expectations include:

- root `data-doc-tier="A"`;
- non-empty `<title>` and `<desc>`;
- projected body text at ~820px GitHub width >= 12px;
- explicit width budgets for long measurable text;
- no clipping, overflow, collision, or tiny-text “fixes”;
- English and Chinese laid out independently when language geometry differs;
- actual render inspection at roughly 820px and 420px widths.

Run:

```bash
python scripts/docs_quality.py
```

**Generated is not reviewed. XML-valid is not visually correct.**

---

## 06 · Atomic replacement

Do not remove a functioning homepage visual merely because a redesign has started.

Preferred workflow:

```text
existing visual remains live
→ replacement passes render + copy + lint
→ README and asset are replaced together
```

Removing an existing asset first is reserved for cases where the old visual is actively misleading or broken.

---

## 07 · Provenance

[`provenance.json`](provenance.json) records provenance for maintained visual assets. Depending on asset class, useful provenance may include:

- asset ID and path;
- creation/edit method;
- date;
- design intent;
- whether user-provided references were used;
- license/use notes;
- semantic source or documentation page the asset presents.

Provenance does not grant semantic authority. It explains where the presentation asset came from and what it is allowed to represent.

When the WeiUI-compatible theme/converter lands, its generated-vs-source status, source token fingerprint/version, and ownership should be recorded explicitly rather than implied by directory placement.

---

## 08 · Adding a new asset or token-derived artifact

Before adding visual material, ask:

1. Does it explain something better than prose/Mermaid alone, or provide a real product-runtime presentation need?
2. Does the concept belong to the generic Framework/product layer rather than one consumer novel?
3. Does Story Loom already have a visual/token pattern for it?
4. What maintained source defines its semantics?
5. Can it be rendered or deterministically generated and reviewed at real target widths?
6. Does it require an English/Chinese pair or locale-sensitive QA?
7. If generated, is there exactly one source of truth and a reproducible conversion path?

If those answers are weak, do not add another decorative file or parallel token set merely to make the repository look busy.

**The asset system is successful when NovelForge looks distinctive, product surfaces reuse the same semantics, and neither presentation nor component tooling becomes a competing source of truth.**
