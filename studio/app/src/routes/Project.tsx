import { For, Show } from "solid-js";
import { CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Project() {
  const { t } = useI18n();
  const studio = useStudio();
  const projection = () => studio.projectResult()?.data?.project;

  return (
    <section class="nf-page nf-project-page">
      <PageIntro title={t("project.title")} body={t("project.body")} />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <form class="nf-inspector-toolbar nf-project-opener" onSubmit={(event) => { event.preventDefault(); void studio.inspectProject(); }}>
          <div class="nf-project-opener-copy">
            <label class="nf-field-label" for="project-root">{t("project.pathLabel")}</label>
            <p class="nf-field-help">{t("project.pathPrivacy")}</p>
          </div>
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
        </form>
        <QueryError message={studio.projectError()} />

        <Show when={projection()} fallback={<div class="wui-empty-state nf-empty"><p>{t("project.noProject")}</p></div>}>
          {(project) => (
            <section class="wui-card wui-card--outlined nf-inspector-surface nf-project-inspector">
              <div class="nf-project-overview-grid">
                <section class="nf-inspector-section">
                  <header class="nf-inspector-section-head"><h2>{t("project.identity")}</h2></header>
                  <div class="nf-detail-list">
                    <div><span>ID</span><strong>{project().project.id ?? "—"}</strong></div>
                    <div><span>{t("project.version")}</span><strong>{project().project.version ?? "—"}</strong></div>
                    <div><span>{t("project.layout")}</span><strong>{project().project.layout ?? "—"}</strong></div>
                    <div><span>{t("project.language")}</span><strong>{project().project.language ?? "—"}</strong></div>
                  </div>
                </section>
                <section class="nf-inspector-section nf-project-framework">
                  <header class="nf-inspector-section-head"><h2>{t("project.framework")}</h2></header>
                  <div class="nf-detail-list">
                    <For each={Object.entries(project().framework_lock)}>
                      {([key, value]) => <div><span>{key}</span><strong class="nf-mono">{String(value)}</strong></div>}
                    </For>
                  </div>
                </section>
              </div>

              <section class="nf-inspector-section nf-project-paths-section">
                <header class="nf-inspector-section-head"><h2>{t("project.paths")}</h2></header>
                <div class="nf-path-grid">
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
              </section>

              <section class="nf-inspector-section nf-project-policy-section">
                <header class="nf-inspector-section-head"><h2>{t("project.policyAvailability")}</h2></header>
                <div class="nf-chip-row nf-policy-chips">
                  <For each={Object.entries(project().policy_availability)}>
                    {([key, available]) => <span class="wui-badge wui-badge--outline">{key}: {String(available)}</span>}
                  </For>
                </div>
              </section>
            </section>
          )}
        </Show>
      </Show>
    </section>
  );
}