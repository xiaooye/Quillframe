import { For, Show, createSignal, onMount } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { InspectorListProjection } from "../authoring/contracts";

type LearningRow = { evidence_id?: string; evidence_kind?: string; interpreted_scope?: string | null; state?: string; promotion_eligible?: number; created_at?: string };

export default function Learning() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [rows, setRows] = createSignal<LearningRow[]>([]);
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);

  const load = async () => {
    if (!studio.projectId() || !studio.bridgeCapabilities()?.operations.includes("inspector.learning.list")) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<InspectorListProjection<LearningRow>>("inspector.learning.list", { project_id: studio.projectId(), limit: 100 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setRows(result.data.items);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };
  onMount(() => void load());

  return (
    <section class="nf-page qf-learning-page">
      <PageIntro eyebrow="LEARNING" title={zh() ? "自动捕获，不等于自动升级。" : "Automatic capture is not automatic promotion."} body={zh() ? "这里展示 Core 已持久化的 learning evidence。candidate / validated / rejected 是学习状态，不会自动改 Project Profile、user taste、General Craft 或 Framework。" : "This view shows learning evidence persisted by Core. Candidate / validated / rejected learning state never automatically rewrites Project Profile, user taste, General Craft or Framework."} />
      <div class="qf-editorial-sheet">
        <div class="qf-section-head"><h2>{zh() ? "Learning evidence" : "Learning evidence"}</h2><button class="wui-button wui-button--outline" type="button" disabled={loading()} onClick={() => void load()}>{zh() ? "刷新" : "Refresh"}</button></div>
        <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><span class="wui-alert__description">{message()}</span></div></div>}</Show>
        <div class="qf-learning-list"><For each={rows()}>{(row) => <article><div><strong>{row.evidence_kind ?? "evidence"}</strong><span class="qf-authority-label">authority=false</span></div><code>{row.evidence_id ?? "—"}</code><p><span>{row.interpreted_scope ?? "unscoped"}</span> · <strong>{row.state ?? "captured"}</strong> · {row.promotion_eligible ? (zh() ? "promotion eligible" : "promotion eligible") : (zh() ? "不会自动 promotion" : "no automatic promotion")}</p></article>}</For><Show when={!loading() && !rows().length}><p>{zh() ? "当前没有 learning evidence。" : "No learning evidence is currently persisted."}</p></Show></div>
      </div>
    </section>
  );
}
