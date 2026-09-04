# Windows 超长篇生产链

2026-08-31 · `SYSTEM-IMPROVE` · Quillframe 500 万字以上网文生产的后继规范。

本规范把 Windows 确认为正式支持平台，把 Quillframe Core clean break 为全 Rust 实现，并把系统目标提升为：可靠规划、创作、修订、审查、结算和维护一部超过 500 万中文字符的超长篇网文。规模目标不是一次性把整书塞进模型，而是要求每一次局部工作都能从稀疏、可验证、可恢复的长期状态继续。

## 01 · 成功定义

系统必须同时成立五件事：

- Windows 与 Linux 都由同一 Rust Core 安全创建、打开、锁定、备份、恢复和原子发布原生 1.0 Project；
- 书、卷、单元、章、场景是可寻址的真实节点，规划提案只有经作者显式激活后才约束生产；
- 章节可以由多个场景组成，读者压力能够影响 Writer，但对 Blind Reader 与独立 reviewer 保持隐藏；
- 修订能沿责任层回退，并识别当前章变化对后续已接受章节造成的影响；
- Corpus v2 只按阶段投影零到四张 source-free 机制卡，并具有可恢复研究、发布、冻结加载、评测与回滚证据。

最终发行包不包含 Python，也不要求用户安装 Node。工程门通过只能证明上述机制成立，不能宣称 500 万字作品的文学质量已经得到证明。文学质量仍需真实长程 canary、真正独立的语义审查和作者确认。

## 02 · Windows 原生安全等价

Windows 实现必须保持现有 POSIX 实现的安全不变量，而不是绕过它们：

- 每一层路径都拒绝符号链接、junction、mount point 和其他 reparse point；
- 文件与目录以句柄确认最终身份、类型、link count 与预期父级；
- 创建使用 exclusive semantics，发布使用同卷原子替换，持久化写入执行 flush；
- 打开期间禁止目标被删除或替换；跨进程锁、CAS、幂等回放和崩溃恢复保持有效；
- traversal、alternate data stream、保留设备名、硬链接替换和竞态攻击 fail closed；
- 未实现等价能力的平台继续拒绝运行。

Windows 与 Linux 路径策略由独立 Rust 原生核心拥有。业务层不得散落“如果是 Windows 就跳过检查”的分支。

## 03 · Shujuku 分层的全 Rust clean break

Quillframe 采用 Shujuku 的单向分层原则，但按原生小说生产系统重新落位：

```text
presentation · SolidJS Studio / Tauri commands / Rust Host API
      ↓
service      · 规划、Context、生产、审查、修订、结算、Corpus 与学习编排
      ↓
data         · SQLite repositories、事务、checkpoint/log、锁、备份与恢复
      ↓
shared/domain· 类型、身份、fingerprint、authority 与纯验证规则
```

依赖只允许向下；`shared/domain` 不依赖存储、模型或 UI，`data` 不拥有文学语义判断，`service` 不直接操作 DOM 或物理 SQLite schema，`presentation` 不绕过 service 写 Project。Rust 实现 `shared/domain`、`data`、`service` 与 Tauri host，SolidJS 只实现 presentation。Node 只用于构建 Studio 静态资源，不是产品运行时、服务端或 durable authority。

这一映射吸收 Shujuku 的 Repository、运行时状态、事件/服务编排、严格读取、snapshot/checkpoint 与提交日志思想；拒绝复制其 SillyTavern DOM、世界书 takeover、prompt SQL、TypeScript/sql.js 运行时和聊天 persona 假设。Tauri host 直接链接 Rust service，不再启动 sidecar。

迁移采用 clean break：不维护 Python/Rust 双写、双读、运行时 fallback、adapter 或长期兼容层。原生 `quillframe_project_v1_0` 及其 SQLite schema 可以保持稳定，由 Rust 针对同一 checksum-known contract 实现；历史 Python run 只能作为冻结 evidence 读取，不成为新 Rust run 的可恢复执行状态。

完成门要求删除 Python packages、`pyproject.toml`、Python CLI/sidecar、Python test/CI 和产品文档中的 Python 运行前提。迁移期间仓库可以暂存尚未移除的 Python before-state，但任何阶段都不得把“双运行时可用”称为最终架构，也不得以一个同时拥有 domain、SQL、业务编排和 Bridge 路由的巨型 Rust 模块冒充分层完成。

## 04 · 超长篇故事层级

唯一层级为：

```text
book
└─ volume
   └─ unit
      └─ chapter
         └─ scene
```

每个节点拥有稳定 ID、父节点、同级顺序、生命周期和绑定的当前规划版本。章节必须绑定真实 manuscript document；场景是因果与 Writer 运行目标，不自动成为单独正文文档。`CH001` 只是初始化节点，不代表项目范围。

删除已被规划、正文、状态或依赖引用的节点不在本规范授权范围内。重排必须使用显式 CAS 和依赖影响报告，不能静默重写历史 run。

## 05 · 四级规划与作者权威

四种规划模式分别拥有封闭 typed envelope：

- `DESIGN-BOOK`：全书读者承诺、主角能动性、核心矛盾、长期进阶、明确终局、完整分卷剧情、跨卷剧情/关系/人物弧、高潮链与不可静默改写边界；
- `DESIGN-VOLUME`：本卷承诺、局势净变化、主要对抗、人物关系运动、卷高潮与向下一卷的遗留债务；
- `PLAN-UNIT`：可闭合的小循环、情绪铺垫—释放—余波、兑现、延迟代价、伏笔与回扣；
- `PLAN-CHAPTER`：本章读者问题、可见回报、人物选择与代价、净变化、章末牵引，以及按顺序排列的场景目标。

模型输出先保存为 fingerprint-bound `proposal`。只有作者针对精确 proposal/version 显式激活后，它才成为 `active`。新激活版本原子 supersede 同一目标的旧 active 版本；proposal、草稿或评审结果都不能自行获得规划权威。

新项目还必须经过独立的 Book Setup 生命周期：`not_started → proposal_ready → author_approved_ready`。Setup 把全书计划与人物／关系决策模型、世界压力种子、初始卷／单元／章身份和滚动规划策略绑定为一个来源可追踪的指纹；达到 500 万字符时，还必须提供固定终局、完整分卷剧情、跨卷弧、逐卷高潮链、人物魅力证明节点与容量架构。批准会绑定精确 active `DESIGN-BOOK` 计划；中断在已激活计划和 Setup head 之间时必须显式报告未完成，并只允许同请求恢复，不能伪报无写入。

## 06 · 生产与修订闭环

章节运行消费当前章、祖先节点的 active plan 和被语义选择的稀疏长期状态。目标选择必须正确匹配 `book`、`volume:<id>`、`unit:<id>`、`chapter:<id>`，不能把裸节点 ID 与 typed target 混用。

一个章节按多个有序场景生产。Character Simulation 与 Scene Resolution 对每个场景维持人物行动所有权和因果闭合；Writer 可以一次实现一个场景或一组连续场景，但最终候选正文只有一个冻结指纹。Surface Writer 只接收单一 Scene Realization Contract，不得同时重复完整计划锁、章节计划与独立场景 brief；章节最低篇幅只在组装后检查，不得机械平分成逐场最低配额。

每个新运行必须冻结生产指导快照，绑定 Framework 正向 Writer 指导、完整 `HF-01..HF-30`、登记的语义审计 rubric，以及从已批准 Setup 的行文／声口／文风／校准来源经原生句柄物化且内容指纹一致的项目指导；调用者也可显式提交同一批准来源的精确字节。Writer 只读取正向投影；专用 Surface Auditor 必须对三十条规则逐项返回 evidence-bound assessment。缺项、重复、未知规则、证据不足或确认失败均不得释放正文；确定性代码不以词表或句长统计代替语义判断。

Reader Pressure 被压缩为 Writer 可用的 brief，并进入 Writer Pack 指纹。它为空时允许自然章节，不强迫每章制造悬念。Blind Reader 只收到正文与 reader-visible 定位，看不到该 brief、计划、规则、预期答案或 treatment 身份。独立 reviewer 和用户可见正文也不接收 Writer 私有指导。

独立审查或 Surface 审计拒绝必须生成只供下一次 REVISE 的内部 repair source。新 Writer 不得直接看到旧 Writer 的推理、Reviewer 链或被拒正文；Editor 根据责任层决定失效范围。REVISE 必须继承来源运行的生产指导快照，并按稳定规则身份合并当前局部要求，不能用一条窄修规则替换原始 Framework／项目／请求约束。任何修订后的完整候选都重新执行 Surface 审计。修订还必须向 Continuity 提供后续已接受章节的依赖摘要，若产生破坏则在结算前输出 downstream impact 与 propagation debt，不自动修改后文 Canon。

## 07 · Corpus v2 分层消费

035 冻结的六域 Corpus v2 是本规范的上游合同。生产链新增四种 source-free 投影：

- 书/卷规划：读者契约、长期推进、情绪循环、人物关系、固定终局与分卷兑现机制；
- 单元/章节规划：兑现、延迟、升级、伏笔回扣和章末牵引机制；
- 场景解析：人物能动性、关系运动、行动—反应、场景转换机制；
- Writer：场景实现与语言节奏机制。

每个阶段允许选择零到四张卡。没有相关机制时保持零卡基线，不得为满足 schema 强塞卡片。运行必须冻结 catalog version、mechanism IDs、选择结果和 receiving-stage fingerprint。Reader、reviewer、Canon 与用户偏好层都看不到 Corpus 身份。

## 08 · 长期状态与成本

超过 500 万字时，任何正常运行都不得加载整书正文或完整 Corpus。上下文必须执行 eligibility、语义选择、hard-budget packing 和 fingerprint-bound freeze；freeze 后禁止未追踪读取。

系统应维护可增量重建的章节依赖、人物/关系/世界状态、读者预期、规划债务、传播债务和 run checkpoint。接受、结算、supersede 与 publication 是不同生命周期状态。

全链账本区分 provider-confirmed、awaiting-reconciliation 与 externally-unreported 成本；未知费用不能记为零。作者不需要预设用户级 token 或费用上限，但系统必须记录实际用量并遵守模型与 Provider 的技术边界。

## 09 · 验收边界

正式验收分为四层：

1. 平台等价：真实 Windows 与 Linux 的安全、竞态、锁、原子发布和恢复测试；
2. 生产闭环：四级规划、多场景、Reader Pressure、拒绝后修订、后续依赖与结算隔离；
3. 增量恢复：以有界多章夹具验证打开、选择、修订、恢复和投影不读取无关正文，并可跨重启续跑；
4. 文学证据：真实连续章节 canary、顺序交换、独立 reviewer 和作者逐章判断。

前三层可以在确定性 CI 中执行，第四层必须显式启动且不得在普通 CI 中消耗模型。
