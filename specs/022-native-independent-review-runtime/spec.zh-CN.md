# 规格 022 · 原生独立审查运行时

## 状态

`SYSTEM-IMPROVE` 实施合同。冻结基线：
`05efed31d37a27e901ab777fa3d544e078d65305`。

## 问题

Quillframe 目前把独立语义审查等同于 GitHub Project/Actions 回执。Codex 与
Claude 能创建全新原生 subagent 调用，但 Core 无法证明其生命周期、绑定 exact
frozen packet，或区分有效判断与调用方伪造 JSON。旧 action 还会在 Core 冻结后
重建 packet，随机 nonce 改变并触发 `independent_packet_mismatch`。

Mapped Project 也存在断链：Git/Markdown adapter 能校验及构建确定性 bundle，
却不能把有界运行时对象实例化到 Project SQLite。

## 必须保持的不变量

1. Core 对每次独立审查只创建一次 packet。native、local 与 GitHub transport 都
   消费其 canonical exact bytes，并以冻结 nonce 作为 worker run reference。
2. Native review 始于一次性持久 lease；生命周期 hook 原子绑定真实子调用及一个
   不同于父 session 的 reviewer session。
3. `quillframe_independent_invocation_receipt_v1` 绑定 Project、run、job、
   candidate/input/packet/result 指纹、nonce、provider、父子 session、host
   agent/invocation ID、生命周期事件、assurance class 及自身指纹。
4. 回执是 host 生命周期证明，不宣称密码学或 OS 级隔离。Native assurance 为
   `host_native_separate_context`。
5. Reviewer 只收到 frozen packet，并声明无 Project、文件、shell、网络、memory
   或写权限。
6. 回执必须与持久生命周期状态匹配才有效。
7. 第一次有效 `pass` 或 `fail` 会跨 transport/provider 消耗 run/candidate。完全
   相同的证据可幂等 replay；禁止 reviewer shopping。只有基础设施故障可重试。
8. 并发相同 submit 只有一个 processing owner，并返回同一持久终态，不重复产生
   release 副作用。
9. `author.run.independent.submit` 接受 `independence_receipt`；
   `bridge_receipt` 保留为弃用中的 GitHub-v1 别名。
10. Readiness 报告 transport、provider 与 assurance class，不再统一要求 GitHub
    issue/comment 字段。
11. 实现其他 provider 前，GitHub 审查如实标记为 `github_copilot_actions`，且必须
    消费 frozen packet。Reusable workflow 只能通过 caller 前置 job 上传的
    artifact 与 Core 签发的 SHA-256 接收这些运行时 bytes；called job 在使用前
    必须下载、限制路径并校验 artifact。同 job 的 composite action 必须同时收到
    exact packet path 与 SHA-256。
12. Mapped Project 可声明 `paths.runtime_context_manifest`。Project-owned manifest
    显式映射 source fingerprint、stable ID、object type、authority、lifecycle、
    domain、allowed stages、target 与有界 runtime payload；Core 不猜 Markdown。
13. `project.projection.preview` 确定性且只读；`apply` 受 CAS 约束、幂等、事务化；
    `status` 报告当前 source/projection identity。
14. Projection 不创建 Canon、Acceptance、Settlement、accepted revision 或作者
    权威。Git/Markdown 保持 durable authority；SQLite 是可重建 runtime projection。
15. 第一次模型调用前，projected Project 必须验证 Project、目标 story
    node/document 与 manifest/source fingerprint。缺失或过期时零模型调用并
    fail closed。
16. Exact released candidate 经 `candidate.visible.get` 读取前，正文不可访问。

## 原生生命周期

`author.run.independent.dispatch.prepare` 冻结已有 packet，并为 provider 与父
session 创建 pending lease；只返回 lease 与 dispatch 元数据，不返回正文或 packet。

`SubagentStart` 以可信父 session、agent type 和真实 agent ID 认领唯一 pending
lease，不能信任 prompt 文本。它创建新 reviewer session，并把 frozen packet 作为
additional context 注入。`SubagentStop` 校验一份 JSON 判断，确定性包装 typed
result，记录终止事件、生成回执并提交。非法 JSON 或 hook 缺失属于基础设施故障，
不是语义拒绝。

## Mapped Project projection

Manifest 是语义编译边界。Preview 只读 adapter 声明的来源且不写入。Apply 在单一
事务内复核 source/target snapshot，再写入 projected source、必需 story/document
target、幂等记录与不可变回执。source drift、authority escalation 或冲突 replay
必须整体回滚。

## 兼容性

- 现有 GitHub peer receipt v1 仍可读取。
- 标准 Project 与未声明 runtime manifest 的 Project 行为不变。
- Candidate visibility 与 Acceptance/Settlement 合同不变。
- 本规格不修改或 repin consumer repository。

## 验收

- 基线及新增 native/projection/visibility 测试通过。
- 证明父子 session 分离、lease 一次性、exact packet、跨 transport 消耗、并发和
  工具拒绝。
- 重建/篡改 packet、nonce/provider/fingerprint 变化、伪造回执、agent ID 复用、
  stale candidate 与 authority escalation 全部 fail closed。
- Projection 确定、幂等、原子且受 stage 限制。
- target/manifest 缺失时模型调用数为零。
- 一次真实 Codex native review 仅经 `candidate.visible.get` 释放本地 Review Draft。
- 不执行 Acceptance 或 Settlement。
