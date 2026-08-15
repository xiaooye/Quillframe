# Specification · NovelForge Product Entry SPA v4

## Baseline

- Framework 开发基线：latest `main`。
- Change class：Product Web surface / structural feature。
- Primary mode：`SYSTEM-IMPROVE`。
- Parent Product Site contract：`specs/004-novelforge-product-site/`。
- v4 是 Product Entry architecture，不是 v3 的视觉 patch。

## Product identity

NovelForge 公共站点是一等 **Product Entry SPA**：它负责吸引潜在用户、展示真实产品能力、提供可操作入口、承载产品知识浏览，并把用户带到 Studio / Publication / Architecture / Docs / GitHub 的正确下一步。

它不是：

- docs skin；
- GitHub README 镜像；
- 静态 marketing brochure；
- 伪造的 SaaS dashboard；
- Generic Core 或 Canon authority。

## Foundation authority

Product Entry 的依赖方向固定为：

`SolidJS application shell → WeiUI tokens/CSS primitives → Story Loom v2 semantic theme → NovelForge Product Entry composition/motion`。

硬要求：

- WeiUI 继续拥有基础 UI contract；
- `assets/brand/tokens.json` 继续是 NovelForge product-token authority；
- `assets/brand/weiui.integration.json` 继续是 WeiUI exact-consumption contract；
- `assets/brand/story-loom.weiui.css` 继续是 live semantic theme；
- 不建立第二套 palette / focus / touch / spacing / component foundation；
- 不引入 `@weiui/react` / `@weiui/headless`；
- Product Entry 可以有 site-only composition variables，但必须从 Story Loom/WeiUI semantic variables 派生。

## Visual direction · premium cute

目标是 **premium cute creative-tech**：专业、精密、有亲和力、有收藏感，不走 austere luxury magazine，也不走廉价粉紫 AI SaaS。

Story Loom lane colors 必须成为真实材质系统：

- project blue；
- runtime violet；
- editorial pink；
- evidence gold；
- validated mint；
- rejected rose。

允许：

- 小型 kawaii mascot / sticker / emoji / 颜文字；
- 微型星星、心形、丝带、闪光、纸张/玻璃/糖果材质反馈；
- 可爱但克制的空状态与成功状态；
- kawaii 作为状态语言，不作为 fake customer/avatar social proof。

禁止：

- 大量无意义 anime hero 人物盖过产品本身；
- fake testimonials / fake users / fake usage stats；
- glass-card soup；
- 单纯黑白 editorial 大标题 + 大留白；
- generic purple-gradient SaaS。

## Product Entry surfaces

### Home

首页必须在首屏和前两屏内提供真实下一步：

- Open Studio；
- Search / Command Palette；
- Explore product capabilities；
- Explore Architecture；
- Browse Publication；
- Browse Knowledge / Docs。

首页不再使用长篇 brochure narrative 作为主交互。产品价值通过可操作 surfaces 展示。

### Studio

`/studio` 不是静态介绍页：

- 说明 current hosted/read-only Studio 的真实边界；
- 提供明显的 hosted Studio CTA；
- 展示真实产品能力入口与状态，不伪装 Core 已绑定；
- hosted surface capability 永远不产生 Canon / Settlement / Framework-write authority。

### Knowledge Explorer

`/docs` 必须成为站内 Knowledge Explorer，不只是 GitHub links。

Build-time pipeline：

`docs/documentation_manifest.json → maintained Markdown source → safe structured AST + search index → static Product Entry assets`。

要求：

- repository Markdown 始终是 content authority；
- 不建立第二 CMS；
- 浏览器运行时不依赖 GitHub API；
- 不把 raw Markdown HTML 未经处理地注入 DOM；
- exact source path / tier / status / authority metadata 可见；
- 中英文按 manifest 的对应 source 构建；
- 支持站内搜索、文档打开、目录、代码块、列表、引用、表格等核心内容结构；
- `/docs/:docId` 可 deep-link。

### Architecture / Publication / Product

这些 route 必须从“静态标题页”升级成 interactive product surfaces：

- 可展开/聚焦的 system map；
- capability/detail popovers；
- Publication profile explorer；
- source truth / boundary drill-down；
- keyboard / touch 可操作。

## Global interaction model

必须提供：

- Command Palette / global search；
- keyboard shortcut（例如 `⌘K` / `Ctrl+K`）；
- mobile-safe equivalent；
- route-aware search results；
- document / product / architecture unified navigation；
- visible focus；
- ≥44×44px touch targets。

Popover / dialog / anchor positioning 可 progressive enhance；fallback 必须保持可操作。

## Modern CSS / Web UI enhancement budget

允许尽可能广泛使用现代 CSS/HTML，但必须有 graceful fallback：

- container size/style queries；
- subgrid；
- `:has()`；
- `color-mix()` / relative semantic color derivation；
- cascade layers / nesting / `@scope` where appropriate；
- masks / clip-path / filters / blend modes；
- conic/radial/mesh-like layered gradients；
- 3D transforms / perspective；
- CSS motion path for small decorative state effects；
- scroll-driven animations / view timelines；
- View Transitions；
- Popover API + Anchor Positioning；
- `@starting-style` + `transition-behavior: allow-discrete`；
- container-driven density changes；
- `content-visibility` for large knowledge content；
- semantic native controls and top-layer behavior。

Hard limits：

- no scroll-jacking；
- no default polling；
- no infinite idle decorative loops；
- no mandatory pointer-only interaction；
- reduced-motion must expose the complete final state；
- unsupported experimental syntax cannot be the only path to content or navigation。

## Information density

v4 不允许以“巨型标题 + 巨大空白”作为主要节奏。

Desktop：

- 每个 viewport 应出现多个可理解或可操作信息点；
- section spacing 应服务 hierarchy，不制造 brochure 空洞；
- product surfaces 优先于纯说明文本。

Mobile：

- 不压缩成不可触控的 dashboard；
- progressive disclosure；
- horizontal scrolling 只能用于明确的可选 carousel，不能承担必读内容。

## Content truth

Product Entry 可以重新组织信息，但不得提升 authority：

- static product proof 来自 current maintained contracts；
- illustrative state 必须标识为 illustrative/derived；
- hosted Studio 的未绑定 Core 状态必须真实呈现；
- Documentation AST/search index 是 source Markdown 的 build-time derivative，`authority=false`；
- Publication/Readiness/Canon 真相继续属于各自 Core contract。

## Acceptance

1. Product Site 自我定位为 Product Entry SPA，而不是 docs site。
2. WeiUI / Story Loom foundation 可由 deterministic QA 证明。
3. Home 前两屏包含至少 4 个真实、可操作 product entry points。
4. 全局 command/search surface 可用 keyboard + touch 操作。
5. `/docs` 读取 build-time generated repository documentation data。
6. 至少一个真实文档可在 SPA 内完整浏览，不需要跳 GitHub。
7. `/docs/:docId` deep link 工作。
8. Architecture / Publication / Studio 至少各有一个真实 interactive affordance。
9. 简中为 native copy；技术标识只在需要时保留英文。
10. premium cute 视觉来自 Story Loom semantic colors，不建立平行 palette。
11. 可加入 emoji / 颜文字 / kawaii sticker state language；不得伪造 social proof。
12. modern CSS enhancement 在 reduced-motion / unsupported feature 下仍保留完整功能。
13. TypeScript/Vite build、Product Site quality、Cloudflare deployment deterministic green。
