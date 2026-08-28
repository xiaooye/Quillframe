# 正典与状态模型 · 永久保存“计划、生成、接受、结算”之间的区别

<p><kbd>TIER C · 契约</kbd>&nbsp;&nbsp;<kbd>权威</kbd>&nbsp;&nbsp;<kbd>结算</kbd>&nbsp;&nbsp;<kbd>证据</kbd></p>

Quillframe 把**故事事实**与计划、草稿、研究、审阅结论、运行时状态、模型记忆和派生摘要严格分开。长篇连续性真正依赖的不是“记住得更多”，而是始终记得：**每一条记录究竟被允许代表什么。**

> **核心不变量 ✦** 一条信息出现在上下文、记忆库、数据库、审阅结果或会话里，并不会让它自动变成正典。

## 01 · 这个模型负责什么

正典与状态模型定义以下通用机制：

- 权威等级与冲突优先级；
- 稳定对象身份；
- 一个事实只有一个权威归属；
- 证据能够证明到什么范围；
- 信息归属；
- 显式 State Delta；
- 依赖影响；
- 事务化结算；
- 写入后的 post-condition 验证；
- 正典、运行时、记忆、学习、研究与审阅状态之间的隔离。

它不定义任何一本具体小说的事实。下游项目拥有自己的实体、Accepted 正文、locked 不变量，以及必要时更细的项目级 precedence。

## 02 · 权威等级

Quillframe 使用一组通用生命周期标签：

```text
proposal     可替换的候选想法或修改建议
active_plan  当前仍然有效的未来意图
review       已生成 / 已修订，等待明确接受的候选稿
accepted     已被明确接受、具备结算资格的正文或状态
locked       明确不变量 / 长期项目常量
```

这些不是随便贴在文件上的工作流标签，它们回答的是不同问题：

- `proposal`：*我们是否可以这样做？*
- `active_plan`：*我们现在是否打算这样做？*
- `review`：*这是不是当前正在考虑的候选稿？*
- `accepted`：*授权用户 / 流程是否明确接受了这份正文或状态？*
- `locked`：*这是否属于普通规划与修订绝不能静默改动的项目不变量？*

项目可以进一步细化 precedence，但绝不能把 Plan / Review 折叠成 Accepted Canon。

## 03 · 通用冲突优先级

当多个来源互相冲突时，一个项目通常按大致以下顺序解析：

1. 当前明确的用户指令；
2. 项目 locked 不变量；
3. Accepted Canon 正文；
4. 已结算的权威当前状态；
5. 权威的人物 / 关系 / 世界 / 连续性当前状态；
6. active plan；
7. 已验证研究 claim；
8. review draft；
9. 临时推断。

运行时 / session / checkpoint **不是正典 precedence 层**。

模型可能在早先聊天里见过某个事实。这只能证明运行时见过它，不能证明故事已经接受它。

## 04 · Plan ≠ 当前状态

如果章节计划写着人物将来会：

- 得到一笔钱；
- 知道一个秘密；
- 获得权限；
- 见到某个人；
- 丢失一个物件；
- 改变一段关系；
- 作出一个承诺；

这些变化都不会因为“计划里已经写了”就进入权威当前状态。

```text
active_plan：未来 X 应该发生
≠
current state：X 已经发生
```

同样的边界也适用于 Scene Card、scenario branch、大纲笔记和 revision proposal。

## 05 · Accepted ≠ Settled

接受与结算故意被拆成两步。

**Acceptance / 接受**：冻结用户明确批准、可以作为正典证据的 artifact。

**Settlement / 结算**：把这份 artifact 真正支持的精确状态变化写入权威状态库。

这样，系统可以安全停在“章节已经接受，但所有受影响状态还没更新完”这个中间点。

也能避免一次部分失败的数据库写入被误报成“正典已经成功更新”。

## 06 · 一个事实只能有一个权威归属

避免同一条 live truth 在多个地方同时可写。派生视图可以总结权威状态，但不能与它竞争。

一个通用映射可以是：

```text
人物身份 / 生平                 → CHAR
关系当前状态                    → REL / ROM
历史 / 故事事件                 → EVT
信息归属                        → INFO / SEC / RUM
资源 / 金钱 / 债务              → RES
权限 / 资格                     → PERM
物件 / 证据                     → ITEM / EVID
开放问题 / 义务                 → LOOP / OBL
伏笔 / 揭示                     → FS / REV
研究来源 / claim                → REF / CLAIM
读者承诺 / 回报                 → PAY
人物弧线 / 人物吸引力           → CARC / APL
人物持续存在 / 参与状态          → PRES
跨对象依赖                      → DEP
```

如果摘要、Memory Bank、Context Cache 或自动生成 profile 重复了这些事实，那么那份副本只是**派生引用**，不是第二个可写 authority。

## 07 · 稳定身份

推荐的通用 ID 家族：

### 故事
`BOOK · VOL · ARC · UNIT · CH · SCN`

### 人物
`CHAR · CARC · APL · PRES`

### 关系
`REL · ROM`

### 世界
`ORG · LOC · INST · ITEM`

### 连续性 / 剧情状态
`EVT · INFO · SEC · RUM · RES · PERM · LOOP · OBL · EVID · FS · REV`

### 研究 / 读者 / 治理
`REF · CLAIM · PAY · MOM · THM · DEP · DEC`

一个 ID 一旦进入 active / accepted，就不能重新分配给另一个实体。

人类可读名称可以变，身份不能变。

## 08 · 真相与“谁知道”必须分开

故事里的事实，不等于任何人物都知道它。

```text
世界真相
≠ 叙述者 / POV 可见范围
≠ 人物知识
≠ 人物信念
≠ 传闻
```

一条现实研究 claim 可以被证实，但某个历史人物仍然不可能知道它。人物也可以非常自信地说错话。传闻即使是假的，也可能真实改变行动。

只要信息归属会改变行为，就应该用 `INFO / SEC / RUM` 或项目自己的等价模型显式记录。

## 09 · 证据只能证明它真正建立的东西

证据范围必须保持窄而精确。

例如：

- 拥有某个物件，不等于理解它的意义；
- 听说一个传闻，不等于传闻为真；
- 某个角色很自信地说了一句话，不等于世界事实成立；
- Scene Card 不能证明事件发生；
- Review Draft 不能证明事件发生；
- semantic reviewer 拒绝一个候选稿，不能证明任何故事事实；
- eval result 不会授予 Canon authority；
- Memory Bank 里有某条信息，不等于人物知道它；
- runtime checkpoint 不能证明叙事事件发生过。

不要因为“这样方便”就扩大证据权限。

## 10 · State Delta 契约

正典结算必须明确到可以审计。

```yaml
artifact_id:
artifact_fingerprint:
ops:
  - op: update
    object_type: RES
    id: RES-...
    before: {...}
    set: {...}
    evidence_ref: 精确 Accepted 正文 / 明确 Canon 指令
```

每一条操作至少需要：

1. 精确的 authority object type；
2. 唯一稳定 ID；
3. 精确 expected before-state；
4. 来自 Accepted artifact 或明确 Canon 指令的证据；
5. dependency impact 分析；
6. 已授权 write intent；
7. 真正执行 mutation；
8. 刷新派生视图；
9. post-condition 验证；
10. trace / receipt。

匹配到 `0` 个或 `>1` 个目标都必须硬停止。

## 11 · 依赖让变化可追踪

`DEP` 或等价依赖模型记录：哪些未来计划、摘要、时间线、计算、研究假设或连续性视图依赖哪些权威状态。

一个已结算事实发生变化后，下游 artifact 可能需要：

- 失效；
- 重算；
- 重新规划；
- 重新审阅；
- 标记 stale。

不要因为未来工作生成成本很高，就强行保留它。

## 12 · 结算是一笔事务

一个通用 settlement 序列是：

```text
明确 acceptance
→ 冻结 Accepted artifact + fingerprint
→ 推导精确 State Delta
→ 验证 before-state
→ 计算 dependency impact
→ checkpoint / write intent
→ 授权 mutation
→ 重建 derived views
→ 验证 post-condition
→ 写 trace / receipt
```

任何 before-state mismatch 或 post-condition failure 都必须进入**结算未完成**状态。

禁止：

- 猜一个“应该差不多”的 before-state；
- 部分成功却宣称全部成功；
- resume 时重复已经完成的 side effect；
- 某条 operation unresolved 时，顺手写入无关状态。

恢复执行必须能区分已经完成的 mutation 与仍然 pending 的 mutation。

## 13 · Context、Memory 与派生视图属于更低权威

Quillframe 可以提供作者可编辑的上下文和记忆控制，但这些控制不能偷偷变成第二套 Canon editor。

`locked` / `accepted` 受保护引用可以作为只读 snapshot 展示在 editable-memory surface 中；编辑这种 snapshot 必须生成**proposal**，不能原地修改受保护 Canon row。

派生记忆必须保持 `authority=false`，保留来源引用 / 指纹，并允许失效与重建。

详见 [上下文与记忆](../docs/context-and-memory.zh-CN.md)。

## 14 · Research 是证据，不是自动获得的故事知识

Verified research 回答的是“外部证据支持什么”，而不是：

- 项目是否选择把它写进自己的虚构世界；
- 这个事件是否已经在本小说发生；
- 某个人物是否知道；
- 当前叙述者是否有资格说；
- 某个未来计划是否已经变成当前状态。

研究 claim 可以约束规划和正文，但除非项目明确把它采用进自己的 world / Canon 模型，否则它的 authority 仍然只属于 research scope。

## 15 · Runtime 与 Review state 只是操作证据

以下内容可以触发工作、验证或 proposal，但本身都不会成为 Canon：

- session history；
- checkpoint；
- handoff；
- webhook / connector event；
- worker receipt；
- semantic-review result；
- Reader Panel result；
- integrity-audit finding；
- quality-evolution ledger；
- eval result；
- CI result；
- corpus observation；
- learning hypothesis；
- model / provider memory。

**能力不等于权威；被存下来不等于权威；判断结论也不等于权威。**

## 16 · 失败语义

遇到以下情况应停止，而不是猜：

- authority class 不清楚；
- target ID 无法精确解析为一个对象；
- before-state 与冻结预期不一致；
- 证据并不支持 proposed delta；
- dependency impact 无法安全限定；
- 低权威 surface 正试图改受保护 Canon；
- post-condition 验证失败；
- resume 无法证明某个 side effect 是否已经发生。

正确状态应是 `settlement_incomplete` 或等价的明确失败，而不是“应该已经成功了”。

## 17 · 不变量

1. 永久保存**计划、生成、接受、结算**之间的区别。
2. Plan / Scene Card / Review 从来不能隐含“已经发生”。
3. Accepted artifact 与 settled state 是两个不同 checkpoint。
4. Runtime / session / memory / learning / corpus / review state 都不能授予 Canon authority。
5. 每条可变权威事实只有一个 canonical home。
6. 状态 mutation 必须有证据、有 precondition，并通过 post-condition 验证。
7. Resume 绝不重复已经完成的 side effect。
8. Derived view 可以重建；权威事实必须始终可追踪。

## 18 · 相关契约

- [故事系统](STORY_SYSTEM.zh-CN.md)：未来规划与依赖。
- [人物与关系系统](CHARACTER_SYSTEM.zh-CN.md)：信息归属、关系 / 当前状态与人物证据。
- [上下文与记忆](../docs/context-and-memory.zh-CN.md)：仍然低于正典权威的作者可见控制层。
- [原生项目契约](../docs/project-contract.zh-CN.md)：四键 manifest、顶层含 `scope: "novel"` 的上下文、fingerprint、项目工程与项目自有权威。
- [Session Runtime](../harness/session_runtime/SESSION_RUNTIME.zh-CN.md)：必须与 Canon 分离的操作状态。
