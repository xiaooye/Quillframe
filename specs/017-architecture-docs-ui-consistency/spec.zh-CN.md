# Quillframe 架构 / 文档 UI 一致性修复 · 规格

## 状态

- 主要任务模式：`SYSTEM-IMPROVE`
- 冻结基线 main：`4e1945f9ba7604891713d4584f47b71b8077bdfc`
- 工作分支：`fix/architecture-docs-ui-consistency`
- 范围：产品语言重构后的缺陷修复；不做重新设计或架构迁移
- 托管：仅 Cloudflare；不配置或部署 Vercel

## 问题 A — 架构执行路径

`/architecture` 的七步执行路径必须保持以下语义顺序：

`Project → Manager → Context → Worker → Gate → Settlement → Publication`

当时的实现混用了七列 Grid、每节点左外边距和绝对定位连接线，后续路由样式又重新定义节点宽度与横向滚动。卡片与连接线因此由不同布局机制控制，造成错位、文本列过窄、省略号，以及移动端横向滚动。

所需机制：

- 由 `architecture-explorer.css` 单独拥有该路由的布局系统；
- 节点与连接线间距必须一起建模；
- 不使用每卡片 margin/translate 定位补丁；
- 不使用绝对定位连接线；
- `unified-product-app.css` 不得在后方覆盖架构轨道；
- 卡片高度与内部节奏一致，文字自然换行；
- 桌面端为七步编辑式横带；
- 平板端按语义重排为 4+3；
- 手机端使用纵向序列；
- 页面不得产生横向溢出；
- hero 路径与主执行路径使用相同的 `architectureNodes` 顺序。

## 问题 B — 文档当前产品身份

当前文档运行时与构建表面必须使用 `Quillframe`。`NovelForge` 只能出现在明确的历史或迁移记录中，不能出现在当前界面、导航、CTA、标题、元数据或实时目标链接里。

当时文档首页仍展示 NovelForge 产品身份及 `/why-novelforge` 链接，但当前 Starlight 清单与配置已使用 `why-quillframe`。必须定点修正这些当前产品引用，不能全局替换。

当前规范目标：

- GitHub：`https://github.com/xiaooye/cn_webnovel_agent`
- Hosted Studio：`https://studio.quillframe.wei-dev.com`
- 产品 / 文档身份：`Quillframe`

## 问题 C — 语义前景色归属

产品与文档前景色必须由语义组件拥有，不能依赖偶然继承或装饰性子选择器。

要求：

- 适当复用现有调色板 token，并以语义别名表达用途；
- 普通导航、激活导航、正文 / 链接、悬停 / 聚焦、操作前景色与弱化文字保持区别；
- 嵌套图标 / 文本 span 通常继承所属链接或控件的前景色；
- 不添加全局 `a { color: ... }` 或 `span { color: ... }` 补丁；
- 不新增 `!important`；
- 可见焦点必须保留，可爱风格不得削弱对比度。

## 响应式 / 无障碍契约

验证目标为 1440、1024、768、430、375 CSS 视口行为。移动 / 触控表面的交互导航目标至少为 44px。保留语义化链接与按钮、键盘访问、可见焦点、`aria-expanded`、减少动态效果和逻辑阅读顺序。

## 确定性质量契约

质量检查必须阻止以下回归：

- 精确的架构语义顺序；
- 唯一的架构布局所有者；
- 桌面 / 平板 / 手机三种执行路径策略；
- 不存在每节点 margin/translate 与绝对定位连接线补丁；
- 共享路由 CSS 不在后方接管架构轨道；
- 当前文档首页、标题和外壳使用 Quillframe 与 `why-quillframe`；
- 使用规范 GitHub 与 Hosted Studio 目标；
- 当前文档运行时组件禁止残留 NovelForge 产品身份；
- 产品 / 文档导航拥有语义颜色，嵌套链接 span 继承父级前景色；
- 被修改的样式所有者中不存在破坏性的全局链接 / span 颜色规则或 `!important`。

## 完成事实

代码完成要求确定性质量与构建检查通过。如果无法使用真实渲染浏览器，必须如实报告：

`代码完成 / 渲染视觉验收待完成`

不得把静态 CSS 检查表述为已经完成的渲染视觉验收。
