import { Show, createSignal } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { CoreRequirementNotice } from "../authoring/AuthoringUI";

export default function Project() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [projectId, setProjectId] = createSignal(studio.projectId());
  const [message, setMessage] = createSignal<string>();
  const [error, setError] = createSignal<string>();
  const [busy, setBusy] = createSignal(false);
  const projection = () => studio.projectProjection();

  const open = async () => {
    if (!projectId().trim()) return;
    setBusy(true); setError(undefined); setMessage(undefined);
    await studio.inspectProject(projectId().trim());
    setBusy(false);
    if (studio.projectError()) setError(studio.projectError());
    else setMessage(zh() ? "已从 Core 读取 Project identity。" : "Project identity loaded from Core.");
  };

  const backup = async () => {
    if (!studio.projectId()) return;
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge<{ bundle_ref?: string; verified?: boolean }>("project.backup", { project_id: studio.projectId() });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setMessage(`${zh() ? "Verified backup" : "Verified backup"}: ${result.data.bundle_ref ?? "created"}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  };

  return (
    <section class="nf-page qf-project-page">
      <PageIntro eyebrow="PROJECT" title={zh() ? "Project identity 来自 Core。" : "Project identity comes from Core."} body={zh() ? "Studio 不把浏览器文件夹、路径存在性或 localStorage 当作 Project authority。当前打开方式使用稳定 Project ID。" : "Studio never treats a browser folder, path existence or localStorage as Project authority. Opening currently uses a stable Project ID."} />
      <section class="qf-editorial-sheet">
        <form class="qf-project-open-line" onSubmit={(event) => { event.preventDefault(); void open(); }}>
          <label class="nf-field-label"><span>Project ID</span><input class="wui-input nf-mono" value={projectId()} onInput={(event) => setProjectId(event.currentTarget.value)} autocomplete="off" spellcheck={false} /></label>
          <button class="wui-button wui-button--solid" disabled={busy() || !projectId().trim()}>{busy() ? (zh() ? "读取中…" : "Loading…") : (zh() ? "从 Core 打开" : "Open from Core")}</button>
        </form>
        <CoreRequirementNotice operation="project.list" compact />
      </section>

      <Show when={projection()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "尚未打开 Project" : "No Project open"}</strong></div>}>
        {(project) => <section class="qf-project-identity">
          <div><span class="nf-eyebrow">IDENTITY</span><h2>{project().project.title}</h2><code>{project().project.project_id}</code></div>
          <dl><dt>{zh() ? "语言" : "Language"}</dt><dd>{project().project.language}</dd><dt>Schema</dt><dd>{project().project.project_schema_version}</dd><dt>{zh() ? "正文" : "Documents"}</dt><dd>{project().counts.documents ?? 0}</dd><dt>{zh() ? "候选" : "Candidates"}</dt><dd>{project().counts.candidates ?? 0}</dd><dt>{zh() ? "运行" : "Runs"}</dt><dd>{project().counts.runs ?? 0}</dd></dl>
          <div class="qf-inline-actions"><A class="wui-button wui-button--solid" href={`/manuscript?project=${encodeURIComponent(project().project.project_id)}`}>{zh() ? "打开正文" : "Open Manuscript"}</A><button class="wui-button wui-button--outline" type="button" disabled={busy() || !studio.bridgeCapabilities()?.operations.includes("project.backup")} onClick={() => void backup()}>{zh() ? "Verified backup" : "Verified backup"}</button></div>
        </section>}
      </Show>
      <Show when={message()}>{(value) => <p class="qf-success-note" role="status">{value()}</p>}</Show><Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Project</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
    </section>
  );
}
