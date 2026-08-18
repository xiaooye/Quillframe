# Plan
1. Freeze fresh main after Core v8 and Studio consumer merges.
2. Reuse only host-mechanics evidence from obsolete PR #129; do not merge its old Core/v5 semantics.
3. Add one-shot Python Core sidecar protocol for `credential-refs`, `invoke`, and self-test.
4. Add Tauri 2 Rust host with exactly one public `bridge_invoke` command.
5. Add OS-native keyring storage with preallocated credential-reference ordering and uncertain-ack recovery.
6. Package the Python sidecar as the Tauri external binary with a target-triple suffix.
7. Add Linux Desktop CI: Studio regression, source sidecar self-test, packaged sidecar self-test, Rust test/check, real Secret Service round-trip, Tauri build.
8. Add/commit Cargo.lock after dependency resolution, then enforce locked Cargo builds.
9. Run full repository CI and Desktop host CI until clean.
10. Update Desktop surface docs/execution receipt, merge the host PR after gates are green, then close obsolete PR #129 as superseded.
11. Keep real live-model production acceptance separately `PENDING_MODEL / awaiting_external` when no user/provider credential is available.
