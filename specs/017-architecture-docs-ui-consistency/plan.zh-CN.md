# Quillframe 架构 / 文档 UI 一致性修复 · 计划

## 权威基线

仅针对冻结的 main `4e1945f9ba7604891713d4584f47b71b8077bdfc`，在 `fix/architecture-docs-ui-consistency` 上实施。

## 1. 架构布局所有权

1. 修改 `site/src/ProductApp.tsx` 的执行路径标记，使每个语义步骤同时拥有节点与连接线。
2. 将全部管线尺寸与重排行为移入 `site/src/styles/architecture-explorer.css`。
3. 从 `unified-product-app.css` 删除后置的 `.architecture-entry .architecture-flow` / 节点尺寸覆盖。
4. 宽桌面使用七个等宽语义步骤，平板使用四列，手机使用单列。
5. 从管线删除每节点左外边距、绝对定位连接线、当前节点 translate 偏移、强制横向滚动、省略号及行数截断。
6. hero 与主路径继续共用同一份 `architectureNodes` 数据源。

## 2. 文档身份审计 / 修复

1. 在两个语言版本中把当前首页文案从 NovelForge 修正为 Quillframe。
2. 将实时 `/why-novelforge` 链接替换为 `/why-quillframe` / `/docs/en/why-quillframe`。
3. 修正 `QuillframePageTitle.astro` 中过时的路由分区 slug。
4. 保留当前外壳已有的规范 GitHub 与 Hosted Studio 目标。
5. 不因历史规格合理包含 NovelForge 而修改历史记录。

## 3. 前景色所有权

1. 基于现有产品与文档调色板 token 添加语义前景色别名。
2. 在 `product-shell.css` 明确指定产品桌面 / 移动导航及页脚的前景色所有权。
3. 让导航图标子 span 继承语义父元素的前景色。
4. 将文档语义导航 / 链接 / 操作 token 应用于当前外壳、侧栏 / 目录、行内链接、链接行及已有 CTA 角色。
5. 删除导致图标与文字颜色分裂的 GitHub 子 span 弱化覆盖。
6. 保留可见焦点与移动端触控目标。

## 4. 质量强化

1. 重写 `architecture-explorer-quality.mjs` 中要求错误横向滚动 / 最小宽度机制的检查。
2. 扩展 `docs-platform-quality.mjs`，加入当前身份 / 链接及语义颜色所有权断言。
3. 扩展 `product-shell-quality.mjs`，加入产品导航 / 页脚颜色所有权与破坏性覆盖防护。
4. 保留现有测试，不削弱无关质量门。

## 5. 验证与发布

运行仓库当前 CI / 构建权威，包括产品质量、文档质量 / 构建、完整仓库工作流触发的 Studio 质量、TypeScript、Vite、Astro/Starlight 与命名空间卫生检查。检查失败并修复真实回归。向 `main` 打开草稿 PR，但不合并。

真实浏览器渲染验收与确定性代码 / 构建完成相互独立。
