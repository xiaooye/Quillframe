# Quillframe Studio · 0.9 产品架构

<p><kbd>SYSTEM-IMPROVE</kbd>&nbsp;&nbsp;<kbd>AUTHORING FIRST</kbd>&nbsp;&nbsp;<kbd>ONE CORE · MANY HOSTS</kbd></p>

Authority baseline：`xiaooye/Quillframe@c363631585fc0dc13cd948db7f60790cf9d4cfae`。

> **UI consumes Core state. UI never invents Core state.**

Studio 0.9 的 canonical stack 是：**SolidJS + TypeScript + Vite → typed BridgeClient → Python Core → SQLite-native**。Desktop 是 **Tauri 2 thin host**；Hosted Web 使用同一 operation semantics。Cloudflare/Vercel 可以托管 Web UI 或 adapter，但不是 Core 数据模型，临时文件系统也不是 canonical SQLite。

## 1. 产品 IA

Creator：

`DESK | MANUSCRIPT | PLAN | STORY | REVIEW | RESEARCH & CORPUS | LEARNING | PUBLISH`

Global：

`AI ASSISTANT DOCK | SEARCH | COMMAND PALETTE | SETTINGS`

Inspector progressive disclosure：

`SESSIONS | RUNS | CHECKPOINTS | CONTEXT | AGENTS/MODELS | SEMANTIC JOBS | CONTROL PLANE | CAPABILITIES | RECEIPTS | DIAGNOSTICS | ARCHITECTURE`

Writer Mode 默认隐藏运行时噪音；Inspector 才展示 provenance、run、receipt、context、diagnostics。视觉统一为 **BORDERLESS + KAWAII-FIRST + EDITORIAL + CONTENT-FIRST**，以 whitespace / typography / alignment / composition 建层级，而不是 card soup。

## 2. Host Bridge

```text
Solid caller
  ↓
BridgeClient.invoke(operation,args)
  ├─ LocalHttpTransport   → local Python host
  ├─ HostedHttpTransport  → authenticated durable Quillframe API
  └─ TauriTransport       → Tauri command
                              ↓
                         Python Core sidecar
                              ↓
                         Quillframe Core
                              ↓
                           SQLite
```

三种 transport 共享 `quillframe_studio_host_bridge_request_v1` / `result_v1`；transport 只负责传输，不能获得 story/Canon/Settlement authority。所有 request 都声明 `authority:false`。`authority_command` 只表示 **Core operation 自己要求显式授权和 exact precondition**。

Browser 不允许直接读 SQLite、任意 Python internals、Cloudflare bindings 或本地文件系统。`localStorage` 只可存 UI preference，例如 last-project id、layout、theme。

## 3. Web

目标路径：

`Studio → New Project → Endpoint → Token → Connected → Start Writing`

Hosted UI 使用 `HostedHttpTransport`。完整 Web 产品必须绑定一个 **durable Quillframe Core API host**：

```text
Hosted Solid UI → authenticated Quillframe API → Python Core → durable SQLite volume
```

静态 Pages/Workers UI 不得宣称自己完成了 Project persistence。当前 repo 已实现 transport contract，但没有冻结并验证一个 `studio.weidev.com` 的 durable Core host，因此 Web end-to-end 状态必须保持 `awaiting_external`，不能用 browser mock 补齐。

## 4. Tauri 2

Desktop 不依赖 Cloudflare：

```text
Solid/Tauri
  ↓ bridge_invoke
Tauri 2 thin Rust host
  ↓ token-bound loopback
long-lived packaged Python Core sidecar
  ↓
~/.quillframe/quillframe.sqlite
~/.quillframe/projects/<id>/project.sqlite
~/.quillframe/.../blobs
```

Rust 不复制 Quillframe business logic。Tauri command 强制 `surface=tauri_local`、`authority=false`；Python sidecar 只绑定 `127.0.0.1`，请求带随机 host token。Sidecar 必须长驻进程，因为 Model Runtime 的默认 credential value 是 session-memory-only。

Desktop “记住 Token”只有在 OS credential facility 经验证后才能启用。没有 keychain/backend 时保持 session-only，绝不退化到 SQLite/plaintext file。

## 5. Persistence

SQLite 是唯一 live persistence authority：WAL、`foreign_keys=ON`、busy timeout、explicit synchronous policy、ordered/checksummed migrations、verified backup/restore、checkpoint 与 doctor/integrity check 均由 Core 管理。

关键语义：

- autosave = `proposal` revision，不等于 Accepted；
- Accepted 不等于 Settled；
- persistence 不等于 Settlement；
- revision parent 由 optimistic CAS 保护；冲突必须暴露，不可 last-write-wins 静默覆盖。

当前 0.9 schema 对 `(document_id, content_fingerprint)` 去重，因此“将历史内容 exact restore 成一个新的 proposal revision”无法在不迁移 schema 的情况下真实表达。`document.revision.restore` 因此明确为 `deferred`；本 SYSTEM-IMPROVE 不偷偷执行 0.9 migration。

## 6. Portable `.qfproject`

`.qfproject` 是 Web↔Tauri 的 portable transfer format，不是第二套 live authority，也不是 `.qfbackup` 改名。

内容：

- deterministic manifest；
- SQLite consistent snapshot；
- referenced `blobs/**`；
- DB/blob fingerprints；
- project identity / schema compatibility metadata。

明确排除：global DB、provider/model service global metadata、credential value/ref、Token、host config、cache、backups、publication exports。

Import 必须验证 archive path、checksum、SQLite integrity 与 embedded project identity；默认遇到同 id Project fail closed，replace 需要显式授权。Phase 1 不做 live SQLite sync。

## 7. Model / AI

连接 UI 只要求 Endpoint + Token。Core Model Runtime 负责 endpoint normalization、model discovery/probe/capability。Token value 默认只在 process/session SecretStore；Bridge 在 fingerprint/evidence 前 redaction secret value。

AI Assistant 不直接写 Canon：

```text
instruction
 → author.run.start
 → production semantic execution
 → qualified Candidate
 → independent Review
 → explicit Accept
 → Accepted ✓ / Not Settled
 → Settlement preflight
 → explicit Settle
```

当前 `author.run.start` 能真实注册 persisted run，但 production semantic worker 的 product dispatch 尚未接入，因此状态保持 `awaiting_semantic`；UI 不得把模型裸输出或 fixture 冒充 Candidate。

## 8. Review / Settlement

Review 展示 incumbent→candidate diff、independent review evidence、gate、candidate fingerprint、Accepted/Settled 状态。Accept 需要 exact candidate fingerprint 与显式 user action，并只产生 `Accepted ✓ · Not Settled`。

Settlement 是独立事务：

1. `settlement.preflight` 读取 exact current Canon fingerprint；
2. 用户显式确认；
3. `settlement.apply` 使用 before-state CAS + idempotency key；
4. before mismatch 或 post-condition failure → `settlement_incomplete`；
5. UI 不自动重试副作用。

## 9. Plan / Story / Research / Learning

这些路由只显示 Core persisted projection，并使用文字 `locked | accepted | active_plan | review | proposal` / status 标签。没有 typed authority mutation contract 时编辑控件 disabled/deferred。

Research ≠ Canon；Corpus ≠ Canon；Research ≠ Character Knowledge。Learning 自动的是 feedback capture/intake，不是 promotion、Project Profile write、Canon write 或 Framework mutation。

## 10. Architecture Inspector

四个 lens：

- **SYSTEM**：Solid / Bridge / Core / SQLite / Model Runtime；
- **EXECUTION**：Session → Run → Context → Agent/Semantic Job → Candidate → Review；
- **AUTHORITY**：Proposal → Review → Accepted → Settlement → Canon；
- **PROJECT**：Project → Story/Plan/Manuscript/Research/Corpus/Learning/Publish。

Host selector 必须改变 transport topology；Tauri lens 中不能出现 Cloudflare 节点。

## 11. Product gate

Web 与 Tauri 的 22-step vertical slice 独立验收。源码存在、按钮可点、Browser mock 或 fixture 都不能算 PASS。任何 route 的必需 Core operation 缺失时只能标记 `unsupported | semantic_pending | awaiting_external | failed_gate`。

本次完整实施清单与逐项 acceptance matrix 见 `studio/specs/STUDIO_PRODUCTIZATION_SYSTEM_IMPROVE.md`。
