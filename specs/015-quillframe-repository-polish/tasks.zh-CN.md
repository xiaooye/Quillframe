# 任务 · Quillframe Repository Polish

格式：`[ID] [Phase] 精确 target + completion criterion`

## Phase 1 · Audit and freeze

- [x] T001 冻结 current `main` 为 `e49304bde7fb0c5ba0822deb3823f960c6425804`，检查 active PR / branches / workflows。
- [x] T002 识别 Agent PR #108 与 UI/UX branch ownership；不 merge、不覆盖。
- [x] T003 Benchmark current mature GitHub repositories，覆盖 agent、framework、Python、frontend、desktop、authoring。

## Phase 2 · Repository landing

- [ ] T004 重构 root README hero、positioning、principles、architecture、workflow、status、Quick Start、docs map、license truth。
- [ ] T005 同步英文与自然中文 root README。
- [ ] T006 只使用稳定 current brand/architecture assets；UI/UX reconciliation 前不固化易过期 Studio screenshot。

## Phase 3 · Contributor surface

- [ ] T007 新增 concise `CONTRIBUTING.md`，包含真实 setup/test commands 和 authority-sensitive change guidance。
- [ ] T008 新增 `SECURITY.md`，优先 GitHub Private Vulnerability Reporting，并明确 secret/project-data 处理。
- [ ] T009 新增标准 `CODE_OF_CONDUCT.md`，不自创复杂 enforcement system。
- [ ] T010 新增精简 issue forms 与 PR template，包含 authority impact 字段。

## Phase 4 · Docs/public naming

- [ ] T011 修复 docs landing 当前语境 NovelForge 文案与退役 Studio domain。
- [ ] T012 修复 active docs 中把 `quillframe` 错误描述成旧命名空间的 compatibility wording。
- [ ] T013 除非存在独立授权的法律/历史任务，否则保留 historical specs 与 legal license 原文。

## Phase 5 · Verification and PR

- [ ] T014 Final review 前重新 fetch live `main`、Agent PR、UI/UX branch；只 reconcile 已 merged facts。
- [ ] T015 验证 Markdown/YAML/relative links，并收集 CI/docs build evidence。
- [ ] T016 没有直接 rendered evidence 时，把 GitHub light/dark QA 报告为 unverified。
- [ ] T017 创建 Draft PR，包含 starting SHA、changed files、truth boundaries、verification、dependencies 与 known limitations；不 merge。
