# NovelForge 产品站 — Godot Replacement Tasks

**范围：** 公开站点 `site/**`。独立 `studio/app/**` 不属于本次迁移。

这里记录 implementation status；最终 release truth 来自**同一个 current HEAD** 的 GitHub Actions 与 deployed site，而不是手工抄写的 CI 状态。

## Runtime replacement

- [x] 让 Godot Web 成为唯一公开 Product runtime。
- [x] 保留 Astro/Starlight 作为 `/docs/**` 唯一 application。
- [x] 让 Solid/Vite 退出 production Product path 与默认 Product `dev` / `build`。
- [x] 保留 `site/src/**` 与精确 Solid/Vite dependencies，但只作为命名明确的 golden visual-and-behavior fixture，用于 parity QA。
- [x] Baseline commands 统一放在 `baseline:*` namespace，不获得 production authority。
- [x] 保留 Product deep-link fallback，同时禁止缺失 Docs path 回退成 Product route。
- [x] Product 视觉保持 2D + controlled 2.5D，不使用 3D nodes。

## Browser/runtime integration

- [x] Product navigation 同步 browser `pushState`。
- [x] 用保留的 JavaScriptBridge callback 把 `popstate` 路由回 live Godot scene。
- [x] Docs navigation 保持 hard document boundary。
- [x] 输出 scene/runtime/layout/history markers 供 Browser QA 使用。
- [x] 提供明确的 desktop、compact、phone layouts。
- [x] 保留 command palette、locale、appearance、mobile menu 与 browser history interactions。

## Visual parity preservation

- [x] 保留 Story Loom brand primitives/assets 作为 canonical design foundation。
- [x] 把保留的 Solid/Vite Kawaii Atelier page 定义为非生产 golden rendered fixture。
- [x] 固定 Inter、CJK、symbol、Thai、Arabic fallback fonts，保证 cross-renderer evidence 确定性。
- [x] 在 Godot source contract 中编码 page-grid、typography、wrap、margin、alignment、responsive flow 与 route identity parity。
- [x] 限制 font fallback scope，防止 decorative glyph coverage 改变普通正文 line metrics。
- [x] 对 golden fixture 运行 route-pair screenshot evidence 与 blocking interaction QA。
- [x] 禁止 migration work 重新解释 approved Kawaii layout。

## 完成所需 build/deploy evidence

只有**同一个 current HEAD** 同时证明以下条件，release 才算完成：

- Golden-baseline fixture quality、Godot source quality 与 production assembly contracts 通过。
- Starlight Docs build 通过。
- 固定版本 Godot editor/template setup 通过。
- 唯一已经通过 parity/size gate 的 Godot exporter 完成 release Web export。
- Cloudflare Pages production assets 全部满足 hard individual-file ceiling。
- Production deploy 与 custom-domain API post-condition 通过。
- Production Browser QA 证明 runtime readiness、Product routes、interactions、responsive layouts、screenshots 与 Docs boundary。
- Route parity QA 对保留 golden fixture 继续保持 green。
- Live HTTP verification 证明 `/` 与 direct Product route 提供 Godot shell，而 `/docs/` 提供不含 Godot shell 的 Starlight。

## Cleanup condition

- [x] 默认 Product `dev` / `build` 明确以 Godot 为 production。
- [x] Solid/Vite dependencies 明确只为 baseline fixture QA 保留，不是 shipped fallback runtime。
- [x] Product source-quality output 明确 `production_cutover: true`。
- [x] Product specification 明确区分公开 Godot runtime 与独立 `studio/app/**` application。
- [x] Live-domain content verification 已进入 deployment workflow，不再依赖外部/人工假设。

Golden fixture 可以为确定性 regression evidence 保留精确 browser-framework dependencies 与 lockfile；这不会使它获得 production runtime 身份。
