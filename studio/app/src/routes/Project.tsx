import { For, Show } from "solid-js";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Project() {
  const { t } = useI18n();
  const studio = useStudio();
  const projection = () => studio.projectResult()?.data?.project;

  return (
    <section class="nf-page">
      <PageIntro title={t("project.title")} body={t("project.body")} />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <form class="wui-card nf-card nf-project-opener" onSubmit={(event) => { event.preventDefault(); void studio.inspectProject(); }}>
          <div class="wui-card__content">
            <label class="nf-field-label" for="project-root">{t("project.pathLabel")}</label>
            <div class="nf-inline-form">
              <input
                id="project-root"
                class="wui-input"
                value={studio.projectRoot()}
                onInput={(event) => studio.setProjectRoot(event.currentTarget.value)}
                placeholder={t("project.pathPlaceholder")}
                autocomplete="off"
                spellcheck={false}
              />
              <button class="wui-button wui-button--solid" type="submit" disabled={studio.projectLoading()}>
                {studio.projectLoading() ? t("common.loading") : t("project.openAction")}
              </button>
            </div>
            <p class="nf-field-help">{t("project.pathPrivacy")}</p>
          </div>
        </form>
        <QueryError message={studio.projectError()} />

        <Show when={projection()} fallback={<div class="wui-empty-state nf-empty"><p>{t("project.noProject")}</p></div>}>
          {(project) => (
            <>
              <div class="nf-two-column">
                <article class="wui-card nf-card">
                  <div class="wui-card__header"><h2>{t("project.identity")}</h2></div>
                  <div class="wui-card__content nf-detail-list">
                    <div><span>ID</span><strong>{project().project.id ?? "—"}</strong></div>
                    <div><span>{t("project.version")}</span><strong>{project().project.version ?? "—"}</strong></div>
                    <div><span>{t("project.layout")}</span><strong>{project().project.layout ?? "—"}</strong></div>
                    <div><span>{t("project.language")}</span><strong>{project().project.language ?? "—"}</strong></div>
                  </div>
                </article>
                <article class="wui-card nf-card">
                  <div class="wui-card__header"><h2>{t("project.framework")}</h2></div>
                  <div class="wui-card__content nf-detail-list">
                    <For each={Object.entries(project().framework_lock)}>
                      {([key, value]) => <div><span>{key}</span><strong class="nf-mono">{String(value)}</strong></div>}
                    </For>
                  </div>
                </article>
              </div>

              <article class="wui-card nf-card">
                <div class="wui-card__header"><h2>{t("project.paths")}</h2></div>
                <div class="wui-card__content nf-path-grid">
                  <For each={Object.entries(project().logical_paths)}>
                    {([domain, entry]) => (
                      <div class="nf-path-row">
                        <div><strong>{domain}</strong><span class="nf-mono">{entry.relative ?? "—"}</span></div>
                        <span class={`wui-badge ${entry.exists ? "wui-badge--success" : "wui-badge--warning"}`}>
                          {entry.exists ? t("project.pathExists") : t("project.pathMissing")}
                        </span>
                      </div>
                    )}
                  </For>
                </div>
              </article>

              <article class="wui-card wui-card--filled nf-card">
                <div class="wui-card__header"><h2>{t("project.policyAvailability")}</h2></div>
                <div class="wui-card__content nf-chip-row">
                  <For each={Object.entries(project().policy_availability)}>
                    {([key, available]) => <span class="wui-badge wui-badge--outline">{key}: {String(available)}</span>}
                  </For>
                </div>
              </article>
            </>
          )}
        </Show>
      </Show>
    </section>
  );
}