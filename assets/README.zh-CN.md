# Quillframe 视觉资产 · 仓库里的 Story Loom

本目录保存 Quillframe 文档与产品界面共用的 Story Loom 展示层和 application-token foundation。它刻意保持精简：一套一致的品牌系统、少量高价值产品图、机器可读的产品语义、精确 dependency provenance 与 deterministic design-system QA，而不是 stock art 仓库，也不是第二套 UI Framework。

> **边界 ✦** 视觉资产与 token 负责帮助理解、建立识别度、保持交互一致性和产品主题。它们永远不是 Framework 行为、Canon、Settlement、semantic truth、production readiness 或 workflow state 的第二权威来源。

---

## 01 · 当前真实资产地图

```text
assets/
├── README.en.md / README.zh-CN.md
├── DESIGN_SYSTEM.en.md / DESIGN_SYSTEM.zh-CN.md
├── provenance.json
├── brand/
│   ├── quillframe-mark.svg
│   ├── quillframe-lockup.svg
│   ├── story-thread.svg
│   ├── tokens.json
│   ├── weiui.integration.json
│   └── story-loom.weiui.css
└── ui/
    ├── home-comparison.en.svg / .zh-CN.svg
    ├── home-architecture.en.svg / .zh-CN.svg
    ├── home-pipeline.en.svg / .zh-CN.svg
    ├── home-quality.en.svg / .zh-CN.svg
    └── home-fit.en.svg / .zh-CN.svg
```

机器集成检查位于[产品站质量门](../site/scripts/quality.mjs)，并由 Story Loom 工作流强制执行。

---

## 02 · 品牌与产品语义权威

`brand/tokens.json` 当前 schema 已是 **`quillframe_brand_tokens_v2`**，继续作为 Quillframe 侧 product-token authority。

它现在包含：

- 稳定的 Story Loom brand/domain semantics；
- light/dark application theme roles；
- 44px minimum touch target、focus geometry 等 interaction budgets；
- mobile-first responsive rules；
- `en-US` + `zh-CN` i18n constraints；
- reduced-motion / no-idle-animation rules；
- no default polling、no heavy default component import 等性能约束。

Generic UI foundation 不能反过来重定义 Quillframe 中 Project、Runtime、Editorial、Evidence、Accepted/Validated、Rejected、Canon authority 或 execution state 的含义。

---

## 03 · WeiUI foundation · 已合并并精确固定

Story Loom → WeiUI bridge 已经是仓库真实 artifact，不再只是未来方向。

[`brand/weiui.integration.json`](brand/weiui.integration.json) 记录：

- WeiUI repository：`xiaooye/weiui`；
- exact commit：`d84d1cd365fb5f90cbbab794d2358f7a13b29b79`；
- license：MIT；
- allowed packages：`@weiui/tokens`、`@weiui/css`；
- forbidden Phase 2C runtime packages：`@weiui/headless`、`@weiui/react`；
- WeiUI runtime JavaScript required：`false`；
- theme layer：`wui-theme`；
- CSS order：WeiUI tokens → WeiUI CSS → Story Loom theme。

[`brand/story-loom.weiui.css`](brand/story-loom.weiui.css) 是当前 live application theme bridge。它把 Story Loom light/dark roles 映射到 WeiUI `--wui-*` variables，同时保留独立的 Quillframe `--qf-*` product semantics。它不能 fork WeiUI `.wui-*` component selector，也不能靠 `!important` 抢 cascade。

因此产品依赖保持单向：

```text
Story Loom v2 product tokens
→ exact-pinned WeiUI tokens/CSS
→ Story Loom wui-theme aliases
→ SolidJS product surfaces
→ Local Web / optional Tauri host
```

WeiUI 在 Phase 2C 中是 zero-JavaScript styling/token foundation，**不是** application runtime，也不是 Quillframe product authority。

---

## 04 · Phase 2C product-stack boundary

选定的 application stack 是 SolidJS + TypeScript + Vite + `@solidjs/router`。

- Local Web 是一等产品面，在最小增量 CPU/RAM 优先时作为首选。
- Tauri 是同一产品之上的 optional/installable host，不再是产品架构中心。
- `@weiui/react` 与 `@weiui/headless` 被明确排除出 Phase 2C runtime。
- Generic Core correctness、CLI、Framework bundle 与 Agent Skill 必须继续独立于 SolidJS/Vite/Tauri 和 WeiUI runtime JavaScript。

完整产品边界见 [`../studio/PRODUCT_ARCHITECTURE.zh-CN.md`](../studio/PRODUCT_ARCHITECTURE.zh-CN.md)。

---

## 05 · Machine-checkable application design contract

运行：

```bash
pnpm --filter @quillframe/product-site quality
```

Checker 会验证：

- exact WeiUI source pin 与 MIT provenance；
- Story Loom v2 / integration schema ID；
- 只允许 `@weiui/tokens` + `@weiui/css`；
- 禁止 React/headless WeiUI runtime；
- `runtime_javascript_from_weiui=false`；
- mobile-first 与 phone `focus-first` behavior；
- minimum 44px touch target；
- baseline locales 精确为 `en-US`、`zh-CN`；
- logical properties required，且禁止 fixed-width locale assumptions；
- reduced motion required，idle animation forbidden；
- no default polling；
- primary/destructive/success/warning role pair 的 required light/dark contrast ≥ 4.5:1；
- `wui-theme`、light/dark definitions、required `--wui-*` / `--qf-*` variables；
- 禁止 `!important`，Story Loom 也不能 fork WeiUI component selector；
- design-system provenance IDs 完整。

这套 deterministic gate 只验证 machine-checkable design contract；它不能替代真实 responsive rendering、accessibility testing、native-copy review 或 runtime CPU/RAM measurement。

---

## 06 · 产品级 UI 图

`ui/` 保存用于 README / 产品入口面的高价值静态 SVG，解释 direct comparison、architecture、production pipeline、quality model 与 fit/tradeoffs。

它们只是 presentation assets；真正可维护的 Markdown/contracts 仍然拥有语义权威。

A 级 SVG 继续要求真实 820px 与窄屏渲染检查、可见文案复核、双语一致性，以及接入前运行 `pnpm --filter @quillframe/product-site quality`。

---

## 07 · Story Loom 基本规则

核心规则：

- 专业技术 / 产品清晰度优先；
- 全仓使用一套原创视觉语言，不拼贴互不相关的风格；
- 二次元编辑感保持克制，不做 mascot noise；
- Generic Framework asset 不包含某本消费小说的人物或 Canon；
- 不使用版权系列角色、Logo，也不直接模仿在世艺术家的具体风格；
- 颜色永远不能单独承载 authority 或 PASS/FAIL；
- generic `success` styling 永远不能证明 Accepted Canon 或 production readiness；
- documentation asset 不提交外部/嵌入字体文件；
- 不在 token/theme contract 旁边维护第二份手抄 Studio palette。

更完整的 static visual grammar 继续见 [文档设计系统](DESIGN_SYSTEM.zh-CN.md)。

---

## 08 · Provenance 与 derived artifacts

[`provenance.json`](provenance.json) 保存维护中 asset 的来源信息。WeiUI integration 现在已经有明确的 source commit/license，以及 Story Loom v2 token contract / application theme provenance ID。

目录位置本身永远不会产生 authority。对于 generated / mapped artifact，provenance 应明确记录：

- authoritative source；
- 适用时的 exact upstream dependency；
- generated-vs-source status；
- mapping contract；
- validation mechanism；
- artifact 只是 presentation，还是会被 product runtime 消费。

**视觉系统真正成功，是让 Quillframe 一眼可识别，让 Studio 复用唯一一套产品语义，同时不让展示工具或 generic UI foundation 变成竞争性的第二权威。**
