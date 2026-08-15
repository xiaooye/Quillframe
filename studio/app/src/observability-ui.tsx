import { For } from "solid-js";
import { useI18n } from "./i18n";
import type { ObservabilityDisplayStatus, ProductionLaneProjection } from "./observability";

const statusClass: Record<ObservabilityDisplayStatus, string> = {
  pass: "nf-status--pass",
  warn: "nf-status--warn",
  blocked: "nf-status--blocked",
  not_applicable: "nf-status--neutral",
  pending: "nf-status--pending",
  unavailable: "nf-status--neutral",
};

export function StatusBadge(props: { status: ObservabilityDisplayStatus; label: string }) {
  return <span class={`nf-status ${statusClass[props.status]}`}>{props.label}</span>;
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
    <aside class="nf-evidence-boundary" aria-labelledby="semantic-evidence-boundary-title">
      <div class="nf-evidence-boundary-mark" aria-hidden="true">≠</div>
      <div>
        <strong id="semantic-evidence-boundary-title">{t("semantic.boundaryTitle")}</strong>
        <p>{t("semantic.boundaryBody")}</p>
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
    <section class="nf-production-preview" aria-labelledby="production-preview-title">
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
