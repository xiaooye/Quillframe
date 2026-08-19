# 计划 022 · 原生独立审查运行时

## 范围裁定

Framework 变更保持通用。Consumer 事实与 CH001 验收位于不提交的本地 overlay；
不得操作 Frostloom 远端。Project 设计阶段仍是 Project-owned input，生产 executor
继续只执行 `DRAFT` 与 `REVISE`。

## 任务 1 · 冻结 packet 与原生证据核心

先补 RED 测试，再实现 migration/repository、通用 invocation receipt、Codex/Claude
一等 provider、跨 transport attempt 消耗与终态 replay、Host Bridge v10 dispatch/
local surface、通用 submit 别名及 transport/provider/assurance readiness 证据。

## 任务 2 · 原生 host adapter 与旧 transport 修复

添加 Codex/Claude reviewer agent、生命周期及工具拒绝 hook；本地 CLI 在无 Project
临时目录消费 exact packet；GitHub action 全程禁止重建 packet，如实标记 Copilot，
移除未实现的 GitHub Models 验收声明。

## 任务 3 · Mapped Project 运行时 projection

添加可选 manifest、确定性 preview、事务 CAS apply、status、迁移/存储、stage
有界 context materialization、mapped CLI 路由与零模型调用 target/manifest preflight。

## 任务 4 · 集成合同与文档

更新成对文档、registry、machine contract、rollback、跨组件回归及确定性构建证据；
交付前完成 task-level 与最终代码审查。

## 任务 5 · 本地 consumer 验收 overlay

只复制必需本地 consumer 文件。完成 BOOK/VOL1/UNIT1/CH1 设计与显式 context
manifest；验证 Framework successor；apply projection；执行 `DRAFT(CH-001)`；
使用一次真实 Codex native review；只经 `candidate.visible.get` 读取 release 后的
Review Draft。保持 `accepted=false`、`settled=false`。

## 回滚

Acceptance/Settlement 前恢复 consumer 旧 lock/action、从 Git 重建 projection 并
删除临时 runtime state。Review Draft 仍非 Canon；任一指纹不符均 fail closed。
