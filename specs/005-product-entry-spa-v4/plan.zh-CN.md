# Plan · NovelForge Product Entry SPA v4

## Phase 0 · Authority / evidence freeze

- latest `main` 作为开发基线。
- 保留 WeiUI / Story Loom v2 authority，不 fork。
- UI/UX Pro Max 只作为设计 evidence。
- 所有 Product claim 对齐 current implementation。

## Phase 1 · Build-time knowledge compiler

- `site/scripts/build-content.mjs` 读取 `docs/documentation_manifest.json`。
- 使用 exact-pinned Markdown parser 将 paired Markdown 编译为安全结构化 AST，不输出未经处理的 raw HTML。
- 为每个文档生成 metadata、TOC、plain-text excerpt、search terms、source path、tier/status。
- 生成统一 product/docs search index。
- Vite build 前自动编译；runtime 不调用 GitHub API。

## Phase 2 · Product Entry shell

重构全局 shell：

- WeiUI-backed command/search trigger；
- `⌘K` / `Ctrl+K` command palette；
- mobile search sheet/dialog；
- appearance / locale / GitHub / Studio actions；
- compact, high-density premium navigation；
- kawaii status language。

## Phase 3 · Premium-cute home

首页从 brochure narrative 改为 interactive entry：

- dense hero/product launcher；
- live capability dock；
- product surface carousel / focus panels；
- Studio launch；
- Architecture explorer teaser；
- Publication profile explorer teaser；
- Knowledge search teaser；
- release/status capsule；
- Story Loom chromatic materials。

## Phase 4 · Knowledge Explorer

`/docs`：

- search + filters；
- tier/status/source metadata；
- responsive document library；
- selected/recent product docs；
- `docs/:docId` article route；
- generated TOC；
- code/list/table/quote rendering；
- source link remains optional provenance, not required reading path。

## Phase 5 · Interactive product routes

- `/studio`：real hosted Studio CTA + capability explorer + unbound-Core truth。
- `/architecture`：focusable subsystem map / detail popovers。
- `/publication`：profile switcher + accepted-text flow + current limits。
- `/product`：interactive capability inventory / boundaries。
- `/changelog`：release timeline/status, not giant static title page。

## Phase 6 · Modern CSS enhancement

Progressively layer:

- container/style queries；
- subgrid；
- `:has()`；
- semantic `color-mix()` derivation；
- masks / clip-path / filters / blend modes；
- gradients / perspective / motion path；
- scroll/view timelines；
- View Transitions；
- Popover + Anchor Positioning；
- `@starting-style` + discrete transitions；
- `content-visibility` for document content。

No infinite idle loops. Reduced-motion returns complete static state.

## Phase 7 · Quality / visual QA

- Product Site deterministic quality gate。
- exact dependency pins。
- generated content contract and stale-data checks。
- native zh-CN leakage gate。
- no fake social proof。
- keyboard/touch/focus/reduced-motion checks。
- desktop/mobile browser render QA。
- Cloudflare deployment post-condition。

## Rollback

v4 knowledge compiler、interaction shell 与 visual/product rewrite 分为可独立 revert 的 commits。回滚 Product Entry 不改变 Generic Core / Studio Core authority。
