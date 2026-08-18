# 实施计划 — Quillframe Model Runtime

## Phase 1 · Kernel

1. 新建 `model_runtime/`：endpoint/security、secret reference、protocol codecs、mock/urllib transport、model discovery、capability evidence、model selection/invoke。
2. 新建 `agent_runtime/`：AgentJob/Result、ToolRuntime、RepositoryToolset、bounded AgentRunner。
3. deterministic tests 覆盖三种 protocol 与完整 tool loop。

## Phase 2 · Persistence / capability routing

1. 新增 global SQLite migration `002_model_runtime.sql`。
2. QuillframeStore 增加 model service/snapshot/evidence query/write API。
3. Runtime Capability 使用 `model_api/model_runtime`，删除 active provider-name capability semantics。
4. runtime registry 增加 generic direct-model route；OpenAI-specific route 降为 compatibility path。

## Phase 3 · Semantic integration

1. 新增 Model Runtime semantic executor wrapper。
2. 保持 semantic job fingerprint/rubric/output contract/independence 不变。
3. 现有 OpenAI Responses adapter 改为 compatibility wrapper 或后续删除重复 HTTP 实现。

## Phase 4 · Core/Host surface

1. CoreOperations 暴露 model service connect/list/get/refresh/delete/replace-secret、models list/capability projection。
2. Host Bridge 由 UI session 接入相同 operation contracts；不直接暴露 secret value。
3. 默认 model selection 自动；exact-model preference 只是 preference，不改变 eligibility。

## Phase 5 · Coding-agent vertical slice

1. `SYSTEM-IMPROVE` read-only planning：repo.read/repo.search。
2. 加 write path：exact before-state + authority + receipt。
3. subprocess 仅在显式 allowlist/grant 后加入。

## Verification

Normal CI：unittest/mock transport，无真实网络/模型。Live compatibility 仅在显式 opt-in environment 下运行。最终进行独立 architecture/semantic review，且不在本任务自动 merge。
