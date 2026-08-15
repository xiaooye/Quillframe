# Product Site Visual Rewrite v3 Plan — 已取代

**状态：** 历史 implementation plan；现由 `plan.zh-CN.md` 取代。

原 v3 plan 面向旧 browser DOM/CSS/Vite Product shell。公开 Product runtime 现在已经迁移到 Godot Web，因此旧实现步骤不得恢复执行。

## 延续到当前架构的视觉工作

仍然有效的视觉方向在当前 Godot architecture 内实现：

1. 将 Story Loom tokens 投影为 generated GDScript；
2. 使用 `Control`/Canvas surfaces 构建 Product stage；
3. 用 connected topology 与 inspector surfaces 表达系统关系；
4. Product、Studio、Architecture、Publication、Inspect、Playground、Agents 使用 semantic route accents；
5. 使用 bounded 2.5D motion 与 input-driven parallax，不运行 idle frame loop；
6. phone 使用独立 portrait topology；
7. 保留双语与 accessibility contracts；
8. 使用 screenshot/browser evidence 验证真实 exported WebAssembly runtime。

当前执行与 acceptance 以 `plan.zh-CN.md` 和 `tasks.zh-CN.md` 为准。
