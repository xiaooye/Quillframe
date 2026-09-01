# Contributing to Quillframe

Quillframe's production runtime is Rust. SolidJS, TypeScript, Vite, and pnpm are used only for Studio, the public site, documentation rendering, and Cloudflare surfaces.

## Requirements

- Rust 1.88 with Cargo
- Node.js 24 and pnpm 10.33.0 for UI work
- Windows or Linux

## Local checks

```text
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features --locked -- -D warnings
cargo test --workspace --all-targets --locked
pnpm run typecheck
pnpm run test
pnpm run build
```

The Tauri crate is intentionally outside the root workspace and must also be checked with its own manifest. Normal checks must not call paid or live model APIs.

Preserve unrelated working-tree changes, keep Project state out of the framework repository, and add deterministic tests for identity, schema, permissions, idempotency, persistence, and publication invariants. Literary judgments belong to model or human review, not heuristic counters.
