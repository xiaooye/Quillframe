<div align="center">
  <img src="brand/quillframe-lockup.svg" alt="Quillframe 自适应小说智能体框架" width="620" />
</div>

# Quillframe Story Loom 设计系统

> **一套视觉语言，同时服务文档与产品 UI。**
>
> Story Loom 把 **项目 → 运行时 → 故事 → 读者体验 → 证据 → 已验证结果** 看成一根持续编织、校验、回接的故事线。专业技术感负责骨架，二次元编辑感负责识别度与温度。🌸

**视觉配比：** `70% 专业技术 / 30% 二次元编辑感`。

本文解释面向人的设计契约。机器权威分别位于 [`brand/tokens.json`](brand/tokens.json)、[`brand/weiui.integration.json`](brand/weiui.integration.json)、[`brand/story-loom.weiui.css`](brand/story-loom.weiui.css) 与[产品站质量门](../site/scripts/quality.mjs)。文档的真实渲染与审查要求继续由 [`../docs/DOCUMENTATION_QA.zh-CN.md`](../docs/DOCUMENTATION_QA.zh-CN.md) 负责。

> **权威边界 ✦** Story Loom 可以表达产品 domain、authority label、execution status、provenance、focus、hierarchy 与 interaction state，但它永远不会创造 Canon、semantic truth、production readiness 或 workflow authority。

---

## 01 · 品牌气质 ✦

Quillframe 应同时具备四种气质：

| 气质 | 设计含义 |
|---|---|
| **精确** | 层级、间距、交互状态和图表语义严谨一致 |
| **编辑感** | 像小说编辑与生产工作台，而不是通用 DevOps dashboard |
| **温度** | 樱花粉、薰衣草紫、纸张感 surface 带来人味与二次元气质 |
| **工程化** | token、dependency pin、provenance、accessibility rule 与 QA 都可检查 |

首页和总览页可以自然使用 `🌸 ✦ ✨ 📖`；契约、Schema、命令面与 machine inspector 应保持克制。

### 标志系统

<img src="brand/quillframe-mark.svg" alt="Quillframe Story Loom 主标志" width="120" />

主标志结合书页、编织成 N 的 story thread 与 forge spark。高曝光入口优先使用 lockup，小尺寸位置使用 mark。不要旋转、发光、随意改色，也不要把 logo 当成 architecture/status icon。只使用系统字体回退，不提交外部字体文件。

---

## 02 · Product Token 权威 · Story Loom v2

机器源：[`brand/tokens.json`](brand/tokens.json)，schema 为 **`quillframe_brand_tokens_v2`**。

当前 token contract 同时覆盖文档语义与 application constraints，是 Quillframe 侧以下内容的 source of truth：

- Story Loom domain families：Project、Runtime、Editorial、Evidence、Validated、Rejected、Neutral；
- application light/dark theme roles；
- typography 与 density roles；
- focus geometry 与 minimum touch target；
- mobile-first responsive behavior；
- `en-US` + `zh-CN` i18n constraints；
- reduced-motion behavior；
- no default polling、no idle decorative animation、no heavy default import 等 runtime-overhead rules。

### Token 纪律

- 柔和色只用于 fill/accent，不做低对比度正文。
- 颜色永远不能单独承载 PASS/FAIL 或 authority。
- Generic `success` styling **不等于** Accepted Canon、production-ready 或有效 publication output。
- Authority、execution state、provenance 与 domain color 必须保持正交。
- Localized UI 中，精确 machine identifier 不翻译。
- 间距默认遵循 4/8 rhythm，除非 machine product token 明确覆盖。

---

## 03 · WeiUI 集成边界 · 已合并

WeiUI 是 generic **zero-JavaScript token/CSS foundation**，不是 Quillframe product authority，也不是 Phase 2C application runtime。

机器契约：[`brand/weiui.integration.json`](brand/weiui.integration.json)。

当前 dependency truth：

```text
Story Loom v2 product tokens
→ exact-pinned xiaooye/weiui
→ @weiui/tokens + @weiui/css
→ story-loom.weiui.css (`wui-theme`)
→ SolidJS product surfaces
→ Local Web / optional Tauri host
```

Integration contract 将 WeiUI 精确固定到 commit `d84d1cd365fb5f90cbbab794d2358f7a13b29b79`，并要求：

- allowed packages：`@weiui/tokens`、`@weiui/css`；
- prohibited Phase 2C runtime packages：`@weiui/react`、`@weiui/headless`；
- `runtime_javascript_from_weiui=false`；
- import order：WeiUI tokens → WeiUI CSS → Story Loom theme；
- Story Loom 只通过 `@layer wui-theme` 覆盖；
- 不 fork `.wui-*` component selector；
- 不用 `!important` 逃逸 cascade。

[`brand/story-loom.weiui.css`](brand/story-loom.weiui.css) 把产品 roles 映射到 `--wui-*` variables，同时把 Quillframe 专属语义保留在 `--qf-*` variables。WeiUI 升级可以改变通用实现细节，但不能静默重定义 Quillframe 概念。

---

## 04 · Application Visual / Runtime Contract

Phase 2C product code 已确定为 **SolidJS + TypeScript + Vite + `@solidjs/router`**。Local Web 是一等产品面；Tauri 是同一产品之上的 optional installable host。

设计系统刻意把职责分开：

- **Story Loom** 拥有产品语义与视觉含义；
- **WeiUI** 拥有 generic reusable CSS/token primitives；
- **SolidJS** 拥有 application behavior 与 reactive UI composition；
- **Studio adapters / Core** 拥有 typed product data 与 commands；
- **Tauri** 可以承载 installable build，但不会获得 story/runtime authority。

### 已由机器强制执行的 app invariants

产品站质量门至少检查：

- exact WeiUI pin 与 provenance；
- SolidJS/TypeScript/Vite product-stack contract；
- zero WeiUI runtime JS；
- minimum touch target `44px`；
- focus ring `3px` + `2px` offset；
- mobile-first breakpoints 与 phone `focus-first` workspace；
- baseline locales 精确为 `en-US`、`zh-CN`；
- logical properties required，fixed-width locale assumptions forbidden；
- reduced motion required；
- idle decorative animation forbidden；
- default polling forbidden；
- heavy default component import forbidden；
- required light/dark contrast ≥ 4.5:1；
- required theme variables/layers，且无 forbidden selector fork。

通过 deterministic design-system QA **不等于**真实 CPU/RAM 性能或视觉可用性已经证明。Phase 2C 仍需要真实 responsive、accessibility、localization、bundle/chunk、idle CPU/RAM、first-interaction 与 host-process measurement。

---

## 05 · Responsive、i18n、Accessibility、Motion

Mobile 是一等产品约束，不是最后再把 desktop 缩小。

- **Phone：** manuscript/workspace 采用 focus-first；Inspector 变成 route/overlay。
- **Tablet：** 可以使用更丰富 split surface，但空间不足时 Inspector 仍是 overlay-or-route。
- **Desktop：** 空间允许时才保持 persistent Inspector。
- **Touch：** interactive target 满足 machine token 的 minimum size。
- **i18n：** layout 必须承受中英文扩张；优先 logical CSS properties；禁止假设英文宽度。
- **Accessibility：** focus 可见、contrast 可测、颜色不是唯一语义通道、screen-reader name 明确。
- **Motion：** reduced-motion 必须支持；不能为了让产品“显得活着”而保留 idle decorative animation。

Story Loom 可以有温度，但不需要一直动。

---

## 06 · Markdown 与文档页面样式

GitHub Markdown 无法依赖 arbitrary product CSS，因此文档继续使用可移植 Story Loom primitives：

1. 主要入口页使用品牌 lockup；
2. `<kbd>` chips 只表达稳定概念；
3. story-thread divider 用于大区块留白；
4. 展示型页面使用 `01 · 系统总览` 这样的编号 H2；
5. 使用“边界 ✦”“为什么重要”等 semantic callout；
6. 只有真正适合 lookup 时才使用 compact matrix；
7. Mermaid 继续作为可检查 source diagram；
8. 小型 mark/footer 只在确实改善节奏时使用。

品牌感来自层级与一致性，不来自反复 Hero 或装饰密度。

---

## 07 · 字体与信息层级

- 每页只保留一个 H1；
- manuscript、UI 与 metadata/mono roles 保持区分；
- heading 在装饰之前先建立 scan order；
- 正文段落短而可读；
- monospace 只用于 ID、schema、path、command、fingerprint 与 state machine；
- table 不承载 essay-length prose；
- decorative Unicode / emoji 不替代正式 label；
- 绝不靠缩小字号到不可读来修 overflow；
- locale expansion 需要时，中英文可以使用不同自然几何。

仓库不会把 font file 作为文档资产分发。

---

## 08 · Mermaid · Story Loom Grammar

Mermaid 继续作为技术文档中可检查的 source chart。

### Lane grammar

- **Project · 天空蓝**：输入、Native Project Contract、Context；
- **Runtime · 薰衣草紫**：Harness、Session、Control Plane、workers；
- **Story / Editorial · 中性 + 樱花粉**：Story core、simulation、draft、reader quality；
- **Evidence · 琥珀色**：feedback、Corpus、learning、eval；
- **Validated · 薄荷绿**：已验证结果，但不隐含 Canon；
- **Reject · danger**：只用于真实 reject/invalid/failed gate。

### Shape / edge grammar

- stadium：boundary/input/output；
- hexagon：decision/manager/semantic gate；
- database：durable state/runtime store；
- subroutine：reusable core mechanism；
- rounded node：普通处理步骤；
- solid edge：主执行/依赖；
- dashed edge：feedback/evidence/resume/reference。

一张图只回答一个核心问题。复杂 nuance 放在附近正文，不塞进超长 node label。

---

## 09 · Tier-A 静态视觉硬契约

首页 / 产品级 SVG 是 maintained semantics 上的 presentation layer：

```text
主张与文案冻结
→ 信息架构
→ Story Loom 布局
→ SVG source
→ 真实 render inspection
→ deterministic lint
→ integration
```

硬要求：

- 默认以 `1200px` 级 viewBox 设计，除非有充分理由；
- 必须检查约 **820px** GitHub 内容宽度和 **420px** narrow width；
- 820px 下正文投影字号至少 **12px**；
- checker 可测量的长文本需要明确 width budget；
- 不允许 clipping、overflow、collision 或靠 tiny text “修复”；
- English / Chinese 必须母语化撰写和独立排版；
- root `data-doc-tier="A"`、非空 `<title>` / `<desc>`、system-font fallbacks only；
- meaningful image 有 alt text；SVG 失效时附近 prose 仍能保留核心语义。

接入前运行 `pnpm --filter @quillframe/product-site quality` 并真实查看渲染结果。**生成出来不等于审过；XML 合法不等于视觉正确。**

---

## 10 · 完成标准

一个 Story Loom 文档或产品 surface 只有同时满足以下条件才算完成：

- 去掉装饰后，信息层级仍然成立；
- domain、authority、execution state 与 provenance 没被压成同一种颜色；
- 中英文表达相同主张，但各自自然；
- phone/narrow behavior 是主动设计，不是偶然结果；
- keyboard/focus/contrast/reduced-motion behavior 可信；
- 产品使用 exact-pinned WeiUI boundary，而不是维护平行手写 palette；
- deterministic docs/design-system QA 为绿；
- 已经做过真实 render；application 工作还要有真实 runtime measurements；
- presentation code 从不成为 Core 或 story truth 的第二权威。

**Story Loom 成功的标准，是 Quillframe 足够工程化、足够有编辑感、足够有辨识度，而且在不牺牲语义诚实的前提下尽可能轻。✦**
