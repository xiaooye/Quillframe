# Windows 超长篇生产链验证记录

2026-09-01 · `SYSTEM-IMPROVE`

## Windows 实机已验证

- `cargo fmt --all -- --check`、workspace `check`、`-D warnings` Clippy 与 `cargo test --workspace --all-targets --locked` 通过。Workspace 共运行 48 项确定性测试：Core 39、host 1、原生文件系统／发布 7、secrets 1。
- 三章 Core 验收真实经过模型驱动的上下文 query／选择、Corpus 与偏好 greenlight、逐场景正文、语义审查／修订、接受、settlement、typed 账本投影、发布、重启连续性与偏好学习。
- 同一验收会篡改角色权威投影，证明 strict open 拒绝；再以 expected revision 3 调用显式本地 Rust Bridge 快照恢复，并证明 strict reopen 成功。恢复回执明确 `semantic_inference=false`。
- Tauri manifest 格式、Clippy 和直连 Core 边界测试通过。
- 根目录 `pnpm` quality、typecheck、test、build 全部通过，覆盖产品站、SolidJS Studio 与 Cloud 合同镜像；Studio 测试证明业务状态只能经过 typed Bridge。
- 全仓扫描不存在 `.py`、`.pyi`、`pyproject.toml` 或 `__pycache__`；CI 另有解释器残留拒绝门。

## 跨平台证据

主 CI 与 Tauri CI 都在 `windows-latest`、`ubuntu-latest` 运行 Core／Tauri，并显式安装 Linux 桌面依赖。本记录不伪造本机 Linux 结果；Ubuntu jobs 才是 Linux 执行证据。

## 证据边界

没有运行合成 500 万字耐久测试。这些绿灯证明确定性生产机制与恢复成立，不证明 500 万字小说的文学质量。真实连续章节文学 canary 与作者判断仍保持 pending。
