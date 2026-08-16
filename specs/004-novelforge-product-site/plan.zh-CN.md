# NovelForge 产品站 — Godot Replacement 计划

**范围：** 仅公开 Product Site `site/**`。`studio/app/**` 继续作为独立本地 Studio application，不属于本次替换。

## 目标架构

```text
Browser
├─ Product routes
│  └─ Godot 4.7.1 Web / GDScript / Compatibility renderer
│     ├─ responsive Control scene
│     ├─ browser route/history bridge
│     ├─ deterministic typography + Kawaii geometry parity
│     └─ locale / appearance / command / mobile interaction bridge
└─ /docs/**
   └─ Astro 7.1.6 + Starlight 0.41.5 semantic HTML

仅用于 Repository QA 的 fixture
└─ site/src/** SolidJS/Vite Story Loom / Kawaii Atelier golden baseline
   └─ 永远不作为 Product runtime 发布
```

Product 与 Docs 组合到同一个 `site/dist/` 部署目录。Product → Docs 有意保持 document boundary。

## Phase 1 — 替换 Product runtime

- 在 `site/godot/Main.tscn` 建立 Godot Web project。
- 所有 Product route 在同一个 live Godot runtime 中实现。
- 用 `pushState` 保留真实 browser URL，并通过 bridge 把 `popstate` 路由回当前 scene。
- `/docs/**` 保持独立 Starlight application。
- 加入品牌化 Web shell 与 runtime-ready browser marker。
- 编译固定版本、single-thread、适合 2D feature set 且满足 hosting ceiling 的 slim Web export template。

## Phase 2 — 让 Solid/Vite 退出生产，而不是删除 parity evidence

- 从 **production runtime path** 与默认 Product `dev` / `build` 中移除 Solid/Vite。
- 保留 `site/src/**` 及其精确 browser dependencies，但只作为明确命名的 golden visual-and-behavior fixture，用于 parity QA。
- Baseline command 统一放在 `baseline:*`；它们没有 production authority。
- 只保留一个已经通过 parity/size gate 的 Godot Web exporter，production assembly 必须消费同一个 artifact。
- 不修改 `studio/app/**`，因为它不是公开 Product Site runtime。

## Phase 3 — 在 Godot 内保留产品契约

- 实现明确的 `desktop`、`compact`、`phone` scene layout。
- 保留 Product deep link 与 no-reload browser back/forward。
- 实现 `en-US` / `zh-CN`、locale persistence、显式 toggle、appearance state、command palette、mobile menu 与 locale-aware Docs handoff。
- 保留 touch target、focus 与 reduced-motion 行为。
- 视觉严格限制为 2D + controlled 2.5D，不引入 3D scene stack。

## Phase 4 — 保留 Story Loom / Kawaii Atelier，禁止迁移变成再设计

- Canonical Story Loom brand primitives/assets 继续位于 `assets/brand/**`。
- 保留的 Solid/Vite site 只作为 rendered golden parity fixture。
- 固定 browser/Godot comparison 所使用的 Latin、CJK、symbol、Thai 与 Arabic fallback fonts。
- 在 Godot source contract 中编码 page-grid、typography、wrap、margin、alignment、responsive flow 与 route identity parity。
- 对 golden fixture 运行 route-pair screenshot evidence 与 blocking interaction QA。
- Visual-diff metric 不得被当成重新解释 approved layout 的许可。

## Phase 5 — Production evidence

最终 current HEAD 必须通过：

- baseline fixture + Godot source + production assembly contracts；
- Starlight Docs staging/build；
- 通过唯一 exporter 完成 Godot scene instantiation 与 release Web export；
- Cloudflare individual-file ceiling check；
- Cloudflare Pages production deploy + custom-domain API post-condition；
- Production Browser QA：runtime、routes、interactions、Docs boundary、desktop/phone 与 screenshots；
- 对保留 golden fixture 的 route parity evidence；
- live HTTP 检查证明 `/` 与一个 direct Product route 是 Godot，而 `/docs/` 仍是 Starlight。

## Repository responsibilities

- `site/godot/**`：唯一公开 Product runtime source。
- `site/src/**`：非生产 Story Loom / Kawaii Atelier golden parity fixture。
- `site/docs-site/**`：Docs application。
- `site/scripts/godot-shadow-source-quality.mjs`：production Godot source/parity contract（为兼容保留历史文件名）。
- `site/scripts/build-godot-shadow.sh`：唯一已经通过 parity/size gate 的 Godot Web exporter（为兼容保留历史文件名）。
- `site/scripts/build-godot-web.sh`：保留 `/docs/**` 的 production root assembler。
- `site/scripts/godot-shadow-browser-shot.mjs`：parity 与 production QA 共用的 deterministic browser screenshot driver。
- `site/scripts/godot-interaction-qa.mjs`：blocking browser interaction evidence。
- `.github/workflows/product-godot-route-parity.yml`：golden-fixture visual/interaction parity evidence。
- `.github/workflows/product-site.yml`：组合 build/deploy + live-domain verification。
- `.github/workflows/product-site-browser-qa.yml`：production visual/runtime acceptance evidence。

## 非目标

- 不同时维护 Unity/Unreal UI。
- 不建立 3D Product scene stack。
- 除 hard hosting constraint 外，不以 tiny bundle/first-load 为优化目标。
- 不把独立 `studio/app/**` local application 纳入公开站点迁移范围。
- 在 approved Kawaii layout 仍依赖 golden browser fixture 做 regression oracle 时，不删除该 fixture。
- Presentation layer 不获得 Canon、Memory、Settlement 或 Framework authority。
