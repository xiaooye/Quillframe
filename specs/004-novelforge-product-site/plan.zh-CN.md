# NovelForge 产品站 — Godot Replacement 计划

**范围：** 仅公开 Product Site `site/**`。`studio/app/**` 继续作为独立本地 Studio application，不属于本次替换。

## 目标架构

```text
Browser
├─ Product routes
│  └─ Godot 4.7.1 Web / GDScript / Compatibility renderer
│     ├─ Main Control scene
│     ├─ live BrowserRouteBridge
│     ├─ Story Loom ThemeBridge
│     ├─ LocaleBridge
│     ├─ AccessibilityBridge
│     └─ 2D/2.5D responsive topology
└─ /docs/**
   └─ Astro 7.1.6 + Starlight 0.41.5 semantic HTML
```

两个应用组合到同一个 `site/dist/` 部署目录。Product → Docs 有意保持 document boundary。

## Phase 1 — 替换 Product runtime

- 在 `site/godot/Main.tscn` 建立 Godot Web project。
- 所有 Product route 在同一个 live Godot runtime 中实现。
- 用 `pushState` 保留真实 browser URL，并通过 bridge 把 `popstate` 路由回当前 scene。
- `/docs/**` 保持独立 Starlight application。
- 加入品牌化 custom Web shell 与 runtime-ready browser marker。
- 编译固定版本、single-thread、适合 2D Product feature set 的 Web export template。

## Phase 2 — 退役旧公开 SPA

- 删除 `site/src`、Product Vite entry/config 与 Product-only Solid/Vite quality scripts。
- 从 `site/package.json` 移除 Product browser-framework runtime dependency。
- 用轻量 static dist server 替代 Vite preview：Product deep route 回退到 Godot host，但 Docs path 永远不回退到 Product。
- 不修改 `studio/app/**`，因为它不是公开 Product Site runtime。

## Phase 3 — 在 Godot 内保留产品契约

- 实现明确的 `desktop`、`compact`、`phone` scene layout。
- 保留 Product deep link 与 no-reload browser back/forward。
- 实现 `en-US` / `zh-CN`、locale persistence、scene 内显式 toggle 与 locale-aware Docs handoff。
- 强制 44px target、keyboard focus、可见 focus ring 与 reduced-motion 行为。
- 视觉严格限制为 2D + controlled 2.5D，不引入 3D scene stack。

## Phase 4 — Story Loom 成为视觉 authority

- 以 `assets/brand/tokens.json` 作为视觉 token authority。
- 在 Godot export 前确定性投影为 generated GDScript。
- Route accent、focus styling、surface 与 semantic state color 都从该 projection 派生。
- 删除持续 decorative idle loop，只保留 transition/interaction 的 bounded motion 与输入驱动 parallax。
- 输出 browser-visible theme/token markers 供 acceptance test 使用。

## Phase 5 — Production evidence

最终 current HEAD 必须同时通过 deployment 与 browser evidence：

- Starlight Docs staging/build；
- Godot scene instantiation + release Web export；
- Cloudflare individual-file ceiling check；
- Cloudflare Pages production deploy + custom-domain post-condition；
- 浏览器验证 root/deep routes、Docs boundary、desktop/phone、Story Loom theme、双语、accessibility marker 与 no-reload history；
- 保存代表性 screenshot 作为 visual regression evidence。

## Repository responsibilities

- `site/godot/**`：唯一公开 Product runtime。
- `site/docs-site/**`：Docs application。
- `site/scripts/generate-godot-theme.mjs`：brand-token projection。
- `site/scripts/godot-web-quality.mjs`：静态 Product runtime contract。
- `site/scripts/godot-browser-proof.mjs`：真实浏览器 runtime evidence。
- `.github/workflows/product-site.yml`：组合 build/deploy。
- `.github/workflows/product-site-browser-qa.yml`：visual/runtime acceptance evidence。

## 非目标

- 不同时维护 Unity/Unreal UI。
- 不建立 3D Product scene stack。
- 除 hard hosting constraint 外，不以 tiny bundle/first-load 为优化目标。
- 不把独立 `studio/app/**` local application 纳入公开站点迁移范围。
- Presentation layer 不获得 Canon、Memory、Settlement 或 Framework authority。
