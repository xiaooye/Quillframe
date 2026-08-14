# NovelForge Visual System · 视觉系统

NovelForge 文档使用两层视觉表达：

1. **Executable Diagrams**：用 Mermaid 表达 architecture、state machine、learning loop、project workflow、dependency graph。
2. **原创 Anime/Manga-inspired Editorial Art**：少量 hero/section 装饰图，让仓库更有识别度，但不能把技术文档变成角色同人页。

## Visual Principles

- 技术文档的专业性优先；
- 使用统一原创视觉系统，不堆无关 stock art；
- Anime-inspired illustration 只负责装饰，不承载 authority；
- Generic Framework asset 不得出现任何 consumer novel 人物或 project-specific imagery；
- 不使用版权 franchise character、logo 或直接模仿特定画师；
- 没有装饰图时，Mermaid diagram 仍必须完整可读；
- 每个 static image 都记录 source/provenance 与 generation/edit date。

## Planned Asset Set

```text
assets/
├── hero-framework.webp        # 仓库主视觉
├── hero-learning.webp         # Adaptive Learning / Corpus section art
├── hero-project-sdk.webp      # Novel-as-software-project section art
├── diagrams/                  # 只有需要时才导出的 static diagram
└── provenance.json            # asset provenance / prompt intent / license status
```

Static asset 真正存在前，Framework release 不得在 README 里引用不存在的图片。Mermaid 始终是 authoritative architecture representation。

## Hero Art Direction

**Framework Hero**：原创近未来 editorial studio。小说作者/工程师面对 story graph、relationship nodes、manuscript pages、tests 与 agent terminals。画面专业、清爽，有克制的 manga/anime character design，不出现 franchise references，不放可辨识的版权文本。

**Learning Hero**：原创 editor-researcher 在多本抽象书籍和 evidence card 之间做对照，旁边 graph 展示 user feedback → hypothesis → corpus discovery → benchmark → eval。

**Project SDK Hero**：把一本小说 repo 视觉化成 software workspace：Canon/state modules、plans、tests、manuscripts、build artifact；不描绘任何具体真实小说。

## Provenance

Generated art 应记录：
- asset ID；
- original generation/edit method；
- date；
- high-level prompt intent；
- 是否使用 user-provided reference；
- license/use note。

不会为了“好看”把 font files 或第三方版权图片直接 commit 进 repo。
