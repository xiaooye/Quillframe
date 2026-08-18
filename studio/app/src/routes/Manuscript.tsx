import { For, Show, createMemo, createSignal, onCleanup, onMount } from "solid-js";
import { A, useSearchParams } from "@solidjs/router";
import { invokeBridge, operationError } from "../bridge";
import { useI18n } from "../i18n";

interface DocumentListItem {
  document_id: string; title: string; document_kind: string;
  latest_revision_id?: string | null; latest_content_fingerprint?: string | null;
  latest_authority_class?: "proposal" | "review" | "accepted" | null;
}
interface DocumentList { items: DocumentListItem[]; }
interface DocumentProjection {
  document: { document_id: string; title: string; document_kind: string };
  latest_revision: null | { revision_id: string; content: string; content_fingerprint: string; authority_class: "proposal" | "review" | "accepted" };
}
interface RevisionSave { revision_id: string; content_fingerprint: string; deduplicated: boolean; }
interface RevisionItem { revision_id: string; parent_revision_id?: string | null; content_fingerprint: string; created_at: string; source: string; authority_class: string; }
interface RevisionList { items: RevisionItem[]; }
interface RevisionCompare { diff: string[]; left_fingerprint: string; right_fingerprint: string; }
interface AuthorRun { run_id?: string; status?: string; request_fingerprint?: string; [key: string]: unknown; }
interface ExportResult { artifact_ref: string; file_name: string; }
interface ArtifactRead { file_name: string; media_type: string; payload_base64: string; }

function fromBase64(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export default function Manuscript() {
  const { locale } = useI18n();
  const zh = createMemo(() => locale() === "zh-CN");
  const [params] = useSearchParams();
  const projectId = createMemo(() => String(params.project || localStorage.getItem("quillframe.ui.lastProjectId") || ""));
  const [documents, setDocuments] = createSignal<DocumentListItem[]>([]);
  const [documentId, setDocumentId] = createSignal<string>();
  const [documentTitle, setDocumentTitle] = createSignal("");
  const [content, setContent] = createSignal("");
  const [revisionId, setRevisionId] = createSignal<string | null>(null);
  const [fingerprint, setFingerprint] = createSignal<string | null>(null);
  const [authority, setAuthority] = createSignal<string>("proposal");
  const [lastSaved, setLastSaved] = createSignal("");
  const [saveState, setSaveState] = createSignal<"idle" | "dirty" | "saving" | "saved" | "conflict" | "failed">("idle");
  const [status, setStatus] = createSignal<string>();
  const [error, setError] = createSignal<string>();
  const [history, setHistory] = createSignal<RevisionItem[]>([]);
  const [diff, setDiff] = createSignal<string[]>([]);
  const [newTitle, setNewTitle] = createSignal("");
  const [aiInstruction, setAiInstruction] = createSignal("");
  const [aiMode, setAiMode] = createSignal("DRAFT");
  const [aiRun, setAiRun] = createSignal<AuthorRun>();
  let timer: number | undefined;
  let saving = false;

  const message = (en: string, cn: string) => zh() ? cn : en;

  const loadDocuments = async (preferred?: string) => {
    const id = projectId();
    if (!id) return;
    const result = await invokeBridge<DocumentList>("document.list", { project_id: id, document_kind: "manuscript" });
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    setDocuments(result.data.items);
    const next = preferred || documentId() || result.data.items[0]?.document_id;
    if (next) await openDocument(next);
  };

  const loadHistory = async (id = documentId()) => {
    if (!id || !projectId()) return;
    const result = await invokeBridge<RevisionList>("document.revisions.list", { project_id: projectId(), document_id: id, limit: 100 });
    if (result.status === "ok" && result.data) setHistory(result.data.items);
  };

  const openDocument = async (id: string) => {
    if (saveState() === "dirty") await saveNow();
    setError(undefined); setDiff([]);
    const result = await invokeBridge<DocumentProjection>("document.get", { project_id: projectId(), document_id: id });
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    setDocumentId(id);
    setDocumentTitle(result.data.document.title);
    const revision = result.data.latest_revision;
    const text = revision?.content ?? "";
    setContent(text); setLastSaved(text);
    setRevisionId(revision?.revision_id ?? null); setFingerprint(revision?.content_fingerprint ?? null);
    setAuthority(revision?.authority_class ?? "proposal"); setSaveState("idle");
    localStorage.setItem("quillframe.ui.lastProjectId", projectId());
    await loadHistory(id);
  };

  const queueSave = () => {
    if (!documentId()) return;
    setSaveState("dirty");
    if (timer !== undefined) window.clearTimeout(timer);
    timer = window.setTimeout(() => { void saveNow(); }, 850);
  };

  const saveNow = async () => {
    const id = documentId();
    if (!id || !projectId()) return;
    if (saving) { queueSave(); return; }
    const snapshot = content();
    if (snapshot === lastSaved()) { setSaveState("saved"); return; }
    saving = true; setSaveState("saving"); setError(undefined);
    try {
      const result = await invokeBridge<RevisionSave>("document.revision.save", {
        project_id: projectId(), document_id: id, content: snapshot,
        expected_parent_revision_id: revisionId(), source: "studio_autosave", authority_class: "proposal",
        provenance: { surface: "studio", interaction: "autosave" },
      });
      if (result.status !== "ok" || !result.data) {
        const code = typeof result.error === "object" && result.error && "code" in result.error ? String((result.error as { code: unknown }).code) : "";
        setSaveState(code === "ConflictError" ? "conflict" : "failed");
        throw new Error(operationError(result));
      }
      setRevisionId(result.data.revision_id); setFingerprint(result.data.content_fingerprint);
      setAuthority("proposal"); setLastSaved(snapshot); setSaveState("saved");
      void loadHistory(id);
      if (content() !== snapshot) queueSave();
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { saving = false; }
  };

  const createDocument = async () => {
    const title = newTitle().trim();
    if (!title || !projectId()) return;
    const id = `doc_${crypto.randomUUID().replaceAll("-", "")}`;
    setError(undefined);
    const result = await invokeBridge("document.create", { project_id: projectId(), document_id: id, title, document_kind: "manuscript" });
    if (result.status !== "ok") { setError(operationError(result)); return; }
    setNewTitle("");
    await loadDocuments(id);
  };

  const compareRevision = async (left: string) => {
    const right = revisionId();
    if (!right || left === right) return;
    const result = await invokeBridge<RevisionCompare>("document.revision.compare", { project_id: projectId(), left_revision_id: left, right_revision_id: right });
    if (result.status !== "ok" || !result.data) { setError(operationError(result)); return; }
    setDiff(result.data.diff);
  };

  const startAiRun = async () => {
    if (!documentId() || !aiInstruction().trim()) return;
    await saveNow();
    setError(undefined); setAiRun(undefined);
    const result = await invokeBridge<AuthorRun>("author.run.start", {
      project_id: projectId(), task_mode: aiMode(), target_ref: `document:${documentId()}`,
      payload: {
        instruction: aiInstruction().trim(), document_id: documentId(), revision_id: revisionId(),
        content_fingerprint: fingerprint(), requested_surface: "manuscript_ai_dock",
      },
      idempotency_key: `studio-run-${crypto.randomUUID()}`,
    });
    if (result.status !== "ok" || !result.data) { setError(operationError(result)); return; }
    setAiRun(result.data);
    setStatus(message("Run registered with Core. Production semantic execution is pending; no candidate has been fabricated.", "Run 已由 Core 注册。Production semantic execution 仍处于 pending；Studio 没有伪造 Candidate。"));
  };

  const backup = async () => {
    const result = await invokeBridge("project.backup", { project_id: projectId() });
    setStatus(result.status === "ok" ? message("Verified backup created.", "已创建并校验 backup。") : operationError(result));
  };

  const exportPortable = async () => {
    setError(undefined);
    const exported = await invokeBridge<ExportResult>("project.export", { project_id: projectId() });
    if (exported.status !== "ok" || !exported.data) { setError(operationError(exported)); return; }
    const artifact = await invokeBridge<ArtifactRead>("artifact.read", { artifact_ref: exported.data.artifact_ref });
    if (artifact.status !== "ok" || !artifact.data) { setError(operationError(artifact)); return; }
    const blob = new Blob([fromBase64(artifact.data.payload_base64)], { type: artifact.data.media_type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = artifact.data.file_name; anchor.click();
    URL.revokeObjectURL(url);
    setStatus(message("Portable project exported without credentials.", "可携 Project 已导出，且不包含 credentials。"));
  };

  onMount(() => { void loadDocuments().catch((cause) => setError(cause instanceof Error ? cause.message : String(cause))); });
  onCleanup(() => { if (timer !== undefined) window.clearTimeout(timer); });

  return (
    <section class="nf-page nf-manuscript-page nf-authoring-canvas">
      <header class="nf-manuscript-header">
        <div><span class="nf-eyebrow">MANUSCRIPT · {projectId() || "no project"}</span><h1>{documentTitle() || message("Manuscript", "手稿")}</h1></div>
        <div class="nf-inline-actions">
          <span class="wui-badge wui-badge--outline">{authority()}</span>
          <span class="wui-badge wui-badge--outline" data-state={saveState()}>{saveState()}</span>
          <button class="wui-button wui-button--ghost" type="button" onClick={() => void backup()}>{message("Backup", "备份")}</button>
          <button class="wui-button wui-button--outline" type="button" onClick={() => void exportPortable()}>.qfproject</button>
        </div>
      </header>

      <Show when={projectId()} fallback={<div class="wui-alert"><div class="wui-alert__body"><strong>{message("Choose or create a project first.", "请先选择或创建 Project。")}</strong><A href="/start">Start</A></div></div>}>
        <div class="nf-manuscript-layout">
          <aside class="nf-binder" aria-label={message("Manuscript binder", "手稿 Binder")}>
            <div class="nf-binder-heading"><strong>{message("Binder", "目录")}</strong><small>{documents().length}</small></div>
            <For each={documents()}>{(item) => <button type="button" class="nf-binder-item" data-active={documentId() === item.document_id ? "true" : undefined} onClick={() => void openDocument(item.document_id)}><span>{item.title}</span><small>{item.latest_authority_class || "proposal"}</small></button>}</For>
            <div class="nf-binder-create"><input value={newTitle()} onInput={(e) => setNewTitle(e.currentTarget.value)} placeholder={message("New chapter / scene", "新章节 / 场景")} /><button class="wui-button wui-button--outline" type="button" disabled={!newTitle().trim()} onClick={() => void createDocument()}>＋</button></div>
          </aside>

          <main class="nf-writing-surface">
            <Show when={documentId()} fallback={<div class="nf-empty-state"><h2>{message("Create the first manuscript document", "创建第一份手稿文档")}</h2><p>{message("Documents are persisted by Core, not browser storage.", "文档由 Core 持久化，不使用浏览器存储充当 authority。")}</p></div>}>
              <textarea class="nf-manuscript-editor" value={content()} onInput={(e) => { setContent(e.currentTarget.value); queueSave(); }} aria-label={message("Manuscript editor", "手稿编辑器")} spellcheck />
              <div class="nf-editor-foot"><span>{content().length.toLocaleString()} {message("characters", "字符")}</span><span>{fingerprint()?.slice(0, 20) || "no revision"}</span><Show when={saveState() === "conflict"}><strong>{message("Revision conflict — reload before overwriting.", "Revision 冲突——请重新加载，不能静默覆盖。")}</strong></Show></div>
            </Show>
          </main>

          <aside class="nf-ai-dock" aria-label={message("AI Assistant", "AI 助手")}>
            <div class="nf-section-heading"><span class="nf-eyebrow">AI</span><h2>{message("Assistant", "助手")}</h2></div>
            <select value={aiMode()} onChange={(e) => setAiMode(e.currentTarget.value)}><option>DRAFT</option><option>REVISE</option><option>AUDIT</option><option>RESEARCH</option></select>
            <textarea value={aiInstruction()} onInput={(e) => setAiInstruction(e.currentTarget.value)} placeholder={message("What should Quillframe do with this manuscript?", "希望 Quillframe 对这份手稿做什么？")} />
            <button class="wui-button" type="button" disabled={!documentId() || !aiInstruction().trim()} onClick={() => void startAiRun()}>{message("Start real Core run", "启动真实 Core Run")}</button>
            <Show when={aiRun()}>{(run) => <div class="nf-run-state"><strong>{String(run().status || "awaiting_semantic")}</strong><code>{String(run().run_id || "")}</code><p>{message("Raw model output is never surfaced here. A Candidate appears only after the production semantic gate qualifies it.", "这里永远不会直接展示 Raw model output。只有通过 production semantic gate 后，Candidate 才能出现。")}</p></div>}</Show>
            <A class="wui-button wui-button--ghost" href={`/review?project=${encodeURIComponent(projectId())}`}>{message("Open Review", "打开 Review")}</A>
          </aside>
        </div>

        <section class="nf-revision-strip">
          <div class="nf-section-heading"><span class="nf-eyebrow">HISTORY</span><h2>{message("Revisions", "版本历史")}</h2></div>
          <div class="nf-revision-list"><For each={history()}>{(item) => <div class="nf-revision-row"><div><strong>{item.authority_class}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div><code>{item.revision_id.slice(0, 18)}…</code><span>{item.source}</span><button class="wui-button wui-button--ghost" type="button" disabled={!revisionId() || item.revision_id === revisionId()} onClick={() => void compareRevision(item.revision_id)}>{message("Compare", "比较")}</button><button class="wui-button wui-button--ghost" type="button" disabled title={message("Exact restore requires a separate 0.9 schema migration because identical fingerprints are currently de-duplicated.", "Exact restore 需要独立的 0.9 schema migration；当前相同 fingerprint 会被去重。")}>{message("Restore · deferred", "恢复 · deferred")}</button></div>}</For></div>
          <Show when={diff().length}><pre class="wui-code-block nf-diff"><code>{diff().join("\n")}</code></pre></Show>
        </section>
      </Show>

      <Show when={status()}><div class="wui-alert" role="status"><div class="wui-alert__body"><span>{status()}</span></div></div></Show>
      <Show when={error()}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong>{error()}</strong></div></div></Show>
    </section>
  );
}
