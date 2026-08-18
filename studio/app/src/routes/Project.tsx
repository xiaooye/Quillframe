import { For, Show, createMemo, createSignal, onMount } from "solid-js";
import { A } from "@solidjs/router";
import { invokeBridge, operationError } from "../bridge";
import { useI18n } from "../i18n";
import { useStudio, type ProjectInspectData } from "../studio";

interface ProjectListItem { project_id: string; title: string; language: string; project_schema_version: number; registered_at: string; last_opened_at: string; }
interface ProjectList { items: ProjectListItem[]; }
interface ExportResult { artifact_ref: string; file_name: string; }

export default function Project() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = createMemo(() => locale() === "zh-CN");
  const t = (en: string, cn: string) => zh() ? cn : en;
  const [projects, setProjects] = createSignal<ProjectListItem[]>([]);
  const [error, setError] = createSignal<string>();
  const [status, setStatus] = createSignal<string>();
  const [deleteConfirm, setDeleteConfirm] = createSignal("");
  const current = () => studio.projectResult()?.data as ProjectInspectData | null | undefined;

  const load = async () => {
    const result = await invokeBridge<ProjectList>("project.list");
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    setProjects(result.data.items);
    const id = studio.projectId() || result.data.items[0]?.project_id;
    if (id) await studio.inspectProject(id);
  };

  const backup = async () => {
    const id = studio.projectId(); if (!id) return;
    const result = await invokeBridge("project.backup", { project_id: id });
    setStatus(result.status === "ok" ? t("Verified backup created.", "已创建并校验 Backup。") : operationError(result));
  };

  const exportPortable = async () => {
    const id = studio.projectId(); if (!id) return;
    const result = await invokeBridge<ExportResult>("project.export", { project_id: id });
    setStatus(result.status === "ok" && result.data ? `${result.data.file_name} · ${t("ready from Manuscript export action", "可在手稿页下载")}` : operationError(result));
  };

  const remove = async () => {
    const id = studio.projectId();
    if (!id || deleteConfirm() !== id) return;
    const result = await invokeBridge("project.delete", { project_id: id, confirm_project_id: id, user_authorized: true, backup_first: true });
    if (result.status !== "ok") { setError(operationError(result)); return; }
    setDeleteConfirm(""); studio.setProjectId(""); setStatus(t("Project removed after verified backup.", "Project 已在备份后移除。"));
    await load();
  };

  onMount(() => { void load().catch((cause) => setError(cause instanceof Error ? cause.message : String(cause))); });

  return <section class="nf-page nf-project-page nf-authoring-canvas">
    <header class="nf-manuscript-header"><div><span class="nf-eyebrow">PROJECT</span><h1>{t("Projects", "Project 管理")}</h1><p>{t("Native Core projects only. Browser folders are not treated as authority.", "这里只管理原生 Core Project；浏览器文件夹不会被当成 authority。")}</p></div><A class="wui-button" href="/start">{t("New / Import", "新建 / 导入")}</A></header>
    <div class="nf-review-layout">
      <aside class="nf-binder"><For each={projects()} fallback={<p class="nf-subtle">{t("No projects yet.", "还没有 Project。")}</p>}>{(project) => <button class="nf-binder-item" type="button" data-active={studio.projectId() === project.project_id ? "true" : undefined} onClick={() => void studio.inspectProject(project.project_id)}><span>{project.title}</span><small>{project.project_id} · {project.language}</small></button>}</For></aside>
      <main class="nf-review-main"><Show when={current()} fallback={<p>{t("Choose a project.", "选择一个 Project。")}</p>}>{(projection) => <>
        <section class="nf-editorial-section"><div class="nf-section-heading"><span class="nf-eyebrow">IDENTITY</span><h2>{projection().project.title}</h2></div><div class="nf-detail-list"><div><span>ID</span><strong>{projection().project.project_id}</strong></div><div><span>{t("Language", "语言")}</span><strong>{projection().project.language}</strong></div><div><span>Schema</span><strong>{projection().project.project_schema_version}</strong></div></div></section>
        <section class="nf-editorial-section"><div class="nf-section-heading"><span class="nf-eyebrow">OPERATIONS</span><h2>{t("Durability", "持久化")}</h2></div><div class="nf-inline-actions"><A class="wui-button" href={`/manuscript?project=${encodeURIComponent(projection().project.project_id)}`}>{t("Open manuscript", "打开手稿")}</A><button class="wui-button wui-button--outline" onClick={() => void backup()}>{t("Backup", "备份")}</button><button class="wui-button wui-button--outline" onClick={() => void exportPortable()}>.qfproject</button></div></section>
        <section class="nf-editorial-section"><div class="nf-section-heading"><span class="nf-eyebrow">DANGER</span><h2>{t("Remove project", "移除 Project")}</h2></div><p>{t("Removal requires typing the exact project id and creates a verified backup first.", "必须输入完整 Project ID；移除前会先创建经校验的 Backup。")}</p><div class="nf-inline-actions"><input value={deleteConfirm()} onInput={(e) => setDeleteConfirm(e.currentTarget.value)} placeholder={projection().project.project_id} /><button class="wui-button wui-button--outline" disabled={deleteConfirm() !== projection().project.project_id} onClick={() => void remove()}>{t("Remove", "移除")}</button></div></section>
      </>}</Show></main>
    </div>
    <Show when={studio.projectError() || error()}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong>{studio.projectError() || error()}</strong></div></div></Show>
    <Show when={status()}><div class="wui-alert" role="status"><div class="wui-alert__body"><span>{status()}</span></div></div></Show>
  </section>;
}
