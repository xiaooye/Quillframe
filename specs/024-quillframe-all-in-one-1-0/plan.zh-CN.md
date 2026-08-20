# Quillframe 1.0 All-in-One 实施计划

本计划以分 Gate、测试驱动的方式实施硬切换规格。每个 Gate 只有在取得新鲜证据后才能前进；Gate 6 之前始终保持预发布状态。

## 工作规则

- 保持 host/framework/project 权威边界。
- CH001 是唯一可执行验收范围。
- 每个 runtime 行为先写失败的契约测试。
- Normal CI 必须确定性执行，禁止实时模型调用或付费外部请求。
- 面向人的文档必须中英文成对。
- 不增加兼容代码；legacy fixture 必须被拒绝，不能被翻译。
- 没有 WorkOS/Cloudflare 真实账户证据时，不得声称外部部署成功。

## Gate 0 — 权威与研究

交付：

- 双语 spec、plan、task ledger；
- 每项来源具有 adopt/adapt/reject 决定的 research register；
- 明确确认 1.0 前 runtime state 全部可丢弃；
- 单一产品拓扑与信任边界决定。

退出证据：YAML 可解析、文档成对存在、研究项不静默引入 dependency，并机器可读地声明 `compatibility_layer_permitted: false` 与 `migration_permitted: false`。

回滚：只删除 spec 024 文档；本 Gate 不修改 runtime。

## Gate 1 — 基础硬切换

1. 创建根 pnpm workspace，让 Site、Docs、Studio、Cloud 使用同一 package manager 与 TypeScript 基线。
2. 在唯一 canonical schema 目录重新声明 1.0 Schema。
3. 将 Host Bridge 当前契约替换为 v11，加入 run subscription/resume/cancel/route-preview。
4. 将 MCP initialize 常量替换为 `2026-07-28` 并要求完全匹配。
5. 删除根级 host hook 的产品正确性依赖，以 `quillframe launch` 作为唯一 bootstrap。
6. 增加 legacy rejection 与 duplicate-contract scan。

退出证据：Bridge 10/MCP 2025 输入必定失败；一个 workspace lockfile 可重复安装；当前产品只引用一套 bridge/protocol；无需根 Claude/Codex 配置即可启动和测试。

回滚：Gate 1 必须整体回滚，禁止用 adapter 保留半完成切换。

## Gate 2 — Core 工作流与 AI 路由

1. 实现 `NovelWorkflowEngine`、显式 transition table 与 append-only typed event。
2. 在 run 创建、generation packet 和全部 release/authority 操作加入 CH001 guard。
3. 实现场景意图、人物意图、转移约束、风险信号、修复计划与生成包类型。
4. 实现 safe-point pause/resume/cancel 和精确 cursor/idempotency。
5. 实现 `ModelTaskProfile`、确定性 route preview、硬预算与显式 fallback receipt。
6. 将 critic/independent review 证据绑定候选指纹；候选变更后失效。
7. 通过 Bridge v11 暴露操作，但不向 Bridge 授予 Canon 权威。

退出证据：transition/property test 覆盖合法与非法边；重放生成字节稳定 receipt；CH002 在 context/model 之前被拒绝；secret 无法进入持久化；independent reject 只进入 repair，不能自动换 reviewer。

回滚：删除 1.0 runtime state 与实现；不迁移或恢复旧状态。

## Gate 3 — 本地产品、公共站点与 Docs

1. 实现 `quillframe launch` 的解析、新建项目、loopback server 生命周期、receipt、浏览器行为与 cloud opt-in。
2. 以 `开始 · 写作 · 审阅 · 发布` 重组 Studio，并保留 `规划 · 故事 · 研究` 与显式 Advanced。
3. Homepage 使用主张、真实 quick demo、流程、证据、隐私、开始六段结构。
4. 在 Web Worker/Pyodide 中运行 CH001 确定性 Core，并把语义结果打包为明确标注的 recorded fixture。
5. Docs 按作者任务与信任边界重建导航。
6. 补齐 empty/loading/error/offline/long-content/responsive/reduced-motion 状态。

退出证据：local launch E2E 仅创建/打开一个 CH001 项目且只绑定 loopback；demo 指纹与 Core fixture 一致并披露 recorded semantic evidence；无需账户/key/network；移动/平板/桌面 accessibility 与 visual snapshot 通过。

回滚：产品壳与 launch server 一起回滚；Core 契约仍可独立测试。

## Gate 4 — Hosted Studio

1. 新增 Cloudflare Worker BFF package，严格处理 origin、CSRF、callback、cookie 与 security header。
2. 在可测试 HTTP interface 后实现 WorkOS AuthKit authorize/callback/logout adapter。
3. 实现 `WorkspaceCoordinator` Durable Object，串行化 personal workspace 与 project manifest 操作。
4. 实现 `SessionVault` Durable Object，使用 AES-GCM secret lease、30 分钟 idle、8 小时 absolute expiry 与显式销毁。
5. 定义加密 R2 project bundle 与 Python Core Container binding。
6. Hosted 自定义 endpoint 只允许 public HTTPS，并防 DNS/redirect SSRF 与 rebinding。
7. Upload 每次都需显式动作；禁止 sync/import。

退出证据：Worker 本地测试覆盖 callback 篡改、CSRF、cookie、expiry、logout、delete、SSRF、rebind、encryption 和 redaction；manifest 仅允许 personal workspace；token 只以 SessionVault ciphertext 持久化；真实部署在账户验收前保持 `awaiting_external`。

回滚：销毁测试 namespace/bucket 并删除 cloud binding；本地产品保持完整。

## Gate 5 — 硬切换审计

1. 删除 obsolete 当前路由、README、package-manager 文件、bridge/MCP 常量与 runtime adapter。
2. 用 1.0 Schema 重建 fixture。
3. 增加理解历史目录的 allowlist scan：历史 spec 可描述旧版本，当前 product/runtime/docs 不得暴露。
4. 确认不存在 redirect、dual read/write、import migrator 或 compatibility feature flag。

退出证据：legacy rejection suite 通过；current-surface scan 零未允许命中；repository hygiene 只识别一个 lockfile 与 canonical contract 位置。

回滚：不通过兼容层回滚，直接修复 1.0 source of truth。

## Gate 6 — 发布验收

重新执行：Python unit/integration/compile、Node test/type/build/lockfile install、Bridge/MCP/Schema 契约、本地 launch/browser E2E、demo offline/truth、cloud Worker security、accessibility/visual QA、repository hygiene/secret scan，以及真实 CH001 从 visible candidate 到 human accept、settlement、publication 的全链路。

发布决定：

- 所有本地可控 Gate 通过后，才把 `VERSION`、Python package、machine manifest、UI metadata 与 release docs 设为 `1.0.0`。
- Hosted live verification 不可用时保留明确预发布版本与 `awaiting_external`。
- mandatory semantic gate 未完成时只能是 `semantic_pending` 或 `failed_gate`，绝不能是 PASS。

## 依赖顺序

```text
Schema + exact protocol
→ workflow/event + model routing
→ Bridge v11 + launch server
→ Studio/Site/Docs/demo
→ Hosted BFF/DO/Container/R2
→ clean-break audit
→ CH001 release evidence
```

## 风险控制

- 契约漂移：canonical schema + 跨语言 fixture test。
- UI 越权：全部 mutation 必须经过 Bridge v11/Core。
- Secret 泄漏：Schema allowlist、redaction test、本地 memory-only lease、Hosted encrypted lease。
- Demo 误导：deterministic/recorded 标签进入 demo receipt。
- Cloud lock-in：BFF/storage adapter 面向内部 manifest，部署 binding 才使用 Cloudflare。
- 范围膨胀：CH001 与 personal workspace 是硬 guard，不是 roadmap 建议。
