import { useI18n } from "./i18n";
import type { ObservabilityDisplayStatus } from "./observability";

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
