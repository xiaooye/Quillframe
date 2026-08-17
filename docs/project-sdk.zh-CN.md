# Project SDK

Quillframe Project 是独立 versioned 的小说工程。Framework 提供 generic production mechanism；Project 提供 concrete story authority。

<img src="assets/architecture/framework-vs-project.zh-CN.svg" alt="Project 指向 pinned framework，而具体人物、Canon、plan、state、research 与 manuscript 都留在 Project 侧" width="100%" />

## Project Identity

受支持 Project 用 `novelforge.toml` 声明 schema/path，在 `novelforge.lock.json` 锁定 exact Framework revision，并可对 materialized framework bundle 做 attestation。这些文件名属于 compatibility identifier，即使 public framework brand 已经是 Quillframe，也继续保留。

## Ownership

Project-owned data 包括具体 BOOK/VOL/ARC/UNIT/CH/SCN instance、character/relationship、current state、claim、dependency、active plan、profile、research、regression、manuscript 与 Accepted Canon。

Generic Framework source 绝不能把这些私有故事事实反向吸收成 built-in behavior。

## Standard 与 Mapped Layout

Project SDK 支持 standard layout；Project Adapter 可以把成熟/legacy repo 映射成同一 logical contract。Mapping 改变 storage path，不改变 authority semantics。

## Reproducibility

Project 应能脱离 chat memory 自己 validate/build。Exact Framework pin 与 deterministic bundle fingerprint 让 runtime bytes 可检查、可复现。Framework current `main` 是 Framework maintenance 的开发 authority，不会在普通 production 中静默替换 consumer pin。

## Change Discipline

结构级改变可以走 spec → plan → tasks → implementation → verification → acceptance；普通 prose micro-edit 不需要假软件工程仪式。无论 layout 如何，Canon mutation 仍必须 explicit acceptance + Settlement。
