# 任务 · Quillframe Repository Polish

格式：`[ID] 精确 target + completion criterion`

## 审计 / reconciliation

- [x] T001 冻结 starting `main` 为 `e49304bde7fb0c5ba0822deb3823f960c6425804`，识别并行 ownership。
- [x] T002 Reconcile 已合并 Agent/Model Runtime PR #108，不引入 provider authority。
- [x] T003 Reconcile 已合并 UI/product-language PR #109 与后续 main layout/consistency fixes。
- [x] T004 Benchmark current high-star agent/framework/product repository README patterns。

## Repository landing

- [x] T005 将 root README 重构为完整产品 landing，并把 Quick Start 放到靠前位置。
- [x] T006 同步自然英文与简体中文版本。
- [x] T007 为 GitHub light/dark render 增加稳定、theme-aware 的 Quillframe mark 与 architecture/production artwork。
- [x] T008 保持 current status 真实：pre-1.0、未发布 Tauri wrapper、不虚构 provider gateway。

## Contributor / legal surface

- [x] T009 增加 `CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`ROADMAP.md`、issue forms 与 PR template。
- [x] T010 将 `LICENSE` 法律产品标识改为 Quillframe，不改变实质 source-available 条款。

## Documentation governance

- [x] T011 在 `documentation_manifest.json` 注册 Model Runtime / Agent Runtime 双语文档。
- [x] T012 在 Starlight 暴露 Model/Agent Runtime，并修复 docs-home links。
- [x] T013 让 standalone `scripts/docs_quality.py` 能针对 current public-doc corpus 真正执行。
- [x] T014 在 normal CI 运行 `docs_quality.py`，不调用模型/API。

## AI-readable public surface

- [x] T015 增加 `robots.txt`、`sitemap.xml`、`sitemap.md`、`llms.txt`、`llms-full.txt`、`auth.md`、AI catalog 与 Agent Skills index。
- [x] T016 发布明确的 `search=yes, ai-input=yes, ai-train=no` content-use signal，同时保持 license 为法律 authority。
- [x] T017 明确否认未支持的 public Core API / MCP / A2A / OAuth / hosted model-gateway claims。

## Verification / finalization

- [x] T018 在前序 exact heads 上取得 docs-governance/runtime/Studio/site 全 CI 绿色证据（runs #128 与 #130）。
- [x] T019 增加 exact-head GitHub README renderer：desktop light/dark + 390px narrow light/dark，并产出 screenshot + JSON artifact。
- [ ] T020 为最终 README head 获得真实 GitHub-render evidence；若新增 workflow 在进入 default branch 前受 GitHub Actions 事件规则阻断，则报告 `awaiting_external`，不得伪造 PASS。
- [ ] T021 并行 session 不再移动相关 surface 后，对 current `main` 做 final late reconciliation。
- [ ] T022 移除/恢复所有临时 PR-specific CI wiring，只保留 reusable QA tooling。
- [ ] T023 Cleanup/reconciliation 后取得 final-head green CI。
- [ ] T024 仅在 connected action 真正支持时写 Repository Description/Homepage/Topics；否则报告精确外部设置值。
- [ ] T025 用 exact final SHA/evidence 刷新 Draft PR #110 body，并保持 Draft/unmerged。
