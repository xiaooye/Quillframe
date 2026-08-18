# 016 · Production Runtime Integration & Model Service Foundation

## Authority
- Primary task mode：`SYSTEM-IMPROVE`。
- 本任务冻结 Framework authority：`5fd991a5621f2c68e1030aa6e0b35014ca4011c7`。
- Branch：`agent/production-runtime-integration`。
- 不允许 consumer Project repin/migration、Canon 写入、小说 DRAFT/REVISE 交付或 Studio 视觉改动。
- 当前 Studio consumer 为 PR #130；本 workstream 只拥有 Core runtime semantics 与 typed Host Bridge contracts。

## 问题
Quillframe 已有 `author.run.start`、Semantic Context Runtime、Agent Runtime 与 Endpoint+Token Model Runtime，但 production execution 尚未成为一个 fingerprint-bound runtime transaction。否则 worker 仍可能依赖后续 Project read，Studio 也缺少完整的 production execution boundary；同时 Model Runtime 缺少稳定的 product-facing Model Service projection。Authoring UI 还明确缺少六个不能由 browser state 代替的 Core primitive：Project list、Document list、Candidate Review evidence、Reject、Request Revision、Settlement preflight。

## 目标架构
`Project authoritative state → tracked Context source projection → semantic profiles → deterministic eligibility → Context Decision Agent → stage Greenlights → Context Freeze → immutable production Context bundle → mandatory production mechanisms → pre-independent qualification → genuine external independent review → user-visible Review Draft`。

每个 mechanism 只能拿自己的 frozen stage context 与受限 upstream artifacts，不拿 SQLite handle，也不能自行扩大 candidate universe。编排层只能为了验证 freeze 是否仍 current 而重新读取 tracked Project state。Freeze 后 mutation 或出现新 source 必须返回 `stale_conflict`；只能通过 explicit Context refresh/supersession 或 fresh run 继续。

## Production mechanisms
沿用现有 mandatory graph：Story/Canon Preflight、Scene Simulation、Character Simulation、Reader Pressure、Event-first Raw Draft、Surface Realization、registered Reader Engagement、Continuity、registered manager self-audit / pre-independent qualification、external Independent Semantic Gate、User-visible Gate。

Raw Draft/private simulation 不进入 user-visible output。新的 AgentJob/session 本身不构成 independence。Manager Model Service 不得自行执行 `quality.production_review` 冒充 release gate。Independent review 必须绑定 exact peer packet/result 与 Project-owned validation receipt。Semantic reject 是有效判断，不允许 reviewer-shopping。

## Context bundle
Context Freeze 绑定 candidate universe、stage selection、source/source-state/profile fingerprint。Production 另外持久化 immutable selected-source payload bundle，使 stage 不需要后续 DB fetch。Bundle 绑定 Freeze fingerprint、selected `model_view` payload、source-universe fingerprint、stage binding 与 explicit supersession metadata；持久化前执行 secret check。

## Model Service
不造第二套 provider subsystem，扩展现有 Generic Model Runtime：普通用户输入仍只有 `Endpoint + Access Token`；Quillframe 自行发现 protocol/model/capability evidence；在客观 discover/probe 支持时兼容 OpenAI Chat、OpenAI Responses、Anthropic Messages；unknown capability 保持 unknown；model capability 永不产生 semantic/Canon/Settlement authority；提供稳定的 connect/list/get/discover/test/capabilities 与 token lifecycle projection。

## Credential boundary
Access Token 值不得进入 Project SQLite、Canon、Context、Context Freeze/bundle、AgentJob、receipts、exports、semantic-worker input 或 public bridge output。Durable state 只能保存 `credential_ref` 与公开 presence metadata。Public bridge result 除了按 secret-bearing key redaction，还必须把对应 secret value 从 nested data/error string 中 scrub。Desktop 应注入 Tauri/OS-keychain SecretStore；Hosted Web 应注入 server-side secure secret/session storage。Generic Core 不依赖 Cloudflare。

## Host Bridge v8 authoring primitives
Core-owned Host Bridge 只暴露真实 typed operation。除 production/model/document primitives 外，v8 必须补齐：
- `project.list`：canonical read-only global Project registry projection；
- `document.list`：canonical project document list，含 latest revision identity/fingerprint；
- `candidate.review.get`：exact Candidate-bound Review projection，包含安全的 Reader、Character、Continuity、Independent、production-readiness evidence，以及 incumbent revision/diff；不得暴露 private reasoning；
- `candidate.reject`：explicit、exact-fingerprint、idempotent Reject；不写 Canon/Settlement；
- `candidate.revision.request`：durable Request Revision receipt/event + effective state；不得静默启动 REVISE，旧 Candidate 也不得继续 Accept；
- `settlement.preflight`：只读验证 Acceptance binding、fingerprint 与 authoritative current Canon before-state；只有单独授权的 `settlement.apply` 才能真正 mutation。

尚无完整 Core transaction 的 project delete / portable import-export / free-floating review 必须保持 unsupported 或 `awaiting_external`，不得伪造成功。

## SQLite hygiene
Owning SQLite layer 必须真正 close context-managed connection，同时保持 WAL、foreign_keys、busy timeout 与 durability policy 不变。

## Acceptance
Deterministic acceptance 必须证明：production 只消费 frozen Context；stage 无 hidden DB fetch；Research≠Character Knowledge；非法 Context ID 被拒绝；stale source universe 被阻断；explicit refresh 建立 supersession；mandatory graph 不可禁用；independent review boundary 真实成立；Endpoint+Token discovery/probe secret-safe；provider failure truthful；bridge public output scrub secret；SQLite hygiene；六个 v8 authoring primitives 与 lifecycle guard；既有 authority contracts；Studio typecheck/build；docs/site checks；以及 deterministic exact Framework bundle verification。

只有当前环境确实存在可用 credential/provider capability 时才做 live-provider acceptance；否则 semantic readiness 保持 `PENDING_MODEL / awaiting_external`，deterministic fixture 不得冒充 live acceptance。
