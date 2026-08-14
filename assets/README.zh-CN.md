# NovelForge 视觉资产 · 仓库里的 Story Loom

本目录保存 NovelForge 文档的正式视觉展示层。它刻意保持精简：一套一致的品牌系统、少量高价值产品图，以及明确的来源记录，而不是堆积 stock art 或无用途装饰图。

> **边界 ✦** 视觉资产负责帮助理解和建立识别度。它永远不是 Framework 行为、系统架构、正典或产品主张的第二权威来源。

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

仓库里不存在的文件，文档不能把它写成“已经可用的资产”。

---

## 02 · 两层视觉体系

### 品牌基础资产

`brand/` 保存稳定的 Story Loom 身份：

- **主标志**：紧凑的 NovelForge 符号；
- **横向组合标志**：主要品牌展示形式；
- **故事线**：装饰性分隔与连续性母题；
- **设计令牌**：机器可读的语义配色来源。

这一层应当低频、成体系地变化。

### 产品级 UI 图

`ui/` 保存用于 README / 产品入口面的高价值静态 SVG，目前负责解释：

- 直接小说系统对比；
- 系统架构；
- 生产流水线；
- 质量模型；
- 适用范围与取舍。

它们只是展示层；真正可维护的 Markdown / contract 仍然拥有语义权威。

---

## 03 · Story Loom 基本规则

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

## 04 · Tier-A 视觉 QA

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

## 05 · 原子替换

开始重设计一张首页图，不代表应该先把现有可用视觉删掉。

默认流程：

```text
旧视觉继续在线
→ 新候选通过 render + 文案 + lint
→ README 与新资产一起完成替换
```

只有旧图本身已经误导、损坏或严重违反当前规则时，才允许为了正确性先撤掉。

---

## 06 · 来源记录

[`provenance.json`](provenance.json) 保存维护中视觉资产的来源信息。根据资产类型，可以记录：

- asset ID 与路径；
- 创建 / 编辑方法；
- 日期；
- 设计意图；
- 是否使用用户提供的参考；
- license / use note；
- 它所展示的语义来源或对应文档。

来源记录不会给视觉资产增加语义权威。它只是解释“这张图从哪里来、允许代表什么”。

---

## 07 · 新增资产前先问什么

准备再增加一张图之前，先回答：

1. 它真的比纯正文 / Mermaid 更容易解释这个概念吗？
2. 这个概念属于通用 Framework，而不是某本消费小说吗？
3. Story Loom 已经有适合它的视觉模式吗？
4. 哪份可维护 source 定义它的语义？
5. 当前环境能在真实 GitHub 宽度下 render 并检查吗？
6. 它是否需要中英文成对资产？

如果这些问题都回答得很弱，就不要为了“看起来内容多”继续往仓库里堆装饰文件。

**视觉系统真正成功，是让 NovelForge 一眼可识别，同时不牺牲技术文档的可检查性。**
