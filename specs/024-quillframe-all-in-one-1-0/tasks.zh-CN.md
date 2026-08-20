# Quillframe 1.0 任务清单

图例：`[ ]` 待做，`[~]` 进行中，`[x]` 已验证，`[!]` 等待外部证据。

## Gate 0

- [x] T000 确认无生产用户/数据并授权破坏性硬切换。
- [x] T001 编写双语产品规格。
- [x] T002 编写双语实施计划。
- [x] T003 登记 adopt/adapt/reject 研究决定与一手来源。
- [x] T004 验证 YAML 与双语文档配对完整性。

## Gate 1

- [x] T100 新增根 pnpm workspace 与唯一 lockfile。
- [x] T101 对齐 Site、Docs、Studio、Cloud 的 TypeScript/tooling。
- [x] T102 新增 1.0 canonical schema catalog 与 validator test。
- [x] T103 只保留 Host Bridge v11。
- [x] T104 新增 `author.run.resume`、`author.run.cancel`、`model.route.preview`。
- [x] T105 新增 cursor-based run subscription 契约。
- [x] T106 MCP 硬切换到 `2026-07-28`。
- [x] T107 新增旧 Bridge/MCP/Schema rejection test。
- [x] T108 删除根 host hook 正确性依赖。

## Gate 2

- [x] T200 先写 workflow transition 与 CH001 边界失败测试。
- [x] T201 实现 Core typed dataclass/Schema validation。
- [x] T202 实现 `NovelWorkflowEngine` 与 append-only event stream。
- [x] T203 实现 pause/resume/cancel safe point 与 replay。
- [x] T204 实现 candidate fingerprint invalidation。
- [x] T205 先写 model route/budget/fallback 失败测试。
- [x] T206 实现 `ModelTaskProfile` 与 route preview。
- [x] T207 实现显式 fallback receipt 与 independent-route integrity。
- [x] T208 通过 Bridge v11 接入 Core 操作。

## Gate 3

- [x] T300 先写 CLI launch 解析/receipt 失败测试。
- [x] T301 实现本地 project resolution/new-project wizard。
- [x] T302 实现 loopback launch server 与生命周期。
- [x] T303 增加 cloud opt-in 边界，禁止隐式上传。
- [x] T304 重组 Studio 主/辅助/Advanced 导航。
- [x] T305 构建 Homepage 六段信息架构。
- [x] T306 新增 Worker/Pyodide 确定性 CH001 demo。
- [x] T307 新增明确标注的 recorded semantic fixture 与 truth receipt。
- [x] T308 重建 Docs 任务导航。
- [x] T309 增加 responsive/offline/error/reduced-motion 状态。
- [x] T310 执行本地 browser/accessibility/visual E2E；production fail-closed 浏览器证据已通过。

## Gate 4

- [x] T400 创建 Cloudflare Worker BFF package 与 binding。
- [x] T401 实现 WorkOS authorize/callback/logout adapter。
- [x] T402 实现 opaque cookie、CSRF、origin 与 security header。
- [x] T403 实现 `WorkspaceCoordinator` Durable Object。
- [x] T404 实现 AES-GCM `SessionVault` lease 与 expiry。
- [x] T405 实现 encrypted R2 project bundle adapter。
- [x] T406 绑定 Python Core Container contract。
- [x] T407 实现 Hosted public-HTTPS endpoint validation。
- [x] T408 测试 logout/delete destruction 与 secret redaction。
- [!] T409 使用账户凭据验证真实 WorkOS/Cloudflare 部署。

## Gate 5

- [x] T500 删除当前 legacy route、package file、constant 与 adapter。
- [x] T501 按 1.0 重建当前 fixture。
- [x] T502 新增理解历史目录的 clean-break scanner。
- [x] T503 证明不存在 redirect、migration、dual path 与 compatibility flag。

## Gate 6

- [x] T600 执行完整 Python suite 与 compile check。
- [x] T601 执行 frozen pnpm install、test、type 与 build。
- [x] T602 执行 contract、legacy rejection 与 secret scan。
- [x] T603 执行 local launch 与 public demo E2E。
- [x] T604 执行 Hosted deterministic/security test。
- [x] T605 执行 accessibility 与 responsive visual QA；production fail-closed 浏览器证据已通过。
- [!] T606 运行真实 CH001 candidate→accept→settle→publish 链路；确定性状态转换已通过，但新鲜独立模型证据为 `PENDING_MODEL`。
- [!] T607 仅在 T409 与 T606 通过后提升版本；当前各表面一致保持 `1.0.0-dev.0`。
- [x] T608 生成并回读含未解决外部证据记录的 release acceptance report。
