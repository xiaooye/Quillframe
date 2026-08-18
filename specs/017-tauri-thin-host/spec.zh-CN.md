# 017 · Tauri 2 Thin Host

## Authority
- Primary task mode：`SYSTEM-IMPROVE`。
- Frozen Framework/Product authority：`main@252fcd6066a73df06953c974f2324e1c264492a6`。
- Branch：`agent/tauri-thin-host-v8`。
- Host Bridge authority：v8。
- 不做 consumer Project repin、不改小说 Canon、不产出正文、不重做 Studio 视觉。

## 目标
为已经 merge 的 SolidJS Studio consumer 补齐真正的 Desktop host，同时不制造第二套 Core implementation。

Canonical dependency 保持：
`SolidJS → Tauri 2 thin host → packaged Python Core sidecar → Host Bridge v8 → Python Core → SQLite`。

## Thin-host ownership
Rust/Tauri 只拥有 window/process lifecycle、IPC framing、sidecar launch、OS integration 与 OS-native secret storage。不得拥有 Context selection、semantic judgment、Model Service capability inference、Project/Document domain query、Candidate lifecycle、Acceptance、Settlement 或 Canon rule。

Frontend 只通过一个 `bridge_invoke` command 收到既有 Host Bridge result envelope。

## Sidecar model
使用 Tauri external binary 打包 one-shot Python Core sidecar。每次 invocation 从 stdin 收一份 JSON payload，从 stdout 返回一份 sanitized JSON result。不需要 localhost server、临时 bearer-token file、hidden polling loop 或 browser database。

## Credential durability
Desktop Model Service credential 必须跨 app restart 保存在 platform-native credential store，绝不写 SQLite/browser state。Durable Core SQLite 只保存 `credential_ref`。

对于会写入 credential 的 request，Tauri 必须先把 secret 以新的 `keyring:qf:<uuid>` reference 写入 OS credential store，再允许 Core 写这个 reference。注入 Python 的 SecretStore 必须返回同一个 preallocated reference。Core 在 commit 前失败则 Tauri 删除它；若 transport acknowledgment 不确定，Tauri 必须重新读取 durable Core credential refs 后再 cleanup，避免误删已经被 Core commit 的 reference。

已有 credential reference 由 sidecar 通过 Model Service repository 在内部枚举，Tauri 从 OS credential store resolve，并只注入当前这一次 sidecar process。Secret bytes 不得进入 public bridge result、receipt、Context 或 log。

## Acceptance
- Python sidecar source self-test 对 Host Bridge v8 PASS。
- PyInstaller one-file target-suffixed sidecar build PASS，并运行同一 self-test。
- Rust unit tests 与 compile 在 current Tauri 2 上 PASS。
- Linux runner 有 D-Bus/keyring support 时，真实 Secret Service set/get/delete round-trip PASS。
- 带 packaged sidecar 的 `cargo tauri build --debug --no-bundle` PASS。
- Studio Web consumer regression 继续全绿。
- Plaintext credential 不进入 public output、SQLite、browser persistence、Vite asset 或 test log。
- Core/Studio semantics 保持 Cloudflare-independent。
- 新 host merge 后才关闭旧 PR #129，并明确其被 supersede。
