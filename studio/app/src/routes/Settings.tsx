import { For, Show, createMemo, createSignal, onMount } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { ModelServiceListProjection, ModelServiceProjection } from "../authoring/contracts";
import { CoreRequirementNotice } from "../authoring/AuthoringUI";

type Section = "general" | "models" | "appearance" | "advanced";
type CapabilityState = "verified" | "detected" | "unknown" | "unavailable";

const sections: Array<{ id: Section; en: string; zh: string }> = [
  { id: "general", en: "General", zh: "通用" },
  { id: "models", en: "AI & Models", zh: "AI 与模型" },
  { id: "appearance", en: "Appearance", zh: "外观" },
  { id: "advanced", en: "Advanced", zh: "高级" },
];

const settingsCopy = {
  "en-US": { endpoint: "API Endpoint", token: "Access Token", autoTitle: "Automatic model selection", connect: "Test / Connect" },
  "zh-CN": { endpoint: "API Endpoint", token: "Access Token", autoTitle: "自动选择模型", connect: "Test / Connect" },
} as const;

function initialSection(): Section {
  const value = new URLSearchParams(window.location.search).get("section") as Section | null;
  return value && sections.some((item) => item.id === value) ? value : "general";
}

function observedState(service: ModelServiceProjection): CapabilityState {
  const state = service.discovery_state?.toLowerCase();
  if (state === "connected" || state === "ready" || state === "verified") return "verified";
  if (state === "detected" || state === "discovering") return "detected";
  if (state === "failed" || state === "unavailable") return "unavailable";
  return "unknown";
}

export default function Settings() {
  const { locale, setLocale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const text = createMemo(() => settingsCopy[locale()]);
  const [section, setSection] = createSignal<Section>(initialSection());
  const [endpoint, setEndpoint] = createSignal("");
  const [token, setToken] = createSignal("");
  const [services, setServices] = createSignal<ModelServiceProjection[]>([]);
  const [connecting, setConnecting] = createSignal(false);
  const [message, setMessage] = createSignal<string>();
  const [error, setError] = createSignal<string>();
  const operations = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);

  const refreshServices = async () => {
    if (!operations().includes("model.service.list")) return;
    setError(undefined);
    try {
      const result = await invokeBridge<ModelServiceListProjection>("model.service.list");
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setServices(result.data.items ?? []);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  };

  const connect = async () => {
    if (!endpoint().trim() || !operations().includes("model.service.add")) return;
    setConnecting(true); setError(undefined); setMessage(undefined);
    const accessToken = token();
    try {
      const result = await invokeBridge<ModelServiceProjection>("model.service.add", { endpoint: endpoint().trim(), access_token: accessToken });
      setToken("");
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setMessage(zh() ? "Model Service 已由 Core discover；Access Token 明文已从表单清除。" : "Core discovered the Model Service; the Access Token value was cleared from the form.");
      await refreshServices();
    } catch (cause) {
      setToken("");
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setConnecting(false); }
  };

  const discover = async (serviceId: string) => {
    if (!operations().includes("model.service.discover")) return;
    setError(undefined);
    try {
      const result = await invokeBridge<ModelServiceProjection>("model.service.discover", { service_id: serviceId });
      if (result.status !== "ok") throw new Error(operationError(result));
      await refreshServices();
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  };

  const testService = async (serviceId: string) => {
    if (!operations().includes("model.service.test")) return;
    setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge("model.service.test", { service_id: serviceId, verify_tools: true });
      if (result.status !== "ok") throw new Error(operationError(result));
      setMessage(zh() ? "Core model probe 已完成；capability evidence 已刷新。" : "Core model probe completed; capability evidence was refreshed.");
      await refreshServices();
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  };

  onMount(() => { if (studio.bridgeAvailable()) void refreshServices(); });

  return (
    <section class="nf-page qf-settings-page">
      <PageIntro eyebrow={zh() ? "设置 · 宿主级" : "SETTINGS · HOST LEVEL"} title={zh() ? "设置服务写作，不接管作品。" : "Settings serve the writing, not the work itself."} body={zh() ? "Project / Canon / Context / Settlement authority 不进入浏览器 settings。Model Service 只通过 typed Core。" : "Project / Canon / Context / Settlement authority never becomes browser settings state. Model Services go through typed Core only."} />
      <div class="qf-settings-layout">
        <nav class="qf-settings-nav" aria-label={zh() ? "设置分类" : "Settings sections"}><For each={sections}>{(item) => <button type="button" data-active={section() === item.id ? "true" : undefined} onClick={() => setSection(item.id)}>{zh() ? item.zh : item.en}</button>}</For></nav>
        <div class="qf-settings-content">
          <Show when={section() === "general"}><section class="qf-editorial-sheet"><span class="nf-eyebrow">GENERAL</span><h2>Studio</h2><dl class="qf-settings-facts"><dt>{zh() ? "传输" : "Transport"}</dt><dd>{studio.transportName()}</dd><dt>Core</dt><dd>{studio.bridgeAvailable() ? (zh() ? "已绑定" : "bound") : (zh() ? "未绑定" : "unbound")}</dd><dt>Project</dt><dd>{studio.projectId() || "—"}</dd><dt>Host Bridge</dt><dd>v{studio.bridgeCapabilities()?.contractVersion ?? "—"}</dd></dl><p>{zh() ? "浏览器持久化只保存 UI convenience，不保存正文或 Canon authority。" : "Browser persistence stores UI convenience only, never manuscript or Canon authority."}</p></section></Show>

          <Show when={section() === "models"}><div class="qf-model-workspace">
            <section class="qf-editorial-sheet qf-model-connect">
              <span class="nf-eyebrow">MODEL SERVICE</span><h2>Endpoint + Access Token</h2><p>{zh() ? "普通用户只连接服务。协议、模型与 capability discovery 由 Quillframe Core 负责。" : "Ordinary users connect a service only. Quillframe Core owns protocol, model and capability discovery."}</p>
              <div class="qf-model-connect-fields">
                <label class="nf-field-label"><span>{text().endpoint}</span><input class="wui-input nf-mono" inputmode="url" autocomplete="url" value={endpoint()} onInput={(event) => setEndpoint(event.currentTarget.value)} placeholder="https://api.example.com/v1" /></label>
                <label class="nf-field-label"><span>{text().token}</span><input class="wui-input nf-mono" type="password" autocomplete="new-password" value={token()} onInput={(event) => setToken(event.currentTarget.value)} placeholder={zh() ? "不会回显" : "Never echoed back"} /><small>{zh() ? "Token 只交给 Host/Core SecretStore；Studio 不写 localStorage、Project state 或 Context。" : "The token is handed only to the Host/Core SecretStore; Studio never writes it to localStorage, Project state or Context."}</small></label>
              </div>
              <button class="wui-button wui-button--solid" type="button" disabled={connecting() || !endpoint().trim() || !operations().includes("model.service.add")} onClick={() => void connect()}>{connecting() ? (zh() ? "连接中…" : "Connecting…") : text().connect}</button>
              <CoreRequirementNotice operation="model.service.add" />
              <Show when={message()}>{(value) => <p class="qf-success-note" role="status">{value()}</p>}</Show><Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">AI & Models</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
            </section>

            <section class="qf-editorial-sheet"><div class="qf-section-head"><div><span class="nf-eyebrow">MODEL SERVICES</span><h2>{zh() ? "模型服务" : "Model Services"}</h2></div><button class="wui-button wui-button--outline" type="button" disabled={!operations().includes("model.service.list")} onClick={() => void refreshServices()}>{zh() ? "刷新" : "Refresh"}</button></div><CoreRequirementNotice operation="model.service.list" compact />
              <div class="qf-model-service-list"><For each={services()}>{(service) => <article><div><strong>{service.endpoint ?? service.service_id ?? "Model Service"}</strong><span class="qf-capability-state">{observedState(service)}</span></div><p>{service.credential_present ? (zh() ? "Credential present · 明文不可见" : "Credential present · value hidden") : (zh() ? "无 credential evidence" : "No credential evidence")}</p><div class="qf-model-chip-list"><For each={service.models ?? []}>{(model) => <span>{model.display_name ?? model.model_id ?? "model"}</span>}</For></div><Show when={service.service_id}><div class="qf-inline-actions"><button class="wui-button wui-button--outline" type="button" disabled={!operations().includes("model.service.discover")} onClick={() => void discover(service.service_id!)}>Discover</button><button class="wui-button wui-button--outline" type="button" disabled={!operations().includes("model.service.test")} onClick={() => void testService(service.service_id!)}>Probe</button></div></Show></article>}</For><Show when={!services().length}><p>{zh() ? "尚未连接 Model Service。" : "No Model Service is connected yet."}</p></Show></div>
            </section>

            <section class="qf-editorial-sheet"><span class="nf-eyebrow">MODEL SELECTION</span><h2>{zh() ? "自动选择" : "Automatic selection"}</h2><div class="qf-default-model-row"><div><strong>{text().autoTitle}</strong><p>{zh() ? "默认使用 Core eligibility/capability evidence；Studio 不靠 vendor 名猜能力。" : "Core eligibility/capability evidence is the default; Studio never guesses capability from a vendor name."}</p></div><span class="wui-badge wui-badge--outline">DEFAULT</span></div></section>
          </div></Show>

          <Show when={section() === "appearance"}><section class="qf-editorial-sheet"><span class="nf-eyebrow">APPEARANCE</span><h2>{zh() ? "外观" : "Appearance"}</h2><p>{zh() ? "主题继续服从 Story Loom 的 warm ivory / dark roles；语言必须支持中英文扩张。" : "Theme follows Story Loom warm-ivory / dark roles; layout must tolerate Chinese and English expansion."}</p><button class="wui-button wui-button--outline" type="button" onClick={() => setLocale(locale() === "zh-CN" ? "en-US" : "zh-CN")}>{locale() === "zh-CN" ? "English" : "中文"}</button></section></Show>

          <Show when={section() === "advanced"}><section class="qf-editorial-sheet"><span class="nf-eyebrow">ADVANCED</span><h2>{zh() ? "协议与诊断只在这里出现" : "Protocol and diagnostics stay here"}</h2><p>{zh() ? "Provider/vendor/protocol identity 只能作为 Core observation；它们不是普通设置实体。" : "Provider/vendor/protocol identity is Core observation only; it is not an ordinary setup entity."}</p><div class="qf-inline-actions"><A class="wui-button wui-button--outline" href="/diagnostics">Diagnostics</A><A class="wui-button wui-button--outline" href="/capabilities">Capabilities</A></div><details><summary>{zh() ? "当前 Core operations" : "Current Core operations"}</summary><pre class="qf-diff"><code>{operations().join("\n") || "unbound"}</code></pre></details></section></Show>
        </div>
      </div>
    </section>
  );
}
