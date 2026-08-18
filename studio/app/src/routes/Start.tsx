import { Show, createMemo, createSignal } from "solid-js";
import { A, useNavigate } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { ProjectCreateResult } from "../authoring/contracts";
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
  const [busy, setBusy] = createSignal(false);
  const [message, setMessage] = createSignal<string>();
  const [error, setError] = createSignal<string>();
  const capabilities = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);

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
      navigate(`/manuscript?project=${encodeURIComponent(result.data.project_id)}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setBusy(false); }
  };

  const openProject = async () => {
    const id = openingId().trim();
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

  return (
    <section class="nf-page qf-start-page">
      <PageIntro
        eyebrow={zh() ? "AUTHORING FIRST · CORE-BACKED" : "AUTHORING FIRST · CORE-BACKED"}
        title={zh() ? "开始写，而不是先配置一套系统。" : "Start writing, not administering a system."}
        body={zh() ? "Project 创建与打开只通过 typed Core operation。浏览器只记住最近使用的 Project ID，不保存正文 authority。" : "Project creation and opening use typed Core operations only. The browser remembers a recent Project ID, never manuscript authority."}
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
            <span class="nf-eyebrow">02 · OPEN PROJECT</span>
            <h2 id="open-project-heading">{zh() ? "打开现有 Project" : "Open existing Project"}</h2>
            <p>{zh() ? "当前 Core 尚未提供 Project registry projection，所以这里按稳定 Project ID 打开。" : "Core does not yet expose a Project registry projection, so opening is by stable Project ID."}</p>
            <label class="nf-field-label"><span>Project ID</span><input class="wui-input nf-mono" value={openingId()} onInput={(event) => setOpeningId(event.currentTarget.value)} autocomplete="off" spellcheck={false} placeholder="my-novel" /></label>
            <button class="wui-button wui-button--outline" type="button" disabled={busy() || !capabilities().includes("project.inspect") || !openingId().trim()} onClick={() => void openProject()}>{zh() ? "打开" : "Open"}</button>
            <CoreRequirementNotice operation="project.list" />
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
