import { Show, createResource } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Capabilities() {
  const { t } = useI18n();
  const studio = useStudio();
  const [data, { refetch }] = createResource(
    () => (studio.bridgeAvailable() ? "bound" : undefined),
    async () => {
      const response = await invokeBridge("capabilities.inspect", studio.projectRoot() ? { project_root: studio.projectRoot() } : {});
      if (response.status !== "ok") throw new Error(JSON.stringify(response.error));
      return response.data;
    },
  );

  return (
    <section class="nf-page">
      <PageIntro
        title={t("capabilities.title")}
        body={t("capabilities.body")}
        actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--outline" type="button" onClick={() => void refetch()}>{t("common.refresh")}</button> : undefined}
      />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <QueryError message={data.error ? String(data.error) : undefined} />
        <Show when={!data.loading} fallback={<div class="nf-loading">{t("common.loading")}</div>}>
          <article class="wui-card nf-card"><div class="wui-card__content"><JsonBlock value={data()} /></div></article>
        </Show>
      </Show>
    </section>
  );
}
