# 016 · Production Runtime Integration & Model Service Foundation

## Authority
- Primary task mode：`SYSTEM-IMPROVE`。
- 本任务冻结 Framework authority：`5fd991a5621f2c68e1030aa6e0b35014ca4011c7`。
- Branch：`agent/production-runtime-integration`。
- 不允许 consumer Project repin/migration、Canon 写入、小说 DRAFT/REVISE 交付或 Studio 视觉改动。
- 并行 Studio UI 为 PR #129；本 workstream 只拥有 Core runtime semantics 与 Host Bridge Core contracts。

## 问题
Quillframe 已能注册 `author.run.start`，也已有 Semantic Context Runtime、Agent Runtime 与 Endpoint+Token Model Runtime，但 production execution 尚未成为一个 fingerprint-bound runtime transaction。Studio 也缺少真实的 `author.run.execute` Core primitive。Model Service 的底层 discovery 已存在，但缺少稳定的 Core/Bridge connect/discover/test/capabilities projection。

## 目标架构
`Project authoritative state → tracked Context source projection → semantic profiles → deterministic eligibility → Context Decision Agent → stage Greenlights → Context Freeze → immutable production Context bundle → production mechanisms → gated Candidate → independent fingerprint-bound review → Review Draft`。

每个 mechanism 只能拿自己的 frozen stage context 与受限 upstream artifacts，不拿 SQLite handle，也不能自行扩大 candidate universe。编排层可以在每个 mechanism 前执行明确记录的 Project state preflight，用于验证 freeze 是否仍 current；freeze 后发生 mutation 或出现新 source 必须 `stale_conflict`，只能显式 refresh/extension 或 fresh run 后继续。

## Production mechanisms
沿用现有 mandatory graph，不重新设计：Story/Canon Preflight、Scene Simulation、Character Simulation、Reader Pressure、Event-first Raw Draft、Surface Realization、Reader Engagement、Continuity、Independent Semantic Gate、User-visible Gate。

Raw Draft 与 private simulation 不写入 public receipt。Independent review 必须是真正独立的新 semantic invocation，并绑定 exact fingerprint；有效 reject 不允许 reviewer-shopping。

## Context bundle
现有 Context Freeze 已绑定 candidate universe、stage selection、source/source-state/profile fingerprint。本任务额外引入 immutable payload bundle，因为只有 profile metadata 不足以让 stage 在无 DB fetch 的情况下执行。Bundle 绑定 Freeze fingerprint、实际 selected source `model_view`、完整 source-universe fingerprint、stage bindings 与 explicit supersession metadata，并在持久化前执行 secret check。

## Model Service
不造第二套 provider subsystem，扩展现有 Generic Model Runtime：普通用户输入仍只有 `Endpoint + Access Token`；Quillframe 自己发现 protocol/model/capability evidence；沿用当前 OpenAI Chat、OpenAI Responses、Anthropic Messages 的可客观发现/验证兼容；unknown capability 保持 unknown；model capability 永不产生 semantic/Canon/Settlement authority；增加稳定 connect/list/get/discover/test/capabilities projection。

## Credential boundary
Access Token 值不得进入 Project SQLite、Canon、Context、Context Freeze/bundle、AgentJob、receipts、logs、exports 或 semantic worker input。Durable state 只能保存 `credential_ref` 和公开 presence metadata。Desktop 由 Tauri/OS keychain SecretStore 提供持久 secret；Web 由 server-side secure secret/session facility 提供。Generic Core 不依赖 Cloudflare。MemorySecretStore 只作为 process-local 非持久 fallback。

## Host Bridge
Core-owned Host Bridge contract 只增加真实能力：document open/revision list、run status/execute/context refresh、Model Service lifecycle/test/discovery/capabilities、现有 Context Inspector。尚无完整 Core transaction 的 project delete / portable import-export / ad-hoc review 必须明确 unsupported，不得伪造。

## SQLite hygiene
修复已知 ResourceWarning 根因：context-managed SQLite connection 必须真正 close，同时保持 WAL、foreign_keys、busy timeout 与 durability policy 不变。

## Acceptance
必须证明：production stage 只消费 frozen payload；stage 无 hidden DB fetch；Research≠Character Knowledge；非法 Context ID 被拒绝而非猜测；freeze 后 mutation/new source 阻断；explicit refresh 产生新 bundle fingerprint；mandatory graph 不可禁用；Context/model capability 不产生 authority；independent review 是独立 invocation 且无 reviewer-shopping；Endpoint+Token discovery/probe secret-safe；bad endpoint/token/network/unsupported protocol truthful failure；Host Bridge 不把 secret 写入 fingerprint/durable state；SQLite connection cleanly closes；既有 Agent/Context/Model/Settlement/authority tests 保持绿色；Studio TypeScript 对 public bridge contract 可构建。

只有当前环境确实存在可用 credential/provider 时才做 live-provider acceptance；否则最终状态必须是 `PENDING_MODEL / awaiting_external`，不得把 deterministic mock 当成 PASS。
