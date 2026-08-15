# NovelForge 产品站

这是 NovelForge 独立的公开产品介绍 / 导航 SPA。

它**不是** Studio 应用，也**不是**仓库文档的替代内容库。它负责对外呈现 NovelForge Core、Studio、Publication、Architecture、Docs 与 release truth，并提供统一的产品叙事和导航入口。

## 技术栈

- SolidJS `1.9.14`
- `@solidjs/router` `0.16.2`
- Vite `8.1.5`
- vite-plugin-solid `2.11.14`
- TypeScript `7.0.2`
- CI / build 使用 Node.js 24.x

所有直接前端依赖均使用精确版本锁定。当前有意不引入 `@weiui/react` 与 `@weiui/headless`。

## Story Loom / WeiUI 边界

产品站不维护第二套配色或设计 token。

它直接消费：

- `../assets/brand/tokens.json` —— NovelForge Story Loom v2 产品 token 权威；
- `../assets/brand/weiui.integration.json` —— WeiUI 精确上游 pin 与消费契约；
- `../assets/brand/story-loom.weiui.css` —— 当前 `wui-theme` 应用映射。

现有 WeiUI source contract 允许使用 `@weiui/tokens` + `@weiui/css`，并要求 WeiUI runtime JavaScript 为零。WeiUI 仓库目前还没有一个可供本产品站依赖的稳定跨仓库 npm 发布契约，因此首个公开版本直接消费维护中的 Story Loom theme，而不会假设一个实际上不存在的 package install 路径。

## 本地开发

```bash
cd site
npm install
npm run quality
npm run dev
```

生产构建：

```bash
npm run build
```

输出目录：`site/dist/`。

## 路由

- `/` —— SaaS 风格 Product Home
- `/product` —— 产品模型与边界
- `/studio` —— Studio 阶段与产品栈
- `/architecture` —— 子系统地图
- `/publication` —— deterministic Publication core
- `/docs` —— 精选 canonical documentation 入口
- `/changelog` —— release truth

Docs 路由只链接仓库内持续维护的文档来源，不会再造第二套 CMS。

## 产品设计契约

公开产品站遵循 issue #34 与 `specs/004-novelforge-product-site/`。

核心规则：

- 先讲清产品价值，再进入架构，而不是 architecture-first onboarding；
- 使用真实 contract evidence，不伪造 testimonial、logo、用户数、SLA 或 pricing；
- mobile-first，交互目标尺寸不小于 44px；
- focus 状态可见，导航可用键盘操作；
- 产品文案支持 `en-US` + `zh-CN`；
- 默认不 polling；
- 不运行 idle animation loop；
- reduced-motion 模式仍保留完整内容；
- 该 SPA 不依赖通用 Core runtime。

运行：

```bash
npm run quality
```

quality script 会验证技术栈版本锁、Story Loom / WeiUI 契约、路由与 locale、基础 UX 不变量、禁止的 runtime dependency、虚假营销 placeholder，以及对 private Core 的错误耦合。

## Cloudflare Pages

构建保持 host-neutral。若部署到 Cloudflare Pages，可配置：

```text
Root directory: site
Build command: npm run build
Build output directory: dist
Production branch: main
```

除非 hosting strategy 发生变化，否则不要添加顶层 `404.html`：Cloudflare Pages 会把没有该文件的站点按单页应用处理，并将进入的路径路由到 SPA root。

首个版本不需要 Pages Function、数据库、认证、analytics SDK 或 Cloudflare-specific product logic。

## 权威边界

Product Site 只负责展示与导航。

它没有 Canon、Memory、semantic、Settlement、Framework-write、production-readiness 或 Publication 权威。产品图示和 UI projection 可以解释 Core state，但永远不会成为第二 source of truth。
