import { createSignal } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";

const initCommand = 'python novelforge.py project init ./my-novel --id my-novel --title "My Novel" --language en';

export default function Start() {
  const { t } = useI18n();
  const [copied, setCopied] = createSignal(false);

  const copyCommand = async () => {
    await navigator.clipboard.writeText(initCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section class="nf-page">
      <PageIntro eyebrow={t("start.eyebrow")} title={t("start.title")} body={t("start.body")} />

      <div class="nf-catalog-grid">
        <article class="wui-card nf-card nf-card-accent">
          <div class="wui-card__header">
            <span class="nf-card-label">{t("start.cliMeta")}</span>
            <h2>{t("start.cliTitle")}</h2>
          </div>
          <div class="wui-card__content">
            <p>{t("start.cliBody")}</p>
            <pre class="wui-code-block"><code>{initCommand}</code></pre>
            <button class="wui-button wui-button--outline" type="button" onClick={() => void copyCommand()}>
              {copied() ? t("agents.copied") : t("start.cliAction")}
            </button>
            <small>{t("start.cliNote")}</small>
          </div>
        </article>

        <article class="wui-card nf-card">
          <div class="wui-card__header">
            <span class="nf-card-label">{t("start.desktopMeta")}</span>
            <h2>{t("start.desktopTitle")}</h2>
          </div>
          <div class="wui-card__content">
            <p>{t("start.desktopBody")}</p>
            <button class="wui-button wui-button--outline" type="button" disabled>{t("start.desktopAction")}</button>
          </div>
        </article>

        <article class="wui-card nf-card">
          <div class="wui-card__header">
            <span class="nf-card-label">{t("start.cloudMeta")}</span>
            <h2>{t("start.cloudTitle")}</h2>
          </div>
          <div class="wui-card__content">
            <p>{t("start.cloudBody")}</p>
            <A class="wui-button wui-button--outline" href="/workspace">{t("start.cloudAction")}</A>
          </div>
        </article>

        <article class="wui-card nf-card">
          <div class="wui-card__header">
            <span class="nf-card-label">{t("start.agentMeta")}</span>
            <h2>{t("start.agentTitle")}</h2>
          </div>
          <div class="wui-card__content">
            <p>{t("start.agentBody")}</p>
            <A class="wui-button wui-button--outline" href="/agents">{t("start.agentAction")}</A>
          </div>
        </article>
      </div>

      <div class="wui-alert" role="note">
        <div class="wui-alert__body">
          <strong class="wui-alert__title">authority=false</strong>
          <span class="wui-alert__description">{t("start.boundary")}</span>
        </div>
      </div>
    </section>
  );
}
