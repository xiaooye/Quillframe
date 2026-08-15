import { For, Show, createMemo, createSignal, onCleanup, onMount, ParentComponent } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { useI18n } from "./i18n";
import { useStudio } from "./studio";

const navigation = [
  ["/", "nav.desk", "✦"],
  ["/project", "nav.project", "◫"],
  ["/workspace", "nav.workspace", "✎"],
  ["/context", "nav.context", "◎"],
  ["/capabilities", "nav.capabilities", "◇"],
  ["/semantic", "nav.semantic", "∿"],
  ["/diagnostics", "nav.diagnostics", "⌁"],
] as const;

const operationRoute: Record<string, string> = {
  "bridge.describe": "/",
  "framework.doctor": "/diagnostics",
  "project.inspect": "/project",
  "capabilities.inspect": "/capabilities",
  "context.inspect": "/context",
  "semantic.catalog": "/semantic",
};

export const AppShell: ParentComponent = (props) => {
  const { t, locale, setLocale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = createSignal(false);
  const [query, setQuery] = createSignal("");
  const [dark, setDark] = createSignal(window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);

  const setTheme = (next: boolean) => {
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
  };
  setTheme(dark());

  const keyHandler = (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      setPaletteOpen((open) => !open);
    }
    if (event.key === "Escape") setPaletteOpen(false);
  };
  onMount(() => window.addEventListener("keydown", keyHandler));
  onCleanup(() => window.removeEventListener("keydown", keyHandler));

  const supported = createMemo(() => studio.bridgeDescription()?.supported_operations ?? []);
  const deferred = createMemo(() => Object.entries(studio.bridgeDescription()?.deferred_operations ?? {}));
  const q = createMemo(() => query().trim().toLowerCase());
  const matches = (value: string) => !q() || value.toLowerCase().includes(q());

  const go = (path: string) => {
    setPaletteOpen(false);
    setQuery("");
    navigate(path);
  };

  return (
    <div class="nf-app-shell">
      <aside class="wui-sidebar nf-sidebar" aria-label={t("nav.primaryLabel")}>
        <A href="/" class="wui-sidebar__header nf-brand">
          <span class="nf-brand-mark" aria-hidden="true">N</span>
          <span class="wui-sidebar__brand-label">
            <strong>{t("app.brand")}</strong>
            <small>{t("app.readOnly")}</small>
          </span>
        </A>
        <nav class="wui-sidebar__content nf-nav-list">
          <For each={navigation}>
            {([path, label, glyph]) => (
              <A
                href={path}
                class="wui-sidebar__item nf-nav-item"
                data-active={location.pathname === path ? "true" : undefined}
                aria-current={location.pathname === path ? "page" : undefined}
              >
                <span class="wui-sidebar__icon nf-nav-glyph" aria-hidden="true">{glyph}</span>
                <span class="wui-sidebar__label">{t(label)}</span>
              </A>
            )}
          </For>
        </nav>
        <div class="wui-sidebar__footer nf-sidebar-foot">
          <span class="wui-badge wui-badge--outline">authority=false</span>
          <small>{t("footer.coreTruth")}</small>
        </div>
      </aside>

      <div class="nf-main-column">
        <header class="wui-app-bar nf-topbar" data-position="sticky">
          <div class="wui-app-bar__brand nf-topbar-context">
            <span class="nf-mobile-brand">{t("app.brand")}</span>
            <Show when={studio.projectResult()?.data?.project.project.title} fallback={<span>{t("project.noProject")}</span>}>
              <strong>{studio.projectResult()?.data?.project.project.title}</strong>
            </Show>
          </div>
          <div class="wui-app-bar__actions nf-topbar-actions">
            <span class="wui-badge wui-badge--outline nf-host-chip" data-surface={studio.surface()}>
              <span class="nf-host-dot" aria-hidden="true" />
              <span>{studio.bridgeAvailable() ? t("host.local") : t("host.cloud")}</span>
            </span>
            <button class="wui-button wui-button--outline nf-command-trigger" type="button" onClick={() => setPaletteOpen(true)} aria-label={t("top.command")}>
              <span aria-hidden="true">⌘</span><span class="nf-command-label">{t("top.command")}</span><kbd>⌘K</kbd>
            </button>
            <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setTheme(!dark())} aria-label={t("top.theme")}>
              <span aria-hidden="true">{dark() ? "☀" : "☾"}</span>
            </button>
            <button class="wui-button wui-button--ghost" type="button" onClick={() => setLocale(locale() === "en-US" ? "zh-CN" : "en-US")} aria-label={t("top.language")}>
              {locale() === "en-US" ? "中文" : "EN"}
            </button>
          </div>
        </header>

        <main class="nf-content" id="main-content">{props.children}</main>

        <footer class="nf-footer">
          <span>{t("footer.readOnly")}</span>
          <span aria-hidden="true">·</span>
          <span>{t("footer.coreTruth")}</span>
        </footer>
      </div>

      <nav class="wui-bottom-nav nf-bottom-nav" aria-label={t("nav.mobileLabel")}>
        <For each={navigation.slice(0, 5)}>
          {([path, label, glyph]) => (
            <A
              href={path}
              class="wui-bottom-nav__item nf-bottom-nav-item"
              data-active={location.pathname === path ? "true" : undefined}
              aria-current={location.pathname === path ? "page" : undefined}
            >
              <span class="wui-bottom-nav__icon" aria-hidden="true">{glyph}</span>
              <small class="wui-bottom-nav__label">{t(label)}</small>
            </A>
          )}
        </For>
      </nav>

      <Show when={paletteOpen()}>
        <div class="wui-command-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setPaletteOpen(false)}>
          <section class="wui-command nf-command" role="dialog" aria-modal="true" aria-label={t("command.title")}>
            <div class="wui-command__input-wrapper">
              <span class="wui-command__icon" aria-hidden="true">⌕</span>
              <input
                class="wui-command__input"
                autofocus
                value={query()}
                onInput={(event) => setQuery(event.currentTarget.value)}
                placeholder={t("command.placeholder")}
              />
            </div>
            <div class="wui-command__list">
              <div class="wui-command__group-label">{t("command.navigation")}</div>
              <For each={navigation.filter(([path, label]) => matches(`${path} ${t(label)}`))}>
                {([path, label, glyph]) => (
                  <button type="button" class="wui-command__item" onClick={() => go(path)}>
                    <span class="wui-command__item-icon" aria-hidden="true">{glyph}</span>
                    <span class="wui-command__item-label">{t(label)}</span>
                  </button>
                )}
              </For>

              <div class="wui-command__group-label">{t("command.supported")}</div>
              <For each={supported().filter(matches)}>
                {(operation) => (
                  <button type="button" class="wui-command__item" onClick={() => go(operationRoute[operation] ?? "/") }>
                    <span class="wui-command__item-icon" aria-hidden="true">✓</span>
                    <span class="wui-command__item-label">{operation}</span>
                  </button>
                )}
              </For>

              <div class="wui-command__group-label">{t("command.deferred")}</div>
              <For each={deferred().filter(([operation]) => matches(operation))}>
                {([operation, info]) => (
                  <div class="wui-command__item" data-disabled title={info.reason}>
                    <span class="wui-command__item-icon" aria-hidden="true">—</span>
                    <span class="wui-command__item-label">{operation}</span>
                    <span class="wui-command__item-shortcut">{info.dependency ?? "Core"}</span>
                  </div>
                )}
              </For>
              <Show when={q() && !navigation.some(([path, label]) => matches(`${path} ${t(label)}`)) && !supported().some(matches) && !deferred().some(([operation]) => matches(operation))}>
                <div class="wui-command__empty">{t("command.noMatches")}</div>
              </Show>
            </div>
          </section>
        </div>
      </Show>
    </div>
  );
};
