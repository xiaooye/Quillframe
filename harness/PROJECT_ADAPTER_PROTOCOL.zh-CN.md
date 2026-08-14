# 项目适配协议 · 映射存储结构，但绝不导入故事事实

NovelForge Project Adapter 的职责，是把某个下游小说仓库的物理目录映射成 Harness 所需的**逻辑项目接口**。它解析项目身份、安全路径、权威领域和依赖信息；它不负责判断哪些内容与当前任务语义相关，也不能把项目事实反向带进通用 Framework source。

> **核心不变量 ✦** 项目拥有实例与事实；NovelForge 拥有通用 Schema 与机制。Adapter 只负责说明“项目自己的东西在哪里、属于哪类逻辑领域”。

---

## 01 · 项目身份

标准项目由两个文件建立根身份：

```text
novelforge.toml
novelforge.lock.json
```

`novelforge.toml` 声明项目身份、Project Schema 兼容性、逻辑权威 / 路径映射、质量与 profile 配置，以及 build 设置。

`novelforge.lock.json` 记录 Framework dependency identity。正式生产的 lock 可以绑定版本、精确 commit 与 bundle fingerprint。

**Lock 负责识别依赖，不会把项目事实的 authority 转让给 Framework。**

旧项目可以通过 mapped adapter 保留不同物理目录，但最终必须解析成同一套逻辑边界。

---

## 02 · 依赖方向只有一个

```text
小说项目 → 锁定的 NovelForge Framework
NovelForge Framework -X→ 项目专属事实
```

通用 Framework source 里不能 hard-code：

- 某个下游仓库名称或路径；
- 某一本书的 BOOK / CHAPTER / SCENE ID；
- 具体人物、关系、世界或剧情状态；
- 项目专属 research claim；
- 私人用户偏好数据；
- 只适用于某个项目的默认 profile。

迁移某本小说时发现的经验，可以启发通用 mechanism；具体项目内容不能跟着 mechanism 一起被嵌进 Framework。

---

## 03 · 标准布局与映射布局

参考实现 [`project_adapter.py`](../project_adapter.py) 支持：

- `standard`：Project SDK 标准目录；
- `mapped`：把旧物理路径映射成要求的逻辑接口。

每条映射路径都会经过确定性检查：

- 必须是非空字符串；
- 相对项目根目录解析；
- 一旦逃逸出 project root，直接拒绝；
- required domain 必须真实存在；
- 记录目标最终是 file、directory 还是缺失的 optional path。

Adapter 可以理解 layout；它**不会因此获得重新解释内容的权限**。

---

## 04 · 项目逻辑领域

标准项目通常暴露：

- bible / story definitions；
- structured state；
- future plans；
- manuscripts；
- profiles；
- evals / tests；
- research；
- corpus refs；
- specs；
- assets。

Mapped legacy project 可以改为显式映射 project entry、start-here / context protocol、story bible、current state、active plans、manuscripts 和 profiles。

物理名称可以不同，**authority class 不能因为目录方便就靠猜**。

例如：

```text
active plan     ≠ current state
review draft    ≠ accepted manuscript
runtime memory  ≠ Canon
corpus evidence ≠ character knowledge
```

---

## 05 · Adapter Resolution 输出是什么

确定性 resolver 会产生类似：

```yaml
schema: novelforge_project_adapter_resolution_v1
project_id: ...
project_version: ...
project_root: ...
layout: standard | mapped
framework_lock: ...
project_schema_version: ...
authority: ...
paths: ...
quality: ...
build: ...
```

这份结果回答的是：**项目自己的材料在哪里、如何被逻辑分类。**

它不是：

- Context Manifest；
- prompt packet；
- semantic relevance ranking；
- 自动生成的 Canon snapshot；
- “这个文件可以安全注入模型”的证明。

---

## 06 · 上下文选择发生在 Adapter 之后

项目解析完成后，Harness 才通过 Context / Memory 系统建立 task-scoped context。

Adapter 绝不能因为能够找到整个 bible / state / manuscript history，就把它们全部送进模型。

当前职责边界是：

```text
项目路径 + authority resolution → Adapter / Project SDK
perspective-safe visibility      → 确定性 Context Runtime
当前任务的 semantic relevance    → context.select 模型契约
hard budget packing              → 确定性运行时
```

这样才能防止“存储结构”悄悄变成“prompt policy”。

---

## 07 · Project Bundle 只是派生视图

Adapter 可以构建紧凑 mapped project bundle，记录：

- 项目身份；
- Framework lock metadata；
- authority / path map；
- 文件 fingerprint 与 size；
- content-index / bundle fingerprint。

它适合 bootstrap 与 reproducibility，但仍然是**derived artifact**，不是第二套 authority database。

项目源状态变化以后，应重新 build bundle，而不是直接编辑 bundle 冒充事实更新。

---

## 08 · Framework 本地物化

项目可以把锁定的 Framework dependency 物化到：

```text
.novelforge/framework/
```

把它视为 read-only dependency cache：

- 按 lock 要求验证 commit / fingerprint；
- 不能直接改 cache 当作 project override；
- 不能从 Framework session history 推断项目事实；
- Framework upgrade 必须是显式 project change；
- compatibility 重新验证完成前，不恢复正式生产。

本地副本可以提升 bootstrap 效率，但不会改变依赖方向。

---

## 09 · Framework Upgrade

会改变行为的 Framework upgrade 属于结构级项目变更：

```text
解析当前 lock
→ 审计 migration / compatibility impact
→ 必要时 spec / plan / tasks
→ 物化 candidate Framework revision
→ 验证 Project contract
→ deterministic tests + 适用的 semantic evals
→ 接受 dependency change
→ 更新 exact lock / bundle evidence
```

Framework Schema 或 mechanism 改变时，不能静默重新解释已经 Accepted 的 Canon。

如果某个 runtime session 在 lock 改变后恢复，必须按新 exact dependency 重新 bootstrap，不能继续相信 provider memory 里的旧 Framework 状态。

---

## 10 · Legacy Migration

成熟旧小说不需要为了接入 NovelForge 先做 destructive directory rewrite。

安全迁移通常是：

```text
审计物理布局
→ 加 manifest + lock
→ 映射逻辑 authority domains
→ 验证路径安全与 required domains
→ 构建 derived project bundle
→ 加 deterministic CI
→ 把真正通用的 mechanism 与项目专属规则分开
→ 删除 stale embedded Framework / runtime copy
```

迁移必须保留旧项目已有 authority semantics。一个目录名看起来像“最终稿”，不足以把 Plan / Review 自动升级成 Accepted Canon。

---

## 11 · 失败时必须停下来

以下情况应 fail closed，而不是猜：

- required project identity 缺失；
- manifest / lock schema 不兼容；
- mapped path 逃逸 project root；
- required logical domain 不存在；
- project profile 尝试静默关闭 mandatory Framework fundamentals；
- 无法按 lock 要求验证 Framework dependency。

Adapter failure 是 bootstrap / compatibility problem，不是模型自行补出项目状态的许可证。

---

## 12 · 相关契约

- [Project SDK](../docs/project-sdk.zh-CN.md)：标准项目结构、验证与 build。
- [Project Adapters 指南](../docs/project-adapters.zh-CN.md)：面向迁移者的使用说明。
- [上下文与记忆](../docs/context-and-memory.zh-CN.md)：完成项目解析以后的 task-aware sparse context。
- [正典状态](../core/CANON_STATE.zh-CN.md)：权威与 settlement。
- [`project_adapter.py`](../project_adapter.py)：确定性参考 resolver。

**Adapter 可以翻译存储形状，但绝不能把“方便”翻译成“权威”。**
