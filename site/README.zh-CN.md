# Quillframe 产品站

Quillframe 的公开 Product 界面现在是一个 **Godot Web 控制室**，并与 Astro/Starlight 文档应用保持明确边界。

## 运行时边界

- 产品路由（`/`、`/product`、`/studio`、`/architecture`、`/publication`、`/inspect`、`/playground`、`/agents`、`/changelog`）运行在同一个 Godot Web 场景中。
- `/docs/**` 完全由 Astro/Starlight 负责，继续输出 semantic HTML。
- 从 Product 进入 Docs 使用真正的 document navigation。
- 浏览器前进／后退会通过 bridge 驱动当前 Godot 场景，不应通过 reload 重启 Product runtime。
- Product 采用 2D-first + 有控制的 2.5D 景深，不使用 Godot 3D nodes。

原来的 SolidJS/Vite Product SPA 已退役：不再构建、不再用于 preview，也不再作为 fallback Product implementation 保留。

## 技术栈

- Product Web runtime：Godot `4.7.1` / GDScript / Compatibility renderer
- `/docs/**`：Astro `7.1.6` + Starlight `0.41.5`
- 静态 staging、验证与本地 dist server：Node.js 24.x
- 组合部署：Cloudflare Pages

`site/package.json` 不再包含 Product browser-framework runtime dependency。

## 构建

```bash
cd site
npm install
npm run quality
npm run build
```

`npm run build` 只准备 `site/dist/` 并构建 Starlight Docs；随后由 Godot 导出唯一的 Product root：

```bash
npm run godot:build
npm run preview -- --host 127.0.0.1 --port 4188
```

最终输出：

```text
site/dist/
  index.html       # Godot Web host shell
  index*.wasm      # Godot Web runtime
  index*.pck       # Product resources
  docs/            # Astro/Starlight semantic HTML app
  _redirects       # Docs canonical roots
```

CI 会编译固定版本、single-thread、2D-specific 的 Godot Web export template，并验证 Cloudflare Pages 的每一个单文件都低于平台 individual-file deployment ceiling。

## 产品路由

产品路由拥有真实 browser URL，但共享同一个活着的 Godot runtime。Browser bridge 会把 `pushState` / `popstate` 与场景导航同步；Browser QA 会实际证明按浏览器返回键时 scene 改变而 document 不 reload。

缺失的 `/docs/**` 永远不会错误落到 Product canvas；Product deep link 则会回退到 Godot host document，与 Cloudflare Pages 的部署行为一致。

## 设计契约

Product 使用 2D UI 加有限 2.5D 空间语言：分层 topology、parallax、animated packets、glow、elevation 与类似 camera composition 的视觉组织，但没有 3D scene stack。移动端使用独立的 portrait topology，而不是把 desktop graph 缩小。

Docs 刻意保持 web-native，以保留长文阅读、链接语义、索引、文本选择与 accessibility 的优势。

## 权威边界

公开 Product 与 Docs 都只是展示／导航层，没有 Canon、Memory、Settlement、Framework-write、production-readiness 或 Publication authority。视觉 projection 可以解释 runtime state，但不会成为第二 source of truth。
