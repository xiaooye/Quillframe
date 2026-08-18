# 规格说明 · Claude Code 与 Codex 统一 Project Bootstrap

状态：Draft

Primary task mode：`SYSTEM-IMPROVE`

## 问题 / 背景

第一轮 zero-setup host work 已经让 Claude Code 能看到 Quillframe authority，但仍没有完成真正的 Quillframe bootstrap lifecycle，也没有为 Codex 提供等价宿主路径。

当前失败是结构问题，不是 prompt 写得不够长：

- 根 `AGENTS.md` 仍只是 router；Codex 会直接读取 `AGENTS.md`，不会解释 Claude 专用的 `@path` import；
- consumer Project 只生成 Claude 配置，没有 Codex lifecycle hooks；
- Claude hook 写入的是临时拼装的 Control Plane session，而不是既有 `quillframe_agent_session_v1`；
- 没有创建/恢复 manager run；
- `primary_task_mode` 永远停在 `UNRESOLVED`；
- authority 已验证后，即使没有 Quillframe task mode/run，当前 hook 仍可能允许 consequential write；
- 若继续分别实现 Claude/Codex bootstrap，容易形成两套会漂移的工作流；
- 用户若从 Generic Framework checkout 直接提出小说创作意图，系统还需要一个安全路径先创建独立 consumer Project，而不能为了通过 write gate 假装小说任务属于 Framework task mode。

## 用户 / 编辑价值

用户应当可以用 Claude Code 或 Codex 打开同一个已经初始化的 Project，并在创作开始前得到同一条 Quillframe execution boundary：

`Project discovery → exact authority verification → manager session → exactly one task_mode → manager run → sparse-context execution`

如果用户从 Generic Framework checkout 开始并提出 fiction intent，宿主应该通过一个极窄的 deterministic escape 创建独立 consumer Project，然后要求从该 Project 重启宿主；不得把故事数据写进 Framework，也不得伪造一个 Framework task mode。

宿主差异只能存在于 adapter 层，不能改变 workflow semantics。

## 当前 Research

当前 Codex 官方支持 Project `AGENTS.md` discovery，以及 project-local `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`SessionEnd` lifecycle hooks。Project `.codex/` 配置与 hook 只有在项目被 trust 后才加载；非 managed command hook 还需要单独 review/trust。`PreToolUse` 可以观察/阻止 Bash 和 `apply_patch` 编辑。因此即使 hooks 尚未 trust，静态 `AGENTS.md` 也必须足以正确说明 Quillframe bootstrap。

Claude Code 会加载 `CLAUDE.md`，支持 `@path` import，并通过项目 settings 提供本任务所需的 lifecycle hooks。现有 `claude_hook.py` 应降为一个调用统一 bootstrap core 的 compatibility wrapper。

## Requirements

1. 增加一个 Claude Code 与 Codex 共用的 host-neutral bootstrap runtime。
2. consumer Project 在允许 consequential host execution 前，必须验证 `quillframe.toml`、exact lock、attestation 与 materialized Framework identity。
3. Host manager session 必须使用既有 `quillframe_agent_session_v1` contract，并通过 Control Plane 持久化。
4. Bootstrap 不得猜 literary task mode。模型/用户必须通过 deterministic command 显式解析且只解析一个合法 Quillframe `task_mode`。
5. 启动 task mode 必须创建一个且仅一个 active manager run，并绑定 verified Project/session/authority snapshot。
6. authority 无效、task mode 未解析或不存在匹配 active run 时，consequential writes 必须 fail closed。
7. 解析 mode / 启动 run 所用 bootstrap command 不能被自己的 write gate 卡死；pre-mode 状态只允许极窄的 Quillframe 自身 deterministic bootstrap command。
8. 根与 consumer `AGENTS.md` 必须直接包含精简 Quillframe bootstrap 规则，使 Codex 在 project hooks 尚未 trust 时仍能正确启动。
9. 新 Project 除 Claude host 配置外，还必须生成 `.codex/hooks.json`。
10. Codex `apply_patch` 必须视为 consequential edit。
11. 为现有 supported Project 增加显式、幂等的 host-install/repair command；不得 repin Framework、改 Canon，也不得在没有安全 precondition 时覆盖未知用户自定义 host instructions。
12. Host adapter 必须返回真实状态，例如 `blocked`、`awaiting_task_mode`、`running`；只把 Quillframe 术语塞进 context 不能算 bootstrap complete。
13. Normal CI 继续 deterministic、model-free。
14. 在 Generic Framework scope 内，fiction intent 不得选择 fiction task mode。Mode 未解析前只能额外放行经过严格 parser 校验的 `quillframe init` / `python -m quillframe.cli init`：必须有一个位于 Framework 外部的 target、必需的 project id/title，不允许 `--force` 或 shell chaining，并继续服从宿主原有 permission/approval。创建后必须从 consumer Project 重启宿主。

## Non-goals

- 不让 Claude Code / Codex 成为 Quillframe Agent Runtime authority。
- 不用 regex/heuristic 猜 literary task mode。
- Host hook 不执行 Canon settlement 或 acceptance。
- 不静默 repin Framework，也不偷偷做 consumer schema migration。
- 不修改 Studio UI/UX。
- 本 workstream 暂不负责把旧 pinned Framework bundle 恢复/materialize 到 `.quillframe/framework`；先修正 host lifecycle，本地 exact bundle delivery 如仍需要应单独处理。

## Authority / Canon 影响

不改变任何 story authority。只强化 host entry、execution identity 与 deterministic preconditions。Model output、host session state 或 hook 成功本身永远不会授予 Canon / Framework promotion authority。

## Compatibility / Overreach Audit

- 继续支持 Claude Project files；`claude_hook.py` 变成薄 compatibility entry。
- Codex hooks 为 additive project-local integration；untrusted Project 仍依赖 `AGENTS.md`，并由用户显式 trust hooks 后才启用 lifecycle enforcement。
- 不自动 repin 任何旧 Project。
- 已存在的自定义 `AGENTS.md` / host config 必须保留；只有已知 generated Quillframe scaffold 或用户显式 force 才允许替换。
- Generic Framework contract 不加入 provider/model-specific authority 假设。
- Framework→consumer init escape 不是通用的 pre-mode shell allowlist；它只让宿主自身的正常 permission layer 可以考虑一条确定性的 Project 创建命令，而底层 init 仍会拒绝 Framework 内部 target 与不满足 exact clean pin 的状态。

## 验收场景

1. Fresh Framework repo 用 Codex 打开时，即使 hook 未 trust，也会从根 `AGENTS.md` 直接看到 Generic Framework boundary。
2. 新初始化 consumer Project 同时包含可工作的 Claude 与 Codex host config。
3. Claude / Codex `SessionStart` 生成等价 verified Project bootstrap snapshot。
4. 持久化 manager session 能通过 `quillframe_agent_session_v1` validation。
5. task mode 解析前，Write/Edit/Bash/apply_patch 被拒绝，但极窄的 mode-start command 可在宿主正常权限层继续处理。
6. `quillframe host-run begin --mode DESIGN-BOOK` 校验 mode、启动一个 run、持久化，然后已授权 Project writes 才可以继续。
7. 非法 mode 或第二个冲突 mode 必须 fail closed，不得静默切换。
8. lock/attestation 被篡改或 Framework identity 变化时，两个宿主都阻止执行。
9. `quillframe host-install` 能幂等升级已知 generated host scaffold，并且不改 lock/attestation/Canon。
10. 既有 deterministic tests、docs quality、Studio build 与 normal no-live-model CI 保持 green。
11. Generic Framework scope 下，严格的外部 target Project init command 可交回宿主正常 approval；Framework 内部 target、`--force` 或 shell chained lookalike 必须在执行前被拒绝。

## 风险

- 两个宿主的 hook schema 存在细微差异；wrapper 必须 normalize input/tool aliases，而不能把 host-specific semantics 泄露到 core。
- Bash gate 过宽会导致 bootstrap deadlock；pre-mode allowlist 必须继续结构化解析，并严格限制在 Quillframe 自身 run bootstrap 与唯一的 Framework→consumer Project creation escape。
- Codex hook trust 是用户安全边界，Quillframe 不应绕过；static instructions 与 diagnostics 必须明确暴露该状态。
