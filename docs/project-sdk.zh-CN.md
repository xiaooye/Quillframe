# 项目开发工具

Quillframe 项目是一套独立、版本化的小说工程。框架提供通用生产机制；项目提供具体故事事实与权威。

<img src="assets/architecture/framework-vs-project.zh-CN.svg" alt="项目指向锁定的框架版本，而具体人物、正典、计划、状态、研究资料和正文都留在项目侧" width="100%" />

## 项目标识

受支持的项目用 `quillframe.toml` 声明模式版本和逻辑路径；`quillframe.lock.json` 保存精确 Framework identity；`framework.attestation.json` 记录同一组 identity 对应的 materialized bundle 证明。

普通生产运行不得把当前 `main`、Claude session 记忆或其他本地 checkout 静默替换成 Project lock。显式升级使用 `quillframe pin`，它是独立的 dependency/authority 变更，而不是普通写作副作用。

## 新建项目

从干净的 Quillframe source checkout 安装本地命令：

```bash
python -m pip install -e .
quillframe doctor
```

然后在 Framework 仓库之外创建小说项目：

```bash
quillframe init ../my-novel \
  --id MY-NOVEL \
  --title "My Novel" \
  --language zh-CN
```

`init` 会固定当前干净 checkout 的 exact git commit，并使用现有 deterministic Framework bundle contract 计算 `sha256:` fingerprint。若 checkout 有未提交修改，exact pin 会拒绝执行；不能把“某个 commit + 一组未提交 bytes”伪装成可复现 authority。

生成的项目同时包含 project-local `CLAUDE.md` 与 `.claude/settings.json`。Claude Code 只是可选宿主：SessionStart 会验证 Project lock / attestation 与本地 Framework，注入 compact bootstrap state；若 consumer authority 无效，`Write`、`Edit`、`Bash` 等 consequential host tools 会 fail closed。Hook 不会获得 Canon、Framework promotion 或 settlement authority。

## 校验与显式重新固定

```bash
quillframe validate .
quillframe build .
```

`validate` 同时返回结构有效性与 `authority_ready`。为兼容旧 Project，缺少 exact commit/fingerprint/attestation 默认会报告 authority warning，而不会在 validate 时偷偷 repin。

只有明确决定升级 Project 所依赖的 Framework 时才运行：

```bash
quillframe pin .
```

该操作重新计算当前 clean checkout 的 exact commit + bundle fingerprint，先写 attestation，再写 authority lock。若中途失败，后续 validation 会得到 mismatch / not-ready，而不是假定部分成功。

## 责任归属

项目拥有的数据包括具体的书、卷、篇章弧、单元、章节和场景实例，人物与关系，当前状态，主张，依赖，活动计划，项目配置，研究资料，回退证据，正文和已接受正典。

通用框架源码绝不能把这些私有故事事实反向吸收成内置行为。Claude Code、hook、CLI、SQLite、模型结果或 capability 也不会仅因为“能执行”就获得故事权威。

## 标准布局与映射布局

项目开发工具支持标准目录布局；项目适配器可以把成熟项目或旧仓库映射成同一套逻辑契约。映射只改变存储路径，不改变事实权威语义。

旧 Project 的 lock migration 必须是显式工程任务；普通创作 run 不会自动把旧 lock 改成当前 Framework。

## 可复现性

项目应能脱离聊天记忆，独立完成校验与构建。精确 commit、确定性 Framework bundle fingerprint 与 attestation 共同让 materialized runtime bytes 可检查、可复现。Framework 当前 `main` 是框架维护阶段的开发依据，不会在普通生产运行中静默替换下游 Project lock。

Framework bundle 现在覆盖公开 `quillframe` Python package、`pyproject.toml` 与 `VERSION`，因此 CLI / façade 的运行字节也进入 consumer fingerprint；工程过程 `specs/`、Git history 与 local runtime state 仍不属于 bundle authority。

## 变更纪律

结构级改变可以走“规格 → 计划 → 任务 → 实现 → 验证 → 验收”；普通正文微调不需要伪造软件工程仪式。无论目录布局如何，修改正典仍然必须有明确接受和经授权的状态落定事务。
