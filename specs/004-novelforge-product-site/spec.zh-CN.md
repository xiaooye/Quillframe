# NovelForge 产品站 — Godot Web 规范

**状态：** 当前实现契约  
**范围：** 公开产品站 `site/**`。独立的本地 Studio 应用 `studio/app/**` 不属于本次替换范围。

## 1. 产品边界

NovelForge 在浏览器中明确分成两个应用：

- **Product surfaces：** `/`、`/product`、`/studio`、`/architecture`、`/publication`、`/inspect`、`/playground`、`/agents`、`/changelog`。
- **Documentation：** `/docs/**`。

Product surfaces 由同一个持续存活的 **Godot 4.7.1 Web** runtime 渲染；Documentation 由 **Astro 7.1.6 + Starlight 0.41.5** 输出 semantic HTML。

`site/src/**` 下原 SolidJS/Vite Product implementation **不再是 Product runtime**。它只作为非权威的 Story Loom / Kawaii Atelier golden visual-and-behavior fixture 保留，用于 screenshot parity QA。默认 Product `dev` / `build` 与 production deployment 必须进入 Godot，绝不能把这个 fixture 当成 fallback Product application。

## 2. Runtime 契约

### G1 — Godot-first Product UI

Product runtime 必须使用 GDScript、Compatibility renderer、自适应 Web canvas，以及 single-thread Web export（除非未来明确改变 hosting contract）。Product UI 使用 Godot `Control` / Canvas primitives。

### G2 — 2D + 有控制的 2.5D

公开 Product runtime 不得引入 `Node3D`、`Camera3D`、mesh、3D physics 或 3D scene stack。空间感来自分层 2D surface、elevation、有限 parallax、route-specific composition 与 interaction feedback。

禁止持续 decorative idle animation。动画只能围绕 route transition 或用户交互短时运行。浏览器启用 `prefers-reduced-motion: reduce` 时，必须保留清晰最终状态并停止 decorative motion。

### G3 — 真实 browser route，不重启 Product

每个 Product route 必须可以直接访问。Product 内部导航必须同步 `history.pushState`。浏览器前进/后退必须通过保留的 `JavaScriptBridge` callback 驱动当前 Godot scene，不应故意 reload document。

进入 `/docs/**` 必须使用 hard document navigation；缺失的 Docs path 不得回退成 Product canvas。

### G4 — Responsive scene composition

Runtime 必须从真实 browser viewport 推导布局，并明确提供 `desktop`、`compact`、`phone` 三种状态。Phone composition 必须是独立 responsive geometry，而不是缩小 desktop scene。

## 3. 视觉 authority 与 parity

### G5 — 保留 Story Loom / Kawaii Atelier

视觉契约由两层互补来源共同约束：

1. `assets/brand/tokens.json`、WeiUI integration metadata 与已提交的 Story Loom brand assets 定义 canonical design primitives 与品牌值。
2. `site/src/**` 下保留的 SolidJS/Vite Story Loom / Kawaii Atelier implementation 只作为迁移用的 **golden rendered visual-and-behavior fixture**。

Godot 必须保留已批准 baseline 的 page grid、typography hierarchy、margin、alignment、wrap、responsive flow、route identity、interaction 与 Kawaii Atelier composition。必须使用确定性固定版本字体与 fallback resources，避免 browser/Godot comparison 因 runner font 漂移。

Golden fixture 没有 production runtime authority，也不得作为 fallback Product application 发布。当前实现不要求另建一个独立权威的 generated GDScript token file；真正 implementation gate 是 current Godot source/parity contracts 与 current-HEAD browser evidence。

## 4. 语言与可访问性

### G6 — 双语 Product 契约

Product 支持 `en-US` 与 `zh-CN`，提供 scene 内显式语言切换，使用 browser storage 持久化选择，并在首次访问时尊重 browser locale。进入 Docs 时跟随当前 Product locale：英文进入 `/docs/en/`，中文进入 `/docs/`。

### G7 — 交互可访问性

Product 可交互控件必须保留 canonical minimum touch target、keyboard focusability、可见 focus treatment 与 reduced-motion 行为。Source/browser QA 对这些 interaction contract 的 regression 必须 fail closed。

## 5. Documentation 契约

`/docs/**` 保持 web-native，以保留长文阅读、semantic link、文本选择、索引、accessibility 与 localization。Starlight 独占 Docs routing/output；Godot 不得接管 Docs path。

## 6. 构建与部署契约

组合构建顺序：

1. staging 并构建 Starlight Docs 到 `site/dist/docs/`；
2. 通过唯一、已经过 parity/size gate 的 exporter 导出 Godot Web runtime；
3. 将 Product artifact 合并到 `site/dist/` root，同时保留 `site/dist/docs/**`；
4. 保留 `_redirects` 等 root routing files；
5. 验证每一个 production asset 都低于 hosting platform individual-file ceiling；
6. 将组合目录部署到 Cloudflare Pages；
7. 实际验证 custom domain 的 `/` 与 direct Product route 由 Godot 提供，而 `/docs/` 仍由 Starlight 提供。

Product bundle size 不是 UX 优化目标。只有 hard hosting/deployment constraint 才构成压缩体积的理由。

## 7. Browser acceptance evidence

最终 current-HEAD acceptance evidence 必须证明：

- Godot engine 启动且 scene 达到 `ready`；
- root 与 deep Product URL 都解析为 Godot host；
- `/docs/` 仍为 Starlight HTML；
- desktop/phone responsive states 正常；
- Kawaii Atelier geometry/typography 与保留的 golden fixture 保持实质一致；
- locale、appearance、command palette、mobile menu 与 browser history interaction 正常；
- 保存代表性 screenshot 作为 visual regression evidence；
- deploy 后 live custom domain 实际提供预期的 Godot/Starlight split。

Visual diff metric 是证据，不是重新设计 approved baseline 的许可。即使没有设置单一数值阈值，结构性 layout、typography 或 interaction regression 仍属于 blocking failure。

## 8. Authority 边界

公开 Product Site、golden visual fixture 与 Docs 都只是 presentation/navigation/test surface，不拥有 Canon、Memory、Settlement、Framework-write、production-readiness 或 Publication authority。任何 visualization/browser projection 都不会成为第二 source of truth。
