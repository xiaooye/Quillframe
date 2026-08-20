# 已被取代的 pre-1.0 endurance plan

> 仅作为审查记录保留。本文件不是执行计划、release authority 或当前
> implementation checklist。native 1.0 contract 与当前 tests 优先于此记录。

## 保留的审查范围

该记录曾审查 host boundary：host 运行 agent，Quillframe 管理小说
authority。当前 native owner 是 `project_resolution.py`、`core_operations.py`、
`studio/project_hub_projection.py`、`studio/host_bridge.py` 及其 contract tests。

当前 Project contract 是精确的：`quillframe.toml` 只有五个 root key
（`schema`、`id`、`title`、`language`、`chapter_scope`），schema 是
`quillframe_project_v1_0`，运行边界是 CH001，manifest fingerprint 是确定性的
`sha256:` evidence，持久化数据位于 `.quillframe/data`，UI/projection authority
为 `false`。

## 历史审查结果

此前 endurance 工作已被 native 1.0 hard cut 取代。任何剩余 release、外部
host 或人工审查工作都没有在本记录中执行，不能从旧 checklist 推断完成。
确定性验证包括 native resolver/bridge tests、精确 fingerprint 检查、CH001
拒绝测试、bundle bytes/fingerprint 检查与显式 authority boundary 检查。

本记录不规定任何已取代的 alternate identity、layout 或 execution behavior。
历史 specs 与 changelog 在各自的历史目录中保留原始措辞。

## 状态

已被取代；没有任何待办 checklist 具有 authority。未来工作应查阅当前 native
contract、实现、tests 与 release evidence。
