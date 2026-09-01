# Windows 超长篇生产链实施计划

2026-08-31 · `SYSTEM-IMPROVE`

## 阶段 1 · 冻结合同与基线

登记 036 规范，冻结 Shujuku → Quillframe 的 `shared/domain → data → service → presentation` 映射，记录当前 Windows 失败基线、现有生产缺口和 Corpus v2 的冻结边界。所有修改保留工作树中的并行成果。

## 阶段 2 · Windows 安全存储

建立 Rust workspace 与可直接链接的 Core crate，统一拥有平台文件系统、SQLite 和 Project 1.0。为 Windows 实现句柄级目录遍历、无 reparse 打开、身份确认、exclusive create、原子替换、durable flush、跨进程锁和恢复；把现有 Linux 安全原语迁入同一 Rust 合同，未知平台 fail closed。

## 阶段 3 · 层级与规划运行时

在 domain 层开放 book/volume/unit/chapter/scene 的节点与四种 typed plan envelope；在 data 层实现 proposal、精确作者激活、祖先依赖 CAS、supersede 和冻结证据；在 service 层让规划模式拥有真实 semantic job 与恢复回执。

## 阶段 4 · 章节生产与修订闭环

让 PLAN-CHAPTER 的有序 scenes 驱动可恢复的逐场景生产；把 Reader Pressure brief、完整祖先计划锁与语义 Context Freeze 接入 Writer Pack；在 data 层持久化 checkpoint/log，在 service 层编排独立审查拒绝后的 repair source、责任层失效图和只供 Continuity 使用的后续依赖摘要。

## 阶段 5 · Corpus v2 运行与分层加载

完成可追加恢复的研究 runner、public atlas、发布注册表和生产 loader。按接收阶段选择零到四张卡并冻结绑定；重建 v2 holdout、LOO、泄漏与三臂评测。

## 阶段 6 · 长期学习、生命周期与账本

桥接带原因的 reject/revision feedback，强化独立 promotion receipt，修正 settled/superseded 投影并汇总内部、独立评审和 Corpus 研究成本状态。

## 阶段 7 · Studio 直连与 Python 移除

把 Studio Tauri host 从 Python sidecar 改为直接链接 Rust Core。迁移 CLI、本地 HTTP/API 与打包流程；删除 Python packages、`pyproject.toml`、Python 测试/CI 和全部运行前提。Node 只保留在 Studio 构建链。

## 阶段 8 · 规模与发布验收

在真实 Windows 和 Linux 运行器上完成安全与恢复回归，以有界多章夹具验证增量执行和重启恢复，并同步双语文档。真实文学金丝雀测试单独排队，只有作者与独立评审证据齐备后才报告文学结论。
