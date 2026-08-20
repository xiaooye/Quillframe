import { For, Show, createMemo, createSignal, onCleanup } from "solid-js";
import type { Locale } from "./content";
import { captureWorkerErrorOwnership, createRestartableWorker, createSingleFlight, isCurrentWorkerEvent, validateQuickDemoReceipt } from "./workerLifecycle";

type QuickDemoReceipt = {
  schema: "quillframe_ch001_quick_demo_receipt_v1";
  chapter_id: "CH001";
  deterministic_core: {
    executed: true;
    modules: string[];
    packet_fingerprint: string;
    workflow_fingerprint: string;
    stage: string;
  };
  semantic_evidence: {
    source: "recorded_fixture";
    live_model_called: false;
    summary: string;
    findings: Array<{ code: string; severity: string; owner: string }>;
  };
  live_model_called: false;
  uploads: 0;
  canon_mutated: false;
  authority: false;
};

type WorkerResponse =
  | { kind: "ready"; pyodide_version: string }
  | { kind: "result"; id: string; receipt: string }
  | { kind: "error"; id: string; error: string };

export default function QuickDemo(props: { locale: Locale }) {
  const [state, setState] = createSignal<"idle" | "loading" | "ready" | "error">("idle");
  const [runtimeVersion, setRuntimeVersion] = createSignal<string>();
  const [receipt, setReceipt] = createSignal<QuickDemoReceipt>();
  const [error, setError] = createSignal<string>();
  const lifecycle = createRestartableWorker<{ kind: "run"; id: string }>(() => new Worker(new URL("./quickDemo.worker.ts", import.meta.url), { type: "module" }));
  const flight = createSingleFlight<void>();
  let workerLease: ReturnType<typeof lifecycle.acquire> | undefined;
  let disposed = false;
  const zh = () => props.locale === "zh-CN";
  const packetShort = createMemo(() => receipt()?.deterministic_core.packet_fingerprint.slice(0, 22));

  const labels = () => zh() ? {
    eyebrow: "QUICK WORKING DEMO · CH001",
    title: "不是动画：让真正的确定性 Core 在浏览器里跑一次。",
    lede: "点击一次，Web Worker 会在本地 Pyodide 中加载 Quillframe 的工作流与生成契约源码，构造 CH001 generation packet，并核对稳定指纹。语义证据来自明确标注的录制夹具，不会伪装成实时模型调用。",
    run: "运行 CH001 演示",
    running: "正在启动本地 Core…",
    rerun: "再次验证",
    deterministic: "Deterministic Core",
    semantic: "Recorded semantic evidence",
    upload: "0 uploads",
    account: "无需账号 / API key",
    before: "点击运行后，这里会显示 Core receipt、生成包指纹和录制语义证据。所有执行都停留在浏览器内。",
    core: "真实 Core 执行",
    evidence: "录制语义证据",
    boundary: "真实性边界",
    boundaryBody: "确定性 packet/workflow 是这次实时执行；语义摘要是固定夹具。两者都 authority=false，不写 Canon、不发布、不结算。",
  } : {
    eyebrow: "QUICK WORKING DEMO · CH001",
    title: "Not an animation: run the real deterministic Core in your browser.",
    lede: "One click loads Quillframe's workflow and generation-contract source into local Pyodide inside a Web Worker, constructs a CH001 generation packet, and verifies stable fingerprints. Semantic evidence is a clearly labelled recording, never presented as a live model call.",
    run: "Run the CH001 demo",
    running: "Starting the local Core…",
    rerun: "Verify again",
    deterministic: "Deterministic Core",
    semantic: "Recorded semantic evidence",
    upload: "0 uploads",
    account: "No account / API key",
    before: "Run it to inspect the Core receipt, generation-packet fingerprint, and recorded semantic evidence. Execution stays in this browser.",
    core: "Real Core execution",
    evidence: "Recorded semantic evidence",
    boundary: "Truth boundary",
    boundaryBody: "The deterministic packet/workflow is executed now; the semantic summary is a fixed fixture. Both are authority=false and cannot write Canon, publish, or settle.",
  };

  const worker = () => {
    workerLease ??= lifecycle.acquire();
    const lease = workerLease;
    lease.worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;
      if (disposed || !lifecycle.isCurrent(lease)) return;
      if (message.kind === "ready") {
        setRuntimeVersion(message.pyodide_version);
        return;
      }
      if (!isCurrentWorkerEvent({ disposed, lifecycle, lease, flight, token: activeRequestToken, requestId: activeRequestId, eventId: message.id })) return;
      if (message.kind === "error") {
        lifecycle.invalidate(lease);
        workerLease = undefined;
        flight.reject(activeRequestToken, new Error(message.error));
        flight.finish(activeRequestToken);
        setError(message.error);
        setState("error");
        return;
      }
      try {
        const parsed = JSON.parse(message.receipt) as QuickDemoReceipt;
        if (!validateQuickDemoReceipt(parsed)) throw new Error("Unexpected demo receipt");
        setReceipt(parsed);
        setState("ready");
        flight.resolve(activeRequestToken, undefined);
      } catch (value) {
        lifecycle.invalidate(lease);
        workerLease = undefined;
        flight.reject(activeRequestToken, value);
        setError(value instanceof Error ? value.message : String(value));
        setState("error");
      }
      flight.finish(activeRequestToken);
    };
    lease.worker.onerror = (event) => {
      if (disposed || !lifecycle.isCurrent(lease)) return;
      const ownsActiveRequest = captureWorkerErrorOwnership({ disposed, lifecycle, lease, flight, token: activeRequestToken, requestId: activeRequestId, eventId: activeRequestId });
      lifecycle.invalidate(lease);
      workerLease = undefined;
      if (!ownsActiveRequest) return;
      flight.reject(activeRequestToken, new Error(event.message || "Quick Demo Worker failed"));
      flight.finish(activeRequestToken);
      setError(event.message || "Quick Demo Worker failed");
      setState("error");
    };
    return lease;
  };

  let activeRequestId = "";
  let activeRequestToken: symbol = Symbol("no-request");
  const run = () => {
    if (disposed) return;
    const started = flight.tryBegin();
    if (!started.accepted) {
      setError(started.error.message);
      return;
    }
    setError(undefined);
    setState("loading");
    activeRequestToken = started.flight.token;
    activeRequestId = crypto.randomUUID();
    try {
      worker().post({ kind: "run", id: activeRequestId });
    } catch (value) {
      if (workerLease) lifecycle.invalidate(workerLease);
      workerLease = undefined;
      flight.reject(activeRequestToken, value);
      flight.finish(activeRequestToken);
      setError(value instanceof Error ? value.message : String(value));
      setState("error");
    }
    void started.flight.promise.catch(() => undefined);
  };

  onCleanup(() => {
    disposed = true;
    flight.dispose(new Error("Quick Demo closed"));
    lifecycle.dispose(new Error("Quick Demo closed"));
  });

  return (
    <section id="quick-demo" class="quick-demo section-pad-soft" data-home-section="demo" aria-labelledby="quick-demo-title">
      <div class="page-width quick-demo-grid">
        <div class="quick-demo-copy">
          <p class="eyebrow">{labels().eyebrow}</p>
          <h2 id="quick-demo-title">{labels().title}</h2>
          <p>{labels().lede}</p>
          <div class="quick-demo-truth-row" aria-label={zh() ? "演示真实性标签" : "Demo truth labels"}>
            <For each={[labels().deterministic, labels().semantic, labels().upload, labels().account]}>{(item) => <span>{item}</span>}</For>
          </div>
          <button class="wui-button wui-button--solid wui-button--xl quick-demo-run" type="button" disabled={state() === "loading"} onClick={run}>
            <span aria-hidden="true">{state() === "loading" ? "◌" : "▶"}</span>
            {state() === "loading" ? labels().running : receipt() ? labels().rerun : labels().run}
          </button>
        </div>

        <div class="wui-card quick-demo-receipt" aria-live="polite" aria-busy={state() === "loading"}>
          <header><div><small>quillframe_ch001_quick_demo_receipt_v1</small><strong>CH001 · authority=false</strong></div><span data-state={state()}>{state()}</span></header>
          <Show when={receipt()} fallback={
            <div class="quick-demo-empty" data-state={state()}>
              <div class="quick-demo-loom" aria-hidden="true"><i /><i /><i /><b>QF</b></div>
              <Show when={error()} fallback={<p>{labels().before}</p>}>{(message) => <p role="alert">{message()}</p>}</Show>
            </div>
          }>
            {(value) => <div class="quick-demo-result">
              <article><span>01</span><div><small>{labels().core}</small><strong>{value().deterministic_core.stage} → packet ready</strong><code>{packetShort()}…</code></div><b>PASS</b></article>
              <article><span>02</span><div><small>{labels().evidence}</small><strong>{value().semantic_evidence.summary}</strong><div class="quick-demo-findings"><For each={value().semantic_evidence.findings}>{(finding) => <code>{finding.code}</code>}</For></div></div><b>FIXTURE</b></article>
              <article class="quick-demo-boundary"><span>03</span><div><small>{labels().boundary}</small><strong>{labels().boundaryBody}</strong><code>model={String(value().live_model_called)} · uploads={value().uploads} · canon={String(value().canon_mutated)}</code></div><b>SAFE</b></article>
            </div>}
          </Show>
          <footer><span>Pyodide {runtimeVersion() ?? "local"}</span><span>production_runtime/*.py</span><span>0 network writes</span></footer>
        </div>
      </div>
    </section>
  );
}
