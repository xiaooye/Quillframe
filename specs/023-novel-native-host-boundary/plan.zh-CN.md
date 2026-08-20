# Spec 023 实施计划 · Quillframe 小说契约原生 Host 边界

## 实施顺序

1. 盘点 operation registry、MCP/skill manifest、Host Bridge、embedded runtime、
   Studio read surface 及全部 version source。
2. 增加 machine-readable capability 分层，将 novelist-facing、internal/ops、
   privileged author 分类，但不复制既有 schema。
3. 更新产品、架构、runtime、integration、Studio 文档及成对 manifest，准确说明
   Host/kernel/Project 边界。
4. 更新单一版本来源和全部发布表面为 `0.9.1`；保留历史 changelog，并记录限制。
5. 增加 raw-draft visibility、privileged operation discovery、version consistency、
   optional embedded runtime 和双语文档回归。
6. 运行 Python、Studio、site、docs、Tauri 确定性/烟测；独立审查 diff 后冻结 RC。

## 文件与所有权

- `specs/023-novel-native-host-boundary/`：本规范及双语计划；
- 既有 `studio/host_bridge_contract.json`、MCP/skill manifest、SDK capability registry：
  只做 surface 分类；
- README、architecture、runtime、integration、Studio 文档、CHANGELOG、版本文件：
  只更新表述与 identity，不重写 runtime；
- 既有 visibility/authority tests：增加边界回归。

不得扩张为通用 agent framework 或全站 UI 重构；CH001 writer-facing review slice 以外的
能力记录为 post-v0.9.1 backlog。

## 审查 gate

- 实施前：source inventory 与双语文档自审；
- 实施后：exact version scan、machine contract 校验、干净确定性 suite、bundle 双构建、
  独立 P0/P1 review；
- 发布交接：复核 exact main commit、tag、artifact checksum，以及下载后的 install/doctor/
  MCP/Bridge smoke。
