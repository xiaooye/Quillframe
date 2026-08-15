import { Show, createSignal } from "solid-js";
import { A } from "@solidjs/router";
import { AuthorityBadge, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

const localCoreCommand = "python studio/local_server.py";

export default function Desk() {
  const { t, locale } = useI18n();
  const studio = useStudio();
  const hosted = () => !studio.bridgeAvailable();
  const [copied, setCopied] = createSignal(false);

  const copyLocalCore = async () => {
    await navigator.clipboard.writeText(localCoreCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section class="nf-page nf-desk-page">
      <PageIntro eyebrow={t("desk.eyebrow")} title={t("desk.title")} body={t("desk.body")} />

      <div class="nf-start-actions" aria-label={t("desk.title")}>
        <A href="/start" class="nf-start-action" data-intent="start-novel">
          <span class="nf-card-label">01</span>
          <strong>{t("desk.startPlaygroundTitle")}</strong>
          <small>{t("desk.startPlaygroundBody")}</small>
        </A>
        <A href="/project" class="nf-start-action" data-intent="open-project">
          <span class="nf-card-label">02</span>
          <strong>{t("desk.startProjectTitle")}</strong>
          <small>{t("desk.startProjectBody")}</small>
        </A>
        <A href="/agents" class="nf-start-action" data-intent="agent-integration">
          <span class="nf-card-label">03</span>
          <strong>{t("desk.startAgentTitle")}</strong>
          <small>{t("desk.startAgentBody")}</small>
        </A>
        <A href={hosted() ? "#core-binding" : "/capabilities"} class="nf-start-action" data-intent="explore-novelforge">
          <span class="nf-card-label">04</span>
          <strong>{t("desk.startExploreTitle")}</strong>
          <small>{t("desk.startExploreBody")}</small>
        </A>
      </div>

      <Show when={hosted()}>
        <section
          id="core-binding"
          class="wui-card wui-card--outlined nf-inspector-surface nf-binding-surface"
          aria-labelledby="binding-heading"
          data-core-unbound={t("host.unboundTitle")}
        >
          <header class="nf-binding-head">
            <div>
              <span class="nf-eyebrow">{t("desk.bindingEyebrow")}</span>
              <h2 id="binding-heading">{t("desk.bindingTitle")}</h2>
              <p>{t("desk.bindingBody")}</p>
            </div>
            <span class="wui-badge wui-badge--outline">Core unbound</span>
          </header>
          <div class="nf-binding-options">
            <article class="nf-binding-option" data-state="available">
              <div class="nf-binding-option-head">
                <span class="nf-binding-dot" aria-hidden="true" />
                <div><strong>{t("desk.bindingLocalTitle")}</strong><small>{t("desk.bindingLocalMeta")}</small></div>
              </div>
              <p>{t("desk.bindingLocalBody")}</p>
              <div class="nf-binding-command">
                <code>{localCoreCommand}</code>
                <button class="wui-button wui-button--outline" type="button" onClick={() => void copyLocalCore()}>
                  {copied() ? (locale() === "zh-CN" ? "已复制" : "Copied") : (locale() === "zh-CN" ? "复制启动命令" : "Copy command")}
                </button>
              </div>
              <span class="wui-badge wui-badge--success">{t("desk.bindingLocalStatus")}</span>
            </article>
            <article class="nf-binding-option" data-state="planned">
              <div class="nf-binding-option-head">
                <span class="nf-binding-dot" aria-hidden="true" />
                <div><strong>{t("desk.bindingRemoteTitle")}</strong><small>{t("desk.bindingRemoteMeta")}</small></div>
              </div>
              <p>{t("desk.bindingRemoteBody")}</p>
              <button class="wui-button wui-button--outline" type="button" disabled>{t("desk.bindingRemoteAction")}</button>
            </article>
            <article class="nf-binding-option" data-state="demo">
              <div class="nf-binding-option-head">
                <span class="nf-binding-dot" aria-hidden="true" />
                <div><strong>{t("desk.bindingDemoTitle")}</strong><small>{t("desk.bindingDemoMeta")}</small></div>
              </div>
              <p>{t("desk.bindingDemoBody")}</p>
              <A class="wui-button wui-button--solid" href="/workspace">{t("desk.bindingDemoAction")}</A>
            </article>
          </div>
        </section>
      </Show>

      <Show when={studio.bridgeAvailable()}>
        <QueryError message={studio.bridgeError() ? String(studio.bridgeError()) : undefined} />

        <div class="nf-metric-grid">
          <article class="wui-card nf-card nf-card-accent">
            <div class="wui-card__content">
              <span class="nf-card-label">{t("desk.bridgeTitle")}</span>
              <strong>{studio.bridgeLoading() ? t("common.loading") : studio.bridgeDescription() ? t("desk.bridgeReady") : t("desk.bridgeUnavailable")}</strong>
              <small>{studio.bridgeDescription()?.contract_schema ?? "novelforge_studio_host_bridge_contract_v1"}</small>
            </div>
          </article>
          <article class="wui-card nf-card">
            <div class="wui-card__content">
              <span class="nf-card-label">{t("desk.queryCount")}</span>
              <strong>{studio.bridgeDescription()?.supported_operations.length ?? "—"}</strong>
              <small>bridge.describe · project.inspect · …</small>
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
            <div class="wui-card__header"><h2>{t("nav.workspace")}</h2></div>
            <div class="wui-card__content">
              <p>{t("playground.body")}</p>
              <A class="wui-button wui-button--outline" href="/workspace">{t("playground.runAction")}</A>
            </div>
          </article>
        </div>
      </Show>
    </section>
  );
}
