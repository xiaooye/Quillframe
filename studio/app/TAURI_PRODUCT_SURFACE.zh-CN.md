# Quillframe Studio · Tauri 2 surface

状态：已在本地按 Host Bridge **v11** 实现；在真实 OS/runtime 验收前不能宣称 desktop release。

## Architecture

```text
SolidJS Studio
→ TauriTransport
→ invoke("bridge_invoke", { request })
→ thin Rust host
   ├─ 直接链接 quillframe-core Rust crate
   └─ OS keyring
→ Host Bridge v11
→ Rust Core + project-local SQLite
```

Rust Core 直接拥有 workflow、Context、Candidate、Settlement、model routing、publication recovery 与 persistence 语义；Tauri 只保留展示与 IPC host 职责，不再存在 sidecar runtime。

## Secret boundary

Access token 只进入 Tauri IPC request。Rust 在调用 Core 前分配 `keyring:qf:*` reference 并把 secret 写入 OS keyring；Core 只接收已提交 reference，绝不把 plaintext 写入 SQLite。失败或未消费的分配会被删除，返回错误会按已知 secret value 脱敏。

## Acceptance gate

真实 desktop artifact 在满足以下证据前保持 unreleased：

- 直接链接 Rust Core 的 Host Bridge v11 round-trip；
- restart 后仍可 create/open/write/review/publish；
- OS keyring set/get/delete 与 restart 后 reference recovery；
- SQLite、browser storage、process log、bridge result、export 均无 secret；
- 不依赖 Cloudflare 的 offline local operation；
- signed installer 与平台权限行为。

静态 TypeScript、Rust unit test 或 browser mock 是必要证据，但不能替代 packaged runtime check。
