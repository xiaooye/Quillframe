# NovelForge Godot 产品运行时

这个目录包含 NovelForge 公共产品界面的 Godot-first 展示运行时。

## 边界

- 产品路由（`/`、`/studio`、`/architecture`、`/publication`、`/inspect`、`/playground`、`/agents`、`/changelog`）由 Godot Web 渲染。
- 文档仍由 `/docs/**` 下的 Astro/Starlight 应用负责。
- 进入 `/docs` 时使用完整文档导航；Godot 永远不接管文档路由。
- 迁移期间保留现有 Solid 产品源码作为参考／fallback source，但正常 site build 完成后，production root export 会由 Godot Web artifact 覆盖。

## 视觉契约

该运行时有意采用 2D-first，并只使用有限的 2.5D 景深提示：

- 只使用 Canvas/UI 节点；不使用 `Node3D`、`Camera3D`、mesh 或 3D physics。
- WebGL 2 使用 Compatibility renderer。
- 景深来自 parallax、分层网格、阴影、动画 packet 与抬升 panel，而不是 3D 场景。
- 路由 URL 与浏览器前进／后退行为仍以 browser history 为 authority。

## 本地导出

安装 Godot 4.7.1 以及匹配的 export templates，然后在 `site/` 下运行：

```bash
npm run build
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

`npm run godot:build` 会导出到 `site/dist/index.html` 及同级 Godot Web artifacts。已经构建好的 `site/dist/docs/` 目录会被保留。

## CI

`.github/workflows/product-site.yml` 固定 Godot `4.7.1-stable`，安装匹配的官方 export templates，先运行现有 product/docs build，再只用 Godot export 替换产品根目录，随后部署到 Cloudflare Pages。

`site/scripts/godot-web-quality.mjs` 锁定跨应用路由边界、Web renderer、产品路由契约，以及刻意不使用 3D nodes 的约束。
