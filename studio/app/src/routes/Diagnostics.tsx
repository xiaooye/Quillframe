import { Show, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";

export default function Diagnostics() {
  const { t } = useI18n();
  const [result, setResult] = createSignal<unknown>();
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);

  const runDoctor = async () => {
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
        actions={<button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void runDoctor()}>{loading() ? t("common.loading") : t("diagnostics.doctorAction")}</button>}
      />
      <QueryError message={error()} />
      <Show when={result() !== undefined}>
        <article class="wui-card nf-card">
          <div class="wui-card__header"><h2>{t("diagnostics.resultTitle")}</h2></div>
          <div class="wui-card__content"><JsonBlock value={result()} /></div>
        </article>
      </Show>
    </section>
  );
}
