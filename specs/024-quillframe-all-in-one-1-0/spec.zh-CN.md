# Quillframe 1.0 All-in-One 产品规格

状态：实施权威  
主任务模式：`SYSTEM-IMPROVE`  
发布目标：`1.0.0`  
验收单元：仅 `CH001`

## 1. 产品主张

Quillframe 1.0 是一套小说治理系统，只提供一种作者心智模型：

> 宿主运行 Agent，Quillframe 治理小说。

产品有三个交付面，但不是三个产品：

1. 公共 Homepage 与任务导向 Docs，内含无需账户的 CH001 快速演示；
2. 由一个标准命令启动的 local-first Studio，后端为 Python Core 与本地 SQLite；
3. 用户显式选择的 Hosted Studio，复用同一产品壳和契约，提供 SSO、隔离会话、加密项目包与用户自带模型凭据。

三者共享 Story Loom 设计 token、产品语言、工作流阶段、Schema 和作者动作；由于信任与执行边界不同，可以独立部署。

## 2. 硬切换决定

目前没有生产用户，也没有需要保留的生产数据。1.0 切换明确允许破坏旧开发状态。

- 禁止兼容层、legacy adapter、旧数据库迁移、双读写、路由重定向、CLI 别名、协议协商和旧版 feature flag。
- 现有开发 fixture 可以删除，并按 1.0 契约重建。
- 历史规格继续作为历史证据保存，但不定义当前 runtime。
- 当前产品收到 1.0 之前的 Schema、Host Bridge、MCP、路由或 launch receipt 时必须 fail closed。
- 0.9 中有用的能力可以被重新声明为原生 1.0 契约，但不得仅为旧调用方而保留。

## 3. 权威与真实性边界

- Project authority 拥有 Canon 和具体作品事实。
- 模型拥有小说语义判断。
- 确定性 runtime 拥有身份、权限、指纹、预算、阶段可见性、持久化、事务、幂等与类型校验。
- 模型输出只是证据或 proposal，不授予 Canon、settlement、publication、durable taste 或 Framework 写权。
- `Accept`、`Settlement`、`Delete`、`Publish` 永远需要作者明确操作。
- 默认使用本地模式；Cloud 不得自动上传、导入或同步项目。
- Secret 不得进入项目存储、模型上下文、run event、receipt、日志、分析、R2 bundle 或导出物。

## 4. 标准创作工作流

`NovelWorkflowEngine` 拥有以下强类型、可恢复流程：

```text
Intent
→ Story / Canon
→ Planning Horizon
→ Character Intent
→ Event Plan
→ Context Freeze
→ Raw Draft
→ Deterministic Checks
→ Reader / Continuity / Style Critics
→ Local Repair
→ Candidate Freeze
→ Pre-independent Qualification
→ Independent Review
→ Human Review
→ Accept
→ Settlement
→ Publish
```

Raw Draft 与人物私有状态永远不是用户可见发布物。1.0 验收期间，projection、context assembly、模型调用、draft、critic、review、accept、settlement 和 publish 只能处理 CH001。

Engine 在 safe point 暴露强类型 pause、resume、cancel。候选稿发生实质变化后，所有绑定旧指纹的 critic/review 证据立即失效。有效 semantic reject 只能进入 repair，禁止 reviewer shopping。

## 5. Core 契约

1.0 runtime 定义以下机器 Schema：

- `quillframe_scene_intent_v1`
- `quillframe_character_intent_v1`
- `quillframe_transition_constraints_v1`
- `quillframe_risk_signals_v1`
- `quillframe_repair_plan_v1`
- `quillframe_generation_packet_v1`
- `quillframe_author_run_event_v1`
- `quillframe_model_task_profile_v1`
- `quillframe_model_route_receipt_v1`
- `quillframe_cloud_project_manifest_v1`
- `quillframe_secret_lease_receipt_v1`
- `quillframe_launch_receipt_v1`

每个状态变更操作都绑定准确的 project、run、artifact、before-state、idempotency key 与 authority evidence。Receipt 是安全投影；除 Core 拥有的 visible release 边界外，不得携带正文。

## 6. 作者模式

`guided` 为默认模式，只呈现下一个有意义的作者决定。`expert` 额外展示 plan、story、research、context、模型路由、证据和 runtime 诊断。模式只改变信息密度，不改变权威、质量 gate 或持久真相。

主导航为 `开始 · 写作 · 审阅 · 发布`；辅助工作为 `规划 · 故事 · 研究`。技术界面集中在明确的 Advanced 区域，不能成为默认首页。

## 7. 模型路由

每个语义任务解析一个 `ModelTaskProfile`，声明角色、必要能力、上下文预算、输出 Schema、独立性、隐私级别、延迟偏好与质量底线。

- 调用前必须执行质量底线与硬费用/上下文预算。
- `model.route.preview` 在不调用模型的前提下解释路由。
- fallback 必须生成强类型 receipt，说明失败路由和受限替代路由；禁止静默 fallback。
- mandatory independent review 必须来自不同的合格 invocation/session，并绑定冻结候选指纹。
- 只允许缓存稳定且不含 secret 的 prompt prefix。
- 禁止跨项目缓存语义输出。
- Provider credential 只作为内存 lease；持久状态最多保存非敏感 reference 与 capability evidence。

## 8. 标准启动流程

唯一用户启动入口：

```text
quillframe launch [PROJECT]
  --new
  --profile local|cloud
  --id PROJECT_ID
  --title TITLE
  --language LANGUAGE
  --port PORT
  --no-browser
  --json
```

无参数时依次解析当前项目、最近打开项目，最后在交互式终端进入新建向导；非交互环境中存在歧义时返回强类型错误。默认 `local`。`cloud` 只开始显式登录/上传流程，运行命令本身不得触发上传。

成功输出 `quillframe_launch_receipt_v1`，包含 loopback URL、profile、项目身份、进程身份、存储边界和是否打开浏览器，不包含 token 或模型 secret。

## 9. Host Bridge v11

Host Bridge v11 是唯一支持版本。除标准 author run/candidate/review/accept/settlement 操作外，还提供：

- `author.run.resume`
- `author.run.cancel`
- `model.route.preview`
- `BridgeClient.subscribeAuthorRun(run_id, cursor)`

订阅使用 cursor，可断点恢复，传输 `quillframe_author_run_event_v1`，但不授予写权。声明其他 bridge version 的请求必须拒绝。

## 10. MCP

唯一协议版本为 `2026-07-28`：本地用 stdio，远端用 Streamable HTTP。Initialize 必须完全匹配，不做协商或 fallback。MCP 只暴露受限 novelist 操作；高权威动作必须位于显式本地/Hosted 产品操作之后。

## 11. 公共演示真实性

Homepage demo 在 Web Worker 中运行 Pyodide 和固定、可分发的 CH001 fixture。它调用真实确定性 Core 契约路径完成 validation、context freeze、checks、candidate fingerprint 和 receipt projection。模型负责的语义结果使用版本化录制 fixture，并明确标为“录制结果”，不能冒充实时 AI。

演示必须区分确定性执行与录制语义结果，不得暗示已经进行 Canon settlement、实时 independent review、cloud persistence 或 provider invocation。演示无需账户和 API key。

## 12. 本地 Studio

本地 Studio 只绑定 loopback，运行 Python Core，并写入项目本地 SQLite。浏览器只是薄产品壳，不得重新实现 Canon 或 workflow authority。本地自定义模型 endpoint 可使用 loopback，或在既有 endpoint 安全策略下由用户明确批准的私网地址。

## 13. Hosted Studio 与 SSO

Hosted Studio 使用：

- WorkOS AuthKit 与 hosted custom auth domain；
- Email OTP、GitHub、Google 与 passkey；
- Cloudflare Worker BFF；
- host-only opaque `HttpOnly; Secure; SameSite=Lax` session cookie；
- 1.0 每个身份只有一个 personal workspace；
- `WorkspaceCoordinator` 与 `SessionVault` Durable Objects；
- Python Core Cloudflare Container；
- R2 中的加密项目 bundle。

SessionVault 使用 AES-GCM 加密 secret lease。Session 空闲 30 分钟或绝对 8 小时后失效。Logout、显式结束 session 和删除项目必须销毁服务端 session/lease。Hosted 自定义模型 endpoint 只能是 public HTTPS，并通过 DNS、redirect、SSRF 与 rebinding 防护；禁止 localhost 和私网。

### Native backup proof 尝试语义

对于 framing 正确、且通过身份绑定的 core proof 的 native backup 请求，单次 nonce 会在 C3A ZIP verifier 运行之前被消费。因此，即使 bundle malformed 或严格 C3A 校验失败，这次尝试也已经消耗。重试必须携带重新签名的 proof 和新发放的 nonce；复用原 proof 或 nonce 必须拒绝。这是原生 1.0 安全契约，不是兼容层或 retry shim。

Team、billing、collaboration、后台同步和旧项目导入均不在 1.0 范围内。

## 14. UI/UX 质量

保留 Story Loom：约 70% 技术编辑精度 + 30% 克制的动漫文学温度。UI 在单一 pnpm workspace 下使用锁定版本的 WeiUI、SolidJS 与 Vite。

- 最小交互目标 44 CSS px；
- 键盘 focus 3 px，offset 2 px；
- 满足 WCAG 2.2 AA 对比度和语义；
- 禁止 idle animation、意外轮询和隐藏网络请求；
- 支持 reduced motion；
- 英文与简体中文结构对等；
- 移动、平板、桌面、空、加载、错误、离线和长内容都是验收状态。

Homepage 区段为 `主张 · 快速演示 · 流程 · 证据 · 隐私 · 开始`。Docs 以任务为中心。Studio 默认展示下一个作者动作，而不是 Framework dashboard。

## 15. 验收 Gate

1. Gate 0 — 双语规格、research register、任务计划和明确的旧数据可丢弃决定。
2. Gate 1 — pnpm workspace、Bridge v11、MCP 2026-07-28 硬切换，无重复 current contract。
3. Gate 2 — workflow engine、模型路由、typed event、pause/resume/cancel 与 CH001 限制。
4. Gate 3 — launch、本地 Studio、Homepage、Docs 和真实标注的 quick demo。
5. Gate 4 — Hosted SSO/BFF/session/BYOK/persistence 实现及本地确定性测试。
6. Gate 5 — 扫描并删除当前 runtime/product 的 legacy/compatibility surface。
7. Gate 6 — 完整 deterministic、E2E、accessibility、security、build 与 CH001 验收证据。

只有全部 gate 通过后才能声明 `1.0.0`。需要外部账户的部署检查可以保持 `awaiting_external`；处于该状态时不得称为已发布 1.0 产品。

## 16. 必需验证

- 依据 lockfile 全新安装与构建；
- 精确拒绝旧 Bridge、MCP、Schema、CLI、URL 和数据库 fixture；
- workflow 与 receipt 的确定性重放；
- 本地 launch 与浏览器 E2E；
- 公共 demo 的真实性与离线行为；
- 模型路由、预算、fallback、secret、timeout 与 independence 故障测试；
- SSO callback、cookie、CSRF、session expiry、logout、delete、SSRF 与 BYOK 隔离测试；
- 加密 cloud persistence 与 restore 测试；
- 键盘、screen-reader 语义、对比度、响应式、reduced-motion 与 Core Web Vitals 预算；
- 一次真实 CH001 流程：candidate visible release → 明确 human accept → settlement → publication。

## 17. 非目标

- CH002 或之后章节的执行；
- Team、role、billing、marketplace、collaboration 或社交功能；
- 自主 Canon mutation 或自主 publication；
- 模仿具体作者或镜像版权 Corpus；
- 把通用 multi-agent orchestration 作为产品功能；
- 迁移任何 1.0 之前的 runtime 或用户数据。
