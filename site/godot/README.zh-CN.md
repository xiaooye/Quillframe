# NovelForge Godot 产品运行时

这个目录现在是 NovelForge 公开站点**唯一的 Product runtime**。

## 边界

- 产品路由（`/`、`/product`、`/studio`、`/architecture`、`/publication`、`/inspect`、`/playground`、`/agents`、`/changelog`）由 Godot Web 渲染。
- 文档继续由 `/docs/**` 下的 Astro/Starlight 应用负责。
- 进入 Docs 使用完整 document navigation；Godot 永远不接管文档路由。
- 原 Solid/Vite Product implementation 已退役，不再作为 production fallback 保留。

## 视觉契约

运行时有意采用 2D-first + 有控制的 2.5D 景深：

- 只使用 Canvas/UI nodes；不使用 `Node3D`、`Camera3D`、mesh 或 3D physics。
- WebGL 2 使用 Compatibility renderer。
- 景深来自 parallax、分层网格、glow、animated packets 和 elevated panels，而不是 3D scene stack。
- 移动端使用独立 portrait topology。

## 浏览器契约

Product navigation 会写入真实 browser history。保留引用的 `JavaScriptBridge.create_callback` 将 `popstate` 直接绑定回当前 live scene，因此浏览器前进／后退会切换 Product route，而不是故意 reload document。Docs 仍是 hard cross-application navigation。

## 本地导出

安装 Godot 4.7.1 与匹配的 NovelForge Web export template，然后在 `site/` 下运行：

```bash
npm run build
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

`npm run build` 准备静态 host files 与 Starlight Docs；`npm run godot:build` 随后输出 `site/dist/index.html`、WebAssembly/resource artifacts，并保留 `site/dist/docs/`。

## CI

`.github/workflows/product-site.yml` 会编译固定的 2D-specific Web template，将 Godot 导出为 Product root，验证 hosting file-size ceiling，并部署组合后的 Godot + Starlight 站点。

`.github/workflows/product-site-browser-qa.yml` 会实际验证 desktop/mobile scenes、Product deep links、Docs boundary，以及 live no-reload browser history。
