import { Show, createMemo, createSignal } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { PageIntro } from "../components";
import { bridgeTransportName, invokeBridge, operationError } from "../bridge";
import { useI18n } from "../i18n";

interface ProjectCreateResult { project_id: string; created: boolean; }
interface ModelConnectResult { service_id: string; endpoint: string; models?: Array<{ model_id?: string; display_name?: string }>; credential_persistence: string; }
interface ArtifactUploadResult { artifact_ref: string; }
interface ProjectImportResult { project_id: string; imported: boolean; }

function toBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunk = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunk) {
    binary += String.fromCharCode(...bytes.subarray(offset, Math.min(bytes.length, offset + chunk)));
  }
  return btoa(binary);
}

const copy = {
  "en-US": {
    eyebrow: "One project · one Core · many hosts",
    title: "Start writing",
    body: "Create a native Quillframe project, optionally connect a model endpoint, then enter the manuscript workspace. Browser storage never becomes project authority.",
    project: "New Project", projectId: "Project ID", titleLabel: "Title", language: "Language", create: "Create project",
    model: "Connect AI", endpoint: "API Endpoint", token: "Access Token", connect: "Connect & discover models", skip: "Start writing without AI",
    tokenNote: "The token is session-only on this host. Its value is not written to SQLite, project state, context, receipts, exports, or .qfproject.",
    importTitle: "Open a portable project", importBody: "Import a validated .qfproject package. Existing projects are never replaced silently.", importAction: "Import .qfproject",
    created: "Project persisted in native Core.", connected: "Connected. Model discovery completed.", unavailable: "Core host is not bound. Authoritative project creation is unavailable on this deployment.",
    transport: "Transport", models: "Discovered models", busy: "Working…",
  },
  "zh-CN": {
    eyebrow: "一个 Project · 一个 Core · 多种宿主",
    title: "开始写作",
    body: "创建原生 Quillframe Project，可选连接模型 Endpoint，然后直接进入手稿工作区。浏览器存储永远不会成为 Project authority。",
    project: "新建 Project", projectId: "Project ID", titleLabel: "书名", language: "语言", create: "创建 Project",
    model: "连接 AI", endpoint: "API Endpoint", token: "Access Token", connect: "连接并发现模型", skip: "先不连接 AI，开始写作",
    tokenNote: "Token 在当前宿主默认只存于会话内存；值不会写入 SQLite、Project state、Context、Receipt、Export 或 .qfproject。",
    importTitle: "打开可携 Project", importBody: "导入经过校验的 .qfproject。已有同名 Project 不会被静默覆盖。", importAction: "导入 .qfproject",
    created: "Project 已持久化到原生 Core。", connected: "连接成功，模型发现已完成。", unavailable: "当前部署没有绑定 Core host，因此不能创建权威 Project。",
    transport: "Transport", models: "发现的模型", busy: "处理中…",
  },
} as const;

export default function Start() {
  const { locale } = useI18n();
  const text = createMemo(() => copy[locale()]);
  const navigate = useNavigate();
  const [projectId, setProjectId] = createSignal("");
  const [title, setTitle] = createSignal("");
  const [language, setLanguage] = createSignal(locale() === "zh-CN" ? "zh-CN" : "en");
  const [createdProject, setCreatedProject] = createSignal<string>();
  const [endpoint, setEndpoint] = createSignal("");
  const [token, setToken] = createSignal("");
  const [model, setModel] = createSignal<ModelConnectResult>();
  const [busy, setBusy] = createSignal(false);
  const [message, setMessage] = createSignal<string>();
  const [error, setError] = createSignal<string>();

  const createProject = async () => {
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge<ProjectCreateResult>("project.create", { project_id: projectId().trim(), title: title().trim(), language: language() });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setCreatedProject(result.data.project_id);
      setMessage(text().created);
      localStorage.setItem("quillframe.ui.lastProjectId", result.data.project_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  };

  const connectModel = async () => {
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge<ModelConnectResult>("model.connect", { endpoint: endpoint().trim(), access_token: token() });
      setToken("");
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setModel(result.data);
      setMessage(text().connected);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); setToken(""); }
    finally { setBusy(false); }
  };

  const enterProject = () => {
    const id = createdProject();
    if (id) navigate(`/manuscript?project=${encodeURIComponent(id)}`);
  };

  const importProject = async (file: File) => {
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      if (!file.name.endsWith(".qfproject")) throw new Error("Only .qfproject files are supported");
      const payload = toBase64(new Uint8Array(await file.arrayBuffer()));
      const uploaded = await invokeBridge<ArtifactUploadResult>("artifact.upload", { file_name: file.name, payload_base64: payload });
      if (uploaded.status !== "ok" || !uploaded.data) throw new Error(operationError(uploaded));
      const imported = await invokeBridge<ProjectImportResult>("project.import", { artifact_ref: uploaded.data.artifact_ref, replace: false });
      if (imported.status !== "ok" || !imported.data) throw new Error(operationError(imported));
      localStorage.setItem("quillframe.ui.lastProjectId", imported.data.project_id);
      navigate(`/manuscript?project=${encodeURIComponent(imported.data.project_id)}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  };

  return (
    <section class="nf-page nf-start-page nf-authoring-canvas">
      <PageIntro eyebrow={text().eyebrow} title={text().title} body={text().body} />

      <Show when={bridgeTransportName() !== "unbound"} fallback={<div class="wui-alert" role="status"><div class="wui-alert__body"><strong>{text().unavailable}</strong></div></div>}>
        <p class="nf-subtle"><strong>{text().transport}:</strong> {bridgeTransportName()}</p>

        <section class="nf-editorial-section" aria-labelledby="new-project-heading">
          <div class="nf-section-heading"><span class="nf-eyebrow">01</span><h2 id="new-project-heading">{text().project}</h2></div>
          <div class="nf-field-grid">
            <label class="nf-field"><span>{text().projectId}</span><input value={projectId()} onInput={(e) => setProjectId(e.currentTarget.value)} autocomplete="off" placeholder="my-novel" /></label>
            <label class="nf-field"><span>{text().titleLabel}</span><input value={title()} onInput={(e) => setTitle(e.currentTarget.value)} placeholder="My Novel" /></label>
            <label class="nf-field"><span>{text().language}</span><select value={language()} onChange={(e) => setLanguage(e.currentTarget.value)}><option value="zh-CN">中文</option><option value="en">English</option></select></label>
          </div>
          <button class="wui-button" type="button" disabled={busy() || !projectId().trim() || !title().trim()} onClick={() => void createProject()}>{busy() ? text().busy : text().create}</button>
        </section>

        <Show when={createdProject()}>
          <section class="nf-editorial-section" aria-labelledby="connect-model-heading">
            <div class="nf-section-heading"><span class="nf-eyebrow">02 · optional</span><h2 id="connect-model-heading">{text().model}</h2></div>
            <div class="nf-field-grid nf-field-grid--wide">
              <label class="nf-field"><span>{text().endpoint}</span><input type="url" value={endpoint()} onInput={(e) => setEndpoint(e.currentTarget.value)} placeholder="https://api.example.com/v1" autocomplete="url" /></label>
              <label class="nf-field"><span>{text().token}</span><input type="password" value={token()} onInput={(e) => setToken(e.currentTarget.value)} autocomplete="off" /></label>
            </div>
            <p class="nf-subtle">{text().tokenNote}</p>
            <div class="nf-inline-actions">
              <button class="wui-button" type="button" disabled={busy() || !endpoint().trim() || !token()} onClick={() => void connectModel()}>{text().connect}</button>
              <button class="wui-button wui-button--ghost" type="button" onClick={enterProject}>{text().skip}</button>
            </div>
            <Show when={model()}>{(connected) => <div class="nf-status-line"><strong>{text().models}:</strong> {connected().models?.map((item) => item.display_name || item.model_id).filter(Boolean).join(", ") || "—"}</div>}</Show>
          </section>
        </Show>

        <section class="nf-editorial-section" aria-labelledby="import-project-heading">
          <div class="nf-section-heading"><span class="nf-eyebrow">portable</span><h2 id="import-project-heading">{text().importTitle}</h2></div>
          <p>{text().importBody}</p>
          <label class="wui-button wui-button--outline nf-file-button">
            {text().importAction}
            <input class="nf-visually-hidden" type="file" accept=".qfproject,application/zip" disabled={busy()} onChange={(event) => { const file = event.currentTarget.files?.[0]; if (file) void importProject(file); }} />
          </label>
        </section>

        <Show when={message()}><div class="wui-alert" role="status"><div class="wui-alert__body"><span>{message()}</span></div></div></Show>
        <Show when={error()}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong>{error()}</strong></div></div></Show>
      </Show>
    </section>
  );
}
