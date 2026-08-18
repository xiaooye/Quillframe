import { For, Show, createMemo, createSignal, onCleanup, onMount } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type {
  ContextRuntimeProjection,
  DocumentListItem,
  DocumentListProjection,
  DocumentProjection,
  DocumentRevisionListProjection,
  RevisionSaveResult,
} from "../authoring/contracts";
import { CoreRequirementNotice, WriterContextStrip } from "../authoring/AuthoringUI";

type SaveState = "idle" | "dirty" | "saving" | "saved" | "conflict" | "failed";
type RevisionRow = { revision_id: string; content_fingerprint: string; created_at?: string; authority_class?: string };

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
  const [documents, setDocuments] = createSignal<DocumentListItem[]>([]);
  const [revisions, setRevisions] = createSignal<RevisionRow[]>([]);
  const [compareLeft, setCompareLeft] = createSignal("");
  const [compareRight, setCompareRight] = createSignal("");
  const [diff, setDiff] = createSignal<string[]>([]);
  const [error, setError] = createSignal<string>();
  const [context, setContext] = createSignal<ContextRuntimeProjection>();
  let timer: number | undefined;

  const wordCount = createMemo(() => content().trim() ? content().trim().split(/\s+/u).length : 0);
  const charCount = createMemo(() => Array.from(content()).length);
  const canSave = () => editable() && !!projectId() && !!documentId() && capabilities().includes("document.revision.save");

  const loadRevisions = async (id: string) => {
    if (!capabilities().includes("document.revisions.list")) return;
    const result = await invokeBridge<DocumentRevisionListProjection>("document.revisions.list", { project_id: projectId(), document_id: id, limit: 100 });
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    setRevisions(result.data.items.map((item) => ({ revision_id: item.revision_id, content_fingerprint: item.content_fingerprint, created_at: item.created_at, authority_class: item.authority_class })));
  };

  const openDocument = async (id: string) => {
    if (!projectId() || !id || !capabilities().includes("document.open")) return;
    setError(undefined);
    try {
      const result = await invokeBridge<DocumentProjection>("document.open", { project_id: projectId(), document_id: id });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const projection = result.data;
      setDocumentId(projection.document.document_id);
      setTitle(projection.document.title);
      setContent(projection.latest_revision?.content ?? "");
      setParentRevisionId(projection.latest_revision?.revision_id ?? null);
      setContentFingerprint(projection.latest_revision?.content_fingerprint);
      setEditable(true);
      setSaveState("idle");
      setDiff([]);
      setCompareLeft("");
      setCompareRight("");
      await loadRevisions(id);
      if (typeof localStorage !== "undefined") localStorage.setItem(`quillframe.ui.lastDocumentId:${projectId()}`, id);
    } catch (cause) {
      setEditable(false);
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const loadDocuments = async () => {
    if (!projectId() || !capabilities().includes("document.list")) return;
    setError(undefined);
    try {
      const result = await invokeBridge<DocumentListProjection>("document.list", { project_id: projectId(), limit: 500 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setDocuments(result.data.items);
      const requested = new URLSearchParams(location.search).get("document")?.trim();
      const remembered = typeof localStorage === "undefined" ? "" : localStorage.getItem(`quillframe.ui.lastDocumentId:${projectId()}`) ?? "";
      const initial = requested || remembered || result.data.items[0]?.document_id || "";
      if (initial && result.data.items.some((item) => item.document_id === initial)) await openDocument(initial);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

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
      setSaveState("saved");
      await loadRevisions(documentId());
      await loadDocuments();
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      setSaveState(/revision conflict|ConflictError|before-state/i.test(message) ? "conflict" : "failed");
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
      const id = documentId().trim();
      const result = await invokeBridge("document.create", { project_id: projectId(), document_id: id, title: title().trim(), document_kind: "manuscript" });
      if (result.status !== "ok") throw new Error(operationError(result));
      await loadDocuments();
      await openDocument(id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
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
    } catch { /* supplemental */ }
  };

  onMount(() => {
    void loadDocuments();
    void refreshContext();
  });
  onCleanup(() => { if (timer) window.clearTimeout(timer); });

  return (
    <section class="nf-page qf-manuscript-page">
      <PageIntro eyebrow="MANUSCRIPT" title={zh() ? "正文是 Studio 的中心。" : "The manuscript is the center of Studio."} body={zh() ? "Binder 与正文都读取 canonical Core。Autosave 只创建 proposal revision；保存不等于 Accepted，更不等于 Settled。" : "Binder and manuscript both read canonical Core state. Autosave creates proposal revisions only; saved is not Accepted and never Settled."} />

      <Show when={projectId()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "先打开 Project" : "Open a Project first"}</strong><a href="/start">{zh() ? "开始" : "Start"}</a></div>}>
        <WriterContextStrip projection={context()} zh={zh()} />
        <div class="qf-manuscript-workspace">
          <aside class="qf-binder" aria-label="Binder">
            <div class="qf-binder__heading"><span class="nf-eyebrow">BINDER</span><strong>{projectId()}</strong></div>
            <CoreRequirementNotice operation="document.list" compact />
            <div class="qf-binder__session">
              <For each={documents()}>{(doc) => <button type="button" data-active={documentId() === doc.document_id ? "true" : undefined} onClick={() => void openDocument(doc.document_id)}><strong>{doc.title}</strong><span>{doc.document_id}</span><small>{doc.latest_authority_class ?? "no revision"}</small></button>}</For>
              <Show when={!documents().length}><small>{zh() ? "暂无正文文档" : "No manuscript documents yet"}</small></Show>
            </div>
            <details open={!editable()}><summary>{zh() ? "新建正文" : "New manuscript"}</summary>
              <label class="nf-field-label"><span>Document ID</span><input class="wui-input nf-mono" value={documentId()} onInput={(event) => setDocumentId(event.currentTarget.value)} placeholder="CH001" /></label>
              <label class="nf-field-label"><span>{zh() ? "标题" : "Title"}</span><input class="wui-input" value={title()} onInput={(event) => setTitle(event.currentTarget.value)} placeholder={zh() ? "第一章" : "Chapter 1"} /></label>
              <button class="wui-button wui-button--solid" type="button" disabled={!capabilities().includes("document.create") || !documentId().trim() || !title().trim()} onClick={() => void createDocument()}>{zh() ? "新建" : "Create"}</button>
            </details>
          </aside>

          <article class="qf-manuscript-editor" aria-label={zh() ? "正文编辑器" : "Manuscript editor"}>
            <header class="qf-manuscript-editor__head">
              <div><span class="nf-eyebrow">{documentId() || "NO DOCUMENT"}</span><h2>{title() || (zh() ? "未选择正文" : "No manuscript selected")}</h2></div>
              <div class="qf-save-state" data-state={saveState()} role="status" aria-live="polite"><strong>{saveState()}</strong><span>{parentRevisionId() ? ` · ${parentRevisionId()}` : ""}</span></div>
            </header>
            <Show when={editable()} fallback={<div class="qf-editor-readonly"><CoreRequirementNotice operation="document.open" /><p>{zh() ? "Core 返回 exact persisted revision 后才启用编辑。浏览器 buffer 不是 canonical manuscript。" : "Editing is enabled only after Core returns the exact persisted revision. The browser buffer is not canonical manuscript state."}</p></div>}>
              <textarea class="qf-manuscript-textarea" aria-label={zh() ? "正文" : "Manuscript text"} value={content()} onInput={(event) => { setContent(event.currentTarget.value); scheduleSave(); }} spellcheck />
              <footer class="qf-manuscript-meta"><span>{charCount()} {zh() ? "字" : "chars"}</span><span>{wordCount()} {zh() ? "词段" : "words"}</span><span>proposal</span><Show when={contentFingerprint()}>{(fp) => <code>{fp()}</code>}</Show></footer>
            </Show>
            <Show when={saveState() === "conflict"}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">revision conflict</strong><span class="wui-alert__description">{zh() ? "Core before-state 已变化。Studio 不自动覆盖；重新打开 canonical revision 后再决定。" : "Core before-state changed. Studio does not overwrite; reopen the canonical revision before deciding."}</span></div></div></Show>
            <Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Manuscript</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
          </article>

          <aside class="qf-revision-rail" aria-label="Revision history">
            <div class="qf-binder__heading"><span class="nf-eyebrow">REVISIONS</span><strong>{revisions().length}</strong></div>
            <CoreRequirementNotice operation="document.revisions.list" compact />
            <For each={revisions()}>{(revision) => <button type="button" class="qf-revision-row" onClick={() => { if (!compareLeft()) setCompareLeft(revision.revision_id); else setCompareRight(revision.revision_id); }}><code>{revision.revision_id}</code><span>{revision.content_fingerprint.slice(0, 18)}…</span><small>{revision.authority_class ?? "—"}</small></button>}</For>
            <Show when={revisions().length >= 2}><div class="qf-revision-compare"><label>Left<input class="wui-input nf-mono" value={compareLeft()} onInput={(event) => setCompareLeft(event.currentTarget.value)} /></label><label>Right<input class="wui-input nf-mono" value={compareRight()} onInput={(event) => setCompareRight(event.currentTarget.value)} /></label><button class="wui-button wui-button--outline" type="button" onClick={() => void compare()}>{zh() ? "比较" : "Compare"}</button></div></Show>
            <Show when={diff().length}><pre class="qf-diff"><code>{diff().join("\n")}</code></pre></Show>
          </aside>
        </div>
      </Show>
    </section>
  );
}
