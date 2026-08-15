import { For, Show, createMemo, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { sourceBooleanStatus, stringList, type FrameworkDoctorProjection } from "../observability";
import { ProductionProjectionPlaceholder, StatusBadge } from "../observability-ui";
import { useStudio } from "../studio";

export default function Diagnostics() {
  const { t } = useI18n();
  const studio = useStudio();
  const [result, setResult] = createSignal<FrameworkDoctorProjection>();
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);
  const missing = createMemo(() => stringList(result()?.missing));
  const forbidden = createMemo(() => stringList(result()?.forbidden_pre_release_compatibility));
  const doctorStatus = createMemo(() => sourceBooleanStatus(result()?.ok));
  const doctorStatusLabel = createMemo(() => {
    if (doctorStatus() === "pass") return t("common.pass");
    if (doctorStatus() === "blocked") return t("common.blocked");
    return t("common.unavailable");
  });

  const runDoctor = async () => {
    if (!studio.bridgeAvailable()) return;
    setLoading(true);
    setError(undefined);
    try {
      const response = await invokeBridge<FrameworkDoctorProjection>("framework.doctor");
      if (response.status !== "ok") {
        setError(JSON.stringify(response.error));
        return;
      }
      setResult(response.data ?? undefined);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(false);
    }
  };

  const validated = () => [
    t("diagnostics.validatedIdentity"),
    t("diagnostics.validatedEntrypoints"),
    t("diagnostics.validatedCompatibilityArtifact"),
  ];
  const notValidated = () => [
    t("diagnostics.notValidatedLiteraryQuality"),
    t("diagnostics.notValidatedReaderEngagement"),
    t("diagnostics.notValidatedIndependentReview"),
    t("diagnostics.notValidatedReadiness"),
    t("diagnostics.notValidatedCanon"),
    t("diagnostics.notValidatedProjectCompatibility"),
    t("diagnostics.notValidatedTaxonomy"),
  ];

  return (
    <section class="nf-page nf-diagnostics-page">
      <PageIntro
        eyebrow={t("diagnostics.eyebrow")}
        title={t("diagnostics.title")}
        body={t("diagnostics.body")}
        actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void runDoctor()}>{loading() ? t("common.loading") : t("diagnostics.doctorAction")}</button> : undefined}
      />

      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <QueryError message={error()} />
        <Show when={result()}>
          {(doctor) => (
            <section class="wui-card wui-card--outlined nf-diagnostic-workstation" aria-labelledby="diagnostics-result-heading">
              <div class="nf-observe-section-head">
                <div>
                  <span class="nf-eyebrow">{t("diagnostics.currentCheck")}</span>
                  <h2 id="diagnostics-result-heading">{t("diagnostics.resultTitle")}</h2>
                  <p>{t("diagnostics.scopeBody")}</p>
                </div>
                <StatusBadge status={doctorStatus()} label={doctorStatusLabel()} />
              </div>

              <div class="nf-diagnostic-facts">
                <div>
                  <span>{t("diagnostics.frameworkVersion")}</span>
                  <strong class="nf-mono">{String(doctor().framework_version ?? t("common.notExposed"))}</strong>
                </div>
                <div>
                  <span>{t("diagnostics.sourceSchema")}</span>
                  <strong class="nf-mono">{String(doctor().schema ?? t("common.notExposed"))}</strong>
                </div>
                <div>
                  <span>{t("diagnostics.missing")}</span>
                  <strong>{missing().length}</strong>
                </div>
                <div>
                  <span>{t("diagnostics.forbidden")}</span>
                  <strong>{forbidden().length}</strong>
                </div>
                <div>
                  <span>{t("diagnostics.modelExecution")}</span>
                  <strong>{doctor().model_execution === false ? t("diagnostics.disabled") : t("common.notExposed")}</strong>
                </div>
              </div>

              <div class="nf-validation-scope">
                <article>
                  <header>
                    <span class="wui-badge wui-badge--success" aria-hidden="true">✓</span>
                    <h3>{t("diagnostics.validatedTitle")}</h3>
                  </header>
                  <ul>
                    <For each={validated()}>{(item) => <li>{item}</li>}</For>
                  </ul>
                  <Show when={missing().length > 0 || forbidden().length > 0}>
                    <div class="nf-diagnostic-exceptions">
                      <Show when={missing().length > 0}>
                        <div class="wui-card wui-card--filled"><strong>{t("diagnostics.missing")}</strong><span class="nf-mono">{missing().join(", ")}</span></div>
                      </Show>
                      <Show when={forbidden().length > 0}>
                        <div class="wui-card wui-card--filled"><strong>{t("diagnostics.forbidden")}</strong><span class="nf-mono">{forbidden().join(", ")}</span></div>
                      </Show>
                    </div>
                  </Show>
                </article>
                <article>
                  <header>
                    <span class="wui-badge wui-badge--outline" aria-hidden="true">—</span>
                    <h3>{t("diagnostics.notValidatedTitle")}</h3>
                  </header>
                  <ul>
                    <For each={notValidated()}>{(item) => <li>{item}</li>}</For>
                  </ul>
                </article>
              </div>

              <details class="nf-raw-evidence">
                <summary>{t("diagnostics.rawEvidence")}</summary>
                <JsonBlock value={doctor()} label={String(doctor().schema ?? "framework.doctor")} />
              </details>
            </section>
          )}
        </Show>
      </Show>

      <ProductionProjectionPlaceholder />
    </section>
  );
}
