# Plan · NovelForge Product Site

## Phase 0 · Contract freeze

- Work tracked in issue #34。
- latest `main` 作为实现基线。
- 复用 Story Loom v2 / WeiUI zero-JS contracts，不 fork。
- Product Site 与 Generic Core runtime dependency 隔离。

## Phase 1 · Site foundation

创建 `site/`：

- exact frontend versions；
- SolidJS + TypeScript + Vite + `@solidjs/router`；
- host-neutral static `dist/`；
- global AppShell / responsive navigation / footer；
- 显式 `en-US` / `zh-CN` locale state；
- 从 repository authority 直接消费 Story Loom application theme；
- base accessibility、focus、touch、responsive、reduced-motion rules。

首阶段不加入 analytics、backend、auth、CMS 或 Tauri runtime。

## Phase 2 · Product Home vertical slice

首页完成一条完整产品叙事：

1. Hero + product thesis；
2. prompt-only failure model；
3. Forge pipeline story；
4. 来自真实 contracts 的 proof modules；
5. Studio；
6. Publication；
7. subsystem bento；
8. one-product/many-host delivery；
9. release truth；
10. final CTA。

禁止 fake social proof。Product proof 必须来自 current machine contracts / observable architecture。

## Phase 3 · Destination routes

增加真实、非 placeholder 页面：Product、Studio、Architecture、Publication、Docs、Changelog。

第一版可以简洁，但每个 route 必须回答一个独立用户问题，并 deep-link 到 canonical repository sources。

## Phase 4 · Documentation portal

先做 curated documentation cards，映射 authoritative source。

后续 structural extension：

- build-time Markdown ingestion；
- 由 documentation manifest 生成 nav；
- build-time search index；
- source/freshness badges；
- 浏览器运行时不依赖 GitHub API。

不得创建第二套内容 store。

## Phase 5 · Deterministic quality

新增 model-free Site CI：

- install exact dependencies；
- production build；
- 运行 `site/scripts/quality.mjs`；
- 阻止 forbidden WeiUI runtime packages；
- 检查 required routes/locales/Story Loom references；
- 检查基础 a11y/responsive/motion source invariants；
- 拒绝已知 fake marketing placeholders。

后续可以加入 browser rendering / Lighthouse-style checks，但 normal CI 保持 deterministic / low-cost。

## Phase 6 · Visual review

第一阶段 product-ready 前：

- render desktop + phone；
- 中英文独立 inspection；
- no horizontal overflow；
- keyboard navigation/focus；
- reduced-motion final state；
- section hierarchy / CTA clarity；
- marketing claims 对齐 current `main`。

## Phase 7 · Hosting

优先 deployment target：Cloudflare Pages。

Build contract：

- root：`site`；
- build command：`npm run build`；
- output：`dist`。

Cloudflare 可替换；SPA 不加入 Cloudflare-specific product logic。

## Phase 8 · Future growth

基础稳定后：interactive architecture explorer、真实 Studio demo、Publication sample preview、build-time docs search、manifest-driven release/status、OpenGraph generation，以及只有经过明确 privacy/product 决策后才考虑匿名 analytics。

## Rollback

所有 site implementation 都必须可单独 revert。删除 `site/` 与 dedicated workflow 后，Framework/Studio runtime behavior 不发生变化。