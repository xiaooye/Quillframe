# NovelForge Visual Assets · Story Loom in the repository

This directory contains the maintained visual presentation layer for NovelForge documentation. It is deliberately small: a coherent brand system, high-value product diagrams, and provenance—not a stock-art library.

> **Boundary ✦** Visual assets improve comprehension and recognition. They never become a second authority for Framework behavior, architecture, Canon, or product claims.

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

If a file is not present in the repository, documentation must not describe it as an available asset.

---

## 02 · Two visual layers

### Brand primitives

`brand/` contains the stable Story Loom identity:

- **mark** — compact NovelForge symbol;
- **lockup** — primary horizontal brand treatment;
- **story thread** — decorative divider / continuity motif;
- **tokens** — machine-readable semantic palette.

These assets should change rarely and coherently.

### Product UI diagrams

`ui/` contains high-value static SVG modules used on product/landing surfaces. They currently explain:

- direct-system comparison;
- architecture;
- production pipeline;
- quality model;
- fit and tradeoffs.

They are presentation assets. The maintained Markdown/contracts remain the source of semantic truth.

---

## 03 · Story Loom rules

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

## 04 · Tier-A visual QA

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

## 05 · Atomic replacement

Do not remove a functioning homepage visual merely because a redesign has started.

Preferred workflow:

```text
existing visual remains live
→ replacement passes render + copy + lint
→ README and asset are replaced together
```

Removing an existing asset first is reserved for cases where the old visual is actively misleading or broken.

---

## 06 · Provenance

[`provenance.json`](provenance.json) records provenance for maintained visual assets. Depending on asset class, useful provenance may include:

- asset ID and path;
- creation/edit method;
- date;
- design intent;
- whether user-provided references were used;
- license/use notes;
- semantic source or documentation page the asset presents.

Provenance does not grant semantic authority. It explains where the presentation asset came from and what it is allowed to represent.

---

## 07 · Adding a new asset

Before adding visual material, ask:

1. Does it explain something better than prose/Mermaid alone?
2. Does the concept belong to the generic Framework rather than one consumer novel?
3. Does Story Loom already have a visual pattern for it?
4. What maintained source defines its semantics?
5. Can it be rendered and reviewed at real GitHub widths?
6. Does it require an English/Chinese pair?

If those answers are weak, do not add another decorative file merely to make the repository look busy.

**The asset system is successful when NovelForge looks distinctive without making the documentation less inspectable.**
