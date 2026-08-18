import { For, Show, createMemo, createSignal, onMount } from "solid-js";
import { A, useNavigate } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { ProjectCreateResult, ProjectListProjection, ProjectRegistryItem } from "../authoring/contracts";
import { CoreRequirementNotice } from "../authoring/AuthoringUI";

export default function Start() {
  const { locale } = useI18n();
  const studio = useStudio();
  const navigate = useNavigate();
  const zh = () => locale() === "zh-CN";
  const [projectId, setProjectId] = createSignal(studio.projectId());
  const [title, setTitle] = createSignal("");
  const [language, setLanguage] = createSignal("zh-CN");
  const [openingId, setOpeningId] = createSignal(studio.projectId());
  const [projects, setProjects] = createSignal<ProjectRegistryItem[]>([]);
  const [busy, setBusy] = createSignal(false);
  const [message, setMessage] = createSignal<string>();
  const [error, setError] = createSignal<string>();
  const capabilities = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);

  const openProject = async (requested = openingId()) => {
    const id = requested.trim();
    if (!id) return;
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      await studio.inspectProject(id);
      if (studio.projectError()) throw new Error(studio.projectError());
      studio.setProjectId(id);
      navigate(`/manuscript?project=${encodeURIComponent(id)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setBusy(false); }
  };

  const loadProjects = async () => {
    if (!capabilities().includes("project.list")) return;
    try {
      const result = await invokeBridge<ProjectListProjection>("project.list", { limit: 100 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setProjects(result.data.items ?? []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const createProject = async () => {
    if (!projectId().trim() || !title().trim()) return;
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge<ProjectCreateResult>("project.create", {
        project_id: projectId().trim(),
        title: title().trim(),
        language: language(),
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      studio.setProjectId(result.data.project_id);
      await studio.inspectProject(result.data.project_id);
      await loadProjects();
      navigate(`/manuscript?project=${encodeURIComponent(result.data.project_id)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setBusy(false); }
  };

  onMount(() => { if (studio.bridgeAvailable()) void loadProjects(); });

  return (
    <section class="nf-page qf-start-page">
      <PageIntro
        eyebrow="AUTHORING FIRST · CORE-BACKED"
        title={zh() ? "开始写，而不是先配置一套系统。" : "Start writing, not administering a system."}
        body={zh() ? "Project registry、Project 创建与打开全部来自 typed Core。浏览器只保存最近选择，永远不是作品 authority。" : "Project registry, creation and opening all come from typed Core. The browser remembers a recent choice only; it is never work authority."}
      />

      <Show when={studio.bridgeAvailable()} fallback={<div class="qf-empty-workspace" role="status"><strong>{zh() ? "Core 未绑定" : "Core unbound"}</strong><p>{zh() ? "Hosted Studio 需要 hosted Core；Desktop 需要 Tauri local Core bridge。UI 不会用浏览器存储代替。" : "Hosted Studio requires a hosted Core; Desktop requires a Tauri local Core bridge. Browser storage is not a substitute."}</p></div>}>
        <div class="qf-onboarding-grid">
          <section class="qf-editorial-sheet" aria-labelledby="create-project-heading">
            <span class="nf-eyebrow">01 · NEW PROJECT</span>
            <h2 id="create-project-heading">{zh() ? "新建 Project" : "New Project"}</h2>
            <p>{zh() ? "只需要稳定 ID、标题和语言。SQLite authority 由 Core 创建。" : "Only a stable ID, title and language. Core creates SQLite authority."}</p>
            <label class="nf-field-label"><span>Project ID</span><input class="wui-input nf-mono" value={projectId()} onInput={(event) => setProjectId(event.currentTarget.value)} autocomplete="off" spellcheck={false} placeholder="my-novel" /></label>
            <label class="nf-field-label"><span>{zh() ? "标题" : "Title"}</span><input class="wui-input" value={title()} onInput={(event) => setTitle(event.currentTarget.value)} autocomplete="off" /></label>
            <label class="nf-field-label"><span>{zh() ? "语言" : "Language"}</span><select class="wui-input" value={language()} onChange={(event) => setLanguage(event.currentTarget.value)}><option value="zh-CN">中文</option><option value="en-US">English</option></select></label>
            <button class="wui-button wui-button--solid" type="button" disabled={busy() || !capabilities().includes("project.create") || !projectId().trim() || !title().trim()} onClick={() => void createProject()}>{busy() ? (zh() ? "创建中…" : "Creating…") : (zh() ? "创建并打开正文" : "Create & open Manuscript")}</button>
          </section>

          <section class="qf-editorial-sheet" aria-labelledby="open-project-heading">
            <div class="qf-section-head"><div><span class="nf-eyebrow">02 · OPEN PROJECT</span><h2 id="open-project-heading">{zh() ? "打开现有 Project" : "Open existing Project"}</h2></div><button class="wui-button wui-button--outline" type="button" disabled={busy() || !capabilities().includes("project.list")} onClick={() => void loadProjects()}>{zh() ? "刷新" : "Refresh"}</button></div>
            <p>{zh() ? "列表来自 canonical Core registry；最近 Project ID 只用于便利，不参与 authority。" : "The list comes from the canonical Core registry; the recent Project ID is convenience only."}</p>
            <CoreRequirementNotice operation="project.list" compact />
            <div class="qf-model-service-list">
              <For each={projects()}>{(project) => <button class="qf-candidate-row" type="button" disabled={busy()} onClick={() => void openProject(project.project_id)}><strong>{project.title}</strong><span>{project.project_id} · {project.language}</span><small>{project.last_opened_at ?? project.registered_at ?? ""}</small></button>}</For>
              <Show when={!projects().length}><p>{zh() ? "暂无 Project；也可以按稳定 ID 打开。" : "No Projects yet; you can also open by stable ID."}</p></Show>
            </div>
            <label class="nf-field-label"><span>Project ID</span><input class="wui-input nf-mono" value={openingId()} onInput={(event) => setOpeningId(event.currentTarget.value)} autocomplete="off" spellcheck={false} placeholder="my-novel" /></label>
            <button class="wui-button wui-button--outline" type="button" disabled={busy() || !capabilities().includes("project.inspect") || !openingId().trim()} onClick={() => void openProject()}>{zh() ? "按 ID 打开" : "Open by ID"}</button>
          </section>
        </div>
      </Show>

      <Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">{zh() ? "操作失败" : "Operation failed"}</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
      <Show when={message()}>{(value) => <p role="status">{value()}</p>}</Show>

      <section class="qf-start-next">
        <div><span class="nf-eyebrow">AI · OPTIONAL</span><h2>{zh() ? "AI 不阻塞普通写作" : "AI never blocks ordinary authoring"}</h2><p>{zh() ? "需要时再到 AI 与模型输入 Endpoint + Access Token。普通用户不选择 provider 类型。" : "When needed, AI & Models asks only for Endpoint + Access Token. Ordinary users never choose a provider type."}</p></div>
        <A class="wui-button wui-button--outline" href="/settings?section=models">{zh() ? "AI 与模型" : "AI & Models"}</A>
      </section>
    </section>
  );
}
