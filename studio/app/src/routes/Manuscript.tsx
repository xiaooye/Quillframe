import { For, Show, createMemo, createSignal, onCleanup, onMount } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { ContextRuntimeProjection, RevisionSaveResult } from "../authoring/contracts";
import { CoreRequirementNotice, WriterContextStrip } from "../authoring/AuthoringUI";

type SaveState = "idle" | "dirty" | "saving" | "saved" | "conflict" | "failed";
type SessionRevision = { revision_id: string; content_fingerprint: string; saved_at: string };

export default function Manuscript() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const capabilities = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);
  const [documentId, setDocumentId] = createSignal("");
  const [title, setTitle] = createSignal("");
  const [content, setContent] = createSignal("");
  const [editable, setEditable] = createSignal(false);
  const [parentRevisionId, setParentRevisionId] = createSignal<string | null>(null);
  const [contentFingerprint, setContentFingerprint] = createSignal<string>();
  const [saveState, setSaveState] = createSignal<SaveState>("idle");
  const [sessionDocuments, setSessionDocuments] = createSignal<Array<{ id: string; title: string }>>([]);
  const [sessionRevisions, setSessionRevisions] = createSignal<SessionRevision[]>([]);
  const [compareLeft, setCompareLeft] = createSignal("");
  const [compareRight, setCompareRight] = createSignal("");
  const [diff, setDiff] = createSignal<string[]>([]);
  const [error, setError] = createSignal<string>();
  const [context, setContext] = createSignal<ContextRuntimeProjection>();
  let timer: number | undefined;

  const wordCount = createMemo(() => content().trim() ? content().trim().split(/\s+/u).length : 0);
  const charCount = createMemo(() => Array.from(content()).length);
  const canSave = () => editable() && !!projectId() && !!documentId() && capabilities().includes("document.revision.save");

  const saveNow = async () => {
    if (!canSave() || saveState() === "saving") return;
    setSaveState("saving");
    setError(undefined);
    try {
      const result = await invokeBridge<RevisionSaveResult>("document.revision.save", {
        project_id: projectId(),
        document_id: documentId(),
        content: content(),
        source: "studio_autosave",
        authority_class: "proposal",
        expected_parent_revision_id: parentRevisionId(),
        provenance: { ui: "Studio Manuscript", autosave: true },
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setParentRevisionId(result.data.revision_id);
      setContentFingerprint(result.data.content_fingerprint);
      setSessionRevisions((current) => current.some((item) => item.revision_id === result.data!.revision_id) ? current : [{ revision_id: result.data!.revision_id, content_fingerprint: result.data!.content_fingerprint, saved_at: new Date().toISOString() }, ...current]);
      setSaveState("saved");
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(`quillframe.ui.lastDocumentId:${projectId()}`, documentId());
        localStorage.setItem(`quillframe.ui.lastRevisionId:${projectId()}:${documentId()}`, result.data.revision_id);
      }
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      setSaveState(/revision conflict|ConflictError/i.test(message) ? "conflict" : "failed");
    }
  };

  const scheduleSave = () => {
    setSaveState("dirty");
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(() => void saveNow(), 850);
  };

  const createDocument = async () => {
    if (!projectId() || !documentId().trim() || !title().trim()) return;
    setError(undefined);
    try {
      const result = await invokeBridge("document.create", {
        project_id: projectId(), document_id: documentId().trim(), title: title().trim(), document_kind: "manuscript",
      });
      if (result.status !== "ok") throw new Error(operationError(result));
      setDocumentId(documentId().trim());
      setParentRevisionId(null);
      setContent("");
      setEditable(true);
      setSaveState("idle");
      setSessionRevisions([]);
      setSessionDocuments((current) => current.some((item) => item.id === documentId()) ? current : [...current, { id: documentId(), title: title() }]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  };

  const attachExistingId = () => {
    setEditable(false);
    setParentRevisionId(null);
    setContent("");
    setSessionRevisions([]);
    setSaveState("idle");
    setError(zh() ? "已选择 Document ID，但当前 Core 没有 document.get；在读取 exact persisted revision 前编辑器保持只读。" : "Document ID selected, but Core does not expose document.get; the editor stays read-only until the exact persisted revision can be read.");
  };

  const compare = async () => {
    if (!compareLeft() || !compareRight()) return;
    setError(undefined);
    try {
      const result = await invokeBridge<{ diff: string[] }>("document.revision.compare", { project_id: projectId(), left_revision_id: compareLeft(), right_revision_id: compareRight() });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setDiff(result.data.diff ?? []);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
  };

  const refreshContext = async () => {
    const runId = studio.lastRunId();
    if (!projectId() || !runId || !capabilities().includes("inspector.context.runtime")) return;
    try {
      const result = await invokeBridge<ContextRuntimeProjection>("inspector.context.runtime", { project_id: projectId(), run_id: runId });
      if (result.status === "ok" && result.data) setContext(result.data);
    } catch { /* Context is supplemental; the editor remains usable without it. */ }
  };

  onMount(() => {
    const remembered = typeof localStorage === "undefined" ? "" : localStorage.getItem(`quillframe.ui.lastDocumentId:${projectId()}`) ?? "";
    if (remembered) setDocumentId(remembered);
    void refreshContext();
  });
  onCleanup(() => { if (timer) window.clearTimeout(timer); });

  return (
    <section class="nf-page qf-manuscript-page">
      <PageIntro eyebrow="MANUSCRIPT" title={zh() ? "正文是 Studio 的中心。" : "The manuscript is the center of Studio."} body={zh() ? "Binder + Manuscript + optional AI/Inspector。Autosave 只创建 proposal revision；保存不等于 Accepted，更不等于 Settled。" : "Binder + Manuscript + optional AI/Inspector. Autosave creates proposal revisions only; saved is not Accepted and never Settled."} />

      <Show when={projectId()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "先打开 Project" : "Open a Project first"}</strong><a href="/start">{zh() ? "开始" : "Start"}</a></div>}>
        <WriterContextStrip projection={context()} zh={zh()} />
        <div class="qf-manuscript-workspace">
          <aside class="qf-binder" aria-label="Binder">
            <div class="qf-binder__heading"><span class="nf-eyebrow">BINDER</span><strong>{projectId()}</strong></div>
            <CoreRequirementNotice operation="document.list" compact />
            <Show when={sessionDocuments().length}>
              <div class="qf-binder__session"><small>{zh() ? "本次会话已创建；切换需要 document.get" : "Created this session; switching requires document.get"}</small><For each={sessionDocuments()}>{(doc) => <button type="button" disabled aria-disabled="true" title={zh() ? "等待 Core document.get 后才能安全切换" : "Safe switching awaits Core document.get"}>{doc.title}<span>{doc.id}</span></button>}</For></div>
            </Show>
            <details open={!editable()}><summary>{zh() ? "新建 / 按 ID 打开" : "New / open by ID"}</summary>
              <label class="nf-field-label"><span>Document ID</span><input class="wui-input nf-mono" value={documentId()} onInput={(event) => setDocumentId(event.currentTarget.value)} placeholder="CH001" /></label>
              <label class="nf-field-label"><span>{zh() ? "标题" : "Title"}</span><input class="wui-input" value={title()} onInput={(event) => setTitle(event.currentTarget.value)} placeholder={zh() ? "第一章" : "Chapter 1"} /></label>
              <div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={!capabilities().includes("document.create") || !documentId().trim() || !title().trim()} onClick={() => void createDocument()}>{zh() ? "新建" : "Create"}</button><button class="wui-button wui-button--outline" type="button" disabled={!documentId().trim()} onClick={attachExistingId}>{zh() ? "按 ID 打开" : "Open by ID"}</button></div>
            </details>
          </aside>

          <article class="qf-manuscript-editor" aria-label={zh() ? "正文编辑器" : "Manuscript editor"}>
            <header class="qf-manuscript-editor__head">
              <div><span class="nf-eyebrow">{documentId() || "NO DOCUMENT"}</span><h2>{title() || (zh() ? "未选择正文" : "No manuscript selected")}</h2></div>
              <div class="qf-save-state" data-state={saveState()} role="status" aria-live="polite"><strong>{saveState()}</strong><span>{parentRevisionId() ? ` · ${parentRevisionId()}` : ""}</span></div>
            </header>
            <Show when={editable()} fallback={<div class="qf-editor-readonly"><CoreRequirementNotice operation="document.get" /><p>{zh() ? "为了避免把浏览器 buffer 当成 canonical manuscript，Core 没有返回正文前不会启用编辑。" : "To avoid treating a browser buffer as canonical manuscript, editing stays disabled until Core can return the persisted text."}</p></div>}>
              <textarea class="qf-manuscript-textarea" aria-label={zh() ? "正文" : "Manuscript text"} value={content()} onInput={(event) => { setContent(event.currentTarget.value); scheduleSave(); }} spellcheck />
              <footer class="qf-manuscript-meta"><span>{charCount()} {zh() ? "字" : "chars"}</span><span>{wordCount()} {zh() ? "词段" : "words"}</span><span>proposal</span><Show when={contentFingerprint()}>{(fp) => <code>{fp()}</code>}</Show></footer>
            </Show>
            <Show when={saveState() === "conflict"}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">revision conflict</strong><span class="wui-alert__description">{zh() ? "Core before-state 已变化。Studio 不会自动覆盖或重试 side effect；需要读取最新 revision 后再决定。" : "Core before-state changed. Studio will not overwrite or retry the side effect; the latest revision must be read before deciding."}</span></div></div></Show>
            <Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Manuscript</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
          </article>

          <aside class="qf-revision-rail" aria-label={zh() ? "Revision history" : "Revision history"}>
            <div class="qf-binder__heading"><span class="nf-eyebrow">REVISIONS</span><strong>{zh() ? "本次会话" : "This session"}</strong></div>
            <CoreRequirementNotice operation="document.get" compact />
            <For each={sessionRevisions()}>{(revision) => <button type="button" class="qf-revision-row" onClick={() => { if (!compareLeft()) setCompareLeft(revision.revision_id); else setCompareRight(revision.revision_id); }}><code>{revision.revision_id}</code><span>{revision.content_fingerprint.slice(0, 18)}…</span></button>}</For>
            <Show when={sessionRevisions().length >= 2}><div class="qf-revision-compare"><label>Left<input class="wui-input nf-mono" value={compareLeft()} onInput={(event) => setCompareLeft(event.currentTarget.value)} /></label><label>Right<input class="wui-input nf-mono" value={compareRight()} onInput={(event) => setCompareRight(event.currentTarget.value)} /></label><button class="wui-button wui-button--outline" type="button" onClick={() => void compare()}>{zh() ? "比较" : "Compare"}</button></div></Show>
            <Show when={diff().length}><pre class="qf-diff"><code>{diff().join("\n")}</code></pre></Show>
          </aside>
        </div>
      </Show>
    </section>
  );
}
