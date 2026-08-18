import { For, Show, createSignal } from "solid-js";
import { inspectBrowserProject, type BrowserProjectProjection } from "../browser-project";
import { PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Project() {
  const { t } = useI18n();
  const studio = useStudio();
  const projection = () => studio.projectResult()?.data?.project;
  const [browserProject, setBrowserProject] = createSignal<BrowserProjectProjection>();
  const [browserLoading, setBrowserLoading] = createSignal(false);

  const importFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setBrowserLoading(true);
    try {
      setBrowserProject(await inspectBrowserProject(files));
    } finally {
      setBrowserLoading(false);
    }
  };

  return (
    <section class="nf-page nf-project-page">
      <PageIntro title={t("project.title")} body={t("project.body")} />

      <section class="wui-card wui-card--outlined nf-inspector-surface nf-browser-import" aria-labelledby="browser-import-heading">
        <div class="nf-browser-import-intro">
          <div>
            <span class="nf-eyebrow">{t("project.browserEyebrow")}</span>
            <h2 id="browser-import-heading">{t("project.browserTitle")}</h2>
            <p>{t("project.browserBody")}</p>
          </div>
          <label class="wui-button wui-button--solid nf-folder-picker">
            <span>{browserLoading() ? t("common.loading") : t("project.browserAction")}</span>
            <input
              type="file"
              multiple
              ref={(element) => element.setAttribute("webkitdirectory", "")}
              onChange={(event) => void importFiles(event.currentTarget.files)}
            />
          </label>
        </div>
        <p class="nf-browser-privacy">{t("project.browserPrivacy")}</p>

        <Show when={browserProject()}>
          {(browser) => (
            <div class="nf-browser-project-result">
              <div class="nf-browser-project-summary">
                <div>
                  <span class="nf-card-label">{t("project.browserPreflight")}</span>
                  <strong>{browser().project?.title ?? browser().project?.id ?? t("project.browserUnknown")}</strong>
                  <small>{browser().project?.id ?? "quillframe_project_v1"}</small>
                </div>
                <div class="nf-browser-project-meta">
                  <span><strong>{browser().files.length}</strong>{t("project.browserFiles")}</span>
                  <span><strong>{browser().framework?.version ?? "—"}</strong>{t("project.framework")}</span>
                </div>
              </div>

              <div class="nf-preflight-checks">
                <For each={browser().checks}>
                  {(check) => (
                    <div class="nf-preflight-row" data-status={check.status}>
                      <span class="nf-preflight-indicator" aria-hidden="true" />
                      <div><strong class="nf-mono">{check.label}</strong><small>{check.detail}</small></div>
                      <span class={`wui-badge ${check.status === "pass" ? "wui-badge--success" : "wui-badge--warning"}`}>
                        {check.status === "pass" ? t("common.pass") : check.status === "missing" ? t("project.pathMissing") : t("project.browserReview")}
                      </span>
                    </div>
                  )}
                </For>
              </div>
              <p class="nf-browser-core-note">{t("project.browserCoreNote")}</p>
            </div>
          )}
        </Show>
      </section>

      <Show
        when={studio.bridgeAvailable()}
        fallback={
          <aside class="nf-project-core-unbound" data-core-unbound={t("host.unboundTitle")}>
            <span class="wui-badge wui-badge--outline">{t("host.cloud")}</span>
            <p>{t("project.browserCoreNote")}</p>
          </aside>
        }
      >
        <section class="nf-core-project-section">
          <div class="nf-section-kicker">
            <span class="nf-eyebrow">{t("project.coreEyebrow")}</span>
            <strong>{t("project.coreTitle")}</strong>
          </div>
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
        </section>
      </Show>
    </section>
  );
}