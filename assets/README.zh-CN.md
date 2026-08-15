# NovelForge 视觉资产 · 仓库里的 Story Loom

本目录保存 NovelForge 文档与产品界面共用的 Story Loom 展示层和设计令牌基础。它刻意保持精简：一套一致的品牌系统、少量高价值产品图、机器可读的产品语义与明确来源记录，而不是 stock art 仓库，也不是第二套 UI Framework。

> **边界 ✦** 视觉资产与设计令牌负责帮助理解、建立识别度并保持展示一致性。它们永远不是 Framework 行为、系统架构、正典、Settlement、语义真相或工作流状态的第二权威来源。

---

## 01 · 当前真实资产地图

```text
assets/
├── README.en.md / README.zh-CN.md
├── DESIGN_SYSTEM.en.md / DESIGN_SYSTEM.zh-CN.md
├── provenance.json
├── brand/
│   ├── novelforge-mark.svg
│   ├── novelforge-lockup.svg
│   ├── story-thread.svg
│   └── tokens.json
└── ui/
    ├── home-comparison.en.svg / .zh-CN.svg
    ├── home-architecture.en.svg / .zh-CN.svg
    ├── home-pipeline.en.svg / .zh-CN.svg
    ├── home-quality.en.svg / .zh-CN.svg
    └── home-fit.en.svg / .zh-CN.svg
```

仓库里不存在的文件，文档不能把它写成“已经可用的资产”。特别是 WeiUI theme 在真正实现进入 `main` 之前，这里不会虚构一个 generated theme 路径。

---

## 02 · 两层维护中的视觉体系

### 品牌与产品语义基础资产

`brand/` 保存稳定的 Story Loom 身份：

- **主标志**：紧凑的 NovelForge 符号；
- **横向组合标志**：主要品牌展示形式；
- **故事线**：装饰性分隔与连续性母题；
- **设计令牌**：机器可读的品牌与产品语义配色来源。

这一层应当低频、成体系地变化。`brand/tokens.json` 是当前 NovelForge 侧的 token authority；未来 interactive theme adapter 可以转换它，但组件库不能反过来重定义 Story Loom 语义。

### 产品级 UI 图

`ui/` 保存用于 README / 产品入口面的高价值静态 SVG，目前负责解释：

- 直接小说系统对比；
- 系统架构；
- 生产流水线；
- 质量模型；
- 适用范围与取舍。

它们只是展示层；真正可维护的 Markdown / contract 仍然拥有语义权威。

---

## 03 · 交互产品桥接 · 已选方向

未来可安装 Studio Shell 已选择 Tauri + React + WeiUI。视觉依赖保持单向：

```text
NovelForge Story Loom tokens
→ deterministic WeiUI-compatible W3C token representation
→ WeiUI token / CSS / React component substrate
→ Tauri Studio shell
```

实现目前仍待落地。在 converter / theme artifact 真正 commit、测试并锁定之前，`assets/brand/tokens.json` 仍是本仓库唯一可以被文档称作“当前存在”的 NovelForge token source。

所有权必须明确：

- **NovelForge** 拥有 Story Loom domain color、产品语义、authority/status/provenance grammar、typography role、density 与视觉人格；
- **WeiUI** 拥有通用可复用 component primitive、组件 interaction/accessibility behavior、CSS mechanics 与公开 token/component contract；
- **adapter** 拥有两层之间的确定性转换；
- **Tauri** 负责可安装产品宿主，但不会获得 Core authority。

不要在 adapter 旁边再手抄第二份 Studio palette。不要把 generic `success` styling 映射成 Accepted Canon。不要让 Tauri、React 或 WeiUI 成为 Generic Core correctness、CLI、Framework bundle 或 Agent Skill 的依赖。

完整产品边界与 acceptance gate 见 [`../studio/PRODUCT_ARCHITECTURE.zh-CN.md`](../studio/PRODUCT_ARCHITECTURE.zh-CN.md)。

---

## 04 · Story Loom 基本规则

完整视觉契约见 [文档设计系统](DESIGN_SYSTEM.zh-CN.md)。

核心规则：

- 先保证专业技术文档质量，再谈装饰；
- 全仓使用一套原创视觉语言，不拼贴互不相关的风格；
- 二次元编辑感保持克制，不把文档做成吉祥物页面；
- 通用 Framework 资产不得包含某本消费小说的人物或正典事实；
- 不使用版权系列角色、Logo，也不直接模仿在世艺术家的具体风格；
- SVG 加载失败时，附近正文仍能解释核心语义；
- 颜色和 emoji 不能成为唯一语义通道；
- 不提交外部或嵌入式字体文件。

---

## 05 · Tier-A 视觉 QA

首页 / 产品级视觉比普通装饰资产要求更严格。

新的或重大重设计的 Tier-A SVG 在进入 README 前必须经过：

```text
文案冻结
→ 信息架构
→ Story Loom 布局
→ GitHub 类宽度真实渲染
→ 窄屏渲染
→ 渲染后逐字检查
→ 中英双语等价检查
→ 确定性文档 lint
→ 正式接入
```

硬要求包括：

- 根节点 `data-doc-tier="A"`；
- 非空 `<title>` 与 `<desc>`；
- 在约 820px GitHub 内容宽度下，正文投影字号不得低于 12px；
- 可测量的长文本必须有明确宽度预算；
- 不允许裁切、出框、碰撞，也不允许靠极小字号“解决”排版；
- 中英文几何差异明显时必须独立排版，不能硬套同一组坐标；
- 必须真实查看约 820px 与 420px 两种宽度的 render。

运行：

```bash
python scripts/docs_quality.py
```

**生成出来不等于审过；XML 合法不等于视觉正确。**

---

## 06 · 原子替换

开始重设计一张首页图，不代表应该先把现有可用视觉删掉。

默认流程：

```text
旧视觉继续在线
→ 新候选通过 render + 文案 + lint
→ README 与新资产一起完成替换
```

只有旧图本身已经误导、损坏或严重违反当前规则时，才允许为了正确性先撤掉。

---

## 07 · 来源记录

[`provenance.json`](provenance.json) 保存维护中视觉资产的来源信息。根据资产类型，可以记录：

- asset ID 与路径；
- 创建 / 编辑方法；
- 日期；
- 设计意图；
- 是否使用用户提供的参考；
- license / use note；
- 它所展示的语义来源或对应文档。

来源记录不会给视觉资产增加语义权威。它只是解释“这张图从哪里来、允许代表什么”。

等 WeiUI-compatible theme / converter 真正落地后，它的 generated-vs-source 状态、source token fingerprint/version 与 ownership 都应该显式记录，而不是靠目录位置暗示。

---

## 08 · 新增资产或 token-derived artifact 前先问什么

准备再增加视觉材料之前，先回答：

1. 它真的比纯正文 / Mermaid 更容易解释概念，或者满足真实产品展示需求吗？
2. 这个概念属于通用 Framework / product layer，而不是某本消费小说吗？
3. Story Loom 已经有适合它的视觉 / token pattern 吗？
4. 哪份可维护 source 定义它的语义？
5. 当前环境能在目标宽度下真实 render，或可确定性生成并检查吗？
6. 它是否需要中英文成对资产或 locale-sensitive QA？
7. 如果它是 generated artifact，是否只有一个 source of truth，并存在可复现转换路径？

如果这些问题都回答得很弱，就不要为了“看起来内容多”继续增加装饰文件或平行 token set。

**视觉系统真正成功，是让 NovelForge 一眼可识别，让产品界面复用同一套语义，同时不让展示层或组件工具变成竞争性的第二权威。**
