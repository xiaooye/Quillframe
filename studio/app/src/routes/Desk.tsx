import { Show } from "solid-js";
import { AuthorityBadge, CoreHostBoundary, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Desk() {
  const { t } = useI18n();
  const studio = useStudio();
  const hosted = () => !studio.bridgeAvailable();

  return (
    <section class="nf-page">
      <PageIntro eyebrow={t("desk.eyebrow")} title={t("desk.title")} body={t("desk.body")} />
      <Show when={studio.bridgeAvailable()}>
        <QueryError message={studio.bridgeError() ? String(studio.bridgeError()) : undefined} />
      </Show>
      <div class="nf-metric-grid">
        <article class="wui-card nf-card nf-card-accent">
          <div class="wui-card__content">
            <span class="nf-card-label">{t("desk.bridgeTitle")}</span>
            <strong>{hosted() ? t("desk.hostedReady") : studio.bridgeLoading() ? t("common.loading") : studio.bridgeDescription() ? t("desk.bridgeReady") : t("desk.bridgeUnavailable")}</strong>
            <small>{hosted() ? t("desk.hostedMeta") : studio.bridgeDescription()?.contract_schema ?? "novelforge_studio_host_bridge_contract_v1"}</small>
          </div>
        </article>
        <article class="wui-card nf-card">
          <div class="wui-card__content">
            <span class="nf-card-label">{t("desk.queryCount")}</span>
            <strong>{studio.bridgeDescription()?.supported_operations.length ?? "—"}</strong>
            <small>{hosted() ? t("host.cloud") : "bridge.describe · project.inspect · …"}</small>
          </div>
        </article>
        <article class="wui-card nf-card">
          <div class="wui-card__content">
            <span class="nf-card-label">{t("desk.deferredCount")}</span>
            <strong>{studio.bridgeDescription() ? Object.keys(studio.bridgeDescription()!.deferred_operations).length : "—"}</strong>
            <small>Core #23</small>
          </div>
        </article>
        <article class="wui-card nf-card">
          <div class="wui-card__content">
            <span class="nf-card-label">{t("desk.authority")}</span>
            <AuthorityBadge />
            <small>canon=false · settlement=false · framework-write=false</small>
          </div>
        </article>
      </div>

      <Show when={hosted()}>
        <CoreHostBoundary />
      </Show>

      <div class="nf-two-column">
        <article class="wui-card nf-card">
          <div class="wui-card__header"><h2>{t("nav.project")}</h2></div>
          <div class="wui-card__content">
            <Show when={studio.projectResult()?.data?.project} fallback={<p class="nf-muted">{t("project.noProject")}</p>}>
              <div class="nf-project-summary">
                <strong>{studio.projectResult()?.data?.project.project.title}</strong>
                <span>{studio.projectResult()?.data?.project.project.id}</span>
                <span>{studio.projectResult()?.data?.project.framework_lock.version as string}</span>
              </div>
            </Show>
          </div>
        </article>
        <article class="wui-card wui-card--filled nf-card">
          <div class="wui-card__header"><h2>{t("workspace.title")}</h2></div>
          <div class="wui-card__content">
            <p>{t("workspace.unavailableBody")}</p>
            <span class="wui-badge wui-badge--warning">{t("workspace.projectionRequired")}</span>
          </div>
        </article>
      </div>
    </section>
  );
}