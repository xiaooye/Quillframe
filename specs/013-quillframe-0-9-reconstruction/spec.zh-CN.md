# 规格说明 — Quillframe 0.9.0 重构

状态：实施中
主任务模式：`SYSTEM-IMPROVE`
冻结的 main：`0d583b25616e7e3b009efcf256ee4b21ecb5f8f7`
目标版本：`0.9.0`

## 问题

0.8 已经有成熟的 Python 语义/运行机制和可用的 SolidJS 产品表面，但当前权威被多套架构分裂：SolidJS 与 Godot 迁移/影子产品并存，baseline/parity/shadow 仍参与构建，公开品牌已经是 Quillframe，技术命名空间却仍保留旧身份；持久化也分散在各子系统自己的 SQLite 或文件中。Studio 的默认信息架构更像运行时检查台，而不是长篇小说工作台。

0.9 是 1.0 之前的破坏性重构，不是兼容版本。

## 唯一当前架构

- 前端只使用 SolidJS + TypeScript + Vite + `@solidjs/router`。
- 桌面端只使用 Tauri 2，且保持轻量宿主。
- Python Quillframe Core 继续拥有故事、人物、权威、状态落定、学习、上下文、质量和编排语义。
- 全局与项目持久化统一为 SQLite；搜索优先使用 FTS5；大文件按内容指纹存入 blobs。
- 本机 HTTP、托管 HTTP 与 Tauri 本机传输共享同一组类型化 Quillframe Host Bridge 操作契约。
- 当前文档只使用 Astro + Starlight。
- 公开、产品与活动技术身份统一为 Quillframe / `quillframe`。
- 所有当前产品路由使用 Borderless Kawaii Editorial 设计语言。

## 必须删除

当前树中不得保留活动 Godot 实现、导出配置、脚本、只服务 Godot 的资源、Godot CI、影子产品架构、路由/产品 parity、`baseline:*` 或 `shadow:*` 产品脚本。迁移期与死兼容层直接删除，不藏在 alias 或 fallback 后面。

历史 specs 与 changelog 可以保留当时真实术语。允许显式的一次性 0.8 项目迁移工具；普通 runtime 不允许回退查找旧格式。

## 项目格式

当前项目身份使用 `quillframe.toml` 与 `quillframe.lock.json`，并使用对应 Quillframe schema/attestation。正常 bootstrap 只读取当前文件。`quillframe migrate-project <old-project>` 是独立迁移操作；旧资料默认只能进入 proposal 等非权威状态，不能凭文件位置推定 Accepted Canon。

## SQLite 持久化

默认数据根：

```text
~/.quillframe/
  quillframe.sqlite
  projects/<project-id>/
    project.sqlite
    blobs/
    exports/
  backups/
  cache/
```

全局数据库保存应用设置、项目注册、最近项目、供应商/模型元数据、被授权的用户级偏好与学习证据、诊断、本地调度与备份元数据。真实密钥只由安全宿主存储保存，普通语义上下文只看凭据引用。

项目数据库直接实现 Framework 既有语义：书/卷/弧/单元/章/场景，文档与不可变修订，人物/关系/世界/地点/时间线，计划与场景卡，Canon claim/state 与角色知识，研究，候选稿/谱系/评审，接受证据与 Settlement，上下文与派生记忆，会话/运行/检查点/事件/交接/回执，学习与偏好，语料/benchmark 与发布构建。

SQLite 权威连接启用 WAL、外键、明确 busy timeout 和合适的同步持久化；迁移有顺序和校验和，事务原子执行；Doctor 检查 quick/integrity/foreign keys/WAL/blob 指纹等；备份使用一致性 snapshot。

自动保存只产生修订。Revision != Accepted。数据库存在记录 != Settlement。

## Studio 与权威

默认作者模式：书桌、正文、规划、故事设定、评审、研究与语料、学习、发布。全局工具：搜索、命令面板、设置、可选 AI Assistant Dock。Sessions/Runs/Checkpoints/Context/Agents/Models/Semantic Jobs/Control Plane/Capabilities/Receipts/Diagnostics/Architecture 全部归入 Inspector Mode。

生产操作只通过操作专用的 Core 命令。浏览器本地 mock 不得冒充 DRAFT/REVISE/AUDIT/SETTLE。每次执行恰好一个主 `task_mode`。`AUDIT` 不重写；`DRAFT` 不落定；接受与落定分开；反馈自动捕获不自动提升；Corpus 不成为 Canon；Research 不静默变成 Character Knowledge。

## 部署与安全

本机默认只绑定 loopback，并自动建立临时本机会话。Tauri 自动管理本机 Core 生命周期，不要求用户手工接 API。公网服务器缺少服务器端安全配置时 fail closed。`QUILLFRAME_SECRET` 绝不能进入 `VITE_*` 或浏览器 bundle；托管登录只用于换取认证会话，同源部署优先 HttpOnly cookie。

静态前端可以部署到普通静态主机、Vercel 或 Cloudflare，但 SQLite 必须留在真正持久化的 Quillframe Server。serverless 临时文件系统不承担权威数据库。

## 设计与中文

现有 SolidJS 首页是视觉北星。层级优先依靠留白、排版、对齐、构图、tint 和语义色，边框只在结构上必要时使用。可爱感来自温暖象牙纸面、编辑型字体、粉蓝/薰衣草/柔粉/薄荷/证据金、少量星点、胶带/索引意象和自然的微文案，而不是卡片海、后台仪表盘、通用 SaaS 网格、玻璃拟态或幼稚动漫装饰。

中文界面使用自然中文；英文只保留在精确标识、命令、代码、文件名和必要专名中。触控目标至少 44px，并尊重 reduced-motion。

## 验收

CI 必须覆盖版本一致性、命名空间卫生、Godot/compat 零活动引用、Python contract/tests、SQLite 清库迁移/顺序迁移/备份恢复/Doctor、站点与文档构建、Studio typecheck/build/路由/本地化、Tauri fmt/check/build-smoke、密钥泄露、主要路由视觉矩阵和性能预算。

任何必需 gate 未通过时，都必须报告真实失败状态，不能称 production-ready。
