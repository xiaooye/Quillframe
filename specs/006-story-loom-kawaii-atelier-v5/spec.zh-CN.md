# Product Experience v5 · Story Loom Kawaii Atelier

## 状态

NovelForge 公共 Product Entry SPA 的候选实现契约。

本规格只取代 Product Entry v4 的**视觉表现与页面编排方向**，不取代 v4 已经真实交付的产品能力：SolidJS 路由、WeiUI foundation、Story Loom 语义 token、Command Palette、交互式 product labs、Hosted Studio 入口、构建期 Knowledge Explorer、文档 AST 渲染、Architecture explorer、Publication explorer、版本状态、可访问性与 authority 边界。

## 产品目标

公共站点必须像一个完整的创作工具产品入口，能够吸引潜在用户进入体验；不能再像文档门户，也不能像静态 SaaS 宣传页。

新的签名视觉方向是 **Story Loom Kawaii Atelier**：

- 旗舰级 creative-tool 完成度；
- 默认使用温暖纸张 / atelier 材质，不再以深色 dashboard chrome 作为主视觉；
- 信息密度高，但层级清楚；
- 用 playful editorial composition 组织不同章节，每一段都有自己的形状和节奏；
- kawaii 只作为精致人格：贴纸、圆润触感控件、少量颜文字/emoji 状态、纸页标签、胶带/丝带、柔和阴影与小型产品物件插画；
- Story Loom 的各条 lane 色真正承担信息组织，不再埋在灰紫玻璃下面；
- 可爱不能替代产品清晰度、证据、可访问性和专业可信度。

目标比例：**90% premium professional product design + 10% kawaii personality**。

## Foundation 与 authority

依赖方向保持：

```text
SolidJS application shell
→ generated WeiUI tokens + CSS primitives
→ Story Loom v2 semantic theme
→ NovelForge Product Experience composition
→ progressive modern-CSS enhancement
```

硬约束：

- 不建立第二套 design token authority；
- 不引入 React / `@weiui/react` / `@weiui/headless`；
- WeiUI 浏览器端 runtime JavaScript 仍为 0；
- 不 import Core 私有实现；
- Product Site 与 generated docs 始终 `authority=false`；
- 不伪造客户、用户量、价格、免费试用、运行时截图或社会证明；
- 不做默认轮询，也不做 decorative frame loop；
- 禁止无限 idle animation；
- `prefers-reduced-motion` 下必须得到完整静态终态；
- mobile 仍是一等产品面，触控尺寸继续派生自 `--nf-touch-target-min`。

## Customer journey

首页必须让用户无需先读文档，就能完成这条路径：

1. 认出 NovelForge 是一款面向小说创作的真实产品；
2. 在一个紧凑 Hero 内理解核心价值；
3. 看到并操作可信的产品工作台；
4. 直接触碰关键系统机制；
5. 进入真实产品入口：Studio、Knowledge、Architecture、Publication；
6. 检查实现证据与当前版本状态。

文档是产品能力与目的地之一，不是整个站点的视觉重心。

## 视觉语法

### Surface

默认表现为 light / warm。Dark 继续允许用户主动选择，但也必须使用 Story Loom chroma，不能再回到 OLED 黑色 SaaS 视觉。

沿用现有语义 lane：

- Project blue → project/context；
- Runtime violet → Studio/runtime；
- Editorial pink → reader/editorial；
- Evidence gold → knowledge/evidence；
- Validated mint → accepted/pass/readiness；
- Rejected rose → failed/rejected。

### Shape language

允许形成签名感的装置包括：

- scalloped / perforated 纸边；
- sticker tab 与 tape corner；
- notebook / atelier window；
- 非对称 bento 与叠放纸页；
- 在 WeiUI primitive 语义之上的 soft clay / tactile 控件；
- squircle / `corner-shape` 渐进增强；
- 少量星星、爱心、丝带、颜文字作为次级状态语言；
- 有价值时用 CSS/SVG 组成的小型产品物件插画。

禁止整页继续由同一种圆角玻璃卡组成。

### Typography

- Hero 标题保持紧凑，不允许一个标题占满整个 viewport；
- 中文拥有独立几何与 native copy；
- display 字体可以更有性格，但正文必须保持高可读系统/sans 栈；
- 高密度 section 主要依赖清晰层级，不依赖巨大留白分隔。

## 交互语法

首页每一个主要 section 都必须包含有意义的交互或真实导航目标。

保留并强化现有真实交互：

- `Cmd/Ctrl+K` Command Palette；
- context budget lab；
- same-candidate readiness lab；
- Product capability browser；
- Hosted Studio；
- Architecture explorer；
- Publication profile switcher；
- Knowledge 搜索/筛选/全文文档 route。

视觉交互可使用 tactile press、layered focus、hover depth、scroll-linked reveal、anchored tooltip/popover、View Transition、container-responsive composition 等增强。

用户不滚动、不交互时，视觉效果应停止；禁止 ambient perpetual motion。

## 首页结构

v5 必须包含：

- **Atelier Hero**：紧凑价值主张 + 真实入口 + 可操作 workspace/desk composition；
- **Story Loom strip**：lane-colored capability objects/tabs，并即时反馈选中状态；
- **Workbench spread**：Context / Readiness labs 作为一个有设计感的 notebook/workbench spread，而不是两张普通 dashboard 卡；
- **Product shelf**：非对称产品入口，Studio 为主要 surface，Knowledge / Architecture / Publication 各自拥有不同视觉身份；
- **Knowledge shelf**：真实 compiled docs/search preview，可见 source truth，但不把首页变成 docs chrome；
- **Trust/footer**：当前 release、GitHub/source 与 no-authority truth 紧凑呈现。

## Route 结构

`/product`、`/studio`、`/architecture`、`/publication`、`/docs`、`/docs/:docId`、`/changelog` 必须明显属于同一套 application shell，不能再以巨大 brochure headline 开场。

使用紧凑 product toolbar、侧边/行内 control、高密度 interactive panel 与 route-specific visual objects。

`/docs` 继续是完整 Knowledge Explorer；`/docs/:docId` 继续使用结构化 AST reader。

## Modern CSS policy

在正确 guard 下允许渐进使用：

- `color-mix()` / OKLCH；
- container size/style queries；
- 支持时使用 scroll-state queries；
- scroll/view timelines；
- View Transitions；
- `:has()`；
- `@property`；
- `@scope`；
- `@starting-style` + discrete transitions；
- CSS anchor positioning / position fallback；
- mask、gradient、blend mode、filter；
- interaction-driven motion path；
- 支持时使用 `corner-shape` 等新 shape primitives。

缺少任何一个增强能力时，基础产品仍必须完整可用。

## Acceptance

v5 只有在以下条件全部满足时才可接受：

- Product Site quality gate 通过；
- TypeScript 与 Vite production build 通过；
- Cloudflare production deploy 通过；
- WeiUI exact generated foundation 继续验证通过；
- generated Knowledge corpus 仍可用；
- desktop/mobile 无水平溢出；
- keyboard focus 与 reduced-motion 正确；
- 新用户第一次访问默认是 warm Story Loom Atelier，而不是 v4 dark glass；
- 首页 section 节奏明显非模板化，信息密度明显高于 v4；
- Studio / Knowledge / Architecture / Publication 都保持直接可操作；
- 所有产品主张都不超过当前真实实现。
