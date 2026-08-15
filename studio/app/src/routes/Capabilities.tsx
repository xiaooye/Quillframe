import { For, Show, createMemo, createResource } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

type FootprintMetric = { files: number; bytes: number; gzip_bytes: number; largest_bytes: number };
type Footprint = {
  schema: "novelforge_studio_footprint_v1";
  generated_at: string;
  measurement: string;
  assets: { javascript: FootprintMetric; css: FootprintMetric };
  runtime_contract: {
    weiui_runtime_javascript_required: boolean;
    persistent_database_required_by_hosted_ui: boolean;
    core_required_for_browser_preflight: boolean;
    core_required_for_local_playground_preview: boolean;
  };
  not_measured: string[];
};

const formatKiB = (bytes: number) => `${(bytes / 1024).toFixed(1)} KiB`;

const footprintCopy = {
  "en-US": {
    eyebrow: "Measured build footprint",
    title: "Performance & footprint",
    body: "These numbers are generated from the production build artifacts. Unknown runtime measurements stay unknown instead of becoming marketing estimates.",
    js: "Browser JavaScript",
    css: "Browser CSS",
    gzip: "gzip",
    weiui: "WeiUI runtime JS",
    core: "Core required for browser-local tools",
    no: "No",
    loading: "Reading build metrics…",
    unavailable: "Build metrics are unavailable in this host. Production builds generate the footprint manifest automatically.",
    notMeasured: "Not measured yet",
    source: "CI-generated · production build artifacts",
  },
  "zh-CN": {
    eyebrow: "实测 Build Footprint",
    title: "Performance / Footprint",
    body: "这些数字直接由 production build artifact 生成。没有测量的 runtime 指标保持未知，不拿营销估算值补空白。",
    js: "Browser JavaScript",
    css: "Browser CSS",
    gzip: "gzip",
    weiui: "WeiUI runtime JS",
    core: "浏览器本地工具是否需要 Core",
    no: "不需要",
    loading: "正在读取 build metrics…",
    unavailable: "当前宿主没有 footprint manifest；production build 会自动生成。",
    notMeasured: "尚未测量",
    source: "CI-generated · production build artifacts",
  },
} as const;

const runtimeCopy = {
  "en-US": {
    eyebrow: "Runtime boundary",
    title: "Observable state is public; one runtime command is guarded",
    body: "NovelForge exposes typed side-effect-free projections and one narrowly scoped local command: session.resume. The command requires a fresh preflight, explicit user authorization, exact Session CAS, and a durable receipt; it does not run a model or gain Project/Canon authority.",
    supported: "Supported Host Bridge operations",
    deferred: "Additional writes still deferred",
    supportedBody: "Queries remain authority=false and side-effect-free. session.resume is local_app-only and may mutate only runtime Session state through its typed command contract.",
    deferredBody: "Generic command dispatch and Project mutation remain unavailable. Every future write needs its own typed Core contract, preconditions, authority policy, CAS/idempotency, and durable receipt.",
    raw: "Raw capability evidence",
  },
  "zh-CN": {
    eyebrow: "Runtime 边界",
    title: "运行状态公开可观测；一个 Runtime Command 已受保护开放",
    body: "NovelForge 已公开类型化、无副作用的运行时投影，并只开放一个严格限定的本地 command：session.resume。它要求 fresh preflight、显式用户授权、精确 Session CAS 与持久 receipt；不会运行模型，也不会获得 Project/Canon authority。",
    supported: "已支持的 Host Bridge 操作",
    deferred: "仍 deferred 的额外写操作",
    supportedBody: "查询仍是 authority=false 且无副作用。session.resume 仅允许 local_app 调用，并且只能通过类型化 command contract 修改 Runtime Session state。",
    deferredBody: "通用 command dispatch 与 Project mutation 仍不可用。未来每一种写操作都必须拥有独立的 Core typed contract、前置条件、authority policy、CAS/idempotency 与持久 receipt。",
    raw: "原始 Capability 证据",
  },
} as const;

export default function Capabilities() {
  const { t, locale } = useI18n();
  const studio = useStudio();
  const fpText = createMemo(() => footprintCopy[locale()]);
  const runtimeText = createMemo(() => runtimeCopy[locale()]);
  const runtimeBoundary = createMemo(() => {
    const description = studio.bridgeDescription();
    if (!description) return undefined;
    return {
      supported: description.supported_operations,
      deferred: Object.entries(description.deferred_operations),
    };
  });
  const [footprint] = createResource(async () => {
    const response = await fetch("/.well-known/novelforge-studio-footprint.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`footprint manifest: ${response.status}`);
    return await response.json() as Footprint;
  });
  const [data, { refetch }] = createResource(
    () => (studio.bridgeAvailable() ? "bound" : undefined),
    async () => {
      const response = await invokeBridge("capabilities.inspect", studio.projectRoot() ? { project_root: studio.projectRoot() } : {});
      if (response.status !== "ok") throw new Error(JSON.stringify(response.error));
      return response.data;
    },
  );

  return (
    <section class="nf-page">
      <PageIntro
        title={t("capabilities.title")}
        body={t("capabilities.body")}
        actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--outline" type="button" onClick={() => void refetch()}>{t("common.refresh")}</button> : undefined}
      />

      <section aria-labelledby="footprint-heading">
        <div class="nf-section-heading">
          <span class="nf-eyebrow">{fpText().eyebrow}</span>
          <h2 id="footprint-heading">{fpText().title}</h2>
          <p>{fpText().body}</p>
        </div>
        <Show when={footprint()} fallback={<div class="wui-card nf-card"><div class="wui-card__content"><p class="nf-muted">{footprint.loading ? fpText().loading : fpText().unavailable}</p></div></div>}>
          {(metrics) => (
            <>
              <div class="nf-metric-grid">
                <article class="wui-card nf-card nf-card-accent"><div class="wui-card__content"><span class="nf-card-label">{fpText().js}</span><strong>{formatKiB(metrics().assets.javascript.bytes)}</strong><small>{fpText().gzip} {formatKiB(metrics().assets.javascript.gzip_bytes)} · {metrics().assets.javascript.files} chunks</small></div></article>
                <article class="wui-card nf-card"><div class="wui-card__content"><span class="nf-card-label">{fpText().css}</span><strong>{formatKiB(metrics().assets.css.bytes)}</strong><small>{fpText().gzip} {formatKiB(metrics().assets.css.gzip_bytes)} · {metrics().assets.css.files} chunk</small></div></article>
                <article class="wui-card nf-card"><div class="wui-card__content"><span class="nf-card-label">{fpText().weiui}</span><strong>{metrics().runtime_contract.weiui_runtime_javascript_required ? "Yes" : fpText().no}</strong><small>{fpText().source}</small></div></article>
                <article class="wui-card nf-card"><div class="wui-card__content"><span class="nf-card-label">{fpText().core}</span><strong>{metrics().runtime_contract.core_required_for_browser_preflight || metrics().runtime_contract.core_required_for_local_playground_preview ? "Yes" : fpText().no}</strong><small>Project Preflight · Local Playground</small></div></article>
              </div>
              <article class="wui-card wui-card--filled nf-card">
                <div class="wui-card__content">
                  <span class="nf-card-label">{fpText().notMeasured}</span>
                  <code>{metrics().not_measured.join(" · ")}</code>
                </div>
              </article>
            </>
          )}
        </Show>
      </section>

      <Show when={runtimeBoundary()}>
        {(boundary) => (
          <section class="wui-card wui-card--outlined nf-inspector-surface nf-diagnostic-workstation" aria-labelledby="runtime-boundary-heading">
            <div class="nf-observe-section-head">
              <div>
                <span class="nf-eyebrow">{runtimeText().eyebrow}</span>
                <h2 id="runtime-boundary-heading">{runtimeText().title}</h2>
                <p>{runtimeText().body}</p>
              </div>
              <span class="wui-badge wui-badge--outline">authority=false</span>
            </div>
            <div class="nf-validation-scope">
              <article>
                <header><span class="wui-badge wui-badge--success">{boundary().supported.length}</span><h3>{runtimeText().supported}</h3></header>
                <p class="nf-observe-footnote">{runtimeText().supportedBody}</p>
                <ul><For each={boundary().supported}>{(operation) => <li><code>{operation}</code></li>}</For></ul>
              </article>
              <article>
                <header><span class="wui-badge wui-badge--outline">{boundary().deferred.length}</span><h3>{runtimeText().deferred}</h3></header>
                <p class="nf-observe-footnote">{runtimeText().deferredBody}</p>
                <ul>
                  <For each={boundary().deferred}>
                    {([operation, projection]) => <li><code>{operation}</code>{projection.dependency ? ` · ${projection.dependency}` : ""}<br />{projection.reason}</li>}
                  </For>
                </ul>
              </article>
            </div>
          </section>
        )}
      </Show>

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <QueryError message={data.error ? String(data.error) : undefined} />
        <Show when={!data.loading} fallback={<div class="nf-loading">{t("common.loading")}</div>}>
          <section class="wui-card wui-card--outlined nf-inspector-surface">
            <details class="nf-raw-evidence">
              <summary>{runtimeText().raw}</summary>
              <JsonBlock value={data()} />
            </details>
          </section>
        </Show>
      </Show>
    </section>
  );
}
