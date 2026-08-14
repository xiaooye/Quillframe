# NovelForge Documentation Design System

> **Design target:** professional technical editorial first, warm/cute accents second.
>
> The visual layer helps readers scan and understand NovelForge. It never changes runtime, Canon, quality, or authority semantics.

## 1. Personality

NovelForge should feel like a serious developer framework with an editorial-fiction identity—not a generic SaaS dashboard and not a pastel toy UI.

**Ratio:** `80% technical / 20% warm editorial`.

- precise, calm, structured;
- friendly without being childish;
- visually memorable without competing with the documentation;
- manga/editorial influence expressed through composition and accents, not fandom imagery.

## 2. Core visual tokens

| Token | Hex | Role |
|---|---|---|
| `ink-950` | `#2B2433` | primary text / diagram labels |
| `ink-700` | `#5F5368` | secondary text |
| `surface` | `#FFFDFB` | warm neutral surface |
| `surface-soft` | `#F8F6FA` | grouped content / subtle panels |
| `sakura` | `#D982A8` | brand accent / human-editorial lane |
| `lavender` | `#8B7AC6` | runtime / agent orchestration lane |
| `sky` | `#5B98C4` | project / context / engineering lane |
| `mint` | `#58A98C` | accepted / validated / safe progress |
| `amber` | `#C9973B` | evidence / corpus / caution |
| `danger` | `#B65363` | rejection / invalid transition / failure |

### Color discipline

- Pastels are **fills**, not low-contrast body text.
- Every meaningful state needs a label, border, icon, line style, or shape in addition to color.
- Never use red/green alone to distinguish outcomes.
- Keep text and primary diagram labels dark enough for comfortable GitHub light-mode reading.

## 3. Typography

GitHub controls rendered fonts, so the system relies on hierarchy rather than custom font files.

- one H1 per page;
- H2 for major concepts, H3 for bounded details;
- short bold lead sentence before long sections when helpful;
- keep paragraphs compact and scannable;
- prefer concise tables for capability comparisons;
- use monospace only for IDs, schemas, paths, commands, and state machines.

Do not fake typography with Unicode decorative characters.

## 4. Layout rhythm

Use a predictable documentation sequence:

1. **Title + one-sentence value proposition**
2. **Navigation / language switch**
3. **Hero or key architecture visual** when useful
4. **At-a-glance cards/table**
5. **Main explanation**
6. **Deep links / next steps**

Keep decorative material out of dense reference sections.

## 5. Components

### Hero

Use one static SVG/WebP hero only on major landing pages. It should contain no authority-bearing information that is unavailable in text.

### Chips / badges

Use badges for stable metadata such as version, documentation language, execution model, or CI status—not as paragraph decoration.

### Callouts

Prefer semantic blockquotes:

- **Key idea** — conceptual invariant
- **Boundary** — authority / safety constraint
- **Why it matters** — reader-oriented explanation
- **Example** — bounded illustration

Avoid a wall of callouts.

### Tables

Use tables for comparisons and matrices, not for long prose. Keep headings noun-like and cells short.

## 6. Mermaid chart language

Mermaid is the authoritative architecture representation. Static illustrations are supplementary.

### Visual grammar

- `sky` — Project / Context / SDK
- `lavender` — Harness / Session / Control Plane / Workers
- `sakura` — Writer / Reader / human-facing quality flow
- `amber` — Evidence / Corpus / Learning inputs
- `mint` — validated result / user-visible gate
- `danger` — rejected / forbidden / invalid state

### Diagram rules

1. One chart answers one question.
2. Prefer left-to-right for pipelines; top-to-bottom for layered architecture.
3. Separate the **production path** from **feedback/learning loops**.
4. Use subgraphs only when they reduce cognitive load.
5. Keep node labels short; explain nuance below the chart.
6. Use dashed edges for feedback/reference paths, solid edges for primary execution/dependency.
7. Avoid crossing edges when a simpler diagram can express the same concept.
8. Do not encode meaning by fill color alone.

### Base class pattern

```mermaid
flowchart LR
    A[Project] --> B[Harness] --> C[Quality Gate]

    classDef project fill:#DDF2FF,stroke:#5B98C4,color:#2B2433,stroke-width:1.5px;
    classDef runtime fill:#E8DDFB,stroke:#8B7AC6,color:#2B2433,stroke-width:1.5px;
    classDef gate fill:#D9F5E5,stroke:#58A98C,color:#2B2433,stroke-width:1.5px;

    class A project;
    class B runtime;
    class C gate;
```

## 7. Cute-style budget

Allowed:
- gentle accent colors;
- rounded diagram nodes;
- sparse editorial sparkles in a hero illustration;
- one small character/editorial motif in future original art;
- subtle wordplay in section microcopy when it does not reduce clarity.

Avoid:
- emoji as structural icons;
- kawaii mascots in technical reference pages;
- excessive gradients/glows;
- candy-color text;
- decorative dividers every few paragraphs;
- mixing anime, glassmorphism, brutalism, and terminal aesthetics on one page.

## 8. Accessibility and resilience

- meaningful images require alt text;
- charts need nearby text explanation;
- important information must remain understandable if SVGs fail to load;
- color cannot be the sole semantic channel;
- visual additions must not depend on external font files;
- prefer lightweight SVG over large raster assets when possible.

## 9. Definition of done

A documentation change is visually ready when:

- hierarchy is obvious at a glance;
- the page can be scanned before it is read deeply;
- visual accents are consistent with this token system;
- diagrams use the shared visual grammar;
- decorative art is supplementary, accessible, and lightweight;
- the page still feels like engineering documentation after all decoration is removed.
