import { For, Show, createMemo, createResource } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { asSemanticPacks, type SemanticCatalogProjection } from "../observability";
import { EvidenceBoundary, MissingCoreField, StatusBadge } from "../observability-ui";
import { useStudio } from "../studio";

export default function Semantic() {
  const { t } = useI18n();
  const studio = useStudio();
  const [data, { refetch }] = createResource(
    () => (studio.bridgeAvailable() ? "bound" : undefined),
    async () => {
      const response = await invokeBridge<SemanticCatalogProjection>("semantic.catalog");
      if (response.status !== "ok") throw new Error(JSON.stringify(response.error));
      return response.data;
    },
  );
  const packs = createMemo(() => asSemanticPacks(data()));
  const contractCount = createMemo(() => packs().reduce((total, pack) => total + pack.contracts.length, 0));

  return (
    <section class="nf-page nf-semantic-page">
      <PageIntro
        eyebrow={t("semantic.eyebrow")}
        title={t("semantic.title")}
        body={t("semantic.body")}
        actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--outline" type="button" onClick={() => void refetch()}>{t("common.refresh")}</button> : undefined}
      />
      <EvidenceBoundary />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <QueryError message={data.error ? String(data.error) : undefined} />
        <Show when={!data.loading} fallback={<div class="nf-loading">{t("common.loading")}</div>}>
          <Show when={packs().length > 0} fallback={<article class="wui-card nf-card"><div class="wui-card__content"><JsonBlock value={data()} /></div></article>}>
            <section class="wui-card wui-card--outlined nf-catalog-workstation" aria-labelledby="semantic-catalog-heading">
              <div class="nf-observe-section-head nf-catalog-summary">
                <div>
                  <span class="nf-eyebrow">{t("semantic.currentProjection")}</span>
                  <h2 id="semantic-catalog-heading">{t("semantic.catalogHeading")}</h2>
                  <p>{t("semantic.catalogScope")}</p>
                </div>
                <div class="nf-catalog-counts" aria-label={t("semantic.catalogHeading")}>
                  <span><strong>{packs().length}</strong>{t("semantic.packCount")}</span>
                  <span><strong>{contractCount()}</strong>{t("semantic.contractCount")}</span>
                </div>
              </div>

              <div class="nf-pack-list">
                <For each={packs()}>
                  {(pack) => (
                    <article class="nf-pack-row">
                      <header class="nf-pack-heading">
                        <div>
                          <span class="nf-card-label">{t("semantic.pack")}</span>
                          <strong class="nf-mono">{pack.id}</strong>
                        </div>
                        <small>{pack.contracts.length} {t("semantic.contractsSuffix")}</small>
                      </header>
                      <p class="nf-pack-description">{pack.description || t("common.notExposed")}</p>
                      <div class="nf-pack-load-boundary">
                        <span>{t("semantic.loadWhen")}</span>
                        <strong>{pack.load_when || t("common.notExposed")}</strong>
                      </div>

                      <div class="nf-contract-list">
                        <For each={pack.contracts}>
                          {(contractId) => (
                            <details class="nf-contract-row">
                              <summary>
                                <div>
                                  <span class="nf-card-label">{t("semantic.contractId")}</span>
                                  <strong class="nf-mono">{contractId}</strong>
                                </div>
                                <StatusBadge status="not_applicable" label={t("semantic.registeredContract")} />
                              </summary>
                              <div class="nf-contract-projection">
                                <div class="nf-observe-field">
                                  <span>{t("semantic.pack")}</span>
                                  <strong class="nf-mono">{pack.id}</strong>
                                </div>
                                <MissingCoreField label={t("semantic.registryVersion")} />
                                <MissingCoreField label={t("semantic.independentGate")} />
                                <MissingCoreField label={t("semantic.inputVisibility")} />
                                <MissingCoreField label={t("semantic.permissionScope")} />
                                <MissingCoreField label={t("semantic.productionEvidence")} />
                              </div>
                              <p class="nf-observe-footnote">{t("semantic.contractLimit")}</p>
                            </details>
                          )}
                        </For>
                      </div>
                    </article>
                  )}
                </For>
              </div>

              <details class="nf-raw-evidence">
                <summary>{t("semantic.rawCatalog")}</summary>
                <JsonBlock value={data()} label={String(data()?.schema ?? "semantic.catalog")} />
              </details>
            </section>
          </Show>
        </Show>
      </Show>
    </section>
  );
}
