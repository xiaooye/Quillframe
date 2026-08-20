# Native Project Contract

一个 Quillframe 1.0 Project 是一部小说唯一的权威边界。Framework 提供通用机制；Project 拥有具体故事事实与 Canon。

## 创建或打开

面向作者的创建与启动入口只有：

```bash
quillframe launch ./my-novel --new \
  --id MY-NOVEL \
  --title "My Novel" \
  --language zh-CN
```

打开已有 Project 使用 `quillframe launch ./my-novel`。不传路径时，交互式 launch 依次检查当前目录、最后一次明确打开的 Project，再提供新建向导；非交互环境无法确定 Project 时会返回 typed error。

## 精确 1.0 identity

根目录 `quillframe.toml` 必须精确声明 `quillframe_project_v1_0`、Project identity、language 与 `chapter_scope = "CH001"`。其他 schema 或 chapter scope 会在打开 Core state 前被拒绝。不存在 import、mapped layout、state upgrader 或 dual read path。

本地持久化状态位于 `.quillframe/data/`，SQLite 必须带有精确的 `project:1.0` schema identity。没有该 identity 的数据库会保持原样并被拒绝；处理 pre-release state 的方式是创建新的 1.0 Project。

## Ownership

Project-owned data 包括故事与角色事实、计划、研究、正文修订、作者显式决定、Accepted Canon、settlement receipt 与 publication state。模型提供语义证据和提案；Core 拥有确定性的 state、permission、fingerprint、budget、transaction 与 idempotency。

浏览器、coding-agent host、模型响应、SQLite 中存在数据或 capability declaration 都不能授予 Canon authority。

## CH001 边界

1.0 验收只执行 CH001。CH002 及后续章节必须在 projection、context assembly、model routing、draft、review、accept、settlement 或 publish 之前被拒绝。

## 可复现与导出

Core-owned backup/export action 会绑定精确 Project 与 artifact fingerprint。Hosted upload 每次都必须显式发起且是单次单向动作；本地 launch 不会自动上传或同步。导出 bundle 可以包含 Project material 与 safe receipt，但不能包含模型 credential 或 private reasoning。

## Native contract boundary

唯一 Project identity contract 是五键 `quillframe.toml`、CH001 context、`manifest_fingerprint` 与 `.quillframe/data` boundary。deterministic transport bundle 可以携带 fingerprint evidence，但永远不是 Project authority。产品创建、打开与正常创作始终通过 `quillframe launch` 和 Host Bridge v11。
