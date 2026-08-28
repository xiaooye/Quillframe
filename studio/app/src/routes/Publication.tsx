import { For, Show, createEffect, createMemo, createSignal, on, onCleanup } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";
import {
  createPublicationRequestGuard,
  createPublicationCollectionRequestGuard,
  parsePublicationArtifact,
  parsePublicationBuild,
  parsePublicationCollection,
  parsePublicationPreview,
  type PublicationBuildProjection,
  type PublicationCollectionProjection,
  type PublicationFormat,
  type PublicationPreviewProjection,
} from "../authoring/contracts";

export default function Publication() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = createMemo(() => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId());
  const routeAcceptance = createMemo(() => new URLSearchParams(location.search).get("acceptance")?.trim() || "");
  const [acceptanceId, setAcceptanceId] = createSignal(routeAcceptance());
  const sourceAcceptance = createMemo(() => acceptanceId().trim());
  const [loadedPreview, setLoadedPreview] = createSignal<{ project_id: string; data: PublicationPreviewProjection }>();
  const preview = () => {
    const loaded = loadedPreview();
    return loaded?.project_id === projectId() && loaded.data.source_acceptance_id === sourceAcceptance() ? loaded.data : undefined;
  };
  const [build, setBuild] = createSignal<PublicationBuildProjection | PublicationCollectionProjection>();
  const [selectedChapters, setSelectedChapters] = createSignal<string[]>([]);
  const [format, setFormat] = createSignal<PublicationFormat>("md");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const [downloaded, setDownloaded] = createSignal<string>();
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];
  const requests = createPublicationRequestGuard(() => ({ project_id: projectId(), acceptance_id: sourceAcceptance(), format: format() }));
  const orderedChapters = () => studio.projectId() === projectId() ? studio.chapters() : [];
  const collectionSources = createMemo(() => orderedChapters().filter((chapter) => selectedChapters().includes(chapter.chapter_id) && chapter.current_acceptance_id)
    .map((chapter) => chapter.current_acceptance_id!));
  const collectionRequests = createPublicationCollectionRequestGuard(() => ({ project_id: projectId(), acceptance_ids: collectionSources(), format: format() }));
  let collectionIntent: { request: string; idempotency_key: string } | undefined;
  let downloadGeneration = 0;
  const downloadUrls = new Set<string>();

  createEffect(on([projectId, routeAcceptance], ([, acceptance]) => setAcceptanceId(acceptance)));
  createEffect(on([projectId, sourceAcceptance], () => {
    requests.invalidate();
    setLoadedPreview(undefined); setBuild(undefined); setError(undefined); setLoading(false); setDownloaded(undefined); downloadGeneration += 1;
  }));
  createEffect(on(format, () => {
    requests.invalidate(); collectionRequests.invalidate();
    setBuild(undefined); setError(undefined); setLoading(false); setDownloaded(undefined); downloadGeneration += 1;
  }, { defer: true }));
  createEffect(on([projectId, collectionSources], () => {
    collectionRequests.invalidate();
    setBuild(undefined); setDownloaded(undefined); setLoading(false); downloadGeneration += 1;
  }, { defer: true }));
  createEffect(on(projectId, () => { setSelectedChapters([]); collectionIntent = undefined; }));
  onCleanup(() => { requests.invalidate(); collectionRequests.invalidate(); downloadGeneration += 1; for (const url of downloadUrls) URL.revokeObjectURL(url); downloadUrls.clear(); });

  const loadPreview = async () => {
    if (!projectId() || !sourceAcceptance() || !operations().includes("publication.preview")) return;
    const request = requests.begin();
    setLoading(true); setError(undefined); setLoadedPreview(undefined); setBuild(undefined);
    try {
      const result = await invokeBridge<PublicationPreviewProjection>("publication.preview", { project_id: request.source.project_id, acceptance_id: request.source.acceptance_id });
      if (!request.isCurrent()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setLoadedPreview({ project_id: request.source.project_id, data: parsePublicationPreview(result.data, request.source.acceptance_id) });
    } catch (cause) {
      if (request.isCurrent()) { setLoadedPreview(undefined); setError(cause instanceof Error ? cause.message : String(cause)); }
    } finally { if (request.isCurrent()) setLoading(false); }
  };

  const buildArtifact = async () => {
    const accepted = preview();
    if (!projectId() || !accepted || !operations().includes("publication.build")) return;
    const request = requests.begin();
    setLoading(true); setError(undefined); setBuild(undefined);
    try {
      const result = await invokeBridge<PublicationBuildProjection>("publication.build", request.source);
      if (!request.isCurrent()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setBuild(parsePublicationBuild(result.data, accepted, request.source.format));
    } catch (cause) {
      if (request.isCurrent()) setError(cause instanceof Error ? cause.message : String(cause));
    } finally { if (request.isCurrent()) setLoading(false); }
  };

  const buildCollection = async () => {
    if (!projectId() || !collectionSources().length || loading() || !operations().includes("publication.collection.build")) return;
    requests.invalidate();
    const request = collectionRequests.begin();
    const serialized = JSON.stringify(request.source);
    if (!collectionIntent || collectionIntent.request !== serialized) collectionIntent = { request: serialized, idempotency_key: `studio-collection-${crypto.randomUUID()}` };
    setLoading(true); setError(undefined); setBuild(undefined); setDownloaded(undefined);
    try {
      const result = await invokeBridge("publication.collection.build", { ...request.source, idempotency_key: collectionIntent.idempotency_key, user_authorized: true });
      if (!request.isCurrent()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setBuild(parsePublicationCollection(result.data, request.source)); collectionIntent = undefined;
    } catch (cause) { if (request.isCurrent()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (request.isCurrent()) setLoading(false); }
  };

  const downloadArtifact = async () => {
    const artifact = build(); const requestedProject = projectId();
    if (!artifact || !requestedProject || loading() || !operations().includes("publication.artifact.get")) return;
    const generation = ++downloadGeneration;
    const current = () => generation === downloadGeneration && build() === artifact && projectId() === requestedProject;
    const expected = { project_id: requestedProject, build_id: artifact.build_id, artifact_fingerprint: artifact.artifact_fingerprint,
      byte_size: artifact.byte_size, source_acceptance_ids: "source_acceptance_ids" in artifact ? artifact.source_acceptance_ids : [artifact.source_acceptance_id] };
    setLoading(true); setError(undefined); setDownloaded(undefined);
    try {
      const result = await invokeBridge("publication.artifact.get", { project_id: requestedProject, build_id: artifact.build_id });
      if (!current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const verified = await parsePublicationArtifact(result.data, expected);
      if (!current()) return;
      const url = URL.createObjectURL(new Blob([verified.bytes.buffer], { type: verified.data.media_type }));
      downloadUrls.add(url);
      const link = document.createElement("a");
      link.href = url; link.download = verified.data.filename;
      document.body.appendChild(link); link.click(); link.remove();
      setDownloaded(verified.data.filename);
      window.setTimeout(() => { URL.revokeObjectURL(url); downloadUrls.delete(url); }, 1000);
    } catch (cause) { if (current()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (current()) setLoading(false); }
  };

  return (
    <section class="nf-page qf-publish-page">
      <PageIntro eyebrow="PUBLISH · VERIFIED OUTPUT" title={zh() ? "把确认过的章节，带出创作桌面。" : "Take confirmed chapters beyond the writing desk."} body={zh() ? "单章预览使用真实接受证据；整本导出只选择当前有效且已结算的章节头。下载前校验文件大小与 SHA-256，派生文件不会改变故事事实。" : "Single-chapter previews use real acceptance evidence. Collections use current, settled chapter heads. File size and SHA-256 are verified before download; derived files do not change story facts."} />

      <section class="qf-editorial-sheet">
        <div class="qf-section-head"><h2>{zh() ? "按章节顺序导出" : "Export in chapter order"}</h2><button class="wui-button wui-button--ghost" type="button" disabled={loading() || studio.chapterLoading()} onClick={() => void studio.refreshChapters()}>{zh() ? "刷新章节" : "Refresh chapters"}</button></div>
        <p>{zh() ? "顺序以 Core 章节目录为准。未结算或前章变化后失效的版本不会自动选入。" : "Order follows Core's chapter list. Unsettled or invalidated revisions are not silently included."}</p>
        <CoreRequirementNotice operation="publication.collection.build" compact />
        <div class="qf-publication-chapters"><For each={orderedChapters()}>{(chapter) => <label><input type="checkbox" disabled={loading() || !chapter.current_acceptance_id} checked={selectedChapters().includes(chapter.chapter_id)} onChange={(event) => setSelectedChapters((current) => event.currentTarget.checked ? [...new Set([...current, chapter.chapter_id])] : current.filter((id) => id !== chapter.chapter_id))} /><span><strong>{chapter.title}</strong><small>{chapter.chapter_id} · {chapter.current_acceptance_id ? (zh() ? "当前已结算版本" : "Current settled revision") : (zh() ? "暂无可导出的有效结算版本" : "No current settled revision")}</small><Show when={chapter.current_acceptance_id}>{(id) => <code>{id()}</code>}</Show></span></label>}</For></div>
        <Show when={studio.chapterError()}>{(message) => <p role="alert">{message()}</p>}</Show>
        <Show when={!orderedChapters().length}><p>{zh() ? "项目中还没有可列出的章节。" : "No chapters are available in this project yet."}</p></Show>
        <label class="nf-field-label"><span>{zh() ? "导出格式" : "Export format"}</span><select class="wui-input" value={format()} disabled={loading()} onChange={(event) => setFormat(event.currentTarget.value as PublicationFormat)}><option value="md">Markdown</option><option value="txt">Text</option></select></label>
        <div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !collectionSources().length || !operations().includes("publication.collection.build")} onClick={() => void buildCollection()}>{zh() ? `生成选中的 ${collectionSources().length} 章` : `Build ${collectionSources().length} selected chapters`}</button><button class="wui-button wui-button--ghost" type="button" disabled={loading()} onClick={() => setSelectedChapters(orderedChapters().filter((chapter) => chapter.current_acceptance_id).map((chapter) => chapter.chapter_id))}>{zh() ? "选择全部有效章节" : "Select all eligible chapters"}</button></div>
      </section>

      <section class="qf-editorial-sheet qf-publish-source">
        <div><span class="nf-eyebrow">ACCEPTED SOURCE</span><h2>{zh() ? "选择 Acceptance" : "Choose Acceptance"}</h2><p>{zh() ? "Acceptance 是输入资格；是否 Settled 是独立状态。" : "Acceptance qualifies the source; whether it is Settled remains a separate state."}</p></div>
        <label class="nf-field-label"><span>Acceptance ID</span><input class="wui-input nf-mono" value={acceptanceId()} onInput={(event) => setAcceptanceId(event.currentTarget.value)} placeholder="accept_…" /></label>
        <div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !projectId() || !acceptanceId().trim() || !operations().includes("publication.preview")} onClick={() => void loadPreview()}>{loading() ? (zh() ? "读取中…" : "Loading…") : (zh() ? "预览派生物" : "Preview derivative")}</button><AuthorityLabel value="Accepted source required" /></div>
      </section>

      <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Publish</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>

      <Show when={preview()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "没有真实 Acceptance，就没有出版预览。" : "No real Acceptance, no publication preview."}</strong></div>}>
        {(result) => <div class="qf-publish-workspace">
          <article class="qf-publish-preview"><header><span class="nf-eyebrow">DERIVED PREVIEW</span><strong>{zh() ? "纯文本预览" : "Plain text preview"}</strong></header><pre class="qf-diff">{result().content}</pre></article>
          <aside class="qf-publish-provenance">
            <span class="nf-eyebrow">PROVENANCE</span>
            <dl><dt>source_acceptance_id</dt><dd><code>{result().source_acceptance_id}</code></dd><dt>source_fingerprint</dt><dd><code>{result().source_fingerprint}</code></dd><dt>document_id</dt><dd><code>{result().document_id ?? "—"}</code></dd><dt>{zh() ? "预览已持久化" : "Preview persisted"}</dt><dd>{String(result().persistent)}</dd></dl>
            <div class="qf-publish-build"><span>{zh() ? "当前格式" : "Current format"}: {format()}</span><button class="wui-button wui-button--outline" type="button" disabled={loading() || !preview() || !operations().includes("publication.build")} onClick={() => void buildArtifact()}>{zh() ? "生成单章派生物" : "Build chapter derivative"}</button></div>
          </aside>
        </div>}
      </Show>
      <Show when={build()}>{(artifact) => <section class="qf-editorial-sheet"><h2>{zh() ? "导出文件" : "Export file"}</h2><dl><dt>{zh() ? "文件大小" : "Byte size"}</dt><dd>{artifact().byte_size} bytes</dd><dt>SHA-256</dt><dd><code>{artifact().artifact_fingerprint}</code></dd></dl><CoreRequirementNotice operation="publication.artifact.get" compact /><button class="wui-button wui-button--solid" type="button" disabled={loading() || !operations().includes("publication.artifact.get")} onClick={() => void downloadArtifact()}>{zh() ? "校验并下载文件" : "Verify and download file"}</button><Show when={downloaded()}>{(name) => <p role="status">{zh() ? "已校验文件并交给浏览器下载" : "Verified file sent to the browser for download"}: {name()}</p>}</Show><details><summary>{zh() ? "构建来源与回执" : "Build provenance and receipt"}</summary><pre class="qf-diff">{JSON.stringify(artifact(), null, 2)}</pre></details></section>}</Show>
      <p class="qf-inspector-boundary">Accepted ≠ Settled · Publication derivative ≠ Canon · authority=false</p>
    </section>
  );
}
