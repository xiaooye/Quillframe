# NovelForge 产品站 — Godot Replacement Tasks

**范围：** 公开站点 `site/**`。独立 `studio/app/**` 不属于本次迁移。

这里记录 implementation status；最终 release truth 来自 **current HEAD** 的 GitHub Actions 与 deployed site，而不是手工抄写的 CI 状态。

## Runtime replacement

- [x] 让 Godot Web 成为唯一公开 Product runtime。
- [x] 保留 Astro/Starlight 作为 `/docs/**` 唯一 application。
- [x] 删除旧 `site/src` Solid Product tree 与 Product Vite entry/config。
- [x] 从 `site/package.json` 移除 Product browser-framework runtime dependency 与 Vite preview。
- [x] 保留 Product deep-link fallback，同时禁止缺失 Docs path 回退成 Product route。
- [x] Product 视觉保持 2D + controlled 2.5D，不使用 3D nodes。

## Browser/runtime integration

- [x] Product navigation 同步 browser `pushState`。
- [x] 用保留引用的 JavaScriptBridge callback 把 `popstate` 路由回 live Godot scene。
- [x] Docs navigation 保持 hard document boundary。
- [x] 输出 scene/runtime/layout/history markers 供 Browser QA 使用。
- [x] 提供明确的 desktop、compact、phone layouts。

## Product contract preservation

- [x] 加入 `en-US` / `zh-CN` Product localization。
- [x] 持久化 locale，并在首次访问时尊重 browser locale。
- [x] 英文 Product 进入 `/docs/en/`，中文 Product 进入 `/docs/`。
- [x] 强制 canonical 44px touch target。
- [x] 加入 keyboard focusability 与可见 focus styling。
- [x] 尊重 reduced-motion preference。

## Story Loom integration

- [x] 以 `assets/brand/tokens.json` 作为 Product visual authority。
- [x] 生成确定性的 Godot token projection，并拒绝 stale generated output。
- [x] Product semantic route accent 与 interaction styling 从 Story Loom tokens 派生。
- [x] 删除持续 decorative idle processing。
- [x] 保留 2.5D depth/parallax 与 bounded route/interaction packet motion。
- [x] 向 Browser QA 暴露 theme/token schema。

## 完成所需 build/deploy evidence

只有**同一个 current HEAD** 同时证明以下条件，release 才算完成：

- Product-site quality 与 Story Loom token checks 通过。
- Starlight Docs build 通过。
- 固定版本 Godot editor/template setup 通过。
- Godot scene instantiation 与 release Web export 通过。
- Cloudflare Pages production assets 全部满足 hard individual-file ceiling。
- Production deploy 与 custom-domain post-condition 通过。
- Browser QA 证明 root/deep Product routes 与 Docs boundary。
- Browser QA 证明 desktop/phone、双语、accessibility markers、Story Loom theme markers 与 no-reload browser history。
- Browser QA screenshots 提供代表性 visual evidence。
- Live custom domain 实际提供 Godot Product runtime + Starlight Docs split。

## Cleanup condition

公开 Product migration 不得留下一个 tracked lockfile/build artifact，继续把已退役 Solid/Vite Product implementation 声明为现役 `site/**` dependency。若保留 lockfile，必须从最终 Godot + Starlight package manifest 重新生成。
