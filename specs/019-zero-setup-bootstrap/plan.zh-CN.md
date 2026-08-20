# 实施计划 · 零配置启动与 Claude Code 宿主守卫

## 选定架构

继续保持 Quillframe runtime authority 与 provider 解耦。Claude Code 只新增一个薄宿主 integration，消费既有 Project / Framework contracts，不建立第二套 agent runtime。

1. 新增 `quillframe` console entrypoint，统一委托 Project SDK、doctor 与 Claude hook dispatch。
2. Project SDK 的显式 init/pin 从 clean Framework source checkout 计算 exact identity：git commit + 现有 deterministic bundle fingerprint，并把 lock 与 attestation 一起写入。
3. 根 `CLAUDE.md` 使用 Claude Code 官方支持的 `@path` imports 加载简洁静态 bootstrap instructions。
4. Claude lifecycle hook 构建 compact bootstrap snapshot。Framework mode 注入 Framework-only 边界；Project mode 读取 manifest、lock、attestation，并在 `SessionStart` 对 materialized Framework 做 exact verification。
5. 已验证 snapshot 缓存在 Project `.quillframe/` runtime state 中。`PreToolUse` 复用它；consumer authority 无效时拒绝 consequential tools，而不是每次 tool call 都重算 bundle。
6. 新 Project scaffold 生成 `.claude/settings.json`，调用 `quillframe claude-hook`。该设置只是 host adapter，不是 Project authority。

## 备选方案

- 把所有规则塞进巨型 `CLAUDE.md`：拒绝。Instruction context 是指导，不是 authority guard，而且过长会降低遵循率。
- 让 Claude Code 变成 Quillframe Agent Runtime：拒绝，违反 provider-neutral architecture。
- 每次 tool call 重算完整 Framework bundle fingerprint：拒绝，I/O 不必要。
- validate 时自动 repin legacy Project：拒绝，migration 必须显式。

## 影响对象 / 路径

- `pyproject.toml`
- `quillframe/cli.py`（新增）
- `project_sdk.py`
- `harness/integrations/claude_hook.py`
- `.claude/settings.json`
- `CLAUDE.md`
- `tests/test_quillframe_bootstrap_host.py`（新增）
- `README.en.md`、`README.zh-CN.md`、`docs/project-sdk.en.md`、`docs/project-sdk.zh-CN.md`

## Dependency Graph

`CLI → Project SDK / persistence doctor / Claude hook`

`Project SDK pin → git identity + release/build_framework_bundle.py → lock + attestation`

`Claude SessionStart → Project/Framework discovery → exact authority verification → cached bootstrap snapshot → additionalContext`

`Claude PreToolUse → cached authority snapshot → allow / deny consequential tool`

## Migration Strategy

不自动迁移。旧 Project 如果 lock 不完整，继续允许 read/structural validate，但返回 `authority_ready=false`。使用 `quillframe pin <project>` 显式升级。

## Test / Eval Strategy

Deterministic tests 覆盖 exact pin creation、dirty-checkout rejection helper、attestation mismatch、hook JSON context、consequential tool fail-closed、root instruction imports 与 console entrypoint metadata。Normal CI 不调用模型。

## Phases / Checkpoints

1. 冻结 spec / plan / tasks。
2. CLI + exact Project pin / attestation。
3. Claude static bootstrap + lifecycle guard。
4. Tests。
5. Docs synchronization。
6. CI 与 human-review readiness。

## Rollback

Revert spec 019 implementation commits。旧 Python entrypoints 继续存在；不执行 Project Canon 或 schema migration。
