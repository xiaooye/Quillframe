import { For } from "solid-js";
import { useI18n } from "./i18n";
import type { ObservabilityDisplayStatus, ProductionLaneProjection } from "./observability";

const statusClass: Record<ObservabilityDisplayStatus, string> = {
  pass: "wui-badge--success",
  warn: "wui-badge--warning",
  blocked: "wui-badge--destructive",
  not_applicable: "wui-badge--outline",
  pending: "wui-badge--soft",
  unavailable: "wui-badge--outline",
};

export function StatusBadge(props: { status: ObservabilityDisplayStatus; label: string }) {
  return <span class={`wui-badge ${statusClass[props.status]}`}>{props.label}</span>;
}

export function MissingCoreField(props: { label: string }) {
  const { t } = useI18n();
  return (
    <div class="nf-observe-field">
      <span>{props.label}</span>
      <strong class="nf-observe-missing">{t("common.notExposed")}</strong>
    </div>
  );
}

export function EvidenceBoundary() {
  const { t } = useI18n();
  return (
    <aside class="wui-alert wui-alert--warning nf-evidence-boundary" aria-labelledby="semantic-evidence-boundary-title">
      <span class="wui-alert__icon" aria-hidden="true">≠</span>
      <div class="wui-alert__body">
        <strong class="wui-alert__title" id="semantic-evidence-boundary-title">{t("semantic.boundaryTitle")}</strong>
        <p class="wui-alert__description">{t("semantic.boundaryBody")}</p>
      </div>
    </aside>
  );
}

export function ProductionProjectionPlaceholder() {
  const { t } = useI18n();
  const lanes: ProductionLaneProjection[] = [
    { id: "candidate", label: t("production.laneCandidate") },
    { id: "surface", label: t("production.laneSurface") },
    { id: "reader_engagement", label: t("production.laneReaderEngagement") },
    { id: "independent_production_review", label: t("production.laneIndependentReview") },
    { id: "continuity", label: t("production.laneContinuity") },
    { id: "production_readiness", label: t("production.laneReadiness") },
    { id: "canon", label: t("production.laneCanon") },
  ];

  return (
    <section class="wui-card wui-card--filled nf-production-preview" aria-labelledby="production-preview-title">
      <div class="nf-observe-section-head">
        <div>
          <span class="nf-eyebrow">{t("production.eyebrow")}</span>
          <h2 id="production-preview-title">{t("production.previewTitle")}</h2>
          <p>{t("production.previewBody")}</p>
        </div>
        <StatusBadge status="unavailable" label={t("production.noProjection")} />
      </div>
      <div class="nf-production-lanes">
        <For each={lanes}>
          {(lane, index) => (
            <div class="nf-production-lane">
              <span class="nf-production-lane-index">{String(index() + 1).padStart(2, "0")}</span>
              <strong>{lane.label}</strong>
              <small>{t("production.coreDependency")}</small>
            </div>
          )}
        </For>
      </div>
      <p class="nf-observe-footnote">{t("production.scopeFootnote")}</p>
    </section>
  );
}
