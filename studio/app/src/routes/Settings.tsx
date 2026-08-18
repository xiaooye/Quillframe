import { For, Show, createMemo, createSignal } from "solid-js";
import { A, useSearchParams } from "@solidjs/router";
import { CoreHostBoundary, PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

type SettingsSection = "general" | "models" | "appearance" | "advanced";
type CapabilityState = "verified" | "detected" | "unknown" | "unavailable";

const sections: ReadonlyArray<{ id: SettingsSection; en: string; zh: string }> = [
  { id: "general", en: "General", zh: "通用" },
  { id: "models", en: "AI & Models", zh: "AI 与模型" },
  { id: "appearance", en: "Appearance", zh: "外观" },
  { id: "advanced", en: "Advanced", zh: "高级" },
];

const capabilityLegend: ReadonlyArray<{ state: CapabilityState; en: string; zh: string; detailEn: string; detailZh: string }> = [
  { state: "verified", en: "Verified", zh: "已验证", detailEn: "Quillframe has direct evidence from an executed probe or runtime result.", detailZh: "Quillframe 已从真实探测或运行结果获得直接证据。" },
  { state: "detected", en: "Detected", zh: "已检测", detailEn: "The Model Runtime observed metadata but has not independently verified behavior.", detailZh: "Model Runtime 已观察到相关元数据，但尚未独立验证实际行为。" },
  { state: "unknown", en: "Unknown", zh: "未知", detailEn: "No reliable observation is available yet.", detailZh: "当前还没有足够可靠的观察结果。" },
  { state: "unavailable", en: "Unavailable", zh: "不可用", detailEn: "The runtime has evidence that this capability is not available.", detailZh: "运行时已有证据表明该能力不可用。" },
];

const copy = {
  "en-US": {
    eyebrow: "GLOBAL SETTINGS · HOST-OWNED",
    title: "Settings that stay out of your manuscript.",
    body: "Configure Studio behavior and connect model APIs without turning runtime infrastructure into Project or Canon state.",
    generalTitle: "General",
    generalBody: "Global host settings appear here only when Quillframe Core exposes a truthful contract. Studio does not synthesize persistence or write Project files on its own.",
    generalNote: "Project truth, Canon, runtime state, and host settings remain separate authority domains.",
    modelsEyebrow: "MODEL API",
    modelsTitle: "Connect a model API with two fields.",
    modelsBody: "The product abstraction is Quillframe → Model Service → API Endpoint + Access Token. Vendor identity, protocol, compatibility, and capability remain runtime observations rather than setup fields.",
    servicesTitle: "Model Services",
    servicesBody: "A Model Service is an API endpoint Quillframe can use for inference. Connection setup always uses the same two-field surface.",
    addService: "Add model service",
    endpoint: "API Endpoint",
    endpointPlaceholder: "https://api.example.com/v1",
    token: "Access Token",
    tokenPlaceholder: "Optional for endpoints that do not require authentication",
    tokenHelp: "The token may be empty for local endpoints that require no authentication. Saved secrets belong in host secret storage and are never shown again by Studio.",
    connect: "Connect",
    contractPending: "Connection is disabled because this branch does not yet expose an operation-specific Model Runtime command through the Host Bridge. Studio will not simulate a successful connection.",
    coreUnbound: "A bound Quillframe Core is required before a model API can be connected.",
    serviceProjectionTitle: "Connected services",
    serviceProjectionEmpty: "Core does not expose a Model Service projection yet. Studio will not infer services from endpoint history, hostname, browser state, or vendor names.",
    modelsListTitle: "Discovered models",
    modelsListBody: "Models appear only after Core reports model discovery from a connected Model Service.",
    modelsListEmpty: "No discovered-model projection is available yet.",
    usageTitle: "Model usage",
    autoTitle: "Automatic model selection",
    autoBadge: "DEFAULT",
    autoBody: "Quillframe chooses an eligible model from runtime evidence and task requirements. An exact-model preference never becomes capability, eligibility, independence, or authority.",
    preferenceTitle: "Exact-model preference",
    preferenceBody: "Available only after Core reports discovered models and eligibility for the relevant task. No model choice is required during onboarding.",
    capabilityTitle: "Capability evidence",
    capabilityBody: "Settings is read-only for capability truth. Manual overrides, when Core supports them, belong in advanced Inspector / Diagnostics and can never appear as Verified.",
    appearanceTitle: "Appearance",
    appearanceBody: "Theme and language controls already live in the Studio top bar. Persistent appearance settings will use host-owned settings contracts when available.",
    advancedTitle: "Advanced",
    advancedBody: "Runtime evidence belongs in Inspector and Diagnostics. Vendor identity, when detected, is diagnostic metadata only—not a setup entity.",
    openInspector: "Open Inspector",
    openDiagnostics: "Open Diagnostics",
    bridgeContracts: "Model Runtime bridge signals",
    noBridgeContracts: "bridge.describe currently exposes no model/inference-related operation.",
    modelBoundary: "User → Quillframe → Model API",
  },
  "zh-CN": {
    eyebrow: "全局设置 · 宿主管理",
    title: "设置留在作品之外。",
    body: "配置 Studio、连接模型 API，同时不把运行基础设施混入 Project 或 Canon。",
    generalTitle: "通用",
    generalBody: "只有 Quillframe Core 暴露真实契约后，全局宿主设置才会在这里出现。Studio 不会自行伪造持久化，也不会暗中写入 Project 文件。",
    generalNote: "Project truth、Canon、运行状态与宿主设置始终属于不同的 authority domain。",
    modelsEyebrow: "模型 API",
    modelsTitle: "只用两个字段连接模型 API。",
    modelsBody: "产品关系固定为 Quillframe → Model Service → API Endpoint + Access Token。厂商身份、协议、兼容方式与模型能力都属于运行时观察结果，不是设置字段。",
    servicesTitle: "模型服务",
    servicesBody: "Model Service 就是 Quillframe 可用于推理的 API 地址。创建连接始终只有同一套两个字段。",
    addService: "添加模型服务",
    endpoint: "API Endpoint",
    endpointPlaceholder: "https://api.example.com/v1",
    token: "Access Token",
    tokenPlaceholder: "无需认证的本机 endpoint 可以留空",
    tokenHelp: "无需认证的本机 endpoint 可以留空。真正保存后的 secret 必须进入宿主 secret store，Studio 不会再次显示明文。",
    connect: "连接",
    contractPending: "当前分支的 Host Bridge 尚未公开 Model Runtime 的专用 command，因此连接按钮保持禁用。Studio 不会模拟连接成功。",
    coreUnbound: "连接模型 API 前需要先绑定 Quillframe Core。",
    serviceProjectionTitle: "已连接的模型服务",
    serviceProjectionEmpty: "Core 当前尚未提供 Model Service 投影。Studio 不会根据 endpoint 历史、hostname、浏览器状态或厂商名称自行推断连接。",
    modelsListTitle: "已发现模型",
    modelsListBody: "只有 Core 从真实 Model Service 返回模型发现结果后，模型才会出现在这里。",
    modelsListEmpty: "当前尚无已发现模型的投影。",
    usageTitle: "模型使用方式",
    autoTitle: "自动选择模型",
    autoBadge: "默认",
    autoBody: "Quillframe 根据运行证据与任务要求选择有资格的模型。指定模型偏好永远不等于 capability、eligibility、independence 或 authority。",
    preferenceTitle: "指定模型偏好",
    preferenceBody: "只有 Core 已提供已发现模型和对应任务的 eligibility 后才开放。首次设置不要求选择模型。",
    capabilityTitle: "能力证据",
    capabilityBody: "普通 Settings 只读展示模型能力事实。若 Core 支持手动覆盖，它只进入高级 Inspector / Diagnostics，而且永远不能显示成 Verified。",
    appearanceTitle: "外观",
    appearanceBody: "主题与语言控制目前已经位于 Studio 顶栏。后续需要持久化时，也只通过宿主设置契约。",
    advancedTitle: "高级",
    advancedBody: "运行证据进入 Inspector 与 Diagnostics。厂商身份即使被检测到，也只能作为 diagnostic metadata，而不是设置实体。",
    openInspector: "打开 Inspector",
    openDiagnostics: "打开 Diagnostics",
    bridgeContracts: "Model Runtime bridge signals",
    noBridgeContracts: "bridge.describe 当前没有公开 model / inference 相关 operation。",
    modelBoundary: "User → Quillframe → Model API",
  },
} as const;

function CapabilityBadge(props: { state: CapabilityState; label: string }) {
  return <span class="nf-capability-state" data-state={props.state}><span aria-hidden="true" />{props.label}</span>;
}

export default function Settings() {
  const { locale } = useI18n();
  const studio = useStudio();
  const [params, setParams] = useSearchParams();
  const text = createMemo(() => copy[locale()]);
  const zh = () => locale() === "zh-CN";
  const [endpoint, setEndpoint] = createSignal("");
  const [token, setToken] = createSignal("");

  const section = createMemo<SettingsSection>(() => {
    const candidate = params.section as SettingsSection | undefined;
    return sections.some((item) => item.id === candidate) ? candidate! : "models";
  });

  const modelBridgeSignals = createMemo(() => {
    const description = studio.bridgeDescription();
    if (!description) return [] as string[];
    const operations = [...description.supported_operations, ...Object.keys(description.deferred_operations ?? {})];
    return operations.filter((operation) => /model|inference/i.test(operation));
  });

  const chooseSection = (id: SettingsSection) => setParams({ section: id }, { replace: true });

  return (
    <section class="nf-page nf-settings-page">
      <PageIntro eyebrow={text().eyebrow} title={text().title} body={text().body} />

      <div class="nf-settings-layout">
        <nav class="nf-settings-nav" aria-label={zh() ? "设置分类" : "Settings sections"}>
          <For each={sections}>{(item) => (
            <button type="button" data-active={section() === item.id ? "true" : undefined} onClick={() => chooseSection(item.id)}>{zh() ? item.zh : item.en}</button>
          )}</For>
        </nav>

        <div class="nf-settings-main">
          <Show when={section() === "general"}>
            <section class="nf-settings-section">
              <span class="nf-eyebrow">SETTINGS</span>
              <h2>{text().generalTitle}</h2>
              <p>{text().generalBody}</p>
              <div class="nf-settings-note"><strong>authority boundary</strong><span>{text().generalNote}</span></div>
            </section>
          </Show>

          <Show when={section() === "models"}>
            <section class="nf-settings-section nf-model-settings-intro">
              <span class="nf-eyebrow">{text().modelsEyebrow}</span>
              <h2>{text().modelsTitle}</h2>
              <p>{text().modelsBody}</p>
              <code class="nf-model-mental-model">{text().modelBoundary}</code>
            </section>

            <section class="nf-settings-section" aria-labelledby="model-services-heading">
              <div class="nf-settings-section-head"><div><span class="nf-section-index">01</span><h2 id="model-services-heading">{text().servicesTitle}</h2><p>{text().servicesBody}</p></div></div>
              <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
                <div class="nf-model-connect-surface">
                  <div class="nf-model-connect-copy"><span class="nf-eyebrow">{text().addService}</span><strong>{text().endpoint} + {text().token}</strong></div>
                  <div class="nf-model-connect-form" role="group" aria-label={text().addService}>
                    <label class="nf-field-label"><span>{text().endpoint}</span><input class="wui-input nf-mono" inputmode="url" autocomplete="url" spellcheck={false} value={endpoint()} onInput={(event) => setEndpoint(event.currentTarget.value)} placeholder={text().endpointPlaceholder} /></label>
                    <label class="nf-field-label"><span>{text().token}</span><input class="wui-input nf-mono" type="password" autocomplete="new-password" value={token()} onInput={(event) => setToken(event.currentTarget.value)} placeholder={text().tokenPlaceholder} /><small class="nf-field-help">{text().tokenHelp}</small></label>
                    <button class="wui-button wui-button--solid" type="button" disabled aria-disabled="true">{text().connect}</button>
                    <p class="nf-model-contract-note">{text().contractPending}</p>
                  </div>
                </div>
              </Show>
              <div class="nf-model-observation-block"><div><strong>{text().serviceProjectionTitle}</strong><span class="wui-badge wui-badge--outline">Core observation</span></div><p>{studio.bridgeAvailable() ? text().serviceProjectionEmpty : text().coreUnbound}</p></div>
            </section>

            <section class="nf-settings-section" aria-labelledby="discovered-models-heading">
              <div class="nf-settings-section-head"><div><span class="nf-section-index">02</span><h2 id="discovered-models-heading">{text().modelsListTitle}</h2><p>{text().modelsListBody}</p></div></div>
              <div class="nf-model-empty-state"><span aria-hidden="true">✦</span><p>{text().modelsListEmpty}</p></div>
            </section>

            <section class="nf-settings-section" aria-labelledby="model-usage-heading">
              <div class="nf-settings-section-head"><div><span class="nf-section-index">03</span><h2 id="model-usage-heading">{text().usageTitle}</h2></div></div>
              <div class="nf-model-usage-row"><div><strong>{text().autoTitle}</strong><p>{text().autoBody}</p></div><span class="wui-badge wui-badge--success">{text().autoBadge}</span></div>
              <div class="nf-model-usage-row" data-muted><div><strong>{text().preferenceTitle}</strong><p>{text().preferenceBody}</p></div><span class="wui-badge wui-badge--outline">unavailable</span></div>
            </section>

            <section class="nf-settings-section" aria-labelledby="capability-evidence-heading">
              <div class="nf-settings-section-head"><div><span class="nf-section-index">04</span><h2 id="capability-evidence-heading">{text().capabilityTitle}</h2><p>{text().capabilityBody}</p></div></div>
              <div class="nf-capability-legend"><For each={capabilityLegend}>{(item) => <div class="nf-capability-row"><CapabilityBadge state={item.state} label={zh() ? item.zh : item.en} /><p>{zh() ? item.detailZh : item.detailEn}</p></div>}</For></div>
            </section>
          </Show>

          <Show when={section() === "appearance"}><section class="nf-settings-section"><span class="nf-eyebrow">APPEARANCE</span><h2>{text().appearanceTitle}</h2><p>{text().appearanceBody}</p></section></Show>

          <Show when={section() === "advanced"}>
            <section class="nf-settings-section">
              <span class="nf-eyebrow">ADVANCED</span><h2>{text().advancedTitle}</h2><p>{text().advancedBody}</p>
              <div class="nf-settings-actions"><A class="wui-button wui-button--outline" href="/inspect">{text().openInspector}</A><A class="wui-button wui-button--outline" href="/diagnostics">{text().openDiagnostics}</A></div>
              <details class="nf-settings-contracts"><summary>{text().bridgeContracts}</summary><Show when={modelBridgeSignals().length > 0} fallback={<p>{text().noBridgeContracts}</p>}><div class="nf-chip-row"><For each={modelBridgeSignals()}>{(operation) => <code>{operation}</code>}</For></div></Show></details>
            </section>
          </Show>
        </div>
      </div>
    </section>
  );
}
