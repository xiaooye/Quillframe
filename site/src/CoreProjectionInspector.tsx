import { For, Show, createMemo, createSignal } from "solid-js";
import type { Locale } from "./content";

type ProjectionBundle = {
  schema: "novelforge_product_projection_bundle_v1";
  project: {
    valid: boolean;
    project: {
      authority: false;
      project: { id?: string | null; title?: string | null; language?: string | null; version?: string | null; layout?: string | null };
      framework_lock: Record<string, unknown>;
      projection_fingerprint?: string;
    };
  };
  runtime: {
    sessions: { count: number; sessions: Array<{ session_id: string; role: string; task_mode?: string | null; status: string; latest_run_id?: string | null; latest_run_status?: string | null; checkpoint_count: number; updated_at: string }> };
    selected_session: null | { session: { session_id: string; runs: Array<{ run_id?: string | null; status?: string | null; output_artifact_fingerprints?: string[] }>; checkpoints: Array<{ checkpoint_id?: string | null; pending_gate?: string | null; pending_handoff?: string | null }> } };
    events: null | { count: number; events: Array<{ event_type: string; run_id?: string | null; artifact_fingerprints?: string[] }> };
    receipts: null | { count: number; receipts: Array<{ stage: string; guards: Array<{ guard_id: string; status: string }>; semantic_jobs: Array<{ contract_id: string; status: string }>; artifact_fingerprints: string[] }> };
  };
  context?: Record<string, unknown> | null;
  bridge_result_fingerprints: string[];
  query_only: true;
  mutation_performed: false;
  authority: false;
  canon_authority: false;
  settlement_authority: false;
};

function isBundle(value: unknown): value is ProjectionBundle {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ProjectionBundle>;
  return candidate.schema === "novelforge_product_projection_bundle_v1"
    && candidate.authority === false
    && candidate.canon_authority === false
    && candidate.settlement_authority === false
    && candidate.query_only === true
    && candidate.mutation_performed === false
    && Boolean(candidate.project)
    && Boolean(candidate.runtime)
    && Array.isArray(candidate.bridge_result_fingerprints);
}

export default function CoreProjectionInspector(props: { locale: Locale }) {
  const zh = () => props.locale === "zh-CN";
  const [bundle, setBundle] = createSignal<ProjectionBundle>();
  const [error, setError] = createSignal("");

  const importProjection = async (file: File | undefined) => {
    if (!file) return;
    setError("");
    try {
      const value: unknown = JSON.parse(await file.text());
      if (!isBundle(value)) throw new Error("Projection bundle schema or authority boundary is invalid.");
      setBundle(value);
    } catch (value) {
      setBundle(undefined);
      setError(value instanceof Error ? value.message : String(value));
    }
  };

  const session = createMemo(() => bundle()?.runtime.selected_session?.session);
  const receipts = createMemo(() => bundle()?.runtime.receipts?.receipts ?? []);
  const guards = createMemo(() => receipts().flatMap((receipt) => receipt.guards));
  const events = createMemo(() => bundle()?.runtime.events?.events ?? []);
  const outputArtifacts = createMemo(() => {
    const values = new Set<string>();
    for (const run of session()?.runs ?? []) for (const fp of run.output_artifact_fingerprints ?? []) values.add(fp);
    for (const receipt of receipts()) for (const fp of receipt.artifact_fingerprints ?? []) values.add(fp);
    return [...values];
  });

  return (
    <section class="core-projection-inspector" data-loaded={bundle() ? "true" : undefined}>
      <header class="core-projection-heading">
        <div>
          <p class="eyebrow">CORE PROJECTION · PORTABLE</p>
          <h2>{zh() ? "检查真实 Runtime 投影，而不是猜项目状态。" : "Inspect real Runtime projections instead of guessing project state."}</h2>
          <p>{zh()
            ? "从绑定的 NovelForge Studio 导出 novelforge_product_projection_bundle_v1，然后在这里本地打开。Hosted Product Site 不会直接连接你的本机 Core。"
            : "Export novelforge_product_projection_bundle_v1 from a bound NovelForge Studio and open it locally here. The hosted Product Site never reaches directly into your local Core."}</p>
        </div>
        <label class="wui-button wui-button--solid core-projection-picker">
          {zh() ? "导入 Core projection" : "Import Core projection"}
          <input type="file" accept="application/json,.json" onChange={(event) => void importProjection(event.currentTarget.files?.[0])} />
        </label>
      </header>

      <Show when={error()}><div class="core-projection-error" role="alert">{error()}</div></Show>

      <Show when={bundle()} fallback={
        <div class="core-projection-empty">
          <span aria-hidden="true">♡</span>
          <strong>{zh() ? "等待安全 projection bundle" : "Waiting for a safe projection bundle"}</strong>
          <small>query_only=true · authority=false · mutation_performed=false</small>
        </div>
      }>
        {(projection) => (
          <>
            <div class="core-projection-stats">
              <div><span>Project</span><strong>{projection().project.project.project.title ?? projection().project.project.project.id ?? "—"}</strong><small>{projection().project.project.project.id ?? "—"}</small></div>
              <div><span>Sessions</span><strong>{projection().runtime.sessions.count}</strong><small>{session()?.session_id ?? (zh() ? "无当前 session" : "no selected session")}</small></div>
              <div><span>Events</span><strong>{projection().runtime.events?.count ?? 0}</strong><small>{events().at(-1)?.event_type ?? "—"}</small></div>
              <div><span>Receipts</span><strong>{projection().runtime.receipts?.count ?? 0}</strong><small>{receipts().at(-1)?.stage ?? "—"}</small></div>
            </div>

            <div class="core-projection-grid">
              <section>
                <header><span>RUN</span><strong>{session()?.runs.at(-1)?.run_id ?? "—"}</strong></header>
                <dl>
                  <div><dt>Status</dt><dd>{session()?.runs.at(-1)?.status ?? "—"}</dd></div>
                  <div><dt>Checkpoints</dt><dd>{session()?.checkpoints.length ?? 0}</dd></div>
                  <div><dt>Pending gates</dt><dd>{session()?.checkpoints.filter((item) => item.pending_gate).length ?? 0}</dd></div>
                  <div><dt>Output artifacts</dt><dd>{outputArtifacts().length}</dd></div>
                </dl>
              </section>
              <section>
                <header><span>GATES</span><strong>{guards().length}</strong></header>
                <Show when={guards().length} fallback={<p>{zh() ? "没有公开 guard evidence。" : "No public guard evidence."}</p>}>
                  <div class="core-projection-list"><For each={guards()}>{(guard) => <div><code>{guard.guard_id}</code><span>{guard.status}</span></div>}</For></div>
                </Show>
              </section>
              <section>
                <header><span>PROVENANCE</span><strong>{projection().bridge_result_fingerprints.length}</strong></header>
                <div class="core-projection-list"><For each={projection().bridge_result_fingerprints}>{(fp) => <code>{fp}</code>}</For></div>
              </section>
            </div>

            <footer class="core-projection-boundary">
              <span>query_only=true</span><span>mutation_performed=false</span><span>authority=false</span><span>canon_authority=false</span><span>settlement_authority=false</span>
            </footer>
          </>
        )}
      </Show>
    </section>
  );
}
