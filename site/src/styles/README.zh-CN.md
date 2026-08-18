# Product Site CSS 架构

Product Site 只有一个样式入口：`index.css`。`main.tsx` 不应直接导入各个页面的 CSS。

级联顺序按职责固定为四层：

1. **基础层** — `site.css`、生成的 WeiUI、Story Loom，以及仓库级共享的 `quillframe-product-language.css` token。
2. **稳定产品原语** — `product-surface.css`、`unified-product-app.css`、`typography.css` 等共享布局与排版契约。
3. **页面功能样式** — Architecture、Publication、Inspector、Playground、Agents 等页面只负责自己的功能内容，不应重新实现全局 chrome 或全局状态。
4. **产品语言组合层** — kawaii / product 视觉组合在页面默认样式之后加载。跨页面的可读性与无障碍规则应放入明确归属的稳定层，而不是继续增加 `*-fixes.css` 或 `*-audit.css`。

不要恢复最终的“audit override”样式表。权威视觉规则应放到拥有该规则的组件或页面层。Product Site 与 Studio 共用的全局视觉 token 应放在 `assets/brand/quillframe-product-language.css`。
