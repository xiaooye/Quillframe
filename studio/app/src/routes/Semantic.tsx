import { For, Show, createMemo, createResource } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

interface CatalogData {
  contracts?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export default function Semantic() {
  const { t } = useI18n();
  const studio = useStudio();
  const [data, { refetch }] = createResource(
    () => (studio.bridgeAvailable() ? "bound" : undefined),
    async () => {
      const response = await invokeBridge<CatalogData>("semantic.catalog");
      if (response.status !== "ok") throw new Error(JSON.stringify(response.error));
      return response.data;
    },
  );
  const contracts = createMemo(() => Array.isArray(data()?.contracts) ? data()!.contracts! : []);

  return (
    <section class="nf-page">
      <PageIntro
        title={t("semantic.title")}
        body={t("semantic.body")}
        actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--outline" type="button" onClick={() => void refetch()}>{t("common.refresh")}</button> : undefined}
      />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <QueryError message={data.error ? String(data.error) : undefined} />
        <Show when={!data.loading} fallback={<div class="nf-loading">{t("common.loading")}</div>}>
          <Show when={contracts().length > 0} fallback={<article class="wui-card nf-card"><div class="wui-card__content"><JsonBlock value={data()} /></div></article>}>
            <div class="nf-catalog-grid">
              <For each={contracts()}>
                {(contract) => (
                  <article class="wui-card nf-card">
                    <div class="wui-card__content">
                      <span class="nf-card-label">{String(contract.kind ?? contract.id ?? "contract")}</span>
                      <strong class="nf-mono">{String(contract.id ?? contract.contract_id ?? "—")}</strong>
                      <small>{String(contract.description ?? contract.purpose ?? "")}</small>
                    </div>
                  </article>
                )}
              </For>
            </div>
          </Show>
        </Show>
      </Show>
    </section>
  );
}
