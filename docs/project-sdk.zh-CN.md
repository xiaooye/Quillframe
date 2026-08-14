<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="54" />
  <p><strong>项目 SDK · 把每一本小说维护成独立治理、可验证、可复现的工程项目</strong></p>
  <p><kbd>脚手架</kbd>&nbsp;&nbsp;<kbd>依赖锁定</kbd>&nbsp;&nbsp;<kbd>结构校验</kbd>&nbsp;&nbsp;<kbd>确定性构建</kbd>&nbsp;&nbsp;<kbd>迁移</kbd></p>
  <p><a href="project-sdk.en.md">English</a> · <a href="README.zh-CN.md">文档中心</a></p>
</div>

# 项目 SDK

NovelForge 提供的是通用小说生产框架；真正消费它的小说 Project 才拥有**这一本书自己的权威状态、计划、稿件、研究、配置、回归证据、测试与接受历史**。

Project SDK 的作用，就是让这些东西脱离任何单次聊天，也依然能够被独立 clone、检查、构建和恢复。

> **依赖方向永远是：Project → 精确锁定的 NovelForge。** 通用框架不能反向吸收某一本小说的 Canon、人物、剧情或用户私有口味。

---

## 01 · 一个完整 NovelForge Project 是什么

它不只是一个 `manuscripts/` 目录。

一个成熟项目应该能够：独立 clone、自描述、做结构校验、确定性构建、执行迁移与回滚，并且不依赖 provider conversation history 才知道“现在做到哪里”。

标准布局通常包含：

`profiles/` —— genre、platform、prose、reader 与 Project-specific 配置。

`bible/` —— 项目自己拥有的世界、人物与故事参考资料。

`state/` —— Canon、current state、ledgers 等项目权威状态。

`plans/` —— 未来意图；不会因为被保存下来就变成 current Canon。

`manuscripts/` —— draft、review、accepted、published 等稿件生命周期。

`research/` —— 现实证据与项目自己的 fictionalization decision。

`corpus/` —— 项目侧语料引用 / evidence index，不是 Framework Canon。

`evals/`、`tests/`、`regressions/` —— 质量与工程证据。

`specs/`、`migrations/` —— 结构级变更记录。

`dist/` —— 可以重新生成的确定性构建产物。

已有成熟目录结构的项目不必为了迁就固定文件夹名而破坏仓库，可以使用 mapped Project Adapter。

---

## 02 · 创建项目脚手架

```bash
python project_sdk.py init ./my-novel \
  --id PROJECT-X \
  --title "My Novel" \
  --framework-version <compatible-version>
```

脚手架会创建：

- `novelforge.toml`；
- `novelforge.lock.json`；
- 标准 authority / manuscript / research / quality 目录；
- 中英文 README；
- Agent discovery 文件；
- profile stub；
- 用于排除 runtime state、本地 Framework materialization 和私有 learning data 的 `.gitignore`。

但 `init` 只是**建立项目骨架**，并不能证明 Framework dependency 已经完整解析。

初始 lock 结构允许 `commit` 或 `bundle_fingerprint` 暂时为空。真正进入受治理的生产运行前，Project 应按照自己的 bootstrap contract 把 Framework 解析到所要求的精确 revision / bundle evidence。

不要从文档里复制一个版本号，然后把“兼容版本”误当成“精确锁定”。

---

## 03 · `novelforge.toml` 描述逻辑项目契约

Manifest 应描述项目本身，而不是某台电脑上的绝对路径。

主要内容包括：

**项目身份** —— stable ID、title、language、Project version、status。

**Framework contract** —— 兼容版本、lockfile 位置，以及 project-to-framework-only 的依赖方向。

**Authority paths** —— Canon、current state、ledgers、bible、profiles、plans、manuscripts、research、corpus、evals、tests、migrations、regressions 与 generated output 的逻辑位置。

**Quality contract** —— Framework generic quality layer 是否保持启用，以及项目声明支持哪些高级机制。

Manifest 是配置与路由证据，不会因为某个 path 被声明为 `plans`，就把里面的内容升级成 Accepted Canon。

---

## 04 · `novelforge.lock.json` 保存 Framework dependency evidence

Lockfile 把 Framework dependency 与项目内容明确分开。

一份已解析的 Framework lock 可以记录：

- repository；
- version / compatibility metadata；
- exact commit；
- deterministic bundle fingerprint；
- bundle format 或 materialization metadata。

真正执行时需要哪些精确字段，由当前 Project bootstrap / Adapter contract 决定。

必须分清两件事：

**兼容版本 ≠ 精确 revision。** 一个版本字段可以说明兼容关系，却不一定唯一确定 Framework bytes。

**Exact commit ≠ exact bundle bytes。** 如果下游使用 deterministic Framework bundle，还可以用 SHA-256 bundle fingerprint 绑定真正被 materialize 的内容。

生产项目绝不能把自己锁定的依赖静默替换成“现在 main 上最新的 Framework”。

---

## 05 · 校验项目结构

```bash
python project_sdk.py validate ./my-novel
```

SDK validator 负责检查它真正拥有的确定性结构，例如：

- Project schema 与必填 identity fields；
- lockfile schema 与 bundle fingerprint 格式；
- 必需逻辑目录 / entry file；
- bilingual structural spec 是否成对；
- manuscript lifecycle 是否存在可疑重复；
- Project profile 是否试图关闭 mandatory Framework Surface Fundamentals。

Validation 故意**不声称**能证明“小说质量很好”“Canon 在语义上完全正确”或者“dependency 已经通过所有 production bootstrap gate”。

它只证明 Project SDK 自己拥有的结构契约。

---

## 06 · 构建确定性 Project bundle

```bash
python project_sdk.py build ./my-novel
```

构建成功后会生成 `dist/project.bundle.json`、按类别拆分的 manifest，以及 fingerprint 文件。

Bundle 会记录：

- Project metadata；
- Framework-lock metadata；
- authority / path configuration；
- bootstrap entry files；
- classified content index；
- 每个文件的 SHA-256 fingerprint；
- content-index fingerprint；
- Project bundle fingerprint。

文件分类会把 authoritative Project material 与 plan、generated manuscript、research、eval、corpus reference、spec、test、asset、metadata 区分开。

目的不是给所有文件贴更多标签，而是避免“仓库里存在的东西”都被当成同一种真相。

`dist/` 是 derived output，应该能够重建。

---

## 07 · Project authority 必须保持显式

Project contract 应把 lifecycle 与 authority 分开。

常见 authority class 包括：

`locked` —— 项目明确锁定的事实；

`accepted` —— 已经明确接受并完成相应结算的事实 / artifact；

`active_plan` —— 当前未来意图；

`review` —— 等待用户接受的候选稿；

`proposal` —— 尚无权威的修改建议。

具体 precedence 由 Project 自己拥有，并应在项目 authority 文档中明确写出。

几个直接后果：

- 内容存进 `plans/` 不代表它已经发生；
- Review manuscript 即使 QA 通过也不等于 Canon；
- 用户接受与结构化 Settlement 是不同事件；
- Memory、semantic result、Corpus evidence 都不能绕过 Project authority model。

---

## 08 · Standard layout 与 mapped Adapter

新项目直接使用标准 scaffold 最简单。

但成熟小说仓库通常已经有自己的目录和数据库组织方式。NovelForge 不要求为了“目录长得像模板”而做破坏性迁移。

Mapped Project Adapter 可以把逻辑角色映射到现有路径，例如 Project profile、Accepted Canon、current state、plans、manuscripts、research 与 regressions。

Adapter 必须保持的是**语义角色**，而不只是“这个 path 存在”。

一个技术上能解析、语义上却映射错的 path，比明确 validation failure 更危险。

继续阅读：[项目适配器](project-adapters.zh-CN.md) · [项目适配器协议](../harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md)

---

## 09 · 真正的结构级变更才需要 spec

遇到 schema migration、新 subsystem、authority change、release engineering 等 consequential structural work，可以用 Project SDK 创建中英双语工程包：

```bash
python project_sdk.py spec-new ./my-novel \
  --title "relationship state migration"
```

生成内容包括配对的：

- specification；
- implementation plan；
- task list。

它适合那些确实需要 migration、rollback、verification 与 acceptance 的变更。

普通正文 micro edit 不要为了“看起来专业”制造完整工程仪式。

---

## 10 · Project 自己拥有 tests 与 quality evidence

一本 Project 可以维护：

- deterministic tests；
- Project-specific eval cases；
- 来自真实失败的 regression evidence；
- continuity checks；
- structural migrations；
- artifact fingerprints 与 acceptance evidence。

Framework quality fundamentals 仍然属于通用机制。Project evidence 可以调整 profile-sensitive 行为，但不能仅因为本地偏好不喜欢某个 gate，就静默关闭明确的 Framework failure mechanism。

Corpus evidence、regression evidence 与 semantic review result 都仍然只是 evidence，不是 Canon。

---

## 11 · Runtime state 不是 Project truth

下面这些通常属于 operational / derived state：

- `.novel-os/` 或同类 runtime database；
- `.novelforge/` 本地 Framework materialization；
- local learning database；
- provider session；
- temporary semantic packet / receipt。

它们可能对执行与恢复非常重要，却不会因此自动成为 Project authority，也不应该默认被 commit 成 story truth。

真正的项目事实仍然来自 Project 明确的 authority structure 与经过授权的 settlement。

---

## 12 · 推荐的生产 bootstrap 顺序

“目录结构校验通过”并不等于完整 bootstrap。

稳健的生产启动通常包括：

**解析 Project。** 读取 `novelforge.toml` 与 `novelforge.lock.json`。

**解析精确 Framework。** materialize / verify Project 真正锁定的 revision。

**读取 Framework authority。** 从那个 exact revision 读取 `HARNESS_MANIFEST.yaml`、Skill contract 与 Harness manager protocol。

**解析 Project Adapter。** 校验 standard / mapped layout，并构建逻辑视图。

**选择唯一 task mode。** 一次 DRAFT 不应偷偷串入 SETTLE 或 SYSTEM-IMPROVE。

**建立 / 恢复 runtime identity。** Session、run、checkpoint 与 capability 都和 Project truth 分开。

**构建稀疏任务上下文。** 只加载当前工作真正需要的 Project slice。

到这一步，“把小说当工程项目”才真正进入运行层，而不只是目录看起来整齐。

---

## 13 · 常见失败

**Lock metadata 存在，但 exact dependency 还没解析** → 完成依赖解析后再进入 production bootstrap。

**Project 结构合法，但 authority 语义仍然含糊** → 修 Project authority / Adapter mapping；结构 validation 不能替代语义边界。

**Framework source 开始出现某一本小说的事实** → dependency-boundary violation；把 Project instance 移回 Project。

**同一稿件路径同时出现在多个 lifecycle directory** → 先解决 lifecycle ambiguity，不能猜哪份最权威。

**Profile 尝试关闭 mandatory Framework Fundamentals** → deterministic validation failure。

**Legacy path 的真实语义已经变化** → Adapter drift；consequential work 前重新验证 mapping。

**把 `dist/` 当 source truth** → 从 authoritative Project files 重建。

---

## 14 · 精确参考

- [`project_sdk.py`](../project_sdk.py) —— scaffold、validate、build 与 spec tooling。
- [项目适配器](project-adapters.zh-CN.md) —— 旧仓库接入。
- [项目适配器协议](../harness/PROJECT_ADAPTER_PROTOCOL.zh-CN.md) —— logical mapping contract。
- [架构总览](architecture.zh-CN.md) —— Project / Framework authority boundary。
- [Framework Bundle](../release/FRAMEWORK_BUNDLE.zh-CN.md) —— deterministic Framework materialization 与 bundle fingerprint。
- [会话运行时](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md) —— Project authority 之外的 operational state。

<div align="center">
  <img src="../assets/brand/novelforge-mark.svg" alt="NovelForge Story Loom 标志" width="48" />
  <br />
  <sub>小说可以自由演化，生产状态仍然可以精确复现。🌸</sub>
</div>
