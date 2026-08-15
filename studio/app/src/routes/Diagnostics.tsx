import { Show, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Diagnostics() {
  const { t } = useI18n();
  const studio = useStudio();
  const [result, setResult] = createSignal<unknown>();
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);

  const runDoctor = async () => {
    if (!studio.bridgeAvailable()) return;
    setLoading(true);
    setError(undefined);
    try {
      const response = await invokeBridge("framework.doctor");
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
      <PageIntro
        title={t("diagnostics.title")}
        body={t("diagnostics.body")}
        actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void runDoctor()}>{loading() ? t("common.loading") : t("diagnostics.doctorAction")}</button> : undefined}
      />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <QueryError message={error()} />
        <Show when={result() !== undefined}>
          <article class="wui-card nf-card">
            <div class="wui-card__header"><h2>{t("diagnostics.resultTitle")}</h2></div>
            <div class="wui-card__content"><JsonBlock value={result()} /></div>
          </article>
        </Show>
      </Show>
    </section>
  );
}
