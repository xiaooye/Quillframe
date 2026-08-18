import { For, Show, createMemo, createSignal } from "solid-js";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { invokeBridge } from "../bridge";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import "../styles/projection-workbenches.css";

type Profile = "text" | "web" | "print" | "epub";
type PublicationPreviewProjection = {
  schema: "quillframe_publication_preview_projection_v1";
  profile: Profile | string;
  compiler_profile: string;
  compiler: "publication/compiler.py";
  source_fingerprint: string;
  accepted_chapters: Array<{ chapter_id: string; title: string; accepted_fingerprint: string }>;
  accepted_fingerprint_guard: true;
  source_authority_verified: false;
  text_preservation: string;
  text_roundtrip: boolean;
  artifact: { sha256: string | null; kind: string; derived: true };
  preview: { kind: "text" | "html" | "xhtml"; content: string; truncated: boolean; entry?: string | null };
  validation?: { valid?: boolean; text_roundtrip?: boolean; external_epubcheck?: unknown; spec_target?: string } | null;
  query_only: true;
  mutation_performed: false;
  model_execution: false;
  authority: false;
  canon_authority: false;
  settlement_authority: false;
};

const profiles: Array<{ id: Profile; icon: string; label: string; meta: string }> = [
  { id: "text", icon: "TXT", label: "Text", meta: "clean_text" },
  { id: "web", icon: "◎", label: "Web", meta: "web_reflow" },
  { id: "print", icon: "▤", label: "Print", meta: "print_book" },
  { id: "epub", icon: "▣", label: "EPUB", meta: "epub3" },
];

const inlineFixture = `{
  "book": {
    "identifier": "urn:quillframe:preview",
    "title": "Quillframe Preview",
    "language": "zh-CN",
    "modified": "2026-08-15T00:00:00Z"
  },
  "chapters": [{
    "chapter_id": "CH-001",
    "title": "第一章",
    "text": "把这里替换成 accepted manuscript text。",
    "accepted_fingerprint": "sha256:REPLACE_WITH_SHA256_OF_EXACT_TEXT"
  }]
}`;

export default function Publication() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [profile, setProfile] = createSignal<Profile>("epub");
  const [mode, setMode] = createSignal<"manifest" | "inline">("manifest");
  const [manifest, setManifest] = createSignal("publication-source.json");
  const [sourceText, setSourceText] = createSignal(inlineFixture);
  const [preview, setPreview] = createSignal<PublicationPreviewProjection>();
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();

  const compile = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const args: Record<string, unknown> = { profile: profile() };
      if (mode() === "manifest") {
        const root = studio.projectRoot().trim();
        if (!root) throw new Error("project_root is required for a project-relative publication source manifest");
        args.project_root = root;
        args.source_manifest = manifest().trim();
      } else {
        const value: unknown = JSON.parse(sourceText());
        if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("publication source JSON must be an object");
        args.source = value as Record<string, unknown>;
      }
      const result = await invokeBridge<PublicationPreviewProjection>("publication.preview", args);
      if (result.status !== "ok" || !result.data) throw new Error(JSON.stringify(result.error));
      setPreview(result.data);
    } catch (value) {
      setError(value instanceof Error ? value.message : String(value));
    } finally {
      setLoading(false);
    }
  };

  const active = createMemo(() => profiles.find((item) => item.id === profile())!);

  return (
    <section class="nf-page nf-live-publication-page">
      <PageIntro
        eyebrow="PUBLICATION COMPILER · DERIVED ONLY"
        title={zh() ? "用真正的 compiler 看同一份正文怎样变成四种载体。" : "Run the real compiler across four derived reading formats."}
        body={zh()
          ? "Studio 调用 publication/compiler.py，在临时目录构建真实 Text、Web、Print 或 EPUB 派生物，并返回 artifact fingerprint 与可视预览。Project、Canon 和 Settlement 都不会被修改。"
          : "Studio calls publication/compiler.py, builds a real Text, Web, Print, or EPUB derivative in a temporary workspace, and returns its artifact fingerprint plus a visual preview. Project, Canon, and Settlement remain untouched."}
        actions={<span class="wui-badge wui-badge--outline">authority=false</span>}
      />

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <section class="nf-publication-source wui-card wui-card--outlined">
          <header>
            <div><span class="nf-eyebrow">ACCEPTED-TEXT FINGERPRINT GUARD</span><h2>{zh() ? "选择 compiler 输入" : "Choose compiler input"}</h2></div>
            <div class="nf-publication-source-tabs">
              <button type="button" class="wui-button wui-button--soft" data-active={mode() === "manifest" ? "true" : undefined} onClick={() => setMode("manifest")}>{zh() ? "Project 内 JSON" : "Project JSON"}</button>
              <button type="button" class="wui-button wui-button--soft" data-active={mode() === "inline" ? "true" : undefined} onClick={() => setMode("inline")}>{zh() ? "内联 JSON" : "Inline JSON"}</button>
            </div>
          </header>

          <Show when={mode() === "manifest"} fallback={
            <label class="nf-publication-source-editor">
              <span>{zh() ? "Publication source JSON" : "Publication source JSON"}</span>
              <textarea value={sourceText()} onInput={(event) => setSourceText(event.currentTarget.value)} spellcheck={false} />
              <small>{zh() ? "accepted_fingerprint 必须与每个 chapter 的 exact UTF-8 text 匹配，否则 compiler fail closed。" : "accepted_fingerprint must match each chapter's exact UTF-8 text or the compiler fails closed."}</small>
            </label>
          }>
            <div class="nf-publication-manifest-grid">
              <label><span>{zh() ? "项目根目录" : "Project root"}</span><input class="wui-input" value={studio.projectRoot()} onInput={(event) => studio.setProjectRoot(event.currentTarget.value)} placeholder="/path/to/project" spellcheck={false} /></label>
              <label><span>{zh() ? "Project-relative source manifest" : "Project-relative source manifest"}</span><input class="wui-input" value={manifest()} onInput={(event) => setManifest(event.currentTarget.value)} placeholder="publication-source.json" spellcheck={false} /></label>
            </div>
          </Show>
        </section>

        <section class="nf-publication-profile-rail" aria-label={zh() ? "出版格式" : "Publication formats"}>
          <For each={profiles}>{(item) => (
            <button type="button" data-active={profile() === item.id ? "true" : undefined} onClick={() => setProfile(item.id)}>
              <span>{item.icon}</span><strong>{item.label}</strong><small>{item.meta}</small>
            </button>
          )}</For>
        </section>

        <div class="nf-publication-runbar">
          <div><span class="nf-eyebrow">CURRENT PROFILE</span><strong>{active().label} · {active().meta}</strong></div>
          <button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void compile()}>
            {loading() ? (zh() ? "编译中…" : "Compiling…") : (zh() ? `生成 ${active().label} 预览` : `Build ${active().label} preview`)}
          </button>
        </div>
        <QueryError message={error()} />

        <Show when={preview()} fallback={<div class="wui-empty-state nf-empty"><p>{zh() ? "运行 compiler 后，这里显示真实派生 artifact。" : "Run the compiler to inspect a real derived artifact."}</p></div>}>
          {(result) => (
            <div class="nf-publication-workbench-live">
              <section class="nf-publication-live-preview" data-profile={profile()}>
                <header><span>{active().icon}</span><strong>{active().label} Preview</strong><small>{result().preview.kind}</small></header>
                <Show when={result().preview.kind !== "text"} fallback={<pre>{result().preview.content}</pre>}>
                  <iframe title={`${active().label} publication preview`} sandbox="" srcdoc={result().preview.content} />
                </Show>
              </section>

              <aside class="nf-publication-live-inspector">
                <header><span class="nf-eyebrow">PROVENANCE</span><h2>{zh() ? "真实编译结果" : "Real compiler result"}</h2></header>
                <dl>
                  <div><dt>Compiler</dt><dd class="nf-mono">{result().compiler}</dd></div>
                  <div><dt>IR</dt><dd class="nf-mono">quillframe_publication_ir_v1</dd></div>
                  <div><dt>Profile</dt><dd>{result().compiler_profile}</dd></div>
                  <div><dt>Source</dt><dd class="nf-mono">{result().source_fingerprint}</dd></div>
                  <div><dt>Artifact</dt><dd class="nf-mono">{result().artifact.sha256 ?? "—"}</dd></div>
                  <div><dt>Text roundtrip</dt><dd>{String(result().text_roundtrip)}</dd></div>
                  <div><dt>Source authority verified</dt><dd>{String(result().source_authority_verified)}</dd></div>
                  <Show when={result().validation}><div><dt>EPUB internal validation</dt><dd>{String(result().validation?.valid)}</dd></div></Show>
                </dl>
                <div class="nf-publication-accepted-list">
                  <span class="nf-eyebrow">ACCEPTED FINGERPRINTS</span>
                  <For each={result().accepted_chapters}>{(chapter) => <div><strong>{chapter.chapter_id} · {chapter.title}</strong><code>{chapter.accepted_fingerprint}</code></div>}</For>
                </div>
                <footer><span>query_only=true</span><span>mutation_performed=false</span><span>model_execution=false</span><span>authority=false</span></footer>
              </aside>
            </div>
          )}
        </Show>
      </Show>
    </section>
  );
}
