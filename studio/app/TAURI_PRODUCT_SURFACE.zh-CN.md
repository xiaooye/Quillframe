# Quillframe Studio · Tauri 2 surface

状态：已在本地按 Host Bridge **v11** 实现；在真实 OS/runtime 验收前不能宣称 desktop release。

## Architecture

```text
SolidJS Studio
→ TauriTransport
→ invoke("bridge_invoke", { request })
→ thin Rust host
   ├─ packaged quillframe-core Python sidecar
   └─ OS keyring
→ Host Bridge v11
→ Python Core + project-local SQLite
```

Rust 只负责 process lifecycle、IPC framing、window integration、secret-store call 与输出脱敏，不复制 Python workflow、Context、Candidate、Settlement、model routing 或 persistence 语义。

## Secret boundary

Access token 只进入 Tauri IPC request。Rust 在调用 Core 前分配 `keyring:qf:*` reference 并把 secret 写入 OS keyring。Sidecar 只接收 request envelope 与已提交 reference，只返回 Bridge result 与 secret action，绝不把 plaintext 写入 SQLite。失败或未消费的分配会被删除；stdout、stderr 与返回错误都会按已知 secret value 脱敏。

## Acceptance gate

真实 desktop artifact 在满足以下证据前保持 unreleased：

- bundled sidecar 的 Host Bridge v11 round-trip；
- restart 后仍可 create/open/write/review/publish；
- OS keyring set/get/delete 与 restart 后 reference recovery；
- SQLite、browser storage、process log、bridge result、export 均无 secret；
- 不依赖 Cloudflare 的 offline local operation；
- signed installer 与平台权限行为。

静态 TypeScript、Rust unit test 或 browser mock 是必要证据，但不能替代 packaged runtime check。
