import { For, Show, createMemo, createSignal } from "solid-js";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { downloadProjection, loadProductProjection, type ProductProjectionBundle } from "../productProjection";
import { useStudio } from "../studio";

type Section = "project" | "session" | "runs" | "checkpoints" | "events" | "receipts" | "context" | "provenance";

const sections: Array<{ id: Section; label: string }> = [
  { id: "project", label: "Project" },
  { id: "session", label: "Session" },
  { id: "runs", label: "Runs" },
  { id: "checkpoints", label: "Checkpoints" },
  { id: "events", label: "Events" },
  { id: "receipts", label: "Receipts" },
  { id: "context", label: "Context" },
  { id: "provenance", label: "Provenance" },
];

function printable(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

export default function Inspector() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [bundle, setBundle] = createSignal<ProductProjectionBundle>();
  const [section, setSection] = createSignal<Section>("project");
  const [manifest, setManifest] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();

  const inspect = async () => {
    setLoading(true);
    setError(undefined);
    try {
      setBundle(await loadProductProjection(
        studio.projectRoot(),
        manifest().trim() ? { contextManifest: manifest().trim() } : {},
      ));
    } catch (value) {
      setError(value instanceof Error ? value.message : String(value));
    } finally {
      setLoading(false);
    }
  };

  const session = createMemo(() => bundle()?.runtime.selected_session?.session);
  const runs = createMemo(() => session()?.runs ?? []);
  const checkpoints = createMemo(() => session()?.checkpoints ?? []);
  const events = createMemo(() => bundle()?.runtime.events?.events ?? []);
  const receipts = createMemo(() => bundle()?.runtime.receipts?.receipts ?? []);

  const countFor = (id: Section) => {
    if (!bundle()) return 0;
    if (id === "project") return 1;
    if (id === "session") return session() ? 1 : 0;
    if (id === "runs") return runs().length;
    if (id === "checkpoints") return checkpoints().length;
    if (id === "events") return events().length;
    if (id === "receipts") return receipts().length;
    if (id === "context") return bundle()?.context ? 1 : 0;
    return bundle()?.bridge_result_fingerprints.length ?? 0;
  };

  return (
    <section class="nf-page nf-core-inspector-page">
      <PageIntro
        eyebrow="CORE INSPECTOR · EXACT PROJECTIONS"
        title={zh() ? "把 Project、Runtime、Receipt 和 Context 放在同一张证据桌上。" : "Put Project, Runtime, Receipts, and Context on one evidence desk."}
        body={zh()
          ? "Inspector 只消费公开 Host Bridge 查询。缺失字段显示为 unavailable；不会根据目录、文件名、capability 或 UI 状态猜 Canon、Settlement、质量结论或 release eligibility。"
          : "Inspector consumes public Host Bridge queries only. Missing fields remain unavailable; directory shape, filenames, capabilities, or UI state never become inferred Canon, Settlement, quality, or release eligibility."}
        actions={<span class="wui-badge wui-badge--outline">authority=false</span>}
      />

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <section class="nf-live-query-bar nf-inspector-query-bar">
          <label>
            <span>{zh() ? "项目根目录" : "Project root"}</span>
            <input class="wui-input" value={studio.projectRoot()} onInput={(event) => studio.setProjectRoot(event.currentTarget.value)} placeholder="/path/to/project" spellcheck={false} />
          </label>
          <label>
            <span>{zh() ? "可选 Context Manifest" : "Optional Context Manifest"}</span>
            <input class="wui-input" value={manifest()} onInput={(event) => setManifest(event.currentTarget.value)} placeholder="context-manifest.json" spellcheck={false} />
          </label>
          <button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void inspect()}>
            {loading() ? (zh() ? "检查中…" : "Inspecting…") : (zh() ? "读取真实投影" : "Inspect real projections")}
          </button>
          <Show when={bundle()}>
            <button class="wui-button wui-button--outline" type="button" onClick={() => downloadProjection(bundle()!, "novelforge-inspector-projection.json")}>{zh() ? "导出" : "Export"}</button>
          </Show>
        </section>
        <QueryError message={error()} />

        <Show when={bundle()} fallback={<div class="wui-empty-state nf-empty"><p>{zh() ? "选择一个绑定到 Local Core 的项目开始检查。" : "Choose a project bound to Local Core to begin inspection."}</p></div>}>
          {(projection) => (
            <div class="nf-core-inspector-workbench">
              <nav class="nf-core-inspector-tabs" aria-label={zh() ? "投影分类" : "Projection sections"}>
                <For each={sections}>{(item) => (
                  <button type="button" data-active={section() === item.id ? "true" : undefined} onClick={() => setSection(item.id)}>
                    <span>{item.label}</span><small>{countFor(item.id)}</small>
                  </button>
                )}</For>
              </nav>

              <section class="nf-core-inspector-panel">
                <Show when={section() === "project"}>
                  <header><div><span class="nf-eyebrow">PROJECT ADAPTER</span><h2>{projection().project.project.project.title ?? projection().project.project.project.id}</h2></div><span class="wui-badge wui-badge--outline">{projection().project.valid ? "valid" : "invalid"}</span></header>
                  <dl class="nf-inspector-kv">
                    <div><dt>Project ID</dt><dd>{printable(projection().project.project.project.id)}</dd></div>
                    <div><dt>Language</dt><dd>{printable(projection().project.project.project.language)}</dd></div>
                    <div><dt>Layout</dt><dd>{printable(projection().project.project.project.layout)}</dd></div>
                    <div><dt>Framework version</dt><dd>{printable(projection().project.project.framework_lock.version)}</dd></div>
                    <div><dt>Framework commit</dt><dd class="nf-mono">{printable(projection().project.project.framework_lock.commit)}</dd></div>
                    <div><dt>Bundle fingerprint</dt><dd class="nf-mono">{printable(projection().project.project.framework_lock.bundle_fingerprint)}</dd></div>
                  </dl>
                </Show>

                <Show when={section() === "session"}>
                  <header><div><span class="nf-eyebrow">RUNTIME SESSION</span><h2>{session()?.session_id ?? (zh() ? "没有 Session" : "No session")}</h2></div><span class="wui-badge wui-badge--outline">{session()?.status ?? "unavailable"}</span></header>
                  <Show when={session()} fallback={<p class="nf-inspector-empty-copy">{zh() ? "Core 没有公开当前 Session。" : "Core exposes no current session."}</p>}>
                    <dl class="nf-inspector-kv">
                      <div><dt>Role</dt><dd>{session()?.role}</dd></div>
                      <div><dt>Task mode</dt><dd>{session()?.task_mode ?? "—"}</dd></div>
                      <div><dt>Transport</dt><dd>{session()?.transport ?? "—"}</dd></div>
                      <div><dt>Latest run</dt><dd class="nf-mono">{session()?.latest_run_id ?? "—"}</dd></div>
                      <div><dt>Session version</dt><dd>{session()?.version}</dd></div>
                      <div><dt>Context manifest ref</dt><dd>{String(session()?.context_policy.context_manifest_ref_present ?? false)}</dd></div>
                    </dl>
                  </Show>
                </Show>

                <Show when={section() === "runs"}>
                  <header><div><span class="nf-eyebrow">RUNS</span><h2>{runs().length}</h2></div></header>
                  <div class="nf-inspector-records"><For each={runs()}>{(run) => <article><header><strong class="nf-mono">{run.run_id ?? "—"}</strong><span>{run.status ?? "—"}</span></header><small>{run.started_at ?? "—"} → {run.ended_at ?? "…"}</small><code>{(run.output_artifact_fingerprints ?? []).join("\n") || "no output artifact fingerprints"}</code></article>}</For></div>
                </Show>

                <Show when={section() === "checkpoints"}>
                  <header><div><span class="nf-eyebrow">CHECKPOINTS</span><h2>{checkpoints().length}</h2></div></header>
                  <div class="nf-inspector-records"><For each={checkpoints()}>{(checkpoint) => <article><header><strong class="nf-mono">{checkpoint.checkpoint_id ?? "—"}</strong><span>{checkpoint.workflow_step ?? "—"}</span></header><small>gate={checkpoint.pending_gate ?? "—"} · handoff={checkpoint.pending_handoff ?? "—"}</small><code>{checkpoint.artifact_fingerprints.join("\n") || "no artifact fingerprints"}</code></article>}</For></div>
                </Show>

                <Show when={section() === "events"}>
                  <header><div><span class="nf-eyebrow">EVENTS</span><h2>{events().length}</h2></div></header>
                  <div class="nf-inspector-records"><For each={events()}>{(event) => <article><header><strong>{event.event_type}</strong><span class="nf-mono">{event.event_id}</span></header><small>{event.created_at ?? event.received_at}</small><code>{event.payload_hash}</code></article>}</For></div>
                </Show>

                <Show when={section() === "receipts"}>
                  <header><div><span class="nf-eyebrow">RUN RECEIPTS</span><h2>{receipts().length}</h2></div></header>
                  <div class="nf-inspector-records"><For each={receipts()}>{(receipt) => <article><header><strong>{receipt.stage}</strong><span class="nf-mono">{receipt.receipt_id}</span></header><small>{receipt.semantic_jobs.length} semantic jobs · {receipt.guards.length} guards</small><code>{receipt.artifact_fingerprints.join("\n") || "no artifact fingerprints"}</code></article>}</For></div>
                </Show>

                <Show when={section() === "context"}>
                  <header><div><span class="nf-eyebrow">CONTEXT INSPECTOR</span><h2>{projection().context ? printable(projection().context.schema) : "unavailable"}</h2></div></header>
                  <Show when={projection().context} fallback={<p class="nf-inspector-empty-copy">{zh() ? "没有提供 Context Manifest，因此没有请求 Context projection。" : "No Context Manifest was supplied, so no Context projection was requested."}</p>}>
                    <pre class="nf-inspector-json">{JSON.stringify(projection().context, null, 2)}</pre>
                  </Show>
                </Show>

                <Show when={section() === "provenance"}>
                  <header><div><span class="nf-eyebrow">BRIDGE PROVENANCE</span><h2>{projection().bridge_result_fingerprints.length} results</h2></div></header>
                  <div class="nf-inspector-fingerprints"><For each={projection().bridge_result_fingerprints}>{(fingerprint) => <code>{fingerprint}</code>}</For></div>
                </Show>
              </section>

              <footer class="nf-live-projection-foot">
                <span>query_only=true</span><span>mutation_performed=false</span><span>authority=false</span><span>canon_authority=false</span><span>settlement_authority=false</span>
              </footer>
            </div>
          )}
        </Show>
      </Show>
    </section>
  );
}
