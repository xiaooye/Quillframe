import { For, Show, createEffect, createMemo, createSignal, on, onCleanup, onMount } from "solid-js";
import { useBeforeLeave, useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { ContextRuntimeProjection, DocumentListItem, DocumentListProjection, DocumentProjection, DocumentRevisionListProjection, RevisionSaveResult } from "../authoring/contracts";
import { createManuscriptBuffer, type ManuscriptBuffer } from "../authoring/manuscriptBuffer";
import { CoreRequirementNotice, WriterContextStrip } from "../authoring/AuthoringUI";

type RevisionRow = { revision_id: string; content_fingerprint: string; created_at?: string; authority_class?: string };

export default function Manuscript() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const capabilities = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);
  const [buffer, setBuffer] = createSignal<ManuscriptBuffer>();
  const [title, setTitle] = createSignal("");
  const [opening, setOpening] = createSignal(false);
  const [creating, setCreating] = createSignal(false);
  const [newTitle, setNewTitle] = createSignal("");
  const [documents, setDocuments] = createSignal<DocumentListItem[]>([]);
  const [revisions, setRevisions] = createSignal<RevisionRow[]>([]);
  const [compareLeft, setCompareLeft] = createSignal("");
  const [compareRight, setCompareRight] = createSignal("");
  const [diff, setDiff] = createSignal<string[]>([]);
  const [error, setError] = createSignal<string>();
  const [context, setContext] = createSignal<ContextRuntimeProjection>();
  let timer: number | undefined;
  let openGeneration = 0;
  let listGeneration = 0;
  let contextGeneration = 0;
  let compareGeneration = 0;
  let leaveGeneration = 0;
  let disposed = false;
  let creationIntent: { project_id: string; title: string; idempotency_key: string } | undefined;
  const message = (cause: unknown) => cause instanceof Error ? cause.message : String(cause);
  const editor = createManuscriptBuffer({
    changed: setBuffer,
    save: async (request) => {
      const response = await invokeBridge<RevisionSaveResult>("document.revision.save", {
        ...request, source: "studio_autosave", authority_class: "proposal",
        provenance: { ui: "Studio Manuscript", autosave: true },
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      return response.data;
    },
  });
  const content = () => buffer()?.content ?? "";
  const documentId = () => buffer()?.document_id ?? "";
  const editable = () => !!buffer() && buffer()?.project_id === projectId() && !opening();
  const charCount = createMemo(() => Array.from(content()).length);
  const wordCount = createMemo(() => content().trim() ? content().trim().split(/\s+/u).length : 0);
  const clearTimer = () => { if (timer !== undefined) window.clearTimeout(timer); timer = undefined; };

  const loadRevisions = async (id: string, requestedProject = projectId()) => {
    if (!capabilities().includes("document.revisions.list")) return;
    const result = await invokeBridge<DocumentRevisionListProjection>("document.revisions.list", { project_id: requestedProject, document_id: id, limit: 100 });
    if (disposed || projectId() !== requestedProject || documentId() !== id) return;
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    if (result.data.project_id !== requestedProject || result.data.document_id !== id || result.data.authority !== false) throw new Error("revision_list_binding_invalid");
    setRevisions(result.data.items);
  };

  const loadDocuments = async () => {
    const requestedProject = projectId();
    const generation = ++listGeneration;
    if (!requestedProject || !capabilities().includes("document.list")) return;
    try {
      const result = await invokeBridge<DocumentListProjection>("document.list", { project_id: requestedProject, document_kind: "manuscript", limit: 500 });
      if (disposed || generation !== listGeneration || projectId() !== requestedProject) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (result.data.project_id !== requestedProject || result.data.authority !== false) throw new Error("document_list_binding_invalid");
      setDocuments(result.data.items);
    } catch (cause) { if (!disposed && generation === listGeneration && projectId() === requestedProject) setError(message(cause)); }
  };

  const saveNow = async () => {
    clearTimer();
    if (!editable() || !capabilities().includes("document.revision.save")) return false;
    const id = documentId();
    const requestedProject = projectId();
    const saved = await editor.flushAndRefresh(async () => {
      if (disposed || documentId() !== id || projectId() !== requestedProject) return;
      // Refresh metadata only. Reopening here would overwrite text typed during the save.
      try { await loadRevisions(id, requestedProject); await loadDocuments(); }
      catch (cause) { if (!disposed && documentId() === id && projectId() === requestedProject) setError(message(cause)); }
    });
    return saved && !disposed && documentId() === id && projectId() === requestedProject && !editor.current()?.dirty;
  };

  const openDocument = async (id: string, forceReload = false) => {
    const requestedProject = projectId();
    if (!requestedProject || !id || !capabilities().includes("document.open")) return;
    if (!forceReload && buffer()?.project_id === requestedProject && documentId() === id) return;
    const generation = ++openGeneration;
    const current = () => !disposed && generation === openGeneration && projectId() === requestedProject;
    if (buffer()?.dirty) {
      const saved = !forceReload && await saveNow();
      if (!current()) return;
      if ((!saved || editor.current()?.dirty) && !window.confirm(zh() ? "未保存的修改仍在编辑器中。放弃这些修改并打开 Core 版本？" : "Unsaved edits remain in the editor. Discard them and open the Core revision?")) return;
    }
    if (!current()) return;
    clearTimer(); setOpening(true); setError(undefined);
    try {
      const result = await invokeBridge<DocumentProjection>("document.open", { project_id: requestedProject, document_id: id });
      if (!current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const projection = result.data;
      if (projection.schema !== "quillframe_document_projection_v1" || projection.project_id !== requestedProject
        || projection.document.document_id !== id || projection.document.document_kind !== "manuscript" || projection.authority !== false
        || projection.latest_revision && (projection.latest_revision.document_id !== id || typeof projection.latest_revision.content !== "string")) throw new Error("document_open_binding_invalid");
      editor.bind({ project_id: requestedProject, document_id: id, content: projection.latest_revision?.content ?? "",
        parent_revision_id: projection.latest_revision?.revision_id ?? null, content_fingerprint: projection.latest_revision?.content_fingerprint });
      setTitle(projection.document.title); setRevisions([]); setDiff([]); setCompareLeft(""); setCompareRight("");
      const chapter = studio.chapters().find((item) => item.document_id === id && item.chapter_id === projection.document.story_node_id);
      if (chapter) studio.setChapterId(chapter.chapter_id);
      await loadRevisions(id, requestedProject);
    } catch (cause) { if (current()) setError(message(cause)); }
    finally { if (current()) setOpening(false); }
  };

  const createChapter = async () => {
    const requestedProject = projectId();
    const chapterTitle = newTitle().trim();
    if (!requestedProject || !chapterTitle || creating() || !capabilities().includes("chapter.create")) return;
    setCreating(true); setError(undefined);
    try {
      if (buffer()?.dirty && !await saveNow()) return;
      if (disposed || projectId() !== requestedProject || editor.current()?.dirty) return;
      if (!creationIntent || creationIntent.project_id !== requestedProject || creationIntent.title !== chapterTitle) {
        creationIntent = { project_id: requestedProject, title: chapterTitle, idempotency_key: `studio-chapter-${crypto.randomUUID()}` };
      }
      const result = await invokeBridge<{ project_id: string; chapter_id: string; document_id: string; authority: false }>("chapter.create", { ...creationIntent, user_authorized: true });
      if (disposed || projectId() !== requestedProject) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (result.data.project_id !== requestedProject || !result.data.chapter_id || !result.data.document_id || result.data.authority !== false) throw new Error("chapter_create_binding_invalid");
      creationIntent = undefined;
      if (newTitle().trim() === chapterTitle) setNewTitle("");
      await studio.refreshChapters();
      if (disposed || projectId() !== requestedProject) return;
      await loadDocuments();
      await openDocument(result.data.document_id);
    } catch (cause) { if (!disposed && projectId() === requestedProject) setError(message(cause)); }
    finally { if (!disposed && projectId() === requestedProject) setCreating(false); }
  };

  const compare = async () => {
    const generation = ++compareGeneration;
    const requestedProject = projectId(); const id = documentId();
    const left = compareLeft(); const right = compareRight();
    if (!left || !right) return;
    try {
      const result = await invokeBridge<{ diff: string[] }>("document.revision.compare", { project_id: requestedProject, left_revision_id: left, right_revision_id: right });
      if (disposed || generation !== compareGeneration || projectId() !== requestedProject || documentId() !== id || compareLeft() !== left || compareRight() !== right) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setDiff(result.data.diff ?? []);
    } catch (cause) { if (!disposed && generation === compareGeneration && projectId() === requestedProject && documentId() === id) setError(message(cause)); }
  };

  const refreshContext = async () => {
    const generation = ++contextGeneration;
    const requestedProject = projectId(); const runId = studio.lastRunId();
    setContext(undefined);
    if (!requestedProject || !runId || !capabilities().includes("inspector.context.runtime")) return;
    try {
      const result = await invokeBridge<ContextRuntimeProjection>("inspector.context.runtime", { project_id: requestedProject, run_id: runId });
      if (!disposed && generation === contextGeneration && projectId() === requestedProject && studio.lastRunId() === runId && result.status === "ok" && result.data) setContext(result.data);
    } catch { /* supplemental evidence; never inferred */ }
  };

  createEffect(on([projectId, capabilities], () => { void loadDocuments(); void refreshContext(); }));
  createEffect(on([projectId, () => studio.chapterId(), () => studio.chapters(), capabilities], () => {
    if (studio.projectId() !== projectId()) return;
    const requested = new URLSearchParams(location.search).get("document")?.trim();
    const chapter = !buffer() && requested ? studio.chapters().find((item) => item.document_id === requested) : studio.selectedChapter();
    if (chapter) void openDocument(chapter.document_id);
  }));
  const beforeUnload = (event: BeforeUnloadEvent) => { if (buffer()?.dirty) { event.preventDefault(); event.returnValue = ""; } };
  onMount(() => window.addEventListener("beforeunload", beforeUnload));
  useBeforeLeave((event) => {
    if (!buffer()?.dirty) return;
    event.preventDefault();
    const generation = ++leaveGeneration;
    void saveNow().then((saved) => {
      if (!disposed && generation === leaveGeneration && ((saved && !editor.current()?.dirty) || window.confirm(zh() ? "正文尚未保存。放弃本地修改并离开？" : "The manuscript is not saved. Discard local edits and leave?"))) event.retry(true);
    });
  });
  onCleanup(() => { disposed = true; openGeneration += 1; listGeneration += 1; contextGeneration += 1; compareGeneration += 1; leaveGeneration += 1; clearTimer(); editor.dispose(); window.removeEventListener("beforeunload", beforeUnload); });

  return (
    <section class="nf-page qf-manuscript-page">
      <PageIntro eyebrow="MANUSCRIPT" title={zh() ? "在章节之间，保持故事的连续。" : "Keep the story connected across chapters."} body={zh() ? "目录和正文来自 Core。自动保存只创建提案版本；审阅、接受、结算仍是分别确认的动作。" : "The chapter list and manuscript come from Core. Autosave creates proposal revisions; review, acceptance and settlement remain separate decisions."} />
      <Show when={projectId()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "先打开小说项目" : "Open a novel first"}</strong><a href="/start">{zh() ? "开始" : "Start"}</a></div>}>
        <WriterContextStrip projection={context()} zh={zh()} />
        <div class="qf-manuscript-workspace">
          <aside class="qf-binder" aria-label={zh() ? "卷章目录" : "Chapter binder"}>
            <div class="qf-binder__heading"><span class="nf-eyebrow">CHAPTERS</span><strong>{projectId()}</strong></div>
            <CoreRequirementNotice operation="chapter.list" compact />
            <div class="qf-binder__session"><For each={studio.chapters()}>{(chapter) => <button type="button" disabled={opening() || creating()} data-active={documentId() === chapter.document_id ? "true" : undefined} onClick={() => void openDocument(chapter.document_id)}><strong>{chapter.title}</strong><span>{chapter.parent_id ? `${chapter.parent_id} · ` : ""}{chapter.chapter_id}</span><small>{chapter.needs_review ? (zh() ? "依赖已变化，需重新审阅" : "Dependencies changed; review required") : documents().find((doc) => doc.document_id === chapter.document_id)?.latest_authority_class ?? (zh() ? "暂无版本" : "No revision")}</small></button>}</For></div>
            <Show when={studio.chapterError()}>{(value) => <p role="alert">{value()}</p>}</Show>
            <Show when={!studio.chapterLoading() && !studio.chapters().length}><p>{zh() ? "暂无章节。新建章节会同时创建关联正文。" : "No chapters. Creating one also creates its linked manuscript."}</p></Show>
            <details open={!studio.chapters().length}><summary>{zh() ? "新建章节" : "New chapter"}</summary><label class="nf-field-label"><span>{zh() ? "章节标题" : "Chapter title"}</span><input class="wui-input" value={newTitle()} onInput={(event) => setNewTitle(event.currentTarget.value)} /></label><button class="wui-button wui-button--solid" type="button" disabled={creating() || !capabilities().includes("chapter.create") || !newTitle().trim()} onClick={() => void createChapter()}>{creating() ? (zh() ? "创建中…" : "Creating…") : (zh() ? "创建章节与正文" : "Create chapter and manuscript")}</button></details>
          </aside>
          <article class="qf-manuscript-editor" aria-label={zh() ? "正文编辑器" : "Manuscript editor"}>
            <header class="qf-manuscript-editor__head"><div><span class="nf-eyebrow">{documentId() || "NO DOCUMENT"}</span><h2>{title() || (zh() ? "未选择正文" : "No manuscript selected")}</h2></div><div class="qf-save-state" data-state={buffer()?.state ?? "idle"} role="status" aria-live="polite"><strong>{opening() ? (zh() ? "读取中…" : "Opening…") : buffer()?.state ?? "idle"}</strong><span>{buffer()?.parent_revision_id ? ` · ${buffer()!.parent_revision_id}` : ""}</span></div></header>
            <Show when={buffer()} fallback={<div class="qf-editor-readonly"><CoreRequirementNotice operation="document.open" /><p>{zh() ? "从目录选择章节。正文以 Core 返回的版本为准。" : "Select a chapter. The editor opens the exact revision returned by Core."}</p></div>}>
              <textarea class="qf-manuscript-textarea" disabled={!editable()} aria-label={zh() ? "正文" : "Manuscript text"} value={content()} onInput={(event) => { editor.edit(event.currentTarget.value); clearTimer(); timer = window.setTimeout(() => void saveNow(), 850); }} spellcheck />
              <footer class="qf-manuscript-meta"><span>{charCount()} {zh() ? "字" : "chars"}</span><span>{wordCount()} {zh() ? "词段" : "words"}</span><span>proposal</span><Show when={buffer()?.content_fingerprint}>{(fp) => <code>{fp()}</code>}</Show></footer>
              <div class="qf-inline-actions"><button class="wui-button wui-button--outline" type="button" disabled={!editable() || buffer()?.state === "saving" || buffer()?.state === "conflict" || !buffer()?.dirty} onClick={() => void saveNow()}>{zh() ? "保存" : "Save"}</button><button class="wui-button wui-button--ghost" type="button" disabled={opening()} onClick={() => void openDocument(documentId(), true)}>{zh() ? "重新打开 Core 版本" : "Reopen Core revision"}</button></div>
            </Show>
            <Show when={buffer()?.state === "conflict"}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">revision conflict</strong><span class="wui-alert__description">{zh() ? "Core 的父版本已变化。你的修改仍保留在编辑器中；不会自动覆盖。" : "Core's parent revision changed. Your edits remain in the editor; no automatic overwrite occurs."}</span></div></div></Show>
            <Show when={buffer()?.error || error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Manuscript</strong><span class="wui-alert__description">{value()}</span></div></div>}</Show>
          </article>
          <aside class="qf-revision-rail" aria-label={zh() ? "版本记录" : "Revision history"}>
            <div class="qf-binder__heading"><span class="nf-eyebrow">REVISIONS</span><strong>{revisions().length}</strong></div><CoreRequirementNotice operation="document.revisions.list" compact />
            <For each={revisions()}>{(revision) => <button type="button" class="qf-revision-row" onClick={() => { if (!compareLeft()) setCompareLeft(revision.revision_id); else setCompareRight(revision.revision_id); }}><code>{revision.revision_id}</code><span>{revision.content_fingerprint.slice(0, 18)}…</span><small>{revision.authority_class ?? "—"}</small></button>}</For>
            <Show when={revisions().length >= 2}><div class="qf-revision-compare"><label>Left<input class="wui-input nf-mono" value={compareLeft()} onInput={(event) => setCompareLeft(event.currentTarget.value)} /></label><label>Right<input class="wui-input nf-mono" value={compareRight()} onInput={(event) => setCompareRight(event.currentTarget.value)} /></label><button class="wui-button wui-button--outline" type="button" onClick={() => void compare()}>{zh() ? "比较" : "Compare"}</button></div></Show><Show when={diff().length}><pre class="qf-diff">{diff().join("")}</pre></Show>
          </aside>
        </div>
      </Show>
    </section>
  );
}
