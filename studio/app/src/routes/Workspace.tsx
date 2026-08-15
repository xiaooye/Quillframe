import { PageIntro } from "../components";
import { useI18n } from "../i18n";

export default function Workspace() {
  const { t } = useI18n();
  return (
    <section class="nf-page nf-workspace-page">
      <PageIntro title={t("workspace.title")} body={t("workspace.body")} />
      <div class="nf-workspace-stage">
        <aside class="wui-card wui-card--filled nf-workspace-outline" aria-hidden="true">
          <span></span><span></span><span></span><span></span>
        </aside>
        <article class="wui-card nf-card nf-focus-placeholder">
          <div class="wui-card__content">
            <span class="nf-unavailable-mark" aria-hidden="true">∅</span>
            <h2>{t("workspace.unavailableTitle")}</h2>
            <p>{t("workspace.unavailableBody")}</p>
            <div class="nf-chip-row">
              <span class="wui-badge wui-badge--warning">{t("common.unavailable")}</span>
              <span class="wui-badge wui-badge--outline">{t("workspace.projectionRequired")}</span>
            </div>
          </div>
        </article>
        <aside class="wui-card wui-card--filled nf-workspace-inspector" aria-hidden="true">
          <span></span><span></span><span></span>
        </aside>
      </div>
    </section>
  );
}