import { A } from "@solidjs/router";
import { For, Show, createMemo, createSignal } from "solid-js";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { downloadProjection, loadProductProjection, type ProductProjectionBundle } from "../productProjection";
import { useStudio } from "../studio";

type NodeId = "project" | "manager" | "context" | "worker" | "gate" | "settlement" | "publication";

const nodes: Array<{ id: NodeId; icon: string; label: string }> = [
  { id: "project", icon: "⌂", label: "Project" },
  { id: "manager", icon: "✦", label: "Manager" },
  { id: "context", icon: "◌", label: "Context" },
  { id: "worker", icon: "⌘", label: "Worker" },
  { id: "gate", icon: "✓", label: "Gate" },
  { id: "settlement", icon: "◇", label: "Settlement" },
  { id: "publication", icon: "▤", label: "Publication" },
];

function printable(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function Architecture() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [bundle, setBundle] = createSignal<ProductProjectionBundle>();
  const [selected, setSelected] = createSignal<NodeId>("project");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();

  const load = async () => {
    setLoading(true);
    setError(undefined);
    try {
      const next = await loadProductProjection(studio.projectRoot());
      setBundle(next);
    } catch (value) {
      setError(value instanceof Error ? value.message : String(value));
    } finally {
      setLoading(false);
    }
  };

  const session = createMemo(() => bundle()?.runtime.selected_session?.session);
  const receipts = createMemo(() => bundle()?.runtime.receipts?.receipts ?? []);
  const events = createMemo(() => bundle()?.runtime.events?.events ?? []);
  const semanticJobs = createMemo(() => receipts().flatMap((receipt) => receipt.semantic_jobs));
  const guards = createMemo(() => receipts().flatMap((receipt) => receipt.guards));
  const settlementEvidence = createMemo(() => [
    ...receipts().filter((receipt) => /settle/i.test(receipt.stage)),
    ...events().filter((event) => /settle/i.test(event.event_type)),
  ]);
  const artifactFingerprints = createMemo(() => {
    const values = new Set<string>();
    for (const run of session()?.runs ?? []) for (const value of run.output_artifact_fingerprints ?? []) values.add(value);
    for (const receipt of receipts()) for (const value of receipt.artifact_fingerprints ?? []) values.add(value);
    return [...values];
  });

  const details = createMemo<Array<[string, unknown]>>(() => {
    const current = selected();
    const projection = bundle();
    if (!projection) return [];
    if (current === "project") {
      const project = projection.project.project;
      return [
        ["Project ID", project.project.id],
        [zh() ? "标题" : "Title", project.project.title],
        ["Layout", project.project.layout],
        ["Framework", project.framework_lock.version],
        ["Commit", project.framework_lock.commit],
        ["Bundle", project.framework_lock.bundle_fingerprint],
      ];
    }
    if (current === "manager") {
      const value = session();
      return [
        ["Session", value?.session_id],
        ["Role", value?.role],
        ["Task mode", value?.task_mode],
        ["Status", value?.status],
        ["Latest run", value?.latest_run_id],
        ["Run status", value?.latest_run_status],
        ["Version", value?.version],
      ];
    }
    if (current === "context") {
      const policy = session()?.context_policy;
      return [
        ["Manifest ref", policy?.context_manifest_ref_present],
        ["Authority snapshot", policy?.authority_snapshot_present],
        ["Allowed artifact refs", policy?.allowed_artifact_ref_count],
        ["Allowed paths", policy?.allowed_path_count],
        ["Forbidden classes", policy?.forbidden_context_classes],
      ];
    }
    if (current === "worker") {
      return [
        [zh() ? "语义任务" : "Semantic jobs", semanticJobs().length],
        ["Contracts", semanticJobs().map((job) => job.contract_id)],
        ["Statuses", semanticJobs().map((job) => `${job.job_id}:${job.status}`)],
      ];
    }
    if (current === "gate") {
      const pending = (session()?.checkpoints ?? []).map((checkpoint) => checkpoint.pending_gate).filter(Boolean);
      return [
        ["Guards", guards().length],
        ["Guard status", guards().map((guard) => `${guard.guard_id}:${guard.status}`)],
        ["Pending gates", pending],
      ];
    }
    if (current === "settlement") {
      return [
        [zh() ? "可观测结算证据" : "Observable settlement evidence", settlementEvidence().length],
        ["Receipt stages", receipts().map((receipt) => receipt.stage)],
        [zh() ? "边界" : "Boundary", zh() ? "没有投影就不推断 Settlement。" : "Settlement is not inferred when no typed projection exists."],
      ];
    }
    return [
      [zh() ? "派生 artifact fingerprints" : "Derived artifact fingerprints", artifactFingerprints().length],
      ["Artifacts", artifactFingerprints()],
      ["Compiler preview", zh() ? "在 Publication 页面通过真实 compiler 查询生成。" : "Generated through the real compiler query on Publication."],
    ];
  });

  const nodeState = (id: NodeId) => {
    if (!bundle()) return "idle";
    if (id === "project") return "observed";
    if (id === "manager") return session() ? "observed" : "empty";
    if (id === "context") return session()?.context_policy ? "observed" : "empty";
    if (id === "worker") return semanticJobs().length ? "observed" : "empty";
    if (id === "gate") return guards().length || (session()?.checkpoints ?? []).some((value) => value.pending_gate) ? "observed" : "empty";
    if (id === "settlement") return settlementEvidence().length ? "observed" : "empty";
    return artifactFingerprints().length ? "observed" : "empty";
  };

  return (
    <section class="nf-page nf-live-architecture-page">
      <PageIntro
        eyebrow={zh() ? "LIVE ARCHITECTURE · CORE PROJECTION" : "LIVE ARCHITECTURE · CORE PROJECTION"}
        title={zh() ? "看这一条真实 Run 怎样穿过 NovelForge。" : "See how this real run moves through NovelForge."}
        body={zh()
          ? "从 Project Adapter、Runtime Session、Context policy、Receipt、Guard 与 Event 读取真实只读投影。没有对应 Core 证据的阶段会显示为空，而不是由 Studio 猜测。"
          : "Reads real, read-only projections from Project Adapter, Runtime Session, Context policy, Receipts, Guards, and Events. Stages without Core evidence stay empty instead of being guessed by Studio."}
        actions={<span class="wui-badge wui-badge--outline">authority=false</span>}
      />

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <section class="nf-live-query-bar">
          <label>
            <span>{zh() ? "项目根目录" : "Project root"}</span>
            <input class="wui-input" value={studio.projectRoot()} onInput={(event) => studio.setProjectRoot(event.currentTarget.value)} placeholder="/path/to/project" spellcheck={false} />
          </label>
          <button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void load()}>
            {loading() ? (zh() ? "读取中…" : "Loading…") : (zh() ? "读取真实 Run" : "Load real run")}
          </button>
          <Show when={bundle()}>
            <button class="wui-button wui-button--outline" type="button" onClick={() => downloadProjection(bundle()!)}>{zh() ? "导出安全投影" : "Export safe projection"}</button>
          </Show>
        </section>
        <QueryError message={error()} />

        <Show when={bundle()} fallback={<div class="wui-empty-state nf-empty"><p>{zh() ? "加载项目后，这里会显示真实 execution lineage。" : "Load a project to inspect its real execution lineage."}</p></div>}>
          <section class="nf-live-architecture-rail" aria-label={zh() ? "真实运行路径" : "Real run path"}>
            <For each={nodes}>{(node, index) => (
              <button type="button" data-active={selected() === node.id ? "true" : undefined} data-state={nodeState(node.id)} onClick={() => setSelected(node.id)}>
                <small>{String(index() + 1).padStart(2, "0")}</small>
                <span aria-hidden="true">{node.icon}</span>
                <strong>{node.label}</strong>
                <i>{nodeState(node.id) === "observed" ? "●" : "○"}</i>
              </button>
            )}</For>
          </section>

          <div class="nf-live-architecture-grid">
            <section class="wui-card wui-card--outlined nf-live-stage-detail">
              <header>
                <span class="nf-eyebrow">{selected().toUpperCase()}</span>
                <h2>{nodes.find((node) => node.id === selected())?.label}</h2>
                <span class="wui-badge wui-badge--outline">{nodeState(selected())}</span>
              </header>
              <dl>
                <For each={details()}>{([key, value]) => <div><dt>{key}</dt><dd class="nf-mono">{printable(value)}</dd></div>}</For>
              </dl>
              <Show when={selected() === "publication"}>
                <A class="wui-button wui-button--soft" href="/publication">{zh() ? "打开真实 Publication Compiler" : "Open real Publication Compiler"}</A>
              </Show>
            </section>

            <section class="wui-card wui-card--outlined nf-live-trace">
              <header><span class="nf-eyebrow">EVENT TRACE</span><h2>{zh() ? "Core 事件" : "Core events"}</h2></header>
              <Show when={events().length} fallback={<p>{zh() ? "当前 Session 没有公开 event。" : "No public events exist for this session."}</p>}>
                <ol>
                  <For each={events().slice(-12)}>{(event) => (
                    <li><span>✦</span><div><strong>{event.event_type}</strong><small class="nf-mono">{event.run_id ?? event.session_id ?? "—"}</small></div></li>
                  )}</For>
                </ol>
              </Show>
            </section>
          </div>

          <footer class="nf-live-projection-foot">
            <span>query_only=true</span><span>mutation_performed=false</span><span>authority=false</span><span>{bundle()!.bridge_result_fingerprints.length} fingerprint-bound results</span>
          </footer>
        </Show>
      </Show>
    </section>
  );
}
