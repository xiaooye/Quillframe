import { For, Show, createMemo, createSignal, onCleanup } from "solid-js";
import type { Locale } from "./content";
import { captureWorkerErrorOwnership, createRestartableWorker, createSingleFlight, isCurrentWorkerEvent, validateQuickDemoReceipt } from "./workerLifecycle";

type QuickDemoReceipt = {
  schema: "quillframe_ch001_quick_demo_receipt_v1";
  chapter_id: "CH001";
  deterministic_core: {
    executed: false;
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
  | { kind: "ready"; runtime_version: string }
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
    title: "检查由 Rust Core 验收测试留下的 CH001 回执。",
    lede: "点击一次会回放由 Rust Core 验收测试生成的 CH001 回执，并核对 generation packet 与 workflow 指纹。语义证据明确标注为录制夹具；这里不会冒充浏览器内正在执行 Core 或模型。",
    run: "运行 CH001 演示",
    running: "正在核对录制回执…",
    rerun: "再次验证",
    deterministic: "Deterministic Core",
    semantic: "Recorded semantic evidence",
    upload: "0 uploads",
    account: "无需账号 / API key",
    before: "点击后，这里会显示录制的 Core receipt、生成包指纹和语义证据，不会发起网络请求。",
    core: "录制的 Rust Core 验收",
    evidence: "录制语义证据",
    boundary: "真实性边界",
    boundaryBody: "packet/workflow 与语义摘要均来自录制的验收夹具。本页不执行 Core；回执 authority=false，不写 Canon、不发布、不结算。",
  } : {
    eyebrow: "QUICK WORKING DEMO · CH001",
    title: "Inspect a CH001 receipt produced by Rust Core acceptance tests.",
    lede: "One click replays a CH001 receipt produced by Rust Core acceptance tests and verifies its generation-packet and workflow fingerprints. Semantic evidence is clearly labelled as recorded; no browser-local Core or model execution is implied.",
    run: "Run the CH001 demo",
    running: "Checking the recorded receipt…",
    rerun: "Verify again",
    deterministic: "Deterministic Core",
    semantic: "Recorded semantic evidence",
    upload: "0 uploads",
    account: "No account / API key",
    before: "Inspect the recorded Core receipt, generation-packet fingerprint, and semantic evidence without making a network request.",
    core: "Recorded Rust Core acceptance",
    evidence: "Recorded semantic evidence",
    boundary: "Truth boundary",
    boundaryBody: "The packet/workflow and semantic summary are recorded acceptance fixtures. This page does not execute Core; authority=false cannot write Canon, publish, or settle.",
  };

  const worker = () => {
    workerLease ??= lifecycle.acquire();
    const lease = workerLease;
    lease.worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;
      if (disposed || !lifecycle.isCurrent(lease)) return;
      if (message.kind === "ready") {
        setRuntimeVersion(message.runtime_version);
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
          <footer><span>{runtimeVersion() ?? "recorded Rust Core receipt"}</span><span>native/quillframe-core</span><span>0 network writes</span></footer>
        </div>
      </div>
    </section>
  );
}
