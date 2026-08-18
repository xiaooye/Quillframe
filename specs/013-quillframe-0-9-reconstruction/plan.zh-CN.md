# 实施计划 — Quillframe 0.9.0 重构

冻结基线：`0d583b25616e7e3b009efcf256ee4b21ecb5f8f7`
分支：`system-improve/quillframe-0.9.0`
主任务模式：`SYSTEM-IMPROVE`

## 执行图

1. 冻结并盘点当前架构、技术身份、产品路由、持久化与部署。
2. 固化 0.9 破坏性规格、删除矩阵、Studio 信息架构与命令/权威矩阵。
3. 从活动树删除 Godot 与迁移期产品兼容层。
4. 把活动技术身份迁到 Quillframe，同时保持历史记录真实。
5. 建立统一 SQLite 全局/项目存储、顺序迁移、文档修订、FTS5、备份恢复与 Doctor。
6. 只通过操作专用的类型化 Core/Product 契约暴露能力；除非精确操作证明，否则权威标志保持 false。
7. 按作者模式重构 Studio，并把 Inspector 放到渐进披露层；现有 SolidJS 首页继续作为视觉北星。
8. 为规划、DRAFT、REVISE、AUDIT、RESEARCH、CORPUS-INGEST、LEARN、SETTLE 提供真实 Core 调度。语义执行实际不可用时，UI 必须显示 pending/unsupported，不能用 mock 冒充。
9. 提供持久但无 Canon 权威的 AI Dock 与真实上下文检查。
10. 增加轻量 Tauri 2 宿主以及 localhost / 自托管 Web 的部署与认证引导。
11. 重写当前文档、迁移指南和设计/UX 契约。
12. 用当前 Framework/Product/Studio/Tauri/SQLite/负向回归验证替换旧 CI。
13. 实测视觉矩阵、可访问性、本地化和性能；只记录真实证据。
14. 移除临时迁移工具，完成死文件与陈旧引用审计，修复 CI；所有 merge-readiness 条件真实通过前，PR #106 保持 Draft。

## 删除分类

- `CURRENT`：保留并迁入 0.9 当前架构。
- `MIGRATION_ONLY`：仅允许执行一次性仓库/项目迁移，之后从活动构建权威中移除。
- `DEAD`：删除。
- `HISTORICAL`：仅保留在历史区域，不参与当前 runtime/build/namespace gate。

## 权威不变量

计划不等于 Canon；修订不等于 Accepted；Review Draft 不等于 Accepted artifact；Accepted 不等于 Settled；聊天分支不等于 Candidate Lineage；Research truth 不等于 Character Knowledge；Corpus 不等于 Canon；反馈自动捕获不等于偏好自动提升；`AUDIT` 只报告；`DRAFT` 不执行 Settlement；每次作者执行恰好保存一个主 task mode。

## 回滚

所有工作隔离在专用分支和 Draft PR，冻结的 main SHA 是仓库回滚锚点。SQLite 迁移显式记录 schema version 与 checksum，校验和不匹配时 fail closed。数据恢复先验证 snapshot 完整性与内容指纹，再原子替换。本任务不修改任何下游小说项目。
