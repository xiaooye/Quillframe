# Documentation Standard

Quillframe 文档只遵守一个最重要的视觉与信息原则：**THE PAGE IS THE CANVAS。** 结构先由 typography、spacing、alignment 与 semantic sequence 建立，再考虑 container。

## Information Architecture

主要文档先用一段话给 mental model；只有空间关系真的能帮助理解时，才加入一张 canonical diagram；随后进入详细解释，contract/schema/reference 放在后面，不要一开页就倒 schema dump。

Docs Home 的信息架构固定为 Start Here、Core Concepts、Writing、Quality、Canon & Settlement、Context & Memory、Learning、Semantic Execution、Session & Control Plane、Corpus & Research、Project Integration、Development、Reference。

## Canvas First, Cards Second

默认状态：no container。

Spacing 能建立 group，就不要画 border；极淡 semantic wash 能建立 group，就不要画 border；typography 能建立 hierarchy，就不要画 border。

只有真实 artifact、state、comparison 或明确 conceptual boundary 才使用边界。禁止 framed section 里再塞 framed card 的嵌套结构。

## Visual Language

Base canvas 使用 warm ivory / soft off-white，正文用 graphite ink；大字号 display type 建立 editorial hierarchy；technical label 小、精确、安静。Kawaii personality 只是克制 accent——全页大约 5%，高密度 technical diagram 甚至更少。

允许极少量 spark、tape fragment、ribbon marker、soft index tab；一张图通常 0–3 个 decorative detail 就够了。

## Semantic Color

Project = soft blue；Runtime = violet；Editorial = soft pink；Evidence = warm cream/gold；Validated = mint；Rejected/Stale = soft rose；Neutral = warm paper + graphite。颜色负责 signal，不能成为唯一的信息载体。

## Diagram Rules

Technical architecture 默认 SVG：diffable、inspectable、scalable、accessible。优先 open group、text-only node、thin connector、short rule、small semantic marker，而不是重复 rounded rectangle。

所有 documentation SVG 必须有 meaningful `<title>` / `<desc>`、可读 label、足够 contrast；结构复杂时文档正文还要有 textual explanation。禁止 AI-generated raster 代替 technical diagram。

## Public Brand 与 Technical Namespace

Quillframe 是 current public brand。旧品牌只在 historical record 或 compatibility identifier 中保留。Repository name、schema ID、`novelforge.toml`、`novelforge.lock.json`、workflow name 与 stable contract ID 属于 technical namespace，禁止 global replace。

## Bilingual Parity

English / 简体中文是 semantic parity 的 native edition，不做逐行硬翻。Canon、SETTLE、Candidate Lineage、Context Manifest 等正式 term 在能提升 contract precision 时可以保留英文。

## Source Hierarchy

Current implementation、schema、tests、current manifest 高于 explanatory docs。Historical spec 保留当时设计记录与当时名称；current docs 可以链接，但不能重写历史。
