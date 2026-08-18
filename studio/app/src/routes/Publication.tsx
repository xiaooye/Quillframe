import { Show, createSignal } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { AuthorityLabel } from "../authoring/AuthoringUI";

type PublicationPreview = {
  schema?: string;
  acceptance_id?: string;
  source_fingerprint?: string;
  accepted_fingerprint_guard?: boolean;
  preview?: { kind?: string; content?: string; truncated?: boolean };
  artifact?: { sha256?: string | null; kind?: string; derived?: boolean };
  authority?: false;
  canon_authority?: false;
  settlement_authority?: false;
  [key: string]: unknown;
};

type PublicationBuild = { schema?: string; acceptance_id?: string; artifact_ref?: string; format?: string; authority?: false; [key: string]: unknown };

export default function Publication() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const [acceptanceId, setAcceptanceId] = createSignal(new URLSearchParams(location.search).get("acceptance")?.trim() || "");
  const [preview, setPreview] = createSignal<PublicationPreview>();
  const [build, setBuild] = createSignal<PublicationBuild>();
  const [format, setFormat] = createSignal("md");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];

  const loadPreview = async () => {
    if (!projectId() || !acceptanceId().trim()) return;
    setLoading(true); setError(undefined); setBuild(undefined);
    try {
      const result = await invokeBridge<PublicationPreview>("publication.preview", { project_id: projectId(), acceptance_id: acceptanceId().trim() });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setPreview(result.data);
    } catch (cause) { setPreview(undefined); setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  const buildArtifact = async () => {
    if (!projectId() || !acceptanceId().trim() || !operations().includes("publication.build")) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<PublicationBuild>("publication.build", { project_id: projectId(), acceptance_id: acceptanceId().trim(), format: format() });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setBuild(result.data);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  return (
    <section class="nf-page qf-publish-page">
      <PageIntro eyebrow="PUBLISH · DERIVED OUTPUT" title={zh() ? "出版从真实 Accepted evidence 开始。" : "Publishing starts from real Accepted evidence."} body={zh() ? "Studio 不再允许手填一段文字并把它叫 Accepted。publication.preview / build 只消费 Core acceptance_id；派生物不改变 Canon，也不替代 Settlement。" : "Studio no longer lets a user paste text and call it Accepted. publication.preview / build consume a Core acceptance_id only; derived output neither changes Canon nor replaces Settlement."} />

      <section class="qf-editorial-sheet qf-publish-source">
        <div><span class="nf-eyebrow">ACCEPTED SOURCE</span><h2>{zh() ? "选择 Acceptance" : "Choose Acceptance"}</h2><p>{zh() ? "Acceptance 是输入资格；是否 Settled 是独立状态。" : "Acceptance qualifies the source; whether it is Settled remains a separate state."}</p></div>
        <label class="nf-field-label"><span>Acceptance ID</span><input class="wui-input nf-mono" value={acceptanceId()} onInput={(event) => setAcceptanceId(event.currentTarget.value)} placeholder="accept_…" /></label>
        <div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !projectId() || !acceptanceId().trim() || !operations().includes("publication.preview")} onClick={() => void loadPreview()}>{loading() ? (zh() ? "读取中…" : "Loading…") : (zh() ? "预览派生物" : "Preview derivative")}</button><AuthorityLabel value="Accepted source required" /></div>
      </section>

      <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Publish</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>

      <Show when={preview()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "没有真实 Acceptance，就没有出版预览。" : "No real Acceptance, no publication preview."}</strong></div>}>
        {(result) => <div class="qf-publish-workspace">
          <article class="qf-publish-preview"><header><span class="nf-eyebrow">DERIVED PREVIEW</span><strong>{String(result().preview?.kind ?? result().schema ?? "preview")}</strong></header><Show when={result().preview?.content} fallback={<pre class="qf-diff"><code>{JSON.stringify(result(), null, 2)}</code></pre>}>{(content) => <Show when={result().preview?.kind !== "text"} fallback={<pre>{content()}</pre>}><iframe title={zh() ? "出版预览" : "Publication preview"} sandbox="" srcdoc={content()} /></Show>}</Show></article>
          <aside class="qf-publish-provenance"><span class="nf-eyebrow">PROVENANCE</span><dl><dt>acceptance_id</dt><dd><code>{String(result().acceptance_id ?? acceptanceId())}</code></dd><dt>source_fingerprint</dt><dd><code>{String(result().source_fingerprint ?? "—")}</code></dd><dt>accepted_fingerprint_guard</dt><dd>{String(result().accepted_fingerprint_guard ?? "Core-defined")}</dd><dt>artifact</dt><dd><code>{String(result().artifact?.sha256 ?? "preview-only")}</code></dd><dt>authority</dt><dd>false</dd></dl><div class="qf-publish-build"><label class="nf-field-label"><span>{zh() ? "格式" : "Format"}</span><select class="wui-input" value={format()} onChange={(event) => setFormat(event.currentTarget.value)}><option value="md">Markdown</option><option value="txt">Text</option><option value="epub">EPUB</option></select></label><button class="wui-button wui-button--outline" type="button" disabled={loading() || !operations().includes("publication.build")} onClick={() => void buildArtifact()}>{zh() ? "生成派生物" : "Build derivative"}</button></div><Show when={build()}>{(artifact) => <pre class="qf-diff"><code>{JSON.stringify(artifact(), null, 2)}</code></pre>}</Show></aside>
        </div>}
      </Show>
      <p class="qf-inspector-boundary">Accepted ≠ Settled · Publication derivative ≠ Canon · authority=false</p>
    </section>
  );
}
