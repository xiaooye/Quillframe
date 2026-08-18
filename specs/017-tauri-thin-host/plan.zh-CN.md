# Plan
1. 在 Core v8 与 Studio consumer merge 后冻结 fresh main。
2. 只把旧 PR #129 当作 host mechanics evidence，不 merge 它的旧 Core/v5 semantics。
3. 增加 one-shot Python Core sidecar protocol：`credential-refs`、`invoke`、self-test。
4. 增加 Tauri 2 Rust host，public surface 只暴露一个 `bridge_invoke` command。
5. 增加 OS-native keyring storage，采用 preallocated credential-reference ordering 与 uncertain-ack recovery。
6. 将 Python sidecar 按 target triple 打成 Tauri external binary。
7. 增加 Linux Desktop CI：Studio regression、source sidecar self-test、packaged sidecar self-test、Rust test/check、真实 Secret Service round-trip、Tauri build。
8. dependency resolution 后提交 Cargo.lock，随后强制 locked Cargo build。
9. 运行完整 repository CI 与 Desktop host CI 直到 clean。
10. 更新 Desktop surface docs/execution receipt，所有 gate 绿色后 merge host PR，再关闭旧 PR #129 并标记 superseded。
11. 没有真实用户/provider credential 时，live-model production acceptance 独立保持 `PENDING_MODEL / awaiting_external`。
