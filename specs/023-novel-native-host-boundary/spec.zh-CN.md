# Spec 023 · Quillframe 小说契约原生 Host 边界

状态：已在 v0.9.1 release-candidate 线上实现；正式发布仍需 exact main / CI / tag 证据

## 决策

Quillframe 是小说契约内核，不是通用 agent harness。产品边界统一表述为：

> The host runs the agent. Quillframe governs the novel.

Codex、Claude Code、Cursor 等 Host 负责通用 session、模型/工具循环、沙箱、
通用 subagent 与 transport。Quillframe 负责 Project resolution、故事/人物/关系/
Canon 契约、POV 与知识边界、计划 horizon、有界 Context、candidate lifecycle、质量
gate、exact independent review、Review Draft 可见性，以及 Acceptance 与 Settlement
分离。具体故事事实、正文、研究、计划和 Accepted Canon 由 Project 负责。

嵌入式 model/agent runtime 继续作为 Studio 实现、本地 adapter、确定性测试实现或无
完整 Host 时的 fallback；它不再是 Quillframe 的产品身份，也不获得 Host 级权限。

## Surface 分层

默认 novelist-facing surface 复用既有 typed operation/schema，只提供小说契约工作：

- Project resolution 与安全 inspection；
- Canon/context query 及有界 Context preview/freeze；
- `author.run` 以及设计、计划、draft、revision lifecycle；
- candidate review、reject、revision 与 `candidate.visible.get`；
- state-delta proposal 与 continuity/consistency inspection。

session/event/checkpoint/handoff、lease/consume-once、provider/runtime diagnostics 和
transport receipt 等继续存在，但应归入明确的 internal/ops namespace 或 capability
manifest。它们是运行 plumbing，不是 novelist authority。

`candidate.accept` 与 `settlement.apply` 属于 privileged author-control surface，必须
有明确的人类/授权人 receipt、exact candidate fingerprint、exact before-state，并且
Acceptance 与 Settlement 是两个独立事务。模型、reviewer、Host、MCP discovery 或
Studio 页面都不能自行授予权限。兼容 operation 可以保留，但 privilege 边界必须进入
机器合同。

## 版本与真相

v0.9.1 使用单一 release identity。`VERSION`、`pyproject.toml`、`HARNESS_MANIFEST.yaml`、
CLI/doctor、Host Bridge metadata、MCP/skill capability manifest、Studio package、
site/docs manifest、Tauri metadata 和 release artifact 必须统一为 `0.9.1`。历史
CHANGELOG 条目保留；当前说明不能把 deferred 能力写成已发布。

文档统一表达 Host → agent loop、Quillframe → novel contract、Project → story
authority 的依赖方向。废止“Quillframe runs the agent”这类表述；仍存在的 embedded
runtime 必须明确是 optional/reference 实现。

## 兼容与非目标

在 authority 与 visibility 合同未改变时，保留既有 Host Bridge operation 与 embedded
runtime adapter。本文不删除 embedded runtime，不建立第二套不兼容 API，也不改变
candidate acceptance/settlement 语义。

以下列为 v0.9.1 之后 backlog，不得阻塞本次发布：全 Studio UI/UX 重构、hosted 多用户/
云部署、完整 author-control profile 产品化、完整 ConStory-Bench、全部 discovery/
arc/web-serial profile、reference novel、全书 empirical benchmark、插件生态、新模型
供应商大全、多人协作与计费，以及完整 typesetting suite。

## 验收不变量

- Host 可以运行通用 agent，但不能获得 Canon 或 Settlement 权限；
- novelist-facing discovery 不能枚举 pre-release raw text；
- 只有 `candidate.visible.get` 能返回 released Review Draft；
- 每次 independent review 都绑定 exact packet/candidate/result 证据；
- 两次明确的人类操作前，`accepted=false` 且 `settled=false`；
- version/capability manifest 与实现、release artifact 一致；
- 无 runtime manifest 的 Standard Project 与 local adapter 继续可用，mapped Project 在
  projection 输入缺失或过期时 fail closed。
