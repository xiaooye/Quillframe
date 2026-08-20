import { For, Show, createMemo, createSignal, onCleanup } from "solid-js";
import brandMark from "../../assets/brand/quillframe-mark.svg?url";
import type { Locale } from "./content";
import { ProductSurfaceHero } from "./ProductSurface";
import type { PublicationCompilerProfile } from "./publicationCompiler.worker";
import { createRestartableWorker, createSingleFlight, createLoadingOwner, isCurrentWorkerEvent, shouldCommitPublicationResult } from "./workerLifecycle";

type UiProfile = {
  id: "text" | "web" | "print" | "epub";
  compilerProfile: PublicationCompilerProfile;
  icon: string;
  labelZh: string;
  labelEn: string;
  artifact: string;
  titleZh: string;
  titleEn: string;
};

type Artifact = {
  name: string;
  mime: string;
  size: number;
  sha256: string;
  base64: string;
};

type PlaygroundResult = {
  schema: "quillframe_publication_playground_result_v1";
  profile: PublicationCompilerProfile;
  compiler: "publication/compiler.py";
  compiler_runtime: string;
  source_fingerprint: string;
  text_preservation: string;
  text_roundtrip: boolean;
  source_authority_verified: false;
  preview: { kind: "text" | "html" | "xhtml"; content: string; entry?: string | null };
  validation: { valid?: boolean; text_roundtrip?: boolean; kind?: string; spec_target?: string; external_epubcheck?: unknown; errors?: string[] } | null;
  artifacts: Artifact[];
  accepted_chapters: Array<{ chapter_id: string; title: string; accepted_fingerprint: string }>;
  authority: false;
  canon_authority: false;
  settlement_authority: false;
  mutation_performed: false;
  model_execution: false;
};

type WorkerResponse =
  | { kind: "ready"; pyodide_version: string }
  | { kind: "result"; id: string; result: string }
  | { kind: "error"; id: string; error: string };

const profiles: UiProfile[] = [
  { id: "text", compilerProfile: "clean_text", icon: "TXT", labelZh: "纯文本", labelEn: "Clean text", artifact: ".txt", titleZh: "只保留正文，不叠加表现层", titleEn: "Exact text, no presentation layer" },
  { id: "web", compilerProfile: "web_reflow", icon: "WEB", labelZh: "网页", labelEn: "Web", artifact: ".html", titleZh: "适配屏幕的阅读表面", titleEn: "Responsive reading surface" },
  { id: "print", compilerProfile: "print_book", icon: "PRINT", labelZh: "印刷版", labelEn: "Print", artifact: "print HTML", titleZh: "面向纸面的分页排版", titleEn: "Paged-media composition" },
  { id: "epub", compilerProfile: "epub3", icon: "EPUB", labelZh: "EPUB", labelEn: "EPUB", artifact: ".epub", titleZh: "可重排的电子书包", titleEn: "Reflowable ebook package" },
];

const MAX_UPLOAD_BYTES = 2 * 1024 * 1024;
const INITIAL_TEXT = "";

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

async function fingerprintText(text: string) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const hex = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `sha256:${hex}`;
}

function cleanTitle(name: string) {
  return name.replace(/\.(json|txt|md|markdown)$/i, "").trim() || "Playground manuscript";
}

async function textSource(text: string, name: string) {
  if (!text.length) throw new Error("Publication source is empty");
  const acceptedFingerprint = await fingerprintText(text);
  const title = cleanTitle(name);
  const heading = text.split(/\r?\n/).find((line) => line.trim())?.replace(/^#{1,6}\s+/, "").trim();
  return {
    book: {
      identifier: `urn:quillframe:playground:${acceptedFingerprint.slice("sha256:".length, "sha256:".length + 24)}`,
      title,
      language: "zh-CN",
      modified: "1970-01-01T00:00:00Z",
    },
    chapters: [{
      chapter_id: "CH-001",
      title: heading && heading.length <= 100 ? heading : title,
      text,
      accepted_fingerprint: acceptedFingerprint,
    }],
  };
}

async function normalizeInput(raw: string, name: string): Promise<Record<string, unknown>> {
  const trimmed = raw.trim();
  if (!trimmed) throw new Error("Publication source is empty");
  if (trimmed.startsWith("{")) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch (value) {
      throw new Error(`JSON parse failed: ${value instanceof Error ? value.message : String(value)}`);
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("JSON source must be an object");
    const candidate = parsed as Record<string, unknown>;
    if (candidate.schema === "quillframe_agent_result_v1") {
      if (typeof candidate.final_text !== "string") throw new Error("quillframe_agent_result_v1 has no final_text to publish");
      return textSource(candidate.final_text, name || "Agent result");
    }
    if (candidate.book && Array.isArray(candidate.chapters)) return candidate;
    throw new Error("JSON must be a publication source {book, chapters} or quillframe_agent_result_v1 with final_text");
  }
  return textSource(raw, name);
}

function decodeArtifact(artifact: Artifact) {
  const binary = atob(artifact.base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function downloadArtifact(artifact: Artifact) {
  const bytes = decodeArtifact(artifact);
  const blob = new Blob([bytes], { type: artifact.mime });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = artifact.name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(href), 0);
}

function ProfileGallery(props: { selected: number; onSelect: (index: number) => void; zh: boolean }) {
  return <div class="unified-publication-gallery">
    <For each={profiles}>{(profile, index) => <button type="button" class={`unified-publication-snapshot snapshot-${profile.id}`} data-active={props.selected === index()} onClick={() => props.onSelect(index())}>
      <span class="snapshot-label">{profile.icon}</span>
      <div class="snapshot-mini-page" aria-hidden="true"><strong>{props.zh ? "真实 compiler 预览" : "Real compiler preview"}</strong><i /><i /><i /><i /></div>
      <small>{props.zh ? profile.labelZh : profile.labelEn}</small>
    </button>}</For>
  </div>;
}

export default function PublicationWorkbench(props: { locale: Locale }) {
  const zh = () => props.locale === "zh-CN";
  const [selected, setSelected] = createSignal(3);
  const [sourceText, setSourceText] = createSignal(INITIAL_TEXT);
  const [sourceName, setSourceName] = createSignal("Playground manuscript");
  const [dragging, setDragging] = createSignal(false);
  const [loading, setLoading] = createSignal(false);
  const [runtimeState, setRuntimeState] = createSignal<"idle" | "loading" | "ready">("idle");
  const [runtimeVersion, setRuntimeVersion] = createSignal<string>();
  const [result, setResult] = createSignal<PlaygroundResult>();
  const [error, setError] = createSignal<string>();
  let fileInput: HTMLInputElement | undefined;
  type CompileMessage = { kind: "compile"; payload: { id: string; profile: PublicationCompilerProfile; source: Record<string, unknown> } };
  const lifecycle = createRestartableWorker<CompileMessage>(() => new Worker(new URL("./publicationCompiler.worker.ts", import.meta.url), { type: "module" }));
  const flight = createSingleFlight<PlaygroundResult>();
  const loadingOwner = createLoadingOwner();
  let compilerLease: ReturnType<typeof lifecycle.acquire> | undefined;
  let activeRequest: { id: string; token: symbol; epoch: number; profile: PublicationCompilerProfile } | undefined;
  let inputEpoch = 0;
  let disposed = false;

  const current = createMemo(() => profiles[selected()]);

  const worker = () => {
    compilerLease ??= lifecycle.acquire();
    const lease = compilerLease;
    setRuntimeState("loading");
    lease.worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;
      if (disposed || !lifecycle.isCurrent(lease)) return;
      if (message.kind === "ready") {
        setRuntimeVersion(message.pyodide_version);
        setRuntimeState("ready");
        return;
      }
      if (!activeRequest || !isCurrentWorkerEvent({ disposed, lifecycle, lease, flight, token: activeRequest.token, requestId: activeRequest.id, eventId: message.id })) return;
      const pending = activeRequest;
      activeRequest = undefined;
      if (message.kind === "error") {
        lifecycle.invalidate(lease);
        compilerLease = undefined;
        flight.reject(pending.token, new Error(message.error));
        setRuntimeState("idle");
      } else {
        try {
          const parsed = JSON.parse(message.result) as PlaygroundResult;
          if (shouldCommitPublicationResult({ capturedEpoch: pending.epoch, currentEpoch: inputEpoch, capturedProfile: pending.profile, currentProfile: current().compilerProfile })) setResult(parsed);
          flight.resolve(pending.token, parsed);
        } catch (value) {
          lifecycle.invalidate(lease);
          compilerLease = undefined;
          flight.reject(pending.token, new Error(`Compiler returned invalid JSON: ${value instanceof Error ? value.message : String(value)}`));
          setRuntimeState("idle");
        }
      }
      flight.finish(pending.token);
    };
    lease.worker.onerror = (event) => {
      if (disposed || !lifecycle.isCurrent(lease)) return;
      lifecycle.invalidate(lease);
      compilerLease = undefined;
      if (activeRequest && flight.isCurrent(activeRequest.token)) {
        flight.reject(activeRequest.token, new Error(event.message || "Publication compiler worker failed"));
        flight.finish(activeRequest.token);
        activeRequest = undefined;
      }
      setRuntimeState("idle");
    };
    return lease;
  };

  onCleanup(() => {
    disposed = true;
    flight.dispose(new Error("Publication workbench closed"));
    lifecycle.dispose(new Error("Publication workbench closed"));
  });

  const compile = async () => {
    const started = flight.tryBegin();
    if (!started.accepted) {
      setError(started.error.message);
      return;
    }
    const token = started.flight.token;
    const loadingToken = loadingOwner.begin();
    setLoading(true);
    setError(undefined);
    try {
      const source = await normalizeInput(sourceText(), sourceName());
      const id = crypto.randomUUID();
      const profile = current().compilerProfile;
      activeRequest = { id, token, epoch: inputEpoch, profile };
      worker().post({ kind: "compile", payload: { id, profile, source } });
      await started.flight.promise;
    } catch (value) {
      if (compilerLease) lifecycle.invalidate(compilerLease);
      compilerLease = undefined;
      setRuntimeState("idle");
      activeRequest = undefined;
      flight.finish(token);
      setResult(undefined);
      setError(value instanceof Error ? value.message : String(value));
    } finally {
      if (loadingOwner.finish(loadingToken)) setLoading(false);
    }
  };

  const loadFile = async (file: File) => {
    setError(undefined);
    if (file.size > MAX_UPLOAD_BYTES) {
      setError(zh() ? "文件超过 2 MiB playground 上限。" : "File exceeds the 2 MiB playground limit.");
      return;
    }
    if (!/\.(json|txt|md|markdown)$/i.test(file.name)) {
      setError(zh() ? "支持 JSON、TXT、MD、Markdown。" : "Supported files: JSON, TXT, MD, Markdown.");
      return;
    }
    try {
      setSourceText(await file.text());
      inputEpoch += 1;
      setSourceName(file.name);
      setResult(undefined);
    } catch (value) {
      setError(value instanceof Error ? value.message : String(value));
    }
  };

  const preview = () => result()?.preview;

  return <div class="page-width section-compact unified-route-page publication-workbench-entry publication-playground">
    <ProductSurfaceHero
      class="kawaii-publication-hero"
      tone="publication"
      eyebrow={<span>🎀 {zh() ? "真实出版 Playground" : "REAL PUBLICATION PLAYGROUND"}</span>}
      badges={<><span class="wui-badge wui-badge--outline">publication/compiler.py</span><span class="wui-badge wui-badge--outline">authority=false</span></>}
      title={zh() ? <>上传或粘贴一份正文，生成<span>真正可下载的出版文件。</span></> : <>Upload or paste manuscript text and build <span>real downloadable publication files.</span></>}
      lede={<p>{zh() ? "浏览器在 Web Worker 里运行仓库同一份 Python compiler。TXT、Web、Print、EPUB 都来自真实 artifact；上传内容不会写入 Project、Canon 或持久状态。" : "The browser runs the repository's same Python compiler inside a Web Worker. TXT, Web, Print, and EPUB previews come from real artifacts; uploads never write Project, Canon, or persistent state."}</p>}
      visual={<ProfileGallery selected={selected()} onSelect={(index) => { inputEpoch += 1; setSelected(index); setResult(undefined); }} zh={zh()} />}
    />

    <section class="publication-input-strip" aria-label={zh() ? "出版输入" : "Publication input"}>
      <div class="publication-input-heading">
        <div><span class="publication-kicker">01 · SOURCE</span><h2>{zh() ? "把 Agent 输出或正文放进来" : "Bring agent output or manuscript text"}</h2></div>
        <div class="publication-local-note"><span>⌂</span><strong>{zh() ? "本地浏览器处理" : "Browser-local processing"}</strong><small>source_authority_verified=false</small></div>
      </div>
      <div class="publication-input-grid">
        <button
          type="button"
          class="publication-dropzone"
          data-dragging={dragging() ? "true" : undefined}
          onClick={() => fileInput?.click()}
          onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            const file = event.dataTransfer?.files?.[0];
            if (file) void loadFile(file);
          }}
        >
          <input ref={fileInput} type="file" accept=".json,.txt,.md,.markdown,application/json,text/plain,text/markdown" hidden onChange={(event) => { const file = event.currentTarget.files?.[0]; if (file) void loadFile(file); event.currentTarget.value = ""; }} />
          <span class="publication-drop-icon">↥</span>
          <strong>{zh() ? "拖入文件，或点击选择" : "Drop a file, or choose one"}</strong>
          <small>.json · .txt · .md · .markdown · ≤ 2 MiB</small>
          <em>{zh() ? "识别 publication source 与 quillframe_agent_result_v1.final_text" : "Understands publication source and quillframe_agent_result_v1.final_text"}</em>
        </button>
        <label class="publication-source-editor">
          <span><strong>{sourceName()}</strong><small>{sourceText().length.toLocaleString()} chars</small></span>
          <textarea value={sourceText()} onInput={(event) => { inputEpoch += 1; setSourceText(event.currentTarget.value); setSourceName("Playground manuscript"); setResult(undefined); }} placeholder={zh() ? "粘贴正文、Markdown、publication source JSON，或 quillframe_agent_result_v1…" : "Paste manuscript text, Markdown, publication source JSON, or quillframe_agent_result_v1…"} spellcheck={false} />
        </label>
      </div>
    </section>

    <section class="publication-compile-strip">
      <div><span class="publication-kicker">02 · COMPILE</span><strong>{current().icon} · {zh() ? current().labelZh : current().labelEn}</strong><small>{zh() ? current().titleZh : current().titleEn}</small></div>
      <div class="publication-runtime-state" data-state={runtimeState()}><span>{runtimeState() === "ready" ? "✓" : runtimeState() === "loading" ? "…" : "○"}</span><small>{runtimeState() === "ready" ? `Pyodide ${runtimeVersion()}` : runtimeState() === "loading" ? (zh() ? "首次加载 Python runtime…" : "Loading Python runtime…") : (zh() ? "首次编译时加载 Python runtime" : "Python runtime loads on first compile")}</small></div>
      <button class="wui-button wui-button--solid publication-compile-button" type="button" disabled={loading() || !sourceText().trim()} onClick={() => void compile()}>{loading() ? (zh() ? "编译中…" : "Compiling…") : (zh() ? `生成 ${current().icon}` : `Build ${current().icon}`)}</button>
    </section>

    <Show when={error()}>{(message) => <div class="publication-error" role="alert"><span>!</span><div><strong>{zh() ? "编译没有完成" : "Compilation did not complete"}</strong><code>{message()}</code></div></div>}</Show>

    <Show when={result()} fallback={<section class="publication-empty-result"><span>✦</span><div><strong>{zh() ? "还没有 artifact" : "No artifact yet"}</strong><p>{zh() ? "选择格式并运行 compiler；这里不会拿示例正文冒充真实预览。" : "Choose a format and run the compiler. This surface does not substitute fixture prose for a real preview."}</p></div></section>}>
      {(compiled) => <>
        <section class="publication-result-heading"><div><span class="publication-kicker">03 · ARTIFACT</span><h2>{zh() ? "真实编译结果" : "Real compiler result"}</h2></div><div class="publication-result-badges"><span class="wui-badge wui-badge--success">compiled</span><span class="wui-badge wui-badge--success">exact text</span><span class="wui-badge wui-badge--soft">downloadable</span></div></section>
        <section class="publication-result-grid">
          <article class="publication-real-preview" data-profile={current().id}>
            <header><div class="publication-preview-brand"><img src={brandMark} alt="" aria-hidden="true" /><span><strong>Quillframe</strong><small>{current().icon} · {compiled().preview.kind}</small></span></div><span>{compiled().preview.entry ?? (zh() ? "真实 artifact 预览" : "real artifact preview")}</span></header>
            <Show when={preview()?.kind !== "text"} fallback={<pre>{preview()?.content}</pre>}>
              <iframe title={`${current().icon} publication artifact preview`} sandbox="" srcdoc={preview()?.content ?? ""} />
            </Show>
          </article>
          <aside class="publication-real-inspector">
            <div class="publication-inspector-title"><span>✧</span><div><small>PROVENANCE</small><h3>{zh() ? "从输入到文件，全程可检查" : "Inspectable from source to file"}</h3></div></div>
            <dl>
              <div><dt>Compiler</dt><dd>publication/compiler.py</dd></div>
              <div><dt>Profile</dt><dd>{compiled().profile}</dd></div>
              <div><dt>Source</dt><dd class="publication-mono">{compiled().source_fingerprint}</dd></div>
              <div><dt>Text roundtrip</dt><dd>{String(compiled().text_roundtrip)}</dd></div>
              <div><dt>Source authority verified</dt><dd>false</dd></div>
              <Show when={compiled().validation}><div><dt>Validation</dt><dd>{String(compiled().validation?.valid)}</dd></div></Show>
              <Show when={compiled().profile === "epub3"}><div><dt>Release EPUBCheck</dt><dd>{zh() ? "未运行 · release 仍需要" : "not run · still required for release"}</dd></div></Show>
            </dl>
            <div class="publication-downloads">
              <span>{zh() ? "生成文件" : "Generated files"}</span>
              <For each={compiled().artifacts}>{(artifact) => <button type="button" onClick={() => downloadArtifact(artifact)}><span>↓</span><div><strong>{artifact.name}</strong><small>{formatBytes(artifact.size)} · {artifact.mime}</small><code>{artifact.sha256}</code></div></button>}</For>
            </div>
          </aside>
        </section>
        <section class="publication-real-provenance">
          <div class="publication-pipeline-step"><span>UPLOAD</span><div><small>PLAYGROUND SOURCE</small><strong>{sourceName()}</strong><code>authority=false</code></div></div><i>→</i>
          <div class="publication-pipeline-step"><span>IR</span><div><small>PUBLICATION IR</small><strong>quillframe_publication_ir_v1</strong><code>{compiled().source_fingerprint}</code></div></div><i>→</i>
          <div class="publication-pipeline-step"><span>PY</span><div><small>REAL COMPILER</small><strong>publication/compiler.py</strong><code>Pyodide · worker</code></div></div><i>→</i>
          <div class="publication-pipeline-step"><span>{current().icon}</span><div><small>DERIVED ARTIFACT</small><strong>{compiled().artifacts[0]?.name ?? current().artifact}</strong><code>canon_authority=false</code></div></div>
        </section>
      </>}
    </Show>
  </div>;
}
