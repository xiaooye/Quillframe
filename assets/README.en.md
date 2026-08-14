# NovelForge Visual System

NovelForge documentation uses two visual layers:

1. **Executable diagrams** — Mermaid charts for architecture, state machines, learning loops, project workflows, and dependency graphs.
2. **Original anime/manga-inspired editorial art** — sparse decorative hero/section artwork that makes the repository memorable without turning technical documentation into a character fandom page.

## Visual principles

- professional technical-documentation first;
- one coherent original visual identity rather than unrelated stock art;
- anime-inspired illustration is decorative, never authority-bearing;
- no consumer-novel characters or project-specific imagery in framework assets;
- avoid copyrighted franchise characters, logos, or direct artist imitation;
- diagrams remain readable without decorative images;
- every static image records source/provenance and generation/edit date.

## Planned asset set

```text
assets/
├── hero-framework.webp        # main repository hero art
├── hero-learning.webp         # adaptive learning / corpus section art
├── hero-project-sdk.webp      # novel-as-software-project section art
├── diagrams/                  # exported static diagrams only when useful
└── provenance.json            # asset provenance / prompt intent / license status
```

The framework release must not reference a static asset until that file actually exists. Mermaid remains the authoritative architecture representation.

## Hero art direction

**Framework hero:** an original near-future editorial studio where a novelist/engineer works across floating story graphs, character relationship nodes, manuscript pages, tests, and agent terminals. Clean professional composition, subtle manga/anime character design, restrained color palette, no franchise references, no readable copyrighted text.

**Learning hero:** an original editor-researcher comparing multiple abstract books and evidence cards while a graph turns user feedback into hypotheses, corpus discovery, benchmarks, and evals.

**Project SDK hero:** a novel repository visualized like a software workspace—Canon/state modules, plans, tests, manuscripts, build artifacts—without depicting any specific real novel.

## Provenance

Generated art should record:
- asset ID;
- original generation/edit method;
- date;
- high-level prompt intent;
- whether any user-provided reference was used;
- license/use note.

No font files or third-party copyrighted image assets are committed merely to improve appearance.
