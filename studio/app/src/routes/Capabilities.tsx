import { For, Show, createMemo, createResource } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { CORE_CONSUMER_REQUIREMENTS } from "../authoring/contracts";

type FootprintMetric = { files: number; bytes: number; gzip_bytes: number; largest_bytes: number };
type Footprint = {
  schema: string;
  generated_at: string;
  assets: { javascript: FootprintMetric; css: FootprintMetric };
  not_measured: string[];
};

const formatKiB = (bytes: number) => `${(bytes / 1024).toFixed(1)} KiB`;

export default function Capabilities() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const operations = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);
  const contracts = createMemo(() => studio.bridgeCapabilities()?.operationContracts ?? {});
  const missingRequirements = createMemo(() => CORE_CONSUMER_REQUIREMENTS.filter((item) => !operations().includes(item.operation)));
  const [footprint] = createResource(async () => {
    const response = await fetch("/.well-known/quillframe-studio-footprint.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`footprint manifest: ${response.status}`);
    return await response.json() as Footprint;
  });

  return (
    <section class="nf-page qf-capabilities-page">
      <PageIntro eyebrow="INSPECTOR · CAPABILITIES" title={zh() ? "只展示 Core 真正声明的 operation。" : "Only operations Core actually declares are shown."} body={zh() ? "BridgeClient 从 bridge.describe 读取当前 operation set。Studio consumer requirement 不会因此变成 capability；未提供的能力明确保持 awaiting_external。" : "BridgeClient reads the current operation set from bridge.describe. A Studio consumer requirement does not become a capability by declaration; missing operations remain awaiting_external."} />

      <section class="qf-editorial-sheet">
        <div class="qf-section-head"><div><span class="nf-eyebrow">BRIDGE</span><h2>{studio.transportName()}</h2></div><span class="qf-authority-label">authority=false</span></div>
        <dl class="qf-settings-facts"><dt>framework</dt><dd>{studio.bridgeCapabilities()?.frameworkVersion ?? "—"}</dd><dt>contract</dt><dd>{studio.bridgeCapabilities()?.contractVersion ?? "—"}</dd><dt>surface</dt><dd>{studio.bridgeCapabilities()?.surface ?? studio.surface()}</dd><dt>operations</dt><dd>{operations().length}</dd></dl>
        <div class="qf-search-results"><For each={operations()}>{(operation) => <article><div><strong><code>{operation}</code></strong><span class="qf-capability-state">supported</span></div><p>{contracts()[operation]?.kind ?? "Core-declared operation"}{contracts()[operation]?.allowed_surfaces ? ` · ${contracts()[operation]?.allowed_surfaces?.join(", ")}` : ""}</p></article>}</For></div>
      </section>

      <section class="qf-editorial-sheet">
        <div class="qf-section-head"><div><span class="nf-eyebrow">STUDIO REQUIREMENTS</span><h2>{zh() ? "仍缺的 Core primitive" : "Core primitives still missing"}</h2></div><strong>{missingRequirements().length}</strong></div>
        <div class="qf-search-results"><For each={missingRequirements()}>{(item) => <article><div><strong><code>{item.operation}</code></strong><span class="qf-capability-state">awaiting_external</span></div><p>{item.userAction}</p><small>{item.whyUiCannotImplement}</small></article>}</For></div>
      </section>

      <section class="qf-editorial-sheet">
        <span class="nf-eyebrow">MEASURED UI FOOTPRINT</span><h2>{zh() ? "Build artifact" : "Build artifact"}</h2>
        <Show when={footprint()} fallback={<p>{footprint.loading ? (zh() ? "读取中…" : "Loading…") : (zh() ? "当前 host 没有 footprint manifest。" : "No footprint manifest in this host.")}</p>}>
          {(metrics) => <div class="qf-authoring-counts"><span><strong>{formatKiB(metrics().assets.javascript.bytes)}</strong>JavaScript</span><span><strong>{formatKiB(metrics().assets.css.bytes)}</strong>CSS</span><span><strong>{formatKiB(metrics().assets.javascript.gzip_bytes)}</strong>JS gzip</span><span><strong>{metrics().not_measured.length}</strong>{zh() ? "未测量项" : "unmeasured"}</span></div>}
        </Show>
      </section>
    </section>
  );
}
