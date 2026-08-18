import { For, Show, createMemo, createSignal } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { CoreRequirementNotice } from "../authoring/AuthoringUI";

type Section = "general" | "models" | "appearance" | "advanced";
type ModelProjection = { model_id?: string; display_name?: string; capabilities?: Record<string, unknown>; protocol_family?: string; metadata?: Record<string, unknown> };
type ServiceProjection = { service_id?: string; endpoint?: string; discovery_state?: string; credential_present?: boolean; models?: ModelProjection[] };
type ServiceList = { items?: ServiceProjection[] };

const sections: Array<{ id: Section; en: string; zh: string }> = [
  { id: "general", en: "General", zh: "通用" },
  { id: "models", en: "AI & Models", zh: "AI 与模型" },
  { id: "appearance", en: "Appearance", zh: "外观" },
  { id: "advanced", en: "Advanced", zh: "高级" },
];

function initialSection(): Section {
  const value = new URLSearchParams(window.location.search).get("section") as Section | null;
  return value && sections.some((item) => item.id === value) ? value : "general";
}

export default function Settings() {
  const { locale, setLocale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [section, setSection] = createSignal<Section>(initialSection());
  const [endpoint, setEndpoint] = createSignal("");
  const [token, setToken] = createSignal("");
  const [services, setServices] = createSignal<ServiceProjection[]>([]);
  const [connecting, setConnecting] = createSignal(false);
  const [message, setMessage] = createSignal<string>();
  const [error, setError] = createSignal<string>();
  const operations = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);

  const refreshServices = async () => {
    if (!operations().includes("model.services.list")) return;
    setError(undefined);
    try {
      const result = await invokeBridge<ServiceList>("model.services.list");
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setServices(result.data.items ?? []);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  };

  const connect = async () => {
    if (!endpoint().trim() || !operations().includes("model.connect")) return;
    setConnecting(true); setError(undefined); setMessage(undefined);
    const accessToken = token();
    try {
      const result = await invokeBridge<ServiceProjection>("model.connect", { endpoint: endpoint().trim(), access_token: accessToken });
      setToken("");
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setMessage(zh() ? "Core 已返回连接结果；Access Token 明文已从表单清除。" : "Core returned the connection result; the Access Token value was cleared from the form.");
      await refreshServices();
    } catch (cause) {
      setToken("");
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setConnecting(false); }
  };

  return (
    <section class="nf-page qf-settings-page">
      <PageIntro eyebrow={zh() ? "设置 · 宿主级" : "SETTINGS · HOST LEVEL"} title={zh() ? "设置服务写作，不接管作品。" : "Settings serve the writing, not the work itself."} body={zh() ? "通用、AI 与模型、外观、高级。Project / Canon / Context / Settlement authority 不进入浏览器 settings。" : "General, AI & Models, Appearance and Advanced. Project / Canon / Context / Settlement authority never becomes browser settings state."} />
      <div class="qf-settings-layout">
        <nav class="qf-settings-nav" aria-label={zh() ? "设置分类" : "Settings sections"}><For each={sections}>{(item) => <button type="button" data-active={section() === item.id ? "true" : undefined} onClick={() => setSection(item.id)}>{zh() ? item.zh : item.en}</button>}</For></nav>
        <div class="qf-settings-content">
          <Show when={section() === "general"}><section class="qf-editorial-sheet"><span class="nf-eyebrow">GENERAL</span><h2>{zh() ? "Studio" : "Studio"}</h2><dl class="qf-settings-facts"><dt>{zh() ? "传输" : "Transport"}</dt><dd>{studio.transportName()}</dd><dt>Core</dt><dd>{studio.bridgeAvailable() ? (zh() ? "已绑定" : "bound") : (zh() ? "未绑定" : "unbound")}</dd><dt>Project</dt><dd>{studio.projectId() || "—"}</dd></dl><p>{zh() ? "浏览器持久化只保存 UI convenience（例如最近 Project ID），不保存正文或 Canon authority。" : "Browser persistence stores UI convenience only (for example the recent Project ID), never manuscript or Canon authority."}</p></section></Show>

          <Show when={section() === "models"}><div class="qf-model-workspace">
            <section class="qf-editorial-sheet qf-model-connect"><span class="nf-eyebrow">MODEL SERVICE</span><h2>{zh() ? "Endpoint + Access Token" : "Endpoint + Access Token"}</h2><p>{zh() ? "普通用户不选择 provider 类型。Quillframe Core 负责协议、模型与 capability discovery。" : "Ordinary users do not choose a provider type. Quillframe Core owns protocol, model and capability discovery."}</p>
              <label class="nf-field-label"><span>Endpoint</span><input class="wui-input nf-mono" inputmode="url" autocomplete="url" value={endpoint()} onInput={(event) => setEndpoint(event.currentTarget.value)} placeholder="https://api.example.com/v1" /></label>
              <label class="nf-field-label"><span>Access Token</span><input class="wui-input nf-mono" type="password" autocomplete="new-password" value={token()} onInput={(event) => setToken(event.currentTarget.value)} placeholder={zh() ? "不会回显" : "Never echoed back"} /><small>{zh() ? "Token storage implementation 属于 Core/host；Studio 不会写入 localStorage、Project SQLite 或 Context。" : "Token storage belongs to Core/host; Studio never writes it to localStorage, Project SQLite or Context."}</small></label>
              <button class="wui-button wui-button--solid" type="button" disabled={connecting() || !endpoint().trim() || !operations().includes("model.connect")} onClick={() => void connect()}>{connecting() ? (zh() ? "连接中…" : "Connecting…") : (zh() ? "Test / Connect" : "Test / Connect")}</button>
              <CoreRequirementNotice operation="model.connect" />
              <Show when={message()}>{(value) => <p class="qf-success-note" role="status">{value()}</p>}</Show><Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">AI & Models</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
            </section>

            <section class="qf-editorial-sheet"><div class="qf-section-head"><div><span class="nf-eyebrow">MODEL SERVICES</span><h2>{zh() ? "模型服务" : "Model Services"}</h2></div><button class="wui-button wui-button--outline" type="button" disabled={!operations().includes("model.services.list")} onClick={() => void refreshServices()}>{zh() ? "刷新" : "Refresh"}</button></div><CoreRequirementNotice operation="model.services.list" compact />
              <div class="qf-model-service-list"><For each={services()}>{(service) => <article><div><strong>{service.endpoint ?? service.service_id ?? "Model Service"}</strong><span class="qf-authority-label">{service.discovery_state ?? "observed"}</span></div><p>{service.credential_present ? (zh() ? "Credential present · 明文不可见" : "Credential present · value hidden") : (zh() ? "无 credential evidence" : "No credential evidence")}</p><div class="qf-model-chip-list"><For each={service.models ?? []}>{(model) => <span>{model.display_name ?? model.model_id ?? "model"}</span>}</For></div></article>}</For><Show when={!services().length}><p>{zh() ? "Core 尚未返回 Model Service projection。" : "Core has not returned a Model Service projection."}</p></Show></div>
            </section>

            <section class="qf-editorial-sheet"><span class="nf-eyebrow">MODEL SELECTION</span><h2>{zh() ? "默认 / 自动选择" : "Default / automatic selection"}</h2><div class="qf-default-model-row"><div><strong>{zh() ? "自动选择模型" : "Automatic model selection"}</strong><p>{zh() ? "默认。当前任务 eligibility 由 Core 决定；用户偏好不能提升 capability。" : "Default. Core decides task eligibility; user preference cannot promote capability."}</p></div><span class="wui-badge wui-badge--outline">DEFAULT</span></div><div class="qf-default-model-row" data-muted><div><strong>{zh() ? "指定模型偏好" : "Exact model preference"}</strong><p>{zh() ? "需要 Core 提供 preference contract 后开放。" : "Available only after Core exposes a preference contract."}</p></div><span>awaiting_external</span></div></section>
          </div></Show>

          <Show when={section() === "appearance"}><section class="qf-editorial-sheet"><span class="nf-eyebrow">APPEARANCE</span><h2>{zh() ? "外观" : "Appearance"}</h2><p>{zh() ? "主题继续服从 Story Loom 的 warm ivory / dark roles；语言必须支持中英文扩张。" : "Theme follows Story Loom warm-ivory / dark roles; layout must tolerate Chinese and English expansion."}</p><button class="wui-button wui-button--outline" type="button" onClick={() => setLocale(locale() === "zh-CN" ? "en-US" : "zh-CN")}>{locale() === "zh-CN" ? "English" : "中文"}</button></section></Show>

          <Show when={section() === "advanced"}><section class="qf-editorial-sheet"><span class="nf-eyebrow">ADVANCED</span><h2>{zh() ? "协议与诊断只在这里出现" : "Protocol and diagnostics stay here"}</h2><p>{zh() ? "Provider/vendor/protocol identity 只能作为 Core observation；它们不是普通设置实体。" : "Provider/vendor/protocol identity is Core observation only; it is not an ordinary setup entity."}</p><div class="qf-inline-actions"><A class="wui-button wui-button--outline" href="/diagnostics">Diagnostics</A><A class="wui-button wui-button--outline" href="/capabilities">Capabilities</A></div><details><summary>{zh() ? "当前 Core operations" : "Current Core operations"}</summary><pre class="qf-diff"><code>{operations().join("\n") || "unbound"}</code></pre></details></section></Show>
        </div>
      </div>
    </section>
  );
}
