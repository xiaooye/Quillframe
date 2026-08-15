# NovelForge Studio 云端宿主

云托管 Studio 是产品交付宿主，不是 NovelForge Core 运行时。

- 生产地址：`https://studio.novelforge.wei-dev.com`
- Cloudflare Pages 项目：`novelforge-studio`
- 产品 surface：`cloud_ui`
- Core host：默认未绑定
- Authority：`false`

Local Web 与云托管使用同一套 SolidJS 应用。Local Web 由 `studio/local_server.py` 注入临时 token；静态 Cloudflare build 则保留 `__NOVELFORGE_STUDIO_TOKEN__` placeholder。Studio 会把未替换的 placeholder 识别为明确的“宿主未绑定”状态，并且不会发出 `/api/bridge/invoke` 请求。

只有真正绑定 Host Bridge transport 后，项目相关查询才可使用。Cloudflare Pages、Pages Functions、Workers、KV、D1、Durable Objects 以及其他 Cloudflare persistence 都不是 NovelForge Core authority，本阶段也不会使用它们合成项目状态或运行时状态。

Cloudflare Pages 直接交付 SPA。`public/_headers` 提供静态安全响应头，`public/robots.txt` 阻止搜索引擎收录产品外壳。Hosted build 刻意不生成顶层 `404.html`，因此 Pages 的原生 SPA fallback 可以把深层路由交回应用外壳。

未来如果加入远程 Core 连接，必须复用公开的类型化 Host Bridge / query-command contract，不能新增一套 Cloudflare 专属语义后端。