import { Show, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

const stages = ["writer_pre_draft", "post_draft_critic", "independent_reviewer", "never"] as const;

export default function ContextRoute() {
  const { t } = useI18n();
  const studio = useStudio();
  const [manifest, setManifest] = createSignal("");
  const [overlay, setOverlay] = createSignal("");
  const [stage, setStage] = createSignal<(typeof stages)[number]>("writer_pre_draft");
  const [result, setResult] = createSignal<unknown>();
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);

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
      const response = await invokeBridge("context.inspect", args);
      if (response.status !== "ok") setError(JSON.stringify(response.error));
      setResult(response.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section class="nf-page">
      <PageIntro title={t("context.title")} body={t("context.body")} />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <div class="wui-card nf-card">
          <div class="wui-card__content nf-form-grid">
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
        </div>
        <QueryError message={error()} />
        <Show when={result() !== undefined}>
          <article class="wui-card nf-card">
            <div class="wui-card__header"><h2>{t("context.resultTitle")}</h2></div>
            <div class="wui-card__content"><JsonBlock value={result()} /></div>
          </article>
        </Show>
      </Show>
    </section>
  );
}
