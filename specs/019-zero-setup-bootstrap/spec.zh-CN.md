# 规格说明 · 零配置启动与 Claude Code 宿主守卫

状态：Draft

## 问题 / 背景

全新源码 checkout 可以在 Quillframe Python 包尚未安装、也尚未建立下游小说 Project 时直接被 Claude Code 打开。当前根 `CLAUDE.md` 只是 router；Claude 生命周期 hook 只记录 telemetry，不注入已经验证的 Quillframe 状态；`project_sdk.py init` 生成的 lock 仍允许 commit / fingerprint 为空。结果是第三方 coding agent 虽然“知道 Quillframe 这个词”，实际执行时仍可能落回自己的通用 brainstorming 工作流。

## 当前状态审计

- Quillframe Agent Runtime 拥有 agent semantics；Claude Code 只是可选宿主 / integration。
- `CLAUDE.md` 没有使用 Claude Code 官方支持的 `@path` import 加载真正 bootstrap contract。
- `.claude/settings.json` 当前只调用 telemetry hook。
- 新 consumer Project 不会得到 Claude Code hook 配置。
- 新 consumer lock 不是 exact pin。
- 已安装 Python package 没有 `quillframe` console entrypoint。

## 用户 / 编辑价值

本地常规路径应当稳定为：

`clone → pip install -e . → quillframe doctor → quillframe init <project> → cd <project> → claude`

Claude Code 启动后，应在第一条用户 prompt 之前就知道：当前位置是 Generic Framework 还是已验证 consumer Project、哪一组 exact Framework bytes 才有权威，以及小说任务必须恰好由一个 Quillframe `task_mode` 统领。

## Requirements

1. 增加真正的 `quillframe` CLI，统一 doctor / init / pin / validate / build 与 Claude host integration。
2. 新 Project 初始化必须把干净 Framework checkout 固定到 exact git commit + deterministic Framework bundle fingerprint。
3. 新 Project 初始化必须生成与同一 identity 绑定的 `framework.attestation.json`。
4. Project validation 必须明确暴露 exact Framework authority 是否 ready，但不得静默迁移旧 Project。
5. 根 Claude Code instructions 必须通过受支持的 import 机制加载真正 Quillframe bootstrap 规则。
6. Claude `SessionStart` 必须注入 compact、typed bootstrap state，而不是只做 telemetry。
7. 新 consumer Project 必须带 project-local Claude hook settings，并通过已安装 Quillframe host bridge 执行。
8. Consumer lock / attestation 无法验证时，Claude consequential tools 必须 fail closed；read-only diagnosis 仍可进行。
9. Generic Framework coding work 仍然必须可用；host guard 不能把 Claude Code 变成 Framework authority，也不能 hard-code 任何 Project facts。
10. Normal CI 继续完全 deterministic、model-free。

## Non-goals

- 不用 Claude Code 取代 Quillframe-owned Agent Runtime。
- 不用 regex / heuristic 猜 literary task mode。
- Hook 不自动 SETTLE Canon，也不自授 write authority。
- 本变更不偷偷迁移所有旧 consumer Project。
- 不修改 Studio UI / UX。

## Authority / Canon 影响

不改变任何小说 Canon 权威。只强化 Framework / Project identity 与宿主执行边界。

## Reader / Prose 影响

间接改善：小说任务会更可靠地进入 Quillframe production workflow，而不是未治理的通用 coding-agent workflow。

## Compatibility Constraints

- 旧 Project 若 lock 不完整，仍然可以 inspect，但明确返回 `authority_ready=false`；不得静默 repin。
- Source checkout / editable install 仍是当前本地 exact pin 的主要开发路径。
- Framework fingerprint 继续使用现有 deterministic bundle contract。

## 验收场景

1. Fresh Framework checkout + editable install 后存在 `quillframe --help` 与 `quillframe doctor`。
2. `quillframe init` 从 clean checkout 创建 non-null exact commit/fingerprint，并生成匹配 attestation。
3. 在 Framework repo 启动 Claude 时，第一轮 context 明确它是 Generic Framework，不得把 fiction Project 写进这里。
4. 在新 consumer Project 启动 Claude 时，第一条用户 prompt 前即得到已验证 Project/Framework authority context。
5. 篡改 consumer lock 或 attestation 后，Write/Edit/Bash 会被 host guard 拒绝。
6. 现有 deterministic tests 与 documentation quality gate 保持 green。

## 风险

- init/pin 时计算 deterministic bundle fingerprint 会产生本地 I/O；显式 pin 操作可接受，但不能每个 tool call 都重算。
- Claude hook JSON contract 未来可能变化；必须用测试锁住当前支持格式，并在异常时安全失败。
- 非 editable 的全局 package 可能没有完整 source checkout；此时 host discovery 应返回 blocked，而不是伪造 authority。