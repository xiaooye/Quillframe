import { For, Show } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

const topology = [
  { id: "studio", label: "SolidJS Studio", note: "authoring UI · authority=false" },
  { id: "client", label: "BridgeClient", note: "typed operation consumer" },
  { id: "transport", label: "Transport", note: "Local HTTP / Hosted HTTP / Tauri IPC" },
  { id: "core", label: "Quillframe Core", note: "semantic + authority owner" },
  { id: "sqlite", label: "SQLite", note: "canonical persistence owned by Core" },
] as const;

export default function Architecture() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const project = () => studio.projectProjection();
  return (
    <section class="nf-page qf-architecture-page">
      <PageIntro eyebrow="INSPECTOR · ARCHITECTURE" title={zh() ? "产品拓扑和运行证据分开看。" : "Product topology and runtime evidence are different views."} body={zh() ? "下面的链路是 Studio 的设计 contract，不是假装正在发生的 Run trace。真实 Session/Run/Context/Receipt 请到对应 Inspector 读取 Core projection。" : "The chain below is the Studio design contract, not a pretend live Run trace. Real Session/Run/Context/Receipt evidence belongs in the corresponding Core-backed Inspector."} />

      <section class="qf-editorial-sheet">
        <div class="qf-section-head"><div><span class="nf-eyebrow">PRODUCT TOPOLOGY · DESIGN CONTRACT</span><h2>Studio → BridgeClient → Core</h2></div><span class="qf-authority-label">not runtime evidence</span></div>
        <ol class="qf-architecture-flow"><For each={topology}>{(node, index) => <li><small>{String(index() + 1).padStart(2, "0")}</small><div><strong>{node.label}</strong><span>{node.note}</span></div>{index() < topology.length - 1 ? <b aria-hidden="true">→</b> : null}</li>}</For></ol>
        <p>{zh() ? "Desktop 的 Transport 必须完全 Cloudflare-independent；Hosted Web 的 Cloudflare 只能是 host implementation，不能改变 operation semantics。" : "Desktop transport must be completely Cloudflare-independent; Cloudflare may host Web infrastructure but cannot change operation semantics."}</p>
      </section>

      <section class="qf-editorial-sheet">
        <div class="qf-section-head"><div><span class="nf-eyebrow">OBSERVED NOW</span><h2>{studio.transportName()}</h2></div><span class="qf-authority-label">authority=false</span></div>
        <dl class="qf-settings-facts"><dt>surface</dt><dd>{studio.surface()}</dd><dt>Core bound</dt><dd>{String(studio.bridgeAvailable())}</dd><dt>framework</dt><dd>{studio.bridgeCapabilities()?.frameworkVersion ?? "—"}</dd><dt>operations</dt><dd>{studio.bridgeCapabilities()?.operations.length ?? 0}</dd><dt>Project</dt><dd>{project()?.project.project_id ?? "—"}</dd><dt>last Run</dt><dd>{studio.lastRunId() || "—"}</dd></dl>
        <Show when={project()}>{(value) => <p>{zh() ? `Core 当前报告 ${value().counts.documents ?? 0} 个 document、${value().counts.runs ?? 0} 个 run。这里只复述 projection，不推断质量或 Canon。` : `Core currently reports ${value().counts.documents ?? 0} documents and ${value().counts.runs ?? 0} runs. This only repeats the projection; it infers no quality or Canon state.`}</p>}</Show>
        <div class="qf-inline-actions"><A class="wui-button wui-button--outline" href={studio.projectId() ? `/runtime?project=${encodeURIComponent(studio.projectId())}` : "/runtime"}>{zh() ? "真实 Runtime" : "Real Runtime"}</A><A class="wui-button wui-button--outline" href={studio.projectId() ? `/context?project=${encodeURIComponent(studio.projectId())}${studio.lastRunId() ? `&run=${encodeURIComponent(studio.lastRunId())}` : ""}` : "/context"}>Context</A><A class="wui-button wui-button--ghost" href="/capabilities">Capabilities</A></div>
      </section>

      <section class="qf-editorial-sheet"><span class="nf-eyebrow">HOST STATUS</span><h2>{zh() ? "Web / Tauri" : "Web / Tauri"}</h2><div class="qf-runtime-columns"><section><header><span>WEB</span><strong>{studio.transportName() === "hosted-http" ? "bound" : "awaiting_external"}</strong></header><article><span>{zh() ? "HostedHttpTransport 需要 host 注入真实 durable Core endpoint。" : "HostedHttpTransport requires the host to inject a real durable Core endpoint."}</span></article></section><section><header><span>TAURI 2</span><strong>{studio.transportName() === "tauri-ipc" ? "bound" : "awaiting_external"}</strong></header><article><span>{zh() ? "TauriTransport 需要真实 bridge_invoke host primitive；Studio 不提供 JS mock。" : "TauriTransport requires a real bridge_invoke host primitive; Studio provides no JS mock."}</span></article></section></div></section>
    </section>
  );
}
