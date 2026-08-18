# Quillframe 全产品视觉语言统一 · 规范

## 状态

- Primary task mode：`SYSTEM-IMPROVE`
- Base main：`e49304bde7fb0c5ba0822deb3823f960c6425804`
- Working branch：`ui/homepage-product-language-unification`
- 设计权威：当前 Product Homepage
- 架构边界：SolidJS + TypeScript + Vite / Tauri 2 / Python Core / SQLite / Astro + Starlight

## 目标

把 Product Site、Docs 与 Studio 收敛为同一套 Quillframe 产品语言，同时保持三类 surface 的信息密度与用途差异。Homepage 保持视觉 reference；其他页面向 Homepage 的设计 DNA 对齐，而不是反向重做 Homepage。

核心视觉模型：

`PAGE == CANVAS`

Hero 的 eyebrow、标题、说明、actions 直接参与 page composition。Hero 本身不是 Card；只有真实 visual object、工具表面、文稿、预览、diagram node、code surface 等内容对象可以成为 bounded surface。

默认 light canvas 为 white / warm ivory / near-white。语义色用于小面积状态、图标、节点、标签、选中项、annotation 与 focus/hover，不作为 route wallpaper。

## 全局产品语言

层级优先级：

`whitespace → typography → alignment → composition → tint/color → decoration → border only when needed`

必须避免：card soup、giant hero card、universal 1px border、nested panel syndrome、route rainbow background、generic admin dashboard、late override CSS、`!important` specificity hack、无限 idle animation 与默认 polling。

Kawaii 通过比例、圆润触控目标、tiny label、index/tape/stitch/sparkle、轻微不对称与友好 microcopy 表达，不通过大面积 pastel wallpaper 或 emoji 堆叠表达。

## Shared shell contract

Public Product Site 的 top navigation、mobile navigation、footer 与 command palette 必须共享同一个可追踪的 navigation model，不能各自硬编码后漂移。

Primary product entries 至少包括：

- Product
- Studio product landing
- Architecture
- Publication
- Docs / Knowledge
- GitHub repository

Utility entries 至少包括：

- Project Inspector
- Local Playground
- Agents
- Changelog
- Hosted Studio

`GitHub` 必须作为真实 external entry，指向 repository root，并使用安全的新窗口 external-link semantics。Footer 与 top navigation 的 primary product section 必须同步；mobile navigation 也必须暴露同一组 primary entries。Command palette 必须能到达 Changelog、GitHub 与 Studio landing，并将 Hosted Studio 与 Studio product landing 明确区分。

可见版本标识必须与当前 0.9.x development line 一致，不保留 0.8.x shell 文案。

## Public routes

必须逐页 audit：`/`、`/product`、`/studio`、`/architecture`、`/publication`、`/inspect`、`/playground`、`/agents`、`/changelog`。

Homepage 保持 reference。

Product：hero borderless；原则内容改为 editorial numbered composition，不使用机械 2x2 SaaS cards。

Studio landing：hero borderless；Hosted Studio visual 可以是独立 workstation object；说明区避免 card grid。

Architecture：白色/ivory 工作纸；interactive execution path 仍真实可用；节点只保留轻量 semantic accents；移除大面积 rainbow radial background 与 dashboard-card feel。

Publication：编辑出版桌 / proofing workspace；格式差异由 paper/browser/EPUB object、typography 与 metadata 表达，不由整页或大面积格式色表达。

Inspect：轻 intro + manifest/lock/attestation workspace，避免 hero-card + tool-card 双层结构。

Playground：scratch workspace；输入与结果是工具 surface，页面本身不是工具卡。

Agents：bridge / wiring workbench；host selector 保持真实交互，避免 host card soup。

Changelog：editorial release notebook / timeline，不做 release card grid。

## Docs

继续 Astro + Starlight。Docs 继承 shared semantic foundation，但采用 reading-first composition：文章和标题直接属于 canvas；sidebar 不做 card stack；code/table/callout 在需要边界时成为局部 surface；中文长文阅读节奏、搜索、语言、主题、TOC、mobile sidebar 与 accessibility 不得退化。

## Studio

Studio 保持 authoring-environment-first。整体为 warm ivory/white workstation，不做 pastel dashboard wallpaper。`.nf-page-intro` 或等价 page intro 的 title/eyebrow/actions 必须属于 workspace canvas，而不是 generic rounded admin card。

Writer Mode 与 Inspector Mode 的真实功能、Core Bridge、settings、model configuration、runtime/session/semantic inspection 均必须保留。Desktop 可多栏，tablet progressive reduction/overlay，phone focus-first。

## Responsive / Accessibility

验证宽度至少约 1440 / 1024 / 768 / 430 / 375。最低 interactive target 44px。保留 semantic HTML、keyboard navigation、visible focus、logical focus order、`aria-expanded`、dialog semantics、skip links、reduced motion、对比度、非 hover-only 与非 color-only state。

## Quality contract

更新 stale visual tests，不删除 gates。Quality 应保护：Homepage visual authority、canvas-first hero、white kawaii baseline、restrained semantic color、no card soup、responsive、touch target、accessibility、real interaction、single style ownership、no specificity hacks、no infinite animation/polling、Docs readability、Studio authoring density。

旧的 `ProductSurfaceHero` 28px radius + shadow + dashed frame 不是 invariant，必须从 quality contract 移除。

Shared shell quality 必须增加 GitHub entry 与 header/footer/mobile navigation synchronization 检查。

## Completion truth

只有 deterministic build/tests、responsive/accessibility checks 与实际 visual QA 完成后才能进入 `review / awaiting_user`。不得自行宣布 design accepted，不得 merge main。