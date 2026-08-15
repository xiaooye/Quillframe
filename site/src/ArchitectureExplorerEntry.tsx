import { For, Show, createEffect, createMemo, createSignal } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import type { Locale } from "./content";

type Props = { initialLocale: Locale };
type Lane = "project" | "runtime" | "evidence" | "editorial" | "validated";

type ArchitectureNode = {
  id: string;
  icon: string;
  lane: Lane;
  title: string;
  titleZh: string;
  summary: string;
  summaryZh: string;
  inputs: string[];
  inputsZh: string[];
  outputs: string[];
  outputsZh: string[];
  authority: string;
  authorityZh: string;
  contracts: string[];
  persisted: string;
  persistedZh: string;
};

const nodes: ArchitectureNode[] = [
  {
    id: "project",
    icon: "⌂",
    lane: "project",
    title: "Project",
    titleZh: "Project",
    summary: "Resolve the project-owned identity, exact framework lock, and logical domains before execution begins.",
    summaryZh: "先解析项目自己拥有的身份、精确 Framework lock 与逻辑域，再允许执行继续。",
    inputs: ["novelforge.toml", "novelforge.lock.json", "framework.attestation.json", "project logical domains"],
    inputsZh: ["novelforge.toml", "novelforge.lock.json", "framework.attestation.json", "项目逻辑域"],
    outputs: ["project identity", "framework identity", "adapter/domain resolution"],
    outputsZh: ["项目身份", "Framework identity", "adapter / logical-domain resolution"],
    authority: "Project-owned files remain the authority. The browser visualization is read-only.",
    authorityZh: "项目自有文件继续拥有权威；这个浏览器可视化只读，不产生 Project authority。",
    contracts: ["novelforge_project_adapter_resolution_v1"],
    persisted: "Project files, lock, and optional attestation remain in the project itself.",
    persistedZh: "Project 文件、lock 与可选 attestation 仍留在项目自身。",
  },
  {
    id: "manager",
    icon: "✦",
    lane: "runtime",
    title: "Manager",
    titleZh: "Manager",
    summary: "Own operational coordination: session/run identity, checkpoints, routing, and control-plane lineage.",
    summaryZh: "负责运行协调：Session / Run identity、checkpoint、routing 与 Control Plane lineage。",
    inputs: ["resolved project", "explicit task intent", "host capability evidence"],
    inputsZh: ["已解析 Project", "显式 task intent", "宿主 capability evidence"],
    outputs: ["session/run identity", "checkpoint boundary", "eligible execution path"],
    outputsZh: ["Session / Run identity", "checkpoint 边界", "符合条件的执行路径"],
    authority: "Operational coordination is not Canon authority and capability is not authority.",
    authorityZh: "运行协调不等于 Canon authority；capability 也不等于 authority。",
    contracts: ["Session / Run identity", "Control Plane", "novelforge_host_capabilities_v1"],
    persisted: "Core may persist checkpoint, event, handoff, and receipt lineage through its public control-plane contracts.",
    persistedZh: "Core 可通过公开 Control Plane contracts 持久化 checkpoint、event、handoff 与 receipt lineage。",
  },
  {
    id: "context",
    icon: "🫧",
    lane: "evidence",
    title: "Context",
    titleZh: "Context",
    summary: "Select a sparse, authority-aware working set and distinguish support from what actually entered the model packet.",
    summaryZh: "选择稀疏、带 authority 的工作集，并区分“被认为有帮助”与“真的进入 model packet”。",
    inputs: ["eligible sources", "stage visibility", "hard context budget"],
    inputsZh: ["eligible sources", "stage visibility", "hard context budget"],
    outputs: ["context view", "loaded support", "dropped / visibility-excluded evidence"],
    outputsZh: ["Context view", "实际 loaded support", "dropped / visibility-excluded evidence"],
    authority: "Context selection and overlays are working evidence; they do not silently become Canon.",
    authorityZh: "Context selection 与 overlay 是工作证据，不会静默升级成 Canon。",
    contracts: ["novelforge_context_inspector_v2", "novelforge_run_receipt_v1"],
    persisted: "Receipts may persist metadata about loading decisions; Studio must not invent a hidden full-context dump.",
    persistedZh: "Receipt 可以持久化加载决策的 metadata；Studio 不会虚构隐藏的 full-context dump。",
  },
  {
    id: "worker",
    icon: "⌘",
    lane: "editorial",
    title: "Worker",
    titleZh: "Worker",
    summary: "Execute a typed semantic contract against the visible inputs and return inspectable result identity.",
    summaryZh: "针对明确可见的输入执行 typed semantic contract，并返回可检查的 result identity。",
    inputs: ["typed task", "visible context", "selected contract"],
    inputsZh: ["typed task", "可见 Context", "selected contract"],
    outputs: ["typed result", "input/result fingerprint", "worker reference / status"],
    outputsZh: ["typed result", "input / result fingerprint", "worker reference / status"],
    authority: "A worker result is evidence. It does not grant framework-write, settlement, or Canon authority by itself.",
    authorityZh: "Worker result 是 evidence；它自身不授予 Framework write、Settlement 或 Canon authority。",
    contracts: ["semantic contract catalog", "typed semantic status / fingerprint"],
    persisted: "Execution evidence can be recorded without persisting private chain-of-thought.",
    persistedZh: "可以记录 execution evidence，而不持久化 private chain-of-thought。",
  },
  {
    id: "gate",
    icon: "✓",
    lane: "validated",
    title: "Gate",
    titleZh: "Gate",
    summary: "Conjoin the required evidence for one exact candidate fingerprint and explain pass, fail, or pending state.",
    summaryZh: "围绕同一个 exact candidate fingerprint 汇合必要证据，并解释 pass / fail / pending。",
    inputs: ["exact candidate fingerprint", "deterministic checks", "semantic review evidence"],
    inputsZh: ["exact candidate fingerprint", "deterministic checks", "semantic review evidence"],
    outputs: ["gate statuses", "blocking evidence", "readiness explanation"],
    outputsZh: ["gate statuses", "blocking evidence", "readiness explanation"],
    authority: "Production readiness is gate evidence, not a literary score and not Canon acceptance.",
    authorityZh: "Production readiness 是 gate evidence，不是文学分数，也不是 Canon acceptance。",
    contracts: ["novelforge_production_readiness_v1"],
    persisted: "Gate evidence stays tied to the exact candidate fingerprint it evaluated.",
    persistedZh: "Gate evidence 必须继续绑定到它实际评估的 exact candidate fingerprint。",
  },
  {
    id: "settlement",
    icon: "◇",
    lane: "evidence",
    title: "Settlement",
    titleZh: "Settlement",
    summary: "Apply eligible accepted changes through Core-owned settlement semantics and preserve the transaction receipt.",
    summaryZh: "通过 Core 拥有的 settlement semantics 应用符合条件的 accepted change，并保留 transaction receipt。",
    inputs: ["accepted decision", "eligible state changes", "provenance / evidence refs"],
    inputsZh: ["accepted decision", "eligible state changes", "provenance / evidence refs"],
    outputs: ["settlement receipt", "committed state transition"],
    outputsZh: ["settlement receipt", "已提交 state transition"],
    authority: "Core owns settlement semantics. UI and preview surfaces cannot infer or manufacture settlement authority.",
    authorityZh: "Settlement semantics 由 Core 拥有；UI 与 preview surface 不能推断或制造 settlement authority。",
    contracts: ["settlement receipts", "Control Plane lineage"],
    persisted: "The authoritative receipt and resulting accepted state are Core/project concerns, not browser-local UI state.",
    persistedZh: "权威 receipt 与 resulting accepted state 属于 Core / Project，不属于 browser-local UI state。",
  },
  {
    id: "publication",
    icon: "📖",
    lane: "validated",
    title: "Publication",
    titleZh: "Publication",
    summary: "Compile accepted manuscript text deterministically into derived publication artifacts with provenance.",
    summaryZh: "把 Accepted manuscript text 确定性编译为带 provenance 的派生出版产物。",
    inputs: ["Accepted manuscript text", "publication profile"],
    inputsZh: ["Accepted manuscript text", "publication profile"],
    outputs: ["clean text", "Web HTML", "print-oriented HTML/CSS", "EPUB 3.3"],
    outputsZh: ["clean text", "Web HTML", "print-oriented HTML / CSS", "EPUB 3.3"],
    authority: "Publication output is derived (authority=false) and must preserve the accepted manuscript text exactly.",
    authorityZh: "Publication output 是 derived artifact（authority=false），并必须精确保留 Accepted manuscript text。",
    contracts: ["novelforge_publication_ir_v1", "publication/compiler.py"],
    persisted: "Derived build artifacts and provenance can be retained without becoming a second manuscript truth model.",
    persistedZh: "可以保留 derived build artifacts 与 provenance，但不会形成第二套 manuscript truth model。",
  },
];

function initialDark() {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export default function ArchitectureExplorerEntry(props: Props) {
  const [locale, setLocale] = createSignal<Locale>(props.initialLocale);
  const [dark, setDark] = createSignal(initialDark());
  const [selected, setSelected] = createSignal(0);
  const [runStep, setRunStep] = createSignal(-1);
  const zh = () => locale() === "zh-CN";
  const current = createMemo(() => nodes[selected()]);

  createEffect(() => {
    document.documentElement.lang = zh() ? "zh-CN" : "en";
    document.documentElement.dataset.locale = locale();
    document.documentElement.classList.toggle("dark", dark());
    localStorage.setItem("novelforge.locale", locale());
    localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
  });

  const startRun = () => {
    setRunStep(0);
    setSelected(0);
  };

  const nextRun = () => {
    if (runStep() < 0) return startRun();
    const next = Math.min(nodes.length - 1, runStep() + 1);
    setRunStep(next);
    setSelected(next);
  };

  const resetRun = () => setRunStep(-1);

  const runState = (index: number) => runStep() < 0
    ? "idle"
    : index < runStep()
      ? "complete"
      : index === runStep()
        ? "current"
        : "pending";

  const selectNode = (index: number) => setSelected(index);

  return (
    <div class="site-shell product-entry architecture-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <a href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </a>
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "架构导航" : "Architecture navigation"}>
          <a class="wui-app-bar__link" href="/">{zh() ? "产品" : "Product"}</a>
          <a class="wui-app-bar__link" href="/inspect">{zh() ? "检查项目" : "Inspect"}</a>
          <a class="wui-app-bar__link" href="/playground">Playground</a>
          <a class="wui-app-bar__link active" href="/architecture" aria-current="page">{zh() ? "架构" : "Architecture"}</a>
          <a class="wui-app-bar__link" href={zh() ? "/docs/architecture" : "/docs/en/architecture"}>{zh() ? "精确文档" : "Exact docs"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href="https://studio.novelforge.wei-dev.com" target="_blank" rel="noreferrer">✦ Studio</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact architecture-main">
        <section class="architecture-intro">
          <div>
            <div class="architecture-badges"><span class="wui-badge wui-badge--soft">INTERACTIVE ARCHITECTURE</span><span class="wui-badge wui-badge--outline">authority=false</span></div>
            <h1>{zh() ? "看一条 NovelForge 运行怎样穿过整个系统。" : "See how one NovelForge run moves through the system."}</h1>
            <p>{zh() ? "Project → Manager → Context → Worker → Gate → Settlement → Publication。点任意节点查看输入、输出、authority、contracts 与可持久化边界；也可以手动模拟一条 run。" : "Project → Manager → Context → Worker → Gate → Settlement → Publication. Select a node to inspect inputs, outputs, authority, contracts, and persistence boundaries, or step through a deterministic run preview."}</p>
          </div>
          <div class="architecture-intro-actions">
            <a class="wui-button wui-button--soft" href={zh() ? "/docs/architecture" : "/docs/en/architecture"}>📚 {zh() ? "阅读架构文档" : "Read architecture docs"}</a>
            <a class="wui-button wui-button--ghost" href="/playground">✦ Playground</a>
          </div>
        </section>

        <section class="wui-card architecture-canvas" aria-label={zh() ? "NovelForge 架构流程" : "NovelForge architecture flow"}>
          <div class="architecture-toolbar">
            <div>
              <small>{zh() ? "可观察执行路径" : "OBSERVABLE EXECUTION PATH"}</small>
              <strong>{runStep() < 0 ? (zh() ? "选择节点，或开始模拟" : "Select a node or start a preview") : `${String(runStep() + 1).padStart(2, "0")} / ${String(nodes.length).padStart(2, "0")} · ${zh() ? nodes[runStep()].titleZh : nodes[runStep()].title}`}</strong>
            </div>
            <div class="architecture-run-actions">
              <button class="wui-button wui-button--solid" type="button" onClick={runStep() < 0 ? startRun : nextRun} disabled={runStep() === nodes.length - 1}>{runStep() < 0 ? (zh() ? "模拟一次 run" : "Simulate a run") : (zh() ? "下一步" : "Next step")}</button>
              <button class="wui-button wui-button--ghost" type="button" onClick={resetRun} disabled={runStep() < 0}>{zh() ? "重置" : "Reset"}</button>
            </div>
          </div>

          <div class="architecture-flow" role="list">
            <For each={nodes}>{(node, index) => (
              <button
                type="button"
                role="listitem"
                class="architecture-node"
                data-lane={node.lane}
                data-active={selected() === index() ? "true" : undefined}
                data-run-state={runState(index())}
                onClick={() => selectNode(index())}
                aria-pressed={selected() === index()}
              >
                <span class="architecture-node-step">{String(index() + 1).padStart(2, "0")}</span>
                <span class="architecture-node-icon" aria-hidden="true">{node.icon}</span>
                <span class="architecture-node-copy"><strong>{zh() ? node.titleZh : node.title}</strong><small>{zh() ? node.summaryZh : node.summary}</small></span>
                <span class="architecture-node-status" aria-hidden="true">{runState(index()) === "complete" ? "✓" : runState(index()) === "current" ? "●" : "→"}</span>
              </button>
            )}</For>
          </div>
        </section>

        <section class="architecture-inspector-grid">
          <article class="wui-card architecture-detail" data-lane={current().lane}>
            <header class="architecture-detail-head">
              <div class="architecture-detail-icon" aria-hidden="true">{current().icon}</div>
              <div><small>{zh() ? "当前节点" : "SELECTED NODE"}</small><h2>{zh() ? current().titleZh : current().title}</h2><p>{zh() ? current().summaryZh : current().summary}</p></div>
            </header>

            <div class="architecture-detail-grid">
              <section><span>{zh() ? "输入" : "Inputs"}</span><ul><For each={zh() ? current().inputsZh : current().inputs}>{(item) => <li>{item}</li>}</For></ul></section>
              <section><span>{zh() ? "输出" : "Outputs"}</span><ul><For each={zh() ? current().outputsZh : current().outputs}>{(item) => <li>{item}</li>}</For></ul></section>
              <section class="architecture-authority"><span>Authority</span><p>{zh() ? current().authorityZh : current().authority}</p></section>
              <section><span>Contracts</span><div class="architecture-contracts"><For each={current().contracts}>{(item) => <code>{item}</code>}</For></div></section>
              <section class="architecture-persisted"><span>{zh() ? "持久化边界" : "Persistence boundary"}</span><p>{zh() ? current().persistedZh : current().persisted}</p></section>
            </div>
          </article>

          <aside class="wui-card architecture-run-evidence">
            <div class="architecture-run-head"><div><small>{zh() ? "模拟 trace" : "PREVIEW TRACE"}</small><h2>{zh() ? "只展示公开可观察边界" : "Public observable boundaries only"}</h2></div><span class="wui-badge wui-badge--outline">deterministic</span></div>
            <p>{zh() ? "这里不是一次真实 Core execution，不调用模型、不写 Canon，也不会推断 private runtime state。它只是把公开 contract 允许产品看到的数据流串起来。" : "This is not a real Core execution. It makes no model call, writes no Canon, and infers no private runtime state. It only connects the data flow exposed by public contracts."}</p>
            <ol class="architecture-trace-list">
              <For each={nodes}>{(node, index) => (
                <li data-state={runState(index())}>
                  <span>{runState(index()) === "complete" ? "✓" : runState(index()) === "current" ? "●" : String(index() + 1).padStart(2, "0")}</span>
                  <div><strong>{zh() ? node.titleZh : node.title}</strong><small>{runState(index()) === "complete" ? (zh() ? "边界已经过" : "boundary traversed") : runState(index()) === "current" ? (zh() ? "当前边界" : "current boundary") : (zh() ? "等待" : "pending")}</small></div>
                </li>
              )}</For>
            </ol>
            <Show when={runStep() === nodes.length - 1}>
              <div class="architecture-run-complete"><span>✦</span><div><strong>{zh() ? "模拟完成" : "Preview complete"}</strong><small>{zh() ? "最终产物仍然是 derived publication，不会反向成为 Canon。" : "The final publication remains derived and does not become Canon by flowing backward."}</small></div></div>
            </Show>
          </aside>
        </section>
      </main>

      <footer class="site-footer architecture-footer">
        <div class="page-width footer-grid">
          <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{zh() ? "UI consumes Core state. UI does not invent Core state. ✦" : "UI consumes Core state. UI does not invent Core state. ✦"}</p></div>
          <div class="footer-links"><a href="/inspect">{zh() ? "检查项目" : "Inspect project"}</a><a href="/playground">Local Playground</a></div>
          <div class="footer-links"><a href={zh() ? "/docs/architecture" : "/docs/en/architecture"}>{zh() ? "精确架构文档" : "Exact architecture docs"}</a><a href="/">{zh() ? "返回产品站" : "Back to product"}</a></div>
        </div>
      </footer>
    </div>
  );
}
