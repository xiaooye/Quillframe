# NovelForge Documentation QA Gate

> Companion contract to [`DOCUMENTATION_STANDARD.en.md`](DOCUMENTATION_STANDARD.en.md) and [`assets/DESIGN_SYSTEM.en.md`](../assets/DESIGN_SYSTEM.en.md).

A Tier-A visual or major customer-facing copy change is **not ready merely because the source file was generated successfully**. NovelForge documentation uses a deliberate self-check gate before a visual or copy block becomes part of the landing experience.

The goal is to catch the class of failures that source review misses: text outside containers, tiny type after GitHub scaling, weak hierarchy, low information density, generic visual language, translationese, misleading claims, and decorative UI that does not improve comprehension.

---

## 1 · Required sequence

```text
Copy / information architecture freeze
→ design-system selection
→ source implementation
→ deterministic docs lint
→ real render inspection
→ copy self-review in isolation
→ composition / brand self-review
→ bilingual parity check
→ only then: README / Docs Home integration
```

The deterministic stage may run in normal CI. It must not invoke paid model APIs.

The semantic/visual self-review is an authoring gate. For especially consequential public positioning, a separate reviewer invocation may be added, but same-session self-review must still happen first.

---

## 2 · Copy-first rule

Do **not** start by drawing boxes and then squeeze prose into whatever space remains.

Before layout:
- state the one question the module answers;
- identify the 3–6 facts a first-time reader must retain;
- write the shortest native-quality copy that preserves those facts;
- classify secondary detail as nearby prose, tooltip-equivalent note, or deep-doc link rather than forcing it into the visual;
- freeze exact product/mechanism names that require source verification.

The visual is a hierarchy for already-understood content, not a container that invents the content structure.

---

## 3 · Deterministic source checks

Run:

```bash
python scripts/docs_quality.py
```

The checker covers objective failures including:
- malformed SVG/XML;
- malformed hexadecimal colors;
- missing `<title>` / `<desc>` on product UI SVGs;
- invalid or missing `viewBox`;
- obvious text coordinates outside the canvas;
- strict Tier-A text-size and text-width budgets when the asset opts into `data-doc-tier="A"`;
- missing width budgets on long text in strict Tier-A SVGs;
- root README regression to fenced arrow-list process diagrams;
- broken local image/file references detectable from Markdown source.

Deterministic lint is necessary, not sufficient.

---

## 4 · Real render inspection

Before committing a new or materially changed Tier-A SVG, render it to a raster preview with an available local renderer/browser and **look at the rendered result**, not just the XML.

Inspect at least:
- native canvas / 100%;
- a GitHub-like content width around 760–900 px;
- a narrow/mobile preview around 360–430 px when the visual is expected to remain readable there.

At each width check:
- no text crosses a card/cell/container boundary;
- no text is clipped by the viewport;
- body text remains readable after scaling;
- line breaks look intentional;
- labels do not collide with strokes, icons, arrows, or neighboring cells;
- padding is visibly consistent;
- the hierarchy is obvious before reading every word;
- no empty decorative region consumes space while important copy is cramped.

If the render cannot be inspected in the current environment, the asset is **not approved for Tier-A integration**. Keep the source as work-in-progress or use a simpler text fallback until inspection is possible.

---

## 5 · UI/UX Pro Max review questions

For product-level modules, explicitly review the result against these priorities:

### Hierarchy
- Can a reader identify the title, primary groups, key contrast, and outcome in 2–3 seconds?
- Is the strongest emphasis attached to the most important information rather than decorative labels?

### Layout
- Is spacing systematic rather than manually improvised per box?
- Are alignment lines and gutters consistent?
- Does the composition have one obvious reading path?

### Typography
- Is type comfortably readable after the asset is scaled to GitHub content width?
- Are there too many font sizes or weights?
- Are dense captions doing work that nearby prose should do instead?

### Brand fit
- Does the result unmistakably belong to the Story Loom system?
- Are semantic colors used consistently rather than as decoration?
- Is the anime-editorial warmth restrained and purposeful?

### Information density
- Does every card/cell earn its space?
- Would a matrix, lane, timeline, or layered diagram communicate the information more directly?
- Are we forcing a card UI onto information that is naturally tabular or sequential?

### Accessibility
- Does meaning survive without color?
- Is the nearby text/alt description enough if the image fails?
- Are contrast and text size appropriate?

A visually polished but indirect or low-information module fails this gate.

---

## 6 · Copy self-review

Review the words **without the visual** before integration.

For every major block ask:
- What is the claim?
- Is it current and source-grounded?
- Is the sentence doing product explanation, mechanism explanation, or marketing filler?
- Can 20–30% of the words be removed without losing meaning?
- Are technical boundaries stated precisely?
- Does the copy expose a real tradeoff when one exists?

Reject:
- vague superlatives;
- repeated “NovelForge provides…” catalog prose;
- narrator-like hype;
- star-score language that hides mechanisms;
- labels that are cute but semantically weak;
- prose written only to fill a card.

---

## 7 · Bilingual copy self-check

English and Chinese are reviewed separately as native copy, then compared for semantic parity.

### English pass
- natural professional English;
- no literal Chinese syntax;
- concise product terminology;
- no unnecessary capitalization or pseudo-enterprise jargon.

### Chinese pass
- read the Chinese edition as if the English file did not exist;
- replace unnecessary English noun chains with natural Chinese;
- preserve exact identifiers only when they are actually normative;
- Chinese diagram labels should be Chinese unless they are product names or exact identifiers;
- remove translationese such as mechanically mirrored clause order or excessive slash-separated English concepts.

### Parity pass
Confirm both editions preserve:
- the same product claim;
- the same limitation/tradeoff;
- the same authority boundary;
- the same comparison dimension;
- the same deep-link destination.

Literal sentence symmetry is not required.

---

## 8 · Tier-A approval record

A new Tier-A asset should carry `data-doc-tier="A"` on its SVG root and pass the strict deterministic checks. The authoring change should record, in the commit/change notes when practical:

- visual purpose;
- source/reference doc;
- rendered widths inspected;
- deterministic lint result;
- copy self-review complete;
- bilingual parity complete when paired;
- any known limitation.

If any item is unresolved, do not present the asset as finished.

---

## 9 · Failure routing

When QA fails, repair the owning layer:

- invalid XML/color/path → source implementation;
- overflow/tiny type/alignment → layout/typography;
- too much text → copy hierarchy, not smaller fonts;
- indirect cards / weak comparison → information architecture;
- generic look → design-system application;
- awkward Chinese/English → language rewrite;
- unsupported competitor claim → research/source layer;
- inaccessible semantics → visual encoding + fallback text.

**Never solve overflow by shrinking text until it technically fits.** That converts a layout failure into a readability failure.
