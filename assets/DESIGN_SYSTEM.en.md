<div align="center">
  <img src="brand/novelforge-lockup.svg" alt="NovelForge — Adaptive Fiction Agent Framework" width="620" />
</div>

# NovelForge Documentation Design System

> **Brand concept: Story Loom.**
>
> NovelForge does not become distinctive by painting generic technical docs pink. Its visual system treats **Project → Runtime → Story → Reader → Evidence → Validated Result** as one continuously woven story thread. Professional technical structure is the skeleton; anime-editorial warmth is the recognition layer. 🌸

**Ratio:** `70% professional technical / 30% anime-editorial warmth`.

This file defines the visual language. [`../docs/DOCUMENTATION_QA.en.md`](../docs/DOCUMENTATION_QA.en.md) defines the required review workflow. A visual is not production-ready merely because it is valid SVG.

---

## 1 · Brand DNA ✦

NovelForge should hold four qualities at once:

| Trait | Design meaning |
|---|---|
| **Precise** | hierarchy, spacing, and diagram semantics stay rigorous |
| **Editorial** | feels like a fiction-production studio, not a generic DevOps dashboard |
| **Warm** | sakura / lavender / soft surfaces add human and anime-editorial character |
| **Engineered** | tokens, provenance, chart grammar, and asset boundaries are inspectable |

Landing pages may naturally use `🌸 ✦ ✨ 📖`; dense contracts, schemas, and CLI docs stay quieter.

---

## 2 · Logo System · Story Loom

### Primary mark

<img src="brand/novelforge-mark.svg" alt="NovelForge Story Loom brand mark" width="120" />

The mark combines three ideas:

1. **Two book-page forms** — fiction, manuscript, and Canon;
2. **Woven N / story thread** — project, runtime, story, and evidence remain traceable;
3. **Forge spark** — validation, revision, and improvement rather than one-shot generation.

### Primary lockup

<img src="brand/novelforge-lockup.svg" alt="NovelForge primary horizontal lockup" width="560" />

Usage:
- README / docs landing pages: prefer the lockup;
- small footer, badge, or avatar: use the mark;
- do not rotate, glow, or arbitrarily recolor it;
- do not use the logo as an architecture/status icon;
- the wordmark uses system-font fallbacks only; the mark itself is vector geometry.

---

## 3 · Token Source of Truth

Machine-readable source: [`brand/tokens.json`](brand/tokens.json).

Markdown and Mermaid cannot directly import JSON, so embedded hex values are mirrors of `tokens.json`. Change the token source first, then synchronize human docs and diagram classes.

| Semantic token | Fill | Stroke | Role |
|---|---|---|---|
| `project` | `#DDEFF8` | `#4F8FBA` | Project / Context / SDK |
| `runtime` | `#E7E1F8` | `#796BC4` | Harness / Session / Worker |
| `editorial` | `#F9DDE9` | `#D6679A` | Writer / Reader / Quality |
| `evidence` | `#F9EDCF` | `#BE892F` | Feedback / Corpus / Eval |
| `validated` | `#DCF1E7` | `#4D9B7D` | Accepted / validated output |
| `rejected` | `#F7DEE2` | `#B95767` | Reject / invalid / failed gate |
| `neutral` | `#FFFDFC` | `#62556D` | Story core / neutral mechanism |

Base ink: `#241D2B`; soft surface: `#F8F5FA`; cluster border: `#E2DAE8`.

### Token discipline

- Pastels are fill/accent colors, not low-contrast body text.
- State meaning must also use labels, shapes, borders, or edge styles.
- Do not rely on red/green alone for PASS/FAIL.
- Spacing follows a 4/8 rhythm.
- Node stroke defaults to about `1.75px`, primary edges to `2px`, feedback edges to dashed styling.

---

## 4 · Markdown Page Chrome

GitHub Markdown cannot depend on arbitrary CSS, so NovelForge page style uses portable primitives:

1. brand lockup on major landing pages;
2. `<kbd>` metadata chips for stable concepts;
3. story-thread divider for breathing space;
4. numbered H2 rhythm such as `01 · System map`;
5. semantic callouts such as `Boundary ✦` and `Why it matters`;
6. compact reference matrices only where tabular lookup is genuinely the job;
7. branded Mermaid for inspectable source diagrams;
8. small mark footer for a quiet close.

Recommended page skeleton:

```text
Logo / lockup
Tagline + metadata chips
Story-thread
One-sentence thesis
Hard boundary
01 · Primary visual / architecture
02 · Core concepts
Story-thread
03 · Navigation / deep links
04 · Principles / next step
Brand mark footer
```

Do not repeat a hero in every section. Brand identity comes from rhythm and consistency, not visual noise.

---

## 5 · Typography & Information Hierarchy

GitHub controls final fonts, so quality comes primarily from hierarchy and sizing rather than committed font files.

- exactly one H1 per page;
- numbered H2s establish navigation rhythm on presentation-oriented pages;
- H3s hold bounded detail;
- long sections may begin with a short bold lead;
- body paragraphs stay short and scannable;
- monospace is for IDs, schemas, paths, commands, and state machines;
- table cells do not hold essay-length prose;
- decorative Unicode / emoji never replace real labels;
- never solve overflow by shrinking body text until it becomes unreadable.

---

## 6 · Mermaid · Story Loom Grammar

Mermaid is the **inspectable source chart**. A rendered static chart may sit above it on presentation surfaces, but Mermaid remains diffable technical reference.

### Lane grammar

- **Project lane — sky**: inputs, Project SDK, Context;
- **Forge lane — lavender**: Harness, Session, Control Plane, Workers;
- **Story lane — neutral + sakura**: Story core, simulation, draft, reader quality;
- **Evidence lane — amber**: feedback, learning, corpus, eval;
- **Validated gate — mint**: user-visible / accepted / validated outcome;
- **Reject lane — danger**: actual reject/invalid states only.

### Shape grammar

- `([stadium])` — boundary / input / output;
- `{{hexagon}}` — decision / manager / semantic gate;
- `[(database)]` — durable runtime/state store;
- `[[subroutine]]` — reusable core mechanism;
- standard rounded node — processing step.

### Edge grammar

- solid = primary execution / dependency;
- dashed = feedback / evidence / resume / reference;
- one chart answers one core question;
- crossing edges are avoided by default;
- nuance belongs below the chart, not inside long node labels.

---

## 7 · Anime-editorial Budget 🌸

Welcome:
- sakura / lavender / mint accents;
- spark / petal / book / story-thread motifs;
- occasional `🌸 ✦ ✨ 📖` on landing surfaces;
- rounded SVG geometry;
- sparse friendly microcopy;
- a future original Framework mascot/editor motif, strictly decorative.

Avoid:
- emoji as the only architecture/status/navigation icon;
- mascots inside technical contracts;
- candy-colored body text;
- wall-to-wall glow or gradients;
- mixing anime, glassmorphism, brutalism, terminal styling, and skeuomorphism on one page;
- putting authority-bearing information only inside visual assets.

---

## 8 · Tier-A Static Visual Contract

Tier-A homepage/product visuals are a **presentation layer over maintained semantics**:

```text
claim / copy contract
→ information architecture
→ Story Loom layout
→ SVG source
→ real render inspection
→ deterministic lint
→ README integration
```

### Hard sizing rules

For a standard homepage visual:

- design around a `1200px`-class source viewBox unless the composition genuinely needs another size;
- validate the result at approximately **820px GitHub content width**;
- also inspect a narrow approximately **420px** render;
- projected body text at the 820px render must be **at least 12px**;
- headings must remain visually distinct after scaling;
- long text elements need an explicit width budget such as `data-max-width` when the deterministic checker can measure them;
- wrapping, clipping, and alignment are layout concerns, not reasons to reduce type below readability.

### Copy rules

- freeze the claim and information hierarchy before drawing boxes;
- write English and Chinese natively; do not reuse English geometry blindly for Chinese copy;
- shorten copy before shrinking type;
- a diagram label names a mechanism or decision, not an essay;
- detailed nuance belongs in nearby prose or the linked deep doc.

### Layout rules

- no text may leave its intended container;
- no important label may overlap an edge, icon, badge, or another text block;
- dense matrices require row/column rhythm and strong scan paths, not card soup;
- whitespace is part of the hierarchy and must not be consumed simply to fit more claims;
- mobile/narrow rendering may become visually denser, but it must remain legible and semantically ordered.

### Asset metadata

New or materially redesigned Tier-A SVGs should use:

- root `data-doc-tier="A"`;
- non-empty `<title>` and `<desc>`;
- system-font fallbacks only;
- no embedded or external font files;
- alt text at the Markdown integration site;
- provenance where required by repository policy.

---

## 9 · Render QA Is Mandatory

**Generated is not reviewed. XML-valid is not visually correct.**

Before a new or materially changed Tier-A visual is referenced from README:

1. render the SVG with a real renderer;
2. inspect it at desktop/GitHub-like width;
3. inspect it again at narrow width;
4. check overflow, clipping, wrapping, hierarchy, density, alignment and brand fit;
5. read every visible label after rendering, not only in source;
6. perform bilingual parity review while allowing native-language layout differences;
7. run `python scripts/docs_quality.py`;
8. only then integrate it into README.

If render inspection is unavailable, the visual remains **WIP** and must not replace a functioning Tier-A asset.

### Atomic replacement

Do not deliberately degrade a production landing page while redesigning an asset.

Preferred sequence:

```text
old visual remains live
→ new candidate passes render + copy + lint
→ one integration commit replaces the presentation
```

If an existing visual is actively misleading or broken, it may be removed for correctness, but that is an exception—not the normal redesign workflow.

---

## 10 · Accessibility / Resilience

- meaningful images have alt text;
- decorative dividers use empty alt text;
- charts have nearby textual explanation;
- core meaning survives if SVG fails to load;
- color and emoji are never the only semantic channels;
- no external font files are required;
- lightweight SVG is preferred;
- logo and charts remain clear against GitHub light/dark surrounding chrome.

---

## 11 · Definition of Done

A NovelForge page or Tier-A visual is complete only when:

- hierarchy is scannable before deep reading;
- copy is correct before decoration is considered;
- removing decoration still leaves rigorous engineering documentation;
- restoring the brand layer makes the surface recognizable as NovelForge;
- typography remains readable at GitHub rendering widths;
- no visible text is clipped, overflowing, collision-prone, or tiny;
- English and Chinese express the same claims while reading naturally in each language;
- actual render inspection has happened;
- deterministic documentation QA is green;
- the visual does not become a second authority for architecture or product claims.

**Story Loom is successful when the system feels engineered, the page feels editorial, and neither quality is sacrificed for the other. ✦**
