import { For, Show, createMemo, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

const stages = ["writer_pre_draft", "post_draft_critic", "independent_reviewer", "never"] as const;

type ContextItemProjection = {
  id: string;
  class: string;
  source?: unknown;
  source_fingerprint?: unknown;
  authority: string;
  inclusion_reason: string;
  stages: string[];
  priority: number;
  pinned: boolean;
  derived: boolean;
  hidden: boolean;
  invalidated: boolean;
  metadata: unknown;
  eligible: boolean;
};

type ContextProjection = {
  schema: "quillframe_context_inspector_v2";
  manifest_id?: string | null;
  stage?: string | null;
  items: ContextItemProjection[];
  proposals: unknown[];
  ordering_policy: string;
  semantic_relevance_field_allowed: false;
  authority: false;
  model_execution: false;
};

const inspectorCopy = {
  "en-US": {
    eyebrow: "Context state snapshot",
    body: "Eligibility below is deterministic stage and overlay visibility. It is not a semantic relevance score and does not select context for the model.",
    items: "Items",
    eligible: "Eligible",
    excluded: "Excluded",
    proposals: "Proposals",
    manifest: "Manifest",
    ordering: "Ordering",
    relevance: "Semantic relevance",
    forbidden: "Not carried",
    authority: "Authority",
    none: "None",
    stageVisibility: "Stage visibility",
    controls: "Controls",
    priority: "priority",
    pinned: "pinned",
    derived: "derived",
    hidden: "hidden",
    invalidated: "invalidated",
    raw: "Raw context evidence",
  },
  "zh-CN": {
    eyebrow: "Context 状态快照",
    body: "下面的 eligible 只表示确定性的阶段 / overlay 可见性；它不是 semantic relevance 分数，也不会替模型完成 Context 选择。",
    items: "条目",
    eligible: "可见",
    excluded: "排除",
    proposals: "提案",
    manifest: "Manifest",
    ordering: "排序规则",
    relevance: "Semantic relevance",
    forbidden: "不携带",
    authority: "Authority",
    none: "无",
    stageVisibility: "阶段可见性",
    controls: "控制状态",
    priority: "priority",
    pinned: "pinned",
    derived: "derived",
    hidden: "hidden",
    invalidated: "invalidated",
    raw: "原始 Context 证据",
  },
} as const;

export default function ContextRoute() {
  const { t, locale } = useI18n();
  const studio = useStudio();
  const [manifest, setManifest] = createSignal("");
  const [overlay, setOverlay] = createSignal("");
  const [stage, setStage] = createSignal<(typeof stages)[number]>("writer_pre_draft");
  const [result, setResult] = createSignal<ContextProjection>();
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);
  const copy = createMemo(() => inspectorCopy[locale()]);

  const inspect = async () => {
    if (!studio.bridgeAvailable()) return;
    if (!studio.projectRoot().trim()) {
      setError(t("context.noProject"));
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      const args: Record<string, unknown> = {
        project_root: studio.projectRoot(),
        manifest: manifest().trim(),
        stage: stage(),
      };
      if (overlay().trim()) args.overlay = overlay().trim();
      const response = await invokeBridge<ContextProjection>("context.inspect", args);
      if (response.status !== "ok" || !response.data) {
        setResult(undefined);
        setError(JSON.stringify(response.error));
        return;
      }
      setResult(response.data);
    } catch (caught) {
      setResult(undefined);
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section class="nf-page nf-context-page">
      <PageIntro title={t("context.title")} body={t("context.body")} />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <div class="nf-inspector-toolbar nf-context-toolbar nf-form-grid">
          <label class="nf-field-label">
            <span>{t("context.manifestLabel")}</span>
            <input class="wui-input" value={manifest()} onInput={(event) => setManifest(event.currentTarget.value)} placeholder={t("context.manifestPlaceholder")} spellcheck={false} />
          </label>
          <label class="nf-field-label">
            <span>{t("context.overlayLabel")}</span>
            <input class="wui-input" value={overlay()} onInput={(event) => setOverlay(event.currentTarget.value)} placeholder={t("context.overlayPlaceholder")} spellcheck={false} />
          </label>
          <label class="nf-field-label">
            <span>{t("context.stageLabel")}</span>
            <select class="wui-input" value={stage()} onChange={(event) => setStage(event.currentTarget.value as (typeof stages)[number])}>
              {stages.map((value) => <option value={value}>{value}</option>)}
            </select>
          </label>
          <button class="wui-button wui-button--solid nf-form-action" type="button" disabled={loading() || !manifest().trim()} onClick={() => void inspect()}>
            {loading() ? t("common.loading") : t("context.inspectAction")}
          </button>
        </div>
        <QueryError message={error()} />
        <Show when={result()}>
          {(snapshot) => {
            const eligibleCount = () => snapshot().items.filter((item) => item.eligible).length;
            return (
              <section class="wui-card wui-card--outlined nf-inspector-surface nf-catalog-workstation nf-context-result" aria-labelledby="context-result-heading">
                <div class="nf-observe-section-head">
                  <div>
                    <span class="nf-eyebrow">{copy().eyebrow}</span>
                    <h2 id="context-result-heading">{t("context.resultTitle")}</h2>
                    <p>{copy().body}</p>
                  </div>
                  <div class="nf-catalog-counts">
                    <span><strong>{snapshot().items.length}</strong>{copy().items}</span>
                    <span><strong>{eligibleCount()}</strong>{copy().eligible}</span>
                    <span><strong>{snapshot().items.length - eligibleCount()}</strong>{copy().excluded}</span>
                    <span><strong>{snapshot().proposals.length}</strong>{copy().proposals}</span>
                  </div>
                </div>

                <div class="nf-diagnostic-facts">
                  <div><span>{copy().manifest}</span><strong class="nf-mono">{snapshot().manifest_id ?? "—"}</strong></div>
                  <div><span>{t("context.stageLabel")}</span><strong class="nf-mono">{snapshot().stage ?? stage()}</strong></div>
                  <div><span>{copy().ordering}</span><strong class="nf-mono">{snapshot().ordering_policy}</strong></div>
                  <div><span>{copy().relevance}</span><strong>{copy().forbidden}</strong></div>
                  <div><span>{copy().authority}</span><strong>{copy().none}</strong></div>
                </div>

                <div class="nf-pack-list">
                  <For each={snapshot().items}>
                    {(item) => (
                      <article class="nf-pack-row">
                        <div class="nf-pack-heading">
                          <div>
                            <strong class="nf-mono">{item.id}</strong>
                            <small>{item.class}</small>
                          </div>
                          <span class={`wui-badge ${item.eligible ? "wui-badge--success" : "wui-badge--outline"}`}>{item.eligible ? copy().eligible : copy().excluded}</span>
                        </div>
                        <div class="nf-pack-description">
                          <strong>{item.authority}</strong><br />
                          {item.inclusion_reason}
                        </div>
                        <div class="nf-pack-load-boundary">
                          <span>{copy().stageVisibility}</span>
                          <strong class="nf-mono">{item.stages.join(" · ")}</strong>
                          <span>{copy().controls}</span>
                          <strong class="nf-mono">
                            {copy().priority} {item.priority} · {copy().pinned} {String(item.pinned)} · {copy().derived} {String(item.derived)} · {copy().hidden} {String(item.hidden)} · {copy().invalidated} {String(item.invalidated)}
                          </strong>
                        </div>
                      </article>
                    )}
                  </For>
                </div>

                <details class="nf-raw-evidence">
                  <summary>{copy().raw}</summary>
                  <JsonBlock value={snapshot()} label={snapshot().schema} />
                </details>
              </section>
            );
          }}
        </Show>
      </Show>
    </section>
  );
}
