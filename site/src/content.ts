export type Locale = "en-US" | "zh-CN";

export type Card = {
  eyebrow?: string;
  title: string;
  body: string;
  meta?: string;
};

export type RouteCopy = {
  eyebrow: string;
  title: string;
  lede: string;
  cards: Card[];
  note?: string;
};

export const copy = {
  "en-US": {
    languageName: "中文",
    nav: {
      product: "Product",
      studio: "Studio",
      architecture: "Architecture",
      publication: "Publication",
      docs: "Docs",
      changelog: "Changelog",
      github: "GitHub",
      menu: "Open navigation",
      close: "Close navigation",
      appearance: "Toggle appearance",
    },
    home: {
      eyebrow: "Adaptive fiction agent framework · 0.8.x",
      title: "A fiction system that can show what it knew, what passed, and what changed.",
      lede: "NovelForge treats long-form fiction as an inspectable creative system: context is grounded, characters only act on evidence they can know, quality gates bind to the exact candidate, and accepted text can travel into deterministic publication without silently changing the manuscript.",
      primaryCta: "Explore the forge",
      secondaryCta: "See the architecture",
      proofLabel: "Proof, not promises",
      problem: {
        eyebrow: "The problem",
        title: "A prompt can make prose. A novel needs memory with rules.",
        lede: "One-shot generation is good at producing text. It is much worse at preserving authority, perspective, continuity, and repair history across a living book.",
        cards: [
          { title: "Context without leakage", body: "Relevant evidence is not enough. NovelForge also checks visibility, story order, stage eligibility, authority, and the hard packet budget before evidence can reach the model." },
          { title: "Characters with epistemic limits", body: "A character action cannot cite future, unknown, or perspective-incompatible evidence as positive support just because the framework stores it somewhere." },
          { title: "Quality without fake scores", body: "Surface, reader engagement, continuity, and independent semantic review remain distinct typed gates. Readiness is a conjunction, not a made-up 8.7/10." },
        ],
      },
      forge: {
        eyebrow: "The forge",
        title: "Creative judgment where it belongs. Deterministic boundaries everywhere else.",
        lede: "The model judges fiction semantics. Code owns authority, visibility, fingerprints, budgets, persistence, typed validation, and transactions.",
        steps: [
          ["01", "Project", "Canon, plans, characters, relationships, research, and current work remain distinct authority classes."],
          ["02", "Context", "Question-bound evidence is filtered for visibility and story order before semantic selection."],
          ["03", "Simulation", "Story, character, reader pressure, and consequence are resolved before line-level surface polish."],
          ["04", "Draft", "Generation consumes a frozen packet; private reasoning and hidden regression material stay outside writer context."],
          ["05", "Gates", "Surface, reader engagement, continuity, and required independent semantic review bind to one candidate fingerprint."],
          ["06", "User-visible", "Only a candidate that satisfies the current gate policy may cross into review; acceptance and settlement remain separate."],
        ],
      },
      proofs: [
        { eyebrow: "Context", title: "Support ≠ loaded context", body: "Run Receipts distinguish evidence selected as support from evidence that actually entered the bounded packet — including budget drops and visibility exclusions.", meta: "novelforge_run_receipt_v1" },
        { eyebrow: "Readiness", title: "One fingerprint, all required gates", body: "The production-readiness record fails closed when required Surface, Reader Engagement, Continuity, or independent semantic evidence is missing, pending, or failing.", meta: "novelforge_production_readiness_v1" },
        { eyebrow: "Character", title: "Knowledge has a story-time boundary", body: "Epistemic status and acquisition mode are separate, and proposed actions must be backed by character-visible, story-ordered evidence.", meta: "character evidence contract" },
        { eyebrow: "Publication", title: "Accepted text stays exact", body: "Publication IR checks source fingerprints and preserves exact Unicode manuscript text while producing derived clean text, Web HTML, print-oriented HTML/CSS, and EPUB 3.3.", meta: "novelforge_publication_ir_v1" },
        { eyebrow: "Hosts", title: "Capability never becomes authority", body: "CLI, Local Web, hosted UI, and Agent Skill may expose different capabilities. Host access never grants Canon, Framework-write, or Settlement authority.", meta: "authority=false" },
        { eyebrow: "Design", title: "The visual system is executable too", body: "Story Loom v2 pins the WeiUI zero-JavaScript foundation and machine-checks theme layering, contrast, touch size, locales, reduced motion, and no-default-polling rules.", meta: "novelforge_brand_tokens_v2" },
      ],
      studio: {
        eyebrow: "Studio",
        title: "A creator workbench, not a runtime dashboard with a manuscript tab.",
        lede: "Creator Mode starts from the work: manuscript, story, review, publication. Inspector Mode reveals the runtime evidence only when you need it.",
        bullets: ["SolidJS + TypeScript + Vite", "Local Web first-class", "WeiUI tokens/CSS with zero WeiUI runtime JS", "Optional Tauri installable host"],
        cta: "Explore Studio",
      },
      publication: {
        eyebrow: "Publication",
        title: "Accepted manuscript in. Deterministic derived formats out.",
        lede: "The minimum publication core already exists. It preserves exact accepted text, validates fingerprints, and builds four explicit profiles without turning output into Canon.",
        profiles: ["clean_text", "web_reflow", "print_book", "epub3"],
        note: "Current print_book output is print-oriented HTML/CSS, not a final paged-media PDF. Release EPUB conformance still requires external EPUBCheck.",
        cta: "Publication details",
      },
      architecture: {
        eyebrow: "Architecture",
        title: "One system, distinct responsibilities.",
        lede: "NovelForge is intentionally not an agent round-table. Each subsystem owns a bounded mechanism and emits typed evidence for the next boundary.",
        cards: [
          { eyebrow: "Project", title: "Canon & state", body: "Authority classes, dependencies, accepted state, plans, and settlement evidence stay explicit." },
          { eyebrow: "Runtime", title: "Harness & sessions", body: "Manager sessions, runs, checkpoints, capabilities, handoffs, fingerprints, and consume-once evidence." },
          { eyebrow: "Story", title: "Simulation & character", body: "Causal story mechanics, character agendas, knowledge, relationships, long-horizon reconciliation." },
          { eyebrow: "Editorial", title: "Reader & surface", body: "Reader pressure, engagement, anti-AI surface fundamentals, candidate evolution, narrow repair routing." },
          { eyebrow: "Evidence", title: "Corpus & learning", body: "Rights-aware benchmarks, preference evidence, counterexamples, rollbackable hypotheses, no Canon leakage." },
          { eyebrow: "Product", title: "Studio & publication", body: "Portable read boundaries, Local Web, Agent Skill, deterministic publication, and inspectable product proof." },
        ],
        cta: "Open architecture",
      },
      delivery: {
        eyebrow: "One product, many hosts",
        title: "Use the interface that fits the work — without changing story truth.",
        hosts: [
          ["CLI", "Scriptable automation and inspection."],
          ["Local Web", "Low-overhead creator workstation and first-class product surface."],
          ["Hosted UI", "The same product model behind a remote typed boundary."],
          ["Agent Skill", "Portable bridge access without private persistence imports."],
        ],
      },
      release: {
        eyebrow: "Release truth",
        title: "0.8.x means active pre-1.0 development.",
        lede: "Latest main is the development baseline. Machine contracts are increasingly explicit and CI-gated, but NovelForge does not pretend that every 8.0-line goal is frozen or complete.",
        cta: "Read the changelog",
      },
      final: {
        title: "Read the system. Inspect the proof. Then decide if it fits your fiction workflow.",
        docs: "Browse documentation",
        github: "View on GitHub",
      },
    },
    routes: {
      product: {
        eyebrow: "Product model",
        title: "NovelForge is a fiction production system, not a prompt wrapper.",
        lede: "It separates creative judgment from deterministic control so a long-running book can accumulate evidence, revisions, and state without turning every previous model output into truth.",
        cards: [
          { title: "Authority before convenience", body: "Locked, accepted, active plan, review, proposal, derived, runtime, learning, and corpus material are not interchangeable." },
          { title: "Evidence before confidence", body: "Context and character decisions can expose exactly what support existed, what was eligible, and what actually entered the active packet." },
          { title: "Repair the owning mechanism", body: "Surface clusters regenerate scenes; reader-grip failures return to Reader Pressure and Scene Simulation; story failures return to Story mechanics." },
          { title: "Acceptance is a real boundary", body: "A review candidate is not Canon. User acceptance and exact settlement remain explicit transitions with fingerprints and before/after evidence." },
        ],
      },
      studio: {
        eyebrow: "NovelForge Studio",
        title: "The creative workbench around Core — with progressive disclosure instead of dashboard overload.",
        lede: "The current product foundation is read-oriented and portable. Phase 2C uses SolidJS and the zero-JavaScript WeiUI token/CSS layer, with Local Web first-class and Tauri optional.",
        cards: [
          { eyebrow: "Phase 1", title: "Run / Context Inspector", body: "Shows the crucial distinction between semantic support and evidence that really entered model context." },
          { eyebrow: "Phase 2A", title: "Project Hub / Scene", body: "A safe read projection for project identity and a creator/inspector scene workspace prototype." },
          { eyebrow: "Phase 2B", title: "Portable Host Bridge", body: "Allowlisted read operations shared by CLI, Local Web/app, hosted UI, and Agent Skill consumers." },
          { eyebrow: "Phase 2C", title: "SolidJS product shell", body: "Mobile-first, bilingual, no default polling, zero WeiUI runtime JavaScript, with measured runtime overhead as an acceptance criterion." },
        ],
      },
      architecture: {
        eyebrow: "System architecture",
        title: "Generic mechanisms stay generic. Project truth stays in the project.",
        lede: "NovelForge defines reusable Story, Character, Canon, Context, Quality, Runtime, Learning, Corpus, Publication, and Product contracts. Consumer novels supply their own characters, world, plans, state, manuscript, and accepted Canon.",
        cards: [
          { title: "Harness", body: "Session-native orchestration, capabilities, routing, handoff and checkpoint semantics." },
          { title: "Context", body: "Sparse question-bounded evidence with visibility, story-order, authority and hard-budget enforcement." },
          { title: "Semantic contracts", body: "Typed model judgments with fingerprints; deterministic validators enforce shape and ownership, not literary taste." },
          { title: "Quality", body: "Reader, continuity, character, surface and independent semantic evidence converge at an explicit readiness boundary." },
          { title: "Learning", body: "Evidence-backed preference hypotheses with scope, contradictions, provenance and rollback." },
          { title: "Publication", body: "Exact-text Accepted manuscript compilation into deterministic, derived publication artifacts." },
        ],
      },
      publication: {
        eyebrow: "Deterministic publication",
        title: "Publication is derived output — never a second manuscript authority.",
        lede: "The current minimum compiler binds to accepted text fingerprints and preserves exact Unicode chapter text. Broader typesetting remains deliberately separate from what is already implemented.",
        cards: [
          { title: "clean_text", body: "A deterministic clean-text representation of Accepted manuscript content." },
          { title: "web_reflow", body: "Reflowable Web HTML derived from the same exact-text Publication IR." },
          { title: "print_book", body: "Print-oriented HTML/CSS. It is not yet the final paged-media PDF pipeline described by the broader Typesetting roadmap." },
          { title: "epub3", body: "Deterministic EPUB 3.3 generation with internal structure/text validation; release conformance requires external EPUBCheck." },
        ],
        note: "Issue #16 remains open for richer semantic IR, fuller profile controls, advanced CJK/Latin typography, paged-media PDF, broader validation, and Studio Publish authoring/preview.",
      },
      docs: {
        eyebrow: "Documentation",
        title: "Deep contracts when you need them. Product story when you do not.",
        lede: "The public site does not replace repository documentation. These links lead to the maintained sources that define current behavior and boundaries.",
        cards: [
          { eyebrow: "Start", title: "Docs Home", body: "Task-oriented entry into architecture, runtime, quality, projects, Studio, and release truth.", meta: "docs/README.en.md" },
          { eyebrow: "Core", title: "Architecture Atlas", body: "Subsystem map and contract-oriented architecture reference.", meta: "docs/architecture-atlas.en.md" },
          { eyebrow: "Production", title: "Production Pipeline", body: "From context freeze and simulation through user-visible review and settlement boundaries.", meta: "docs/production-pipeline.en.md" },
          { eyebrow: "Quality", title: "Quality Assurance", body: "Surface, Reader Engagement, Continuity and semantic gate semantics.", meta: "docs/quality-assurance.en.md" },
          { eyebrow: "Product", title: "Studio Architecture", body: "Creator/Inspector product model, portable hosts, SolidJS/WeiUI foundation, and current gaps.", meta: "studio/PRODUCT_ARCHITECTURE.en.md" },
          { eyebrow: "Release", title: "0.8.x Development Inventory", body: "What is merged, what remains open, and what must not be described as shipped.", meta: "docs/8-0-development-inventory.en.md" },
        ],
      },
      changelog: {
        eyebrow: "Release truth",
        title: "A changelog that separates implementation from aspiration.",
        lede: "NovelForge is pre-1.0. The current ledger records merged machine/product behavior and keeps remaining Core/Product gaps explicit rather than silently promoting roadmaps into capabilities.",
        cards: [
          { title: "0.8.0 identity", body: "Manifest, CLI, Skill, Project SDK default, MCP metadata, and documentation governance use one pre-1.0 development identity." },
          { title: "Breaking cleanup is still possible", body: "Before 1.0, justified machine-contract cleanup may land on latest main when architecture and deterministic CI support it." },
          { title: "History stays history", body: "Older 7.x changelog/spec records retain their original meaning; active docs do not rewrite the past to make current naming look inevitable." },
        ],
      },
    } satisfies Record<string, RouteCopy>,
  },
  "zh-CN": {
    languageName: "EN",
    nav: {
      product: "产品",
      studio: "Studio",
      architecture: "架构",
      publication: "出版",
      docs: "文档",
      changelog: "变更记录",
      github: "GitHub",
      menu: "打开导航",
      close: "关闭导航",
      appearance: "切换外观",
    },
    home: {
      eyebrow: "自适应小说 Agent Framework · 0.8.x",
      title: "一套能告诉你：它知道了什么、通过了什么、又改了什么的小说系统。",
      lede: "NovelForge 把长篇小说当成一套可检查的创作系统：Context 有明确依据，角色只能依据自己真正知道的信息行动，质量 Gate 绑定同一个候选稿 fingerprint，而 Accepted 正文进入确定性出版流程时不会被静默改写。",
      primaryCta: "看看这座 Forge",
      secondaryCta: "打开系统架构",
      proofLabel: "不是承诺，是证据",
      problem: {
        eyebrow: "问题不在于能不能生成文字",
        title: "一个 Prompt 可以写出一段话；一本长篇，需要有规则的记忆。",
        lede: "一次性生成最擅长的是把字写出来。真正难的是一本书持续推进以后，谁有权成为事实、谁知道什么、哪里发生过修订、证据有没有真的进入上下文。",
        cards: [
          { title: "Context 不能只看“相关”", body: "证据即使相关，也要先过 visibility、故事时间顺序、stage eligibility、authority 与 hard budget；能被找到，不代表能被模型看到。" },
          { title: "角色不能偷看作者后台", body: "某条信息存在于 Framework state，并不代表角色知道。Future、unknown 或与当前视角不兼容的 evidence 不能替角色行动背书。" },
          { title: "质量不是编一个总分", body: "Surface、Reader Engagement、Continuity、independent semantic review 是不同 Gate。Readiness 是 conjunction，不是“8.7 分所以可以发”。" },
        ],
      },
      forge: {
        eyebrow: "The Forge",
        title: "需要文学判断的地方交给模型；需要边界的地方交给确定性系统。",
        lede: "模型负责判断小说语义。代码负责 authority、visibility、fingerprint、budget、persistence、typed validation 与 transaction。",
        steps: [
          ["01", "Project", "Canon、plan、character、relationship、research 与当前工作保留各自 authority class。"],
          ["02", "Context", "问题绑定 evidence；visibility 与 story order 在 semantic selection 前先确定性过滤。"],
          ["03", "Simulation", "先解决因果、角色 agenda、reader pressure 与 consequence，再谈表面润色。"],
          ["04", "Draft", "Generation 只消费冻结后的 packet；private reasoning 与 hidden regression material 不进入 writer context。"],
          ["05", "Gates", "Surface、Reader Engagement、Continuity 与 required independent semantic review 绑定同一个 candidate fingerprint。"],
          ["06", "User-visible", "只有满足当前 Gate policy 的候选稿才能进入可见 Review；Accepted 与 Settlement 仍然是后面的独立边界。"],
        ],
      },
      proofs: [
        { eyebrow: "Context", title: "被认为有帮助 ≠ 真正进了上下文", body: "Run Receipt 分开记录 semantic selection 认为是 support 的 evidence，与最后真正塞进 bounded packet 的 evidence，也记录 budget drop 与 visibility exclusion。", meta: "novelforge_run_receipt_v1" },
        { eyebrow: "Readiness", title: "同一个 fingerprint，所有 required Gate", body: "Surface、Reader Engagement、Continuity 或 independent semantic evidence 只要 required 且缺失、pending 或 fail，就不能被说成 ready。", meta: "novelforge_production_readiness_v1" },
        { eyebrow: "Character", title: "角色知识有故事时间边界", body: "Epistemic status 与 acquisition mode 分开；proposed action 必须拿角色可见、遵守 story order 的 evidence 做依据。", meta: "character evidence contract" },
        { eyebrow: "Publication", title: "Accepted 正文保持精确一致", body: "Publication IR 校验 source fingerprint，并在生成 clean text、Web HTML、print-oriented HTML/CSS、EPUB 3.3 时保留 exact Unicode manuscript text。", meta: "novelforge_publication_ir_v1" },
        { eyebrow: "Hosts", title: "有能力，不等于有权威", body: "CLI、Local Web、Hosted UI、Agent Skill 可以拥有不同 host capability，但这些 capability 不会自动产生 Canon、Framework-write 或 Settlement authority。", meta: "authority=false" },
        { eyebrow: "Design", title: "设计系统本身也能被验证", body: "Story Loom v2 精确固定 zero-JS WeiUI foundation，并用 machine checks 守住 theme layer、contrast、touch target、locale、reduced motion 与 no-default-polling。", meta: "novelforge_brand_tokens_v2" },
      ],
      studio: {
        eyebrow: "Studio",
        title: "先是创作工作台，再是 Runtime Inspector。",
        lede: "Creator Mode 从 Manuscript、Story、Review、Publish 开始；只有真正需要追 evidence 时，Inspector Mode 才把 Run、Context、fingerprint 与 capability 展开。",
        bullets: ["SolidJS + TypeScript + Vite", "Local Web 是一等产品面", "WeiUI tokens/CSS，零 WeiUI runtime JS", "可选 Tauri 桌面宿主"],
        cta: "看看 Studio",
      },
      publication: {
        eyebrow: "Publication",
        title: "Accepted manuscript 进去，确定性的 derived formats 出来。",
        lede: "最小 Publication Core 已经真实存在：保留 exact Accepted text，验证 fingerprint，再按明确 profile 构建派生格式；输出本身不会变成 Canon。",
        profiles: ["clean_text", "web_reflow", "print_book", "epub3"],
        note: "当前 print_book 是 print-oriented HTML/CSS，不是最终 paged-media PDF。EPUB 真正做 release conformance 时仍要求 external EPUBCheck。",
        cta: "查看出版能力",
      },
      architecture: {
        eyebrow: "Architecture",
        title: "一套系统，但每个机制都有自己的职责。",
        lede: "NovelForge 刻意不做 agent round-table。每个 subsystem 只拥有有边界的机制，并把 typed evidence 交给下一道边界。",
        cards: [
          { eyebrow: "Project", title: "Canon & state", body: "Authority class、dependency、Accepted state、plan 与 settlement evidence 全部显式存在。" },
          { eyebrow: "Runtime", title: "Harness & sessions", body: "Manager session、run、checkpoint、capability、handoff、fingerprint 与 consume-once evidence。" },
          { eyebrow: "Story", title: "Simulation & character", body: "因果机制、角色 agenda、知识边界、关系与 long-horizon reconciliation。" },
          { eyebrow: "Editorial", title: "Reader & surface", body: "Reader Pressure、engagement、anti-AI Surface Fundamentals、candidate evolution 与 narrow repair routing。" },
          { eyebrow: "Evidence", title: "Corpus & learning", body: "Rights-aware benchmark、preference evidence、counterexample、可 rollback hypothesis，而且不能泄漏进 Canon。" },
          { eyebrow: "Product", title: "Studio & publication", body: "Portable read boundary、Local Web、Agent Skill、deterministic publication 与可检查 product proof。" },
        ],
        cta: "打开架构",
      },
      delivery: {
        eyebrow: "一个产品，多种宿主",
        title: "用适合当前工作的界面，但不要改变故事真相。",
        hosts: [
          ["CLI", "适合脚本化自动化与 inspection。"],
          ["Local Web", "低额外开销的 Creator Workstation，也是一等产品面。"],
          ["Hosted UI", "在 remote typed boundary 后使用同一套产品模型。"],
          ["Agent Skill", "通过 portable bridge 消费能力，不需要知道私有 persistence。"],
        ],
      },
      release: {
        eyebrow: "Release truth",
        title: "0.8.x 表示 active pre-1.0 development。",
        lede: "latest main 是开发基线。越来越多 machine contract 已经显式并进入 CI，但 NovelForge 不会把还没冻结、还没完成的 8.0-line 目标提前写成稳定 1.0。",
        cta: "查看变更记录",
      },
      final: {
        title: "先看系统，再看证据，然后决定它是否适合你的小说工作流。",
        docs: "浏览文档",
        github: "打开 GitHub",
      },
    },
    routes: {
      product: {
        eyebrow: "Product model",
        title: "NovelForge 是小说生产系统，不是 Prompt Wrapper。",
        lede: "它把 creative judgment 与 deterministic control 分开，让一本长期运行的书可以持续积累 evidence、revision 与 state，而不是让每一次模型输出都顺手升级成事实。",
        cards: [
          { title: "Authority 先于方便", body: "locked、accepted、active plan、review、proposal、derived、runtime、learning、corpus 不能混成一层“记忆”。" },
          { title: "Evidence 先于自信", body: "Context 与 Character decision 可以解释：有什么依据、哪些依据 eligible、最后哪些真的进入 active packet。" },
          { title: "失败回到 owning mechanism", body: "Surface cluster 回 whole-scene regeneration；reader-grip failure 回 Reader Pressure + Scene Simulation；story failure 回 Story mechanics。" },
          { title: "Accepted 是真正边界", body: "Review candidate 不是 Canon。用户 Accepted 与 exact Settlement 都是显式 transition，并绑定 fingerprint 与 before/after evidence。" },
        ],
      },
      studio: {
        eyebrow: "NovelForge Studio",
        title: "Core 周围的创作工作台，用 progressive disclosure 代替 dashboard overload。",
        lede: "当前 Product foundation 以 read-oriented、portable 为主。Phase 2C 使用 SolidJS + zero-JS WeiUI token/CSS，Local Web first-class，Tauri optional。",
        cards: [
          { eyebrow: "Phase 1", title: "Run / Context Inspector", body: "把“semantic support”与“真正进入 model context”的 evidence 明确分开。" },
          { eyebrow: "Phase 2A", title: "Project Hub / Scene", body: "安全的 Project read projection，以及 Creator/Inspector Scene workspace prototype。" },
          { eyebrow: "Phase 2B", title: "Portable Host Bridge", body: "CLI、Local Web/app、Hosted UI、Agent Skill 共用 allowlisted read operations。" },
          { eyebrow: "Phase 2C", title: "SolidJS product shell", body: "Mobile-first、双语、no default polling、零 WeiUI runtime JS，并把真实 runtime overhead measurement 当 acceptance criteria。" },
        ],
      },
      architecture: {
        eyebrow: "System architecture",
        title: "Generic mechanism 保持 generic；Project truth 永远留在 Project。",
        lede: "NovelForge 定义可复用的 Story、Character、Canon、Context、Quality、Runtime、Learning、Corpus、Publication 与 Product contracts；具体小说自己拥有角色、世界、计划、状态、正文和 Accepted Canon。",
        cards: [
          { title: "Harness", body: "Session-native orchestration、capability、routing、handoff 与 checkpoint semantics。" },
          { title: "Context", body: "Sparse question-bounded evidence，执行 visibility、story-order、authority 与 hard-budget。" },
          { title: "Semantic contracts", body: "Typed model judgment + fingerprint；deterministic validator 管 shape 与 ownership，不冒充文学审美。" },
          { title: "Quality", body: "Reader、continuity、character、surface、independent semantic evidence 在显式 readiness boundary 汇合。" },
          { title: "Learning", body: "Evidence-backed preference hypothesis，带 scope、contradiction、provenance 与 rollback。" },
          { title: "Publication", body: "Accepted manuscript exact-text compilation → deterministic derived publication artifacts。" },
        ],
      },
      publication: {
        eyebrow: "Deterministic publication",
        title: "Publication 是 derived output，不是第二份 manuscript authority。",
        lede: "当前 minimum compiler 绑定 Accepted text fingerprint，并保留 exact Unicode chapter text；更大的 Typesetting scope 与已经实现的部分保持明确分界。",
        cards: [
          { title: "clean_text", body: "Accepted manuscript content 的 deterministic clean-text representation。" },
          { title: "web_reflow", body: "从同一 exact-text Publication IR 生成 reflowable Web HTML。" },
          { title: "print_book", body: "Print-oriented HTML/CSS；它还不是 broader Typesetting roadmap 中的 final paged-media PDF。" },
          { title: "epub3", body: "Deterministic EPUB 3.3 generation + internal structure/text validation；release conformance 仍要求 external EPUBCheck。" },
        ],
        note: "Issue #16 继续承载 richer semantic IR、完整 profile controls、advanced CJK/Latin typography、paged-media PDF、更广 validation 与 Studio Publish authoring/preview。",
      },
      docs: {
        eyebrow: "Documentation",
        title: "想深入时再读 Contract；不想深入时先理解产品。",
        lede: "这个公开站点不会替代 repository docs。下面所有入口都指向维护中的 source-of-truth 文档。",
        cards: [
          { eyebrow: "Start", title: "Docs Home", body: "按任务进入 Architecture、Runtime、Quality、Project、Studio 与 Release truth。", meta: "docs/README.zh-CN.md" },
          { eyebrow: "Core", title: "Architecture Atlas", body: "Subsystem map + contract-oriented architecture reference。", meta: "docs/architecture-atlas.zh-CN.md" },
          { eyebrow: "Production", title: "Production Pipeline", body: "从 Context Freeze / Simulation 到 User-visible Review / Settlement boundary。", meta: "docs/production-pipeline.zh-CN.md" },
          { eyebrow: "Quality", title: "Quality Assurance", body: "Surface、Reader Engagement、Continuity、semantic gate semantics。", meta: "docs/quality-assurance.zh-CN.md" },
          { eyebrow: "Product", title: "Studio Architecture", body: "Creator/Inspector、portable hosts、SolidJS/WeiUI foundation 与 current gaps。", meta: "studio/PRODUCT_ARCHITECTURE.zh-CN.md" },
          { eyebrow: "Release", title: "0.8.x Development Inventory", body: "哪些已经 merged、哪些仍 open、哪些绝不能冒充 shipped。", meta: "docs/8-0-development-inventory.zh-CN.md" },
        ],
      },
      changelog: {
        eyebrow: "Release truth",
        title: "一份会把 implementation 和 aspiration 分开的 Changelog。",
        lede: "NovelForge 仍是 pre-1.0。当前 ledger 只记录已经 merged 的 machine/product behavior，并把剩余 Core/Product gap 明确留在 open，而不是把 roadmap 偷偷升格成 capability。",
        cards: [
          { title: "0.8.0 identity", body: "Manifest、CLI、Skill、Project SDK default、MCP metadata 与 documentation governance 共用一个 pre-1.0 development identity。" },
          { title: "Breaking cleanup 仍可能发生", body: "1.0 前，只要架构有充分理由并有 deterministic CI，machine-contract cleanup 仍可以进入 latest main。" },
          { title: "历史保持历史", body: "旧 7.x changelog/spec 保留原始语义；当前 docs 不会为了让新 naming 看起来“从来如此”而倒写历史。" },
        ],
      },
    } satisfies Record<string, RouteCopy>,
  },
} as const;

export const githubRoot = "https://github.com/xiaooye/cn_webnovel_agent";

export function sourceUrl(path: string): string {
  return `${githubRoot}/blob/main/${path}`;
}
