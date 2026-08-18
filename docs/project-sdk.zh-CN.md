# 项目开发工具

Quillframe 项目是一套独立、版本化的小说工程。框架提供通用生产机制；项目提供具体故事事实与权威。

<img src="assets/architecture/framework-vs-project.zh-CN.svg" alt="项目指向锁定的框架版本，而具体人物、正典、计划、状态、研究资料和正文都留在项目侧" width="100%" />

## 项目标识

受支持的项目用 `quillframe.toml` 声明模式版本和逻辑路径；`quillframe.lock.json` 保存精确框架身份；`framework.attestation.json` 记录同一身份所对应的实体化框架构建包证明。

普通生产运行不得用当前 `main`、宿主会话记忆或另一份本地源码工作区静默替换项目锁。显式升级使用 `quillframe pin`；这是依赖与权威变更，不是普通创作的副作用。

## 新建项目

从干净的 Quillframe 源码工作区安装本地命令：

```bash
python -m pip install -e .
quillframe doctor
```

然后在框架仓库之外创建小说项目：

```bash
quillframe init ../my-novel \
  --id MY-NOVEL \
  --title "My Novel" \
  --language zh-CN
```

`quillframe init` 会固定当前干净源码工作区的精确 Git commit，计算确定性的框架构建包指纹，写入匹配的证明文件，然后安装 Claude Code 与 Codex 的生成式宿主脚手架。若框架源码工作区存在未提交修改，精确固定会拒绝执行；不能把“某个 commit + 一组未提交字节”伪装成可复现权威。

## Claude Code 与 Codex 启动流程

Claude Code 与 Codex 都只是可选宿主，不是 Quillframe 工作流权威。两个宿主都进入同一条确定性生命周期：

`Project discovery → exact authority verification → typed manager session → exactly one task_mode → manager run → sparse Context execution`

`SessionStart` 时，宿主适配器会创建或恢复真正的 `quillframe_agent_session_v1`，并注入包含 `QF_SESSION_ID` 的精简上下文。此时 Project 的精确权威可以已经验证成功，但在模型/用户完成语义判断、明确选择且只选择一个 Quillframe `task_mode`，并启动 manager run 之前，有副作用的工作仍然被阻止。例如宿主会注入类似以下精确命令：

```bash
quillframe host-run begin \
  --session-id SES-CODEX-... \
  --mode DESIGN-BOOK \
  --project .
```

可以用 `quillframe host-run status --session-id ... --project .` 查看当前确定性状态。宿主 bootstrap 的真实状态只有 `blocked`、`awaiting_task_mode` 或 `running`；仅仅把 Quillframe 术语塞进模型上下文不算完成启动。

在进入 `running` 前，`Write`、`Edit`、`Bash` 等有副作用的操作默认拒绝；Codex 的 `apply_patch` 同样按编辑处理。Mode 尚未解析时，唯一允许的 Bash 例外是与注入的精确 session ID 绑定、经过严格解析的 Quillframe `host-run` bootstrap 命令；带 shell chaining 的相似命令不会被放行。

### Codex 的 trust 边界

Codex 会在工作前读取 Project `AGENTS.md`，所以生成文件现在直接包含 Quillframe bootstrap 规则，而不是只做链接跳转。Project 也会生成 `.codex/hooks.json`，但 Codex 会把 Project trust 和非托管 command hook 的 review/trust 当作用户安全边界。如果启动上下文里没有 `QF_SESSION_ID`，请先在 Codex 中打开 `/hooks`，审查并信任 Quillframe hooks，然后重启该 Codex session；在此之前不要执行有副作用的 Project 写入。

### 修复现有 Project 的宿主脚手架

较早创建、但仍受支持的 Project 可以显式安装或修复当前宿主配置：

```bash
quillframe host-install .
```

这个操作与 `quillframe pin` 明确分离：它不会修改 Framework lock / attestation，也不会改变任何 Project Canon、计划、profiles、正文或故事状态。已知由 Quillframe 生成的文件会幂等升级；如果检测到未知的用户自定义 `AGENTS.md` 或宿主配置，则返回 `manual_merge_required`，不会静默覆盖。只有用户明确决定替换时才使用 `--force`。

## 校验与显式重新固定

```bash
quillframe validate .
quillframe build .
```

`validate` 同时返回结构有效性与 `authority_ready`。为了兼容旧项目，缺少精确 commit、指纹或证明文件时会报告权威警告，而不会在校验阶段偷偷重新固定。

只有明确决定升级项目所依赖的框架时才运行：

```bash
quillframe pin .
```

该操作重新计算当前干净源码工作区的精确 commit 与构建包指纹，先写证明文件，再写权威锁。若中途失败，后续校验会得到不匹配或未就绪状态，而不是把部分完成猜成成功。

## 责任归属

项目拥有的数据包括具体的书、卷、篇章弧、单元、章节和场景实例，人物与关系，当前状态，主张，依赖，活动计划，项目配置，研究资料，回退证据，正文和已接受正典。

通用框架源码绝不能把这些私有故事事实反向吸收成内置行为。Claude Code、Codex、Hook、命令行、SQLite、模型结果或宿主能力也不会仅因为“能够执行”就获得故事权威。

## 标准布局与映射布局

项目开发工具支持标准目录布局；项目适配器可以把成熟项目或旧仓库映射成同一套逻辑契约。映射只改变存储路径，不改变事实权威语义。

旧项目的框架锁迁移必须是显式工程任务；普通创作运行不会自动把旧锁改成当前框架。

## 可复现性

项目应能脱离聊天记忆，独立完成校验与构建。精确 commit、确定性框架构建包指纹与证明文件共同让实体化运行字节可检查、可复现。框架当前 `main` 是框架维护阶段的开发依据，不会在普通生产运行中静默替换下游项目锁。

框架构建包现在覆盖公开 `quillframe` Python package、`pyproject.toml` 与 `VERSION`，因此命令行与公共 façade 的运行字节也进入下游项目指纹；工程过程 `specs/`、Git 历史与本地运行状态仍不属于构建包权威。

## 变更纪律

结构级改变可以走“规格 → 计划 → 任务 → 实现 → 验证 → 验收”；普通正文微调不需要伪造软件工程仪式。无论目录布局如何，修改正典仍然必须有明确接受和经授权的状态落定事务。
