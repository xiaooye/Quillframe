import { JSX, Show } from "solid-js";
import { useI18n } from "./i18n";

export function PageIntro(props: { eyebrow?: string; title: string; body: string; actions?: JSX.Element }) {
  return (
    <header class="nf-page-intro">
      <div>
        <Show when={props.eyebrow}><span class="nf-eyebrow">{props.eyebrow}</span></Show>
        <h1>{props.title}</h1>
        <p>{props.body}</p>
      </div>
      <Show when={props.actions}><div class="nf-page-actions">{props.actions}</div></Show>
    </header>
  );
}

export function JsonBlock(props: { value: unknown; label?: string }) {
  return (
    <div class="nf-json-block">
      <Show when={props.label}><div class="nf-json-label">{props.label}</div></Show>
      <pre><code>{JSON.stringify(props.value, null, 2)}</code></pre>
    </div>
  );
}

export function QueryError(props: { message?: string }) {
  const { t } = useI18n();
  return (
    <Show when={props.message}>
      <div class="wui-alert nf-alert" role="alert">
        <strong>{t("common.error")}</strong>
        <span>{props.message}</span>
      </div>
    </Show>
  );
}

export function CoreHostBoundary() {
  const { t } = useI18n();
  return (
    <section class="wui-card nf-card nf-host-boundary" aria-labelledby="core-host-boundary-title">
      <div class="wui-card__content nf-host-boundary-content">
        <span class="wui-badge wui-badge--outline">{t("host.cloud")}</span>
        <div>
          <h2 id="core-host-boundary-title">{t("host.unboundTitle")}</h2>
          <p>{t("host.unboundBody")}</p>
        </div>
        <small>{t("host.unboundFoot")}</small>
      </div>
    </section>
  );
}

export function AuthorityBadge() {
  return <span class="wui-badge wui-badge--outline">authority=false</span>;
}
