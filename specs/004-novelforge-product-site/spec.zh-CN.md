# NovelForge 产品站 — Godot Web 规范

**状态：** 当前实现契约  
**范围：** 公开产品站 `site/**`。独立的本地 Studio 应用 `studio/app/**` 不属于本次替换范围。

## 1. 产品边界

NovelForge 在浏览器中明确分成两个应用：

- **Product surfaces：** `/`、`/product`、`/studio`、`/architecture`、`/publication`、`/inspect`、`/playground`、`/agents`、`/changelog`。
- **Documentation：** `/docs/**`。

Product surfaces 由同一个持续存活的 **Godot 4.7.1 Web** runtime 渲染；Documentation 由 **Astro 7.1.6 + Starlight 0.41.5** 输出 semantic HTML。`site/**` 下原 SolidJS/Vite Product implementation 已退役，不得重新作为 fallback Product runtime 引入。

## 2. Runtime 契约

### G1 — Godot-first Product UI

Product runtime 必须使用 GDScript、Compatibility renderer、自适应 Web canvas，以及 single-thread Web export（除非未来明确改变 hosting contract）。Product UI 使用 Godot `Control` / Canvas primitives。

### G2 — 2D + 有控制的 2.5D

公开 Product runtime 不得引入 `Node3D`、`Camera3D`、mesh、3D physics 或 3D scene stack。空间感来自分层 topology、elevation、parallax、glow、route accent 与短时 execution packet motion。

禁止持续 decorative idle animation。动画只能围绕 route transition 或用户交互短时运行。浏览器启用 `prefers-reduced-motion: reduce` 时，decorative motion 必须冻结，同时保留清晰最终状态。

### G3 — 真实 browser route，不重启 Product

每个 Product route 必须可以直接访问。Product 内部导航必须同步 `history.pushState`。浏览器前进/后退必须通过保留引用的 `JavaScriptBridge.create_callback` 驱动当前 Godot scene，不应故意 reload document。

进入 `/docs/**` 必须使用 hard document navigation；缺失的 Docs path 不得回退成 Product canvas。

### G4 — Responsive scene composition

Runtime 必须从真实 browser viewport 推导布局，并明确提供 `desktop`、`compact`、`phone` 三种状态。Phone topology 必须是独立 portrait composition，而不是缩小 desktop graph。

## 3. 视觉 authority

### G5 — Story Loom token projection

`assets/brand/tokens.json` 是视觉 token authority。Product build 必须通过 `site/scripts/generate-godot-theme.mjs` 确定性生成 `site/godot/generated/story_loom_tokens.gd`。

Runtime 必须提供可被 Browser QA 验证的 `Story Loom v2` 与 `novelforge_brand_tokens_v2` 标记。Route accent 必须来自 semantic token family，不得另建互相冲突的品牌色系统。

## 4. 语言与可访问性

### G6 — 双语 Product 契约

Product 支持 `en-US` 与 `zh-CN`，提供 scene 内显式语言切换，使用 browser storage 持久化选择，并在首次访问时尊重中文 browser locale。进入 Docs 时跟随当前 Product locale：英文进入 `/docs/en/`，中文进入 `/docs/`。

### G7 — 交互可访问性

Product 可交互控件必须至少 44px，支持 keyboard focus，并显示来自 Story Loom interaction tokens 的可见 focus ring。Browser QA 必须验证相应 accessibility markers。

## 5. Documentation 契约

`/docs/**` 保持 web-native，以保留长文阅读、semantic link、文本选择、索引、accessibility 与 localization。Starlight 独占 Docs routing/output；Godot 不得接管 Docs path。

## 6. 构建与部署契约

组合构建顺序：

1. staging 并构建 Starlight Docs 到 `site/dist/docs/`；
2. Godot Web 导出到 `site/dist/index.html` 及 WebAssembly/resource artifacts；
3. 保留 `_redirects` 等 root static files；
4. 验证每一个 production asset 都低于 hosting platform individual-file ceiling；
5. 将组合目录部署到 Cloudflare Pages。

Product bundle size 不是 UX 优化目标。只有 hard hosting/deployment constraint 才构成压缩体积的理由。

## 7. Browser acceptance evidence

最终 current-HEAD Browser QA 必须证明：

- Godot engine 启动且 scene 达到 `ready`；
- root 与 deep Product URL 都解析为 Godot host；
- `/docs/` 仍为 Starlight HTML；
- desktop/phone responsive states 正常；
- Story Loom token/theme marker 存在；
- `en-US` / `zh-CN` 都能在 live runtime 内应用；
- 44px/accessibility 与 motion marker 存在；
- 浏览器历史能切换 live Product scene 且 document 不 reload；
- 代表性的 desktop route screenshot 有实质差异。

## 8. Authority 边界

公开 Product Site 与 Docs 都只是 presentation/navigation surface，不拥有 Canon、Memory、Settlement、Framework-write、production-readiness 或 Publication authority。任何 visualization/browser projection 都不会成为第二 source of truth。
