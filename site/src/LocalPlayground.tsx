import { For, Show, createMemo, createSignal } from "solid-js";
import type { Locale } from "./content";

type PlaygroundMode = "DRAFT" | "REVISE" | "AUDIT" | "PLAN-CHAPTER";

type TracePreset = {
  mode: PlaygroundMode;
  purposeZh: string;
  purposeEn: string;
  context: string[];
  contracts: string[];
  execution: string[];
  evidence: string[];
  resultZh: string;
  resultEn: string;
};

type Props = { locale: Locale };

const presets: Record<PlaygroundMode, TracePreset> = {
  DRAFT: {
    mode: "DRAFT",
    purposeZh: "从冻结上下文进入场景模拟、人物行动与 event-first raw draft 之前的执行预览。",
    purposeEn: "Preview the path from frozen context into scene simulation, character action, and event-first raw drafting.",
    context: ["accepted canon", "active plan", "character knowledge", "scene pressure", "selected prose profile"],
    contracts: ["context.select", "character.action_propose", "scene.resolve_actions"],
    execution: ["Context Freeze", "Story / Canon Preflight", "Scene Simulation", "Character Simulation", "Raw Draft boundary"],
    evidence: ["source-bound context", "character knowledge bounds", "causal action proposals", "scene resolution trace"],
    resultZh: "准备一个受边界约束的 DRAFT 运行输入；不会在这个浏览器 demo 中生成或接受正文。",
    resultEn: "Prepare a bounded DRAFT run input; this browser demo does not generate or accept manuscript prose.",
  },
  REVISE: {
    mode: "REVISE",
    purposeZh: "把现稿问题路由回真正 owning layer，并比较 repair candidate，而不是默认句子润色。",
    purposeEn: "Route draft failures back to the owning layer and compare repair candidates instead of defaulting to sentence polish.",
    context: ["current candidate", "accepted canon", "reader pressure", "character agenda", "known findings"],
    contracts: ["revision.diagnose", "reader.engagement_audit", "character.integrity", "quality.compare"],
    execution: ["Candidate Freeze", "Failure Diagnosis", "Owning-layer Routing", "Repair Candidate", "Comparison Gate"],
    evidence: ["diagnostic findings", "reader-impact evidence", "character-integrity evidence", "incumbent / challenger comparison"],
    resultZh: "形成 revision diagnosis 的示例 trace；不把“改了”自动等同于“更好”。",
    resultEn: "Produce an example revision-diagnosis trace without treating a change as automatic improvement.",
  },
  AUDIT: {
    mode: "AUDIT",
    purposeZh: "展示独立质量审查会读取什么、产生什么 evidence，以及为什么 semantic result 本身不授予 authority。",
    purposeEn: "Show what an independent quality audit consumes and emits, and why semantic results never grant authority by themselves.",
    context: ["candidate artifact", "quality rubric", "explicit commitments", "canon references", "publication gate"],
    contracts: ["quality.production_review", "reader.engagement_audit", "continuity.commitment_audit"],
    execution: ["Artifact Fingerprint", "Independent Review Boundary", "Semantic Findings", "Gate Evaluation", "No automatic settlement"],
    evidence: ["fingerprint-bound review", "reader findings", "commitment audit", "gate rationale"],
    resultZh: "得到一个 mock audit envelope；它可以提供证据，但不能自己改变 Canon 或 publication state。",
    resultEn: "Return a mock audit envelope that can carry evidence but cannot mutate Canon or publication state.",
  },
  "PLAN-CHAPTER": {
    mode: "PLAN-CHAPTER",
    purposeZh: "展示章节规划如何利用稀疏上下文与长期约束，同时保留因果分叉空间。",
    purposeEn: "Preview chapter planning with sparse context and long-horizon constraints while preserving causal alternatives.",
    context: ["book / volume direction", "active plan", "open commitments", "character agendas", "recent state delta"],
    contracts: ["context.select", "plan.reconcile", "scene.diverge"],
    execution: ["Goal Boundary", "Context Selection", "Plan Reconciliation", "Causal Alternatives", "Plan Proposal"],
    evidence: ["active-plan sources", "commitment constraints", "divergent scenario options", "proposal provenance"],
    resultZh: "产生一个非 Canon 的计划提案 trace；只有显式接受与 settlement 才可能改变 durable state。",
    resultEn: "Produce a non-Canon planning proposal trace; only explicit acceptance and settlement may change durable state.",
  },
};

function stableFingerprint(value: string) {
  let hashA = 0x811c9dc5;
  let hashB = 0x9e3779b9;
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    hashA ^= code;
    hashA = Math.imul(hashA, 0x01000193);
    hashB ^= code + index;
    hashB = Math.imul(hashB, 0x85ebca6b);
  }
  return `${(hashA >>> 0).toString(16).padStart(8, "0")}${(hashB >>> 0).toString(16).padStart(8, "0")}`;
}

export default function LocalPlayground(props: Props) {
  const [mode, setMode] = createSignal<PlaygroundMode>("DRAFT");
  const [source, setSource] = createSignal("");
  const [ran, setRan] = createSignal(false);
  const zh = () => props.locale === "zh-CN";
  const preset = createMemo(() => presets[mode()]);
  const compactSource = createMemo(() => source().trim());
  const inputFingerprint = createMemo(() => stableFingerprint(`${mode()}\n${compactSource()}`));
  const blocks = createMemo(() => compactSource() ? compactSource().split(/\n\s*\n/).filter(Boolean).length : 0);
  const ready = createMemo(() => compactSource().length >= 40);

  const text = createMemo(() => zh() ? {
    eyebrow: "Local Playground · Deterministic Preview",
    title: "先把 NovelForge 的运行过程变成可以玩的东西。",
    lede: "输入一段文本，选择真实 task mode，然后在浏览器里查看一个确定性的 execution trace。这里不调用模型、不做 semantic routing，也不写入任何 Project state。",
    input: "工作文本",
    placeholder: "贴一段场景、章节计划、现稿或审阅对象……\n\n这个 playground 只用它来构造可重复的演示 trace。",
    mode: "Task mode",
    run: "生成演示 trace",
    reset: "清空",
    privacy: "纯本地 · 0 model calls",
    trace: "Execution trace",
    notRun: "输入至少 40 个字符，再生成一个本地演示 trace。",
    short: "输入还太短；可以预览结构，但不会标记为 prepared。",
    prepared: "Demo input prepared",
    context: "Context Manifest",
    contracts: "Contract candidates",
    execution: "Execution",
    evidence: "Evidence",
    result: "Result",
    chars: "字符",
    blocks: "段落",
    fingerprint: "Demo fingerprint",
    boundary: "这些 contract 只是当前 mode 的示例候选，不是 deterministic router 的真实选择。NovelForge 的 semantic contract activation 仍由 model / manager 决定，exact contract ID resolution 才由确定性 runtime 完成。",
    resultBoundary: "此结果没有 Canon write、publication、settlement 或 durable-state authority。",
  } : {
    eyebrow: "Local Playground · Deterministic Preview",
    title: "Make the NovelForge execution path something you can actually play with.",
    lede: "Paste working text, choose a real task mode, and inspect a deterministic execution trace in the browser. No model call, no semantic routing, and no Project-state write occurs here.",
    input: "Working text",
    placeholder: "Paste a scene, chapter plan, current draft, or review target…\n\nThe playground uses it only to construct a reproducible demo trace.",
    mode: "Task mode",
    run: "Generate demo trace",
    reset: "Clear",
    privacy: "Local only · 0 model calls",
    trace: "Execution trace",
    notRun: "Enter at least 40 characters, then generate a local demo trace.",
    short: "The input is still short; the structure can be previewed but will not be marked prepared.",
    prepared: "Demo input prepared",
    context: "Context Manifest",
    contracts: "Contract candidates",
    execution: "Execution",
    evidence: "Evidence",
    result: "Result",
    chars: "Characters",
    blocks: "Blocks",
    fingerprint: "Demo fingerprint",
    boundary: "These contracts are illustrative candidates for the selected mode, not the output of a deterministic semantic router. NovelForge contract activation remains model / manager owned; deterministic runtime resolves exact contract IDs.",
    resultBoundary: "This result carries no Canon-write, publication, settlement, or durable-state authority.",
  });

  const execute = () => setRan(true);
  const clear = () => { setSource(""); setRan(false); };

  return (
    <div class="playground-shell">
      <section class="playground-intro">
        <div>
          <p class="eyebrow">{text().eyebrow}</p>
          <h1>{text().title}</h1>
          <p>{text().lede}</p>
        </div>
        <span class="wui-badge wui-badge--success playground-local-badge">⌁ {text().privacy}</span>
      </section>

      <div class="playground-workspace">
        <section class="wui-card playground-input-panel">
          <div class="playground-mode-row">
            <div><p class="eyebrow">{text().mode}</p><strong>{preset().mode}</strong></div>
            <div class="playground-mode-tabs" role="group" aria-label={text().mode}>
              <For each={Object.keys(presets) as PlaygroundMode[]}>{(item) => (
                <button type="button" data-active={mode() === item} onClick={() => { setMode(item); setRan(false); }}>{item}</button>
              )}</For>
            </div>
          </div>
          <p class="playground-purpose">{zh() ? preset().purposeZh : preset().purposeEn}</p>
          <label class="playground-input-label" for="playground-source">{text().input}</label>
          <textarea
            id="playground-source"
            value={source()}
            onInput={(event) => { setSource(event.currentTarget.value); setRan(false); }}
            placeholder={text().placeholder}
            spellcheck="false"
          />
          <div class="playground-input-meta">
            <span>{text().chars} <strong>{compactSource().length}</strong></span>
            <span>{text().blocks} <strong>{blocks()}</strong></span>
            <span>{text().fingerprint} <code>{inputFingerprint()}</code></span>
          </div>
          <div class="playground-actions">
            <button type="button" class="wui-button wui-button--solid" disabled={!compactSource()} onClick={execute}>▶ {text().run}</button>
            <button type="button" class="wui-button wui-button--soft" disabled={!compactSource()} onClick={clear}>{text().reset}</button>
          </div>
        </section>

        <section class="wui-card playground-trace-panel">
          <div class="playground-trace-heading">
            <div><p class="eyebrow">{text().trace}</p><h2>{mode()}</h2></div>
            <span class="playground-prepared" data-ready={ran() && ready()}>{ran() && ready() ? "✓ " + text().prepared : "○ deterministic mock"}</span>
          </div>

          <Show when={ran()} fallback={<div class="playground-empty-trace"><span aria-hidden="true">⌁</span><p>{text().notRun}</p></div>}>
            <Show when={!ready()}><p class="playground-short-note">{text().short}</p></Show>
            <div class="playground-trace-flow">
              <article class="playground-stage">
                <header><span>01</span><strong>{text().context}</strong></header>
                <ul><For each={preset().context}>{(item) => <li>{item}</li>}</For></ul>
              </article>
              <article class="playground-stage">
                <header><span>02</span><strong>{text().contracts}</strong></header>
                <ul class="playground-contract-list"><For each={preset().contracts}>{(item) => <li><code>{item}</code></li>}</For></ul>
              </article>
              <article class="playground-stage">
                <header><span>03</span><strong>{text().execution}</strong></header>
                <ol><For each={preset().execution}>{(item) => <li>{item}</li>}</For></ol>
              </article>
              <article class="playground-stage">
                <header><span>04</span><strong>{text().evidence}</strong></header>
                <ul><For each={preset().evidence}>{(item) => <li>{item}</li>}</For></ul>
              </article>
              <article class="playground-stage playground-stage--result">
                <header><span>05</span><strong>{text().result}</strong></header>
                <p>{zh() ? preset().resultZh : preset().resultEn}</p>
                <div class="playground-result-envelope">
                  <code>{`{ mode: "${mode()}", status: "${ready() ? "prepared" : "needs_input"}", fingerprint: "${inputFingerprint()}" }`}</code>
                </div>
              </article>
            </div>
            <p class="playground-contract-boundary">{text().boundary}</p>
            <p class="playground-authority-boundary">⚑ {text().resultBoundary}</p>
          </Show>
        </section>
      </div>
    </div>
  );
}
