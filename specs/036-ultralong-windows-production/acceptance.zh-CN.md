# Windows 超长篇生产链接受条件

2026-08-31 · `SYSTEM-IMPROVE`

只有以下各项都有证据时，工程计划才可收口：

- Windows 与 Linux 原生 Project 全生命周期通过真实平台安全、竞态、锁和恢复测试；
- 四级规划 proposal 不能自行激活，作者激活与 supersede 具备精确 CAS 回执；
- 多场景章节、Reader Pressure、盲审隔离、独立拒绝修订和后续依赖影响测试通过；
- Corpus v2 运行、发布、冻结加载、0–4 分层选择、泄漏门和回滚可执行；
- 有界多章夹具证明打开、选择、修订、恢复和投影均为增量执行，可从检查点恢复，且不会读取无关正文；
- 生命周期、反馈和成本投影不把 accepted 当 settled，不把未知费用记为零；
- 双语文档、Manifest、确定性 CI 与真实平台 runner 同步。
- 最终产品可在没有 Python 和 Node runtime 的机器上运行；仓库不存在 Python 产品代码、sidecar、测试或 CI。

真实文学 canary 可以在工程收口后继续保持 `awaiting_user` 或 `semantic_pending`。在作者未审阅连续章节前，不得宣称系统已经证明能写好 500 万字小说。
