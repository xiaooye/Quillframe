# Windows 超长篇生产链验证记录

2026-09-01 · `SYSTEM-IMPROVE`

## Windows 实机已验证

- `cargo fmt --all -- --check`、workspace `check`、`-D warnings` Clippy 与 `cargo test --workspace --all-targets --locked` 通过。Workspace 当前结果为 Core 70 passed／1 ignored、host 1、原生文件系统／发布 7、secrets 1；忽略项是需显式启动的千章元数据耐久 profile。
- Book Setup 回归覆盖来源指纹、人物／关系决策模型、世界压力种子、500 万字符容量架构、固定终局、完整分卷／弧／高潮绑定、作者批准、active 全书计划绑定、批准中断恢复，以及幂等键冲突在计划写入前失败。
- 三章 Core 验收经过模型驱动的上下文 query／选择、Corpus 与偏好 greenlight、读取已批准 Setup 的私有人物模拟、因果场景解析、Director Note 隔离、逐场景正文与最小篇幅校验、语义审查／修订、接受、settlement、typed 账本投影、发布、重启连续性与偏好学习；同一生产释放、接受和结算请求会返回原收据，不产生第二份候选或重复落定。
- 同一验收会篡改角色权威投影，证明 strict open 拒绝；再以 expected revision 3 调用显式本地 Rust Bridge 快照恢复，并证明 strict reopen 成功。恢复回执明确 `semantic_inference=false`。
- Tauri manifest 格式、Clippy 和直连 Core 边界测试通过。
- 在 Node 24 与 pnpm 10.33.0 下，根目录 `pnpm` quality、typecheck、test、build 全部通过，覆盖产品站、SolidJS Studio 与 Cloud 合同镜像；Studio 测试证明显式模型选择仍由 Core 目录复核，业务状态只能经过 typed Bridge。
- 全仓扫描不存在 `.py`、`.pyi`、`pyproject.toml` 或 `__pycache__`；CI 另有解释器残留拒绝门。

## 跨平台证据

主 CI 与 Tauri CI 都在 `windows-latest`、`ubuntu-latest` 运行 Core／Tauri，并显式安装 Linux 桌面依赖。本记录不伪造本机 Linux 结果；Ubuntu jobs 才是 Linux 执行证据。

## 证据边界

没有运行合成 500 万字耐久测试，也没有把确定性 mock 中的独立审查阶段当作真实独立 invocation 证据。这些绿灯证明契约、事务、阶段隔离与恢复成立，不证明 500 万字小说的文学质量。真实连续章节文学 canary、真正独立的审稿调用与作者判断仍保持 pending。
