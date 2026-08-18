import { For, Show, createMemo, createSignal, onCleanup, onMount, ParentComponent } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { useI18n } from "./i18n";
import type { MessageKey } from "./locales/types";
import { useStudio } from "./studio";
import { StudioIcon, type StudioIconName } from "./StudioIcon";

type NavigationLabel = MessageKey | "Runtime" | "Control Plane" | "Inspector" | "Architecture" | "Publication" | "Settings";
type NavigationEntry = readonly [string, NavigationLabel, StudioIconName];

const productNavigation: ReadonlyArray<NavigationEntry> = [
  ["/", "nav.desk", "home"],
  ["/project", "nav.project", "project"],
  ["/control", "Control Plane", "capabilities"],
  ["/workspace", "nav.workspace", "workspace"],
  ["/agents", "nav.agents", "agents"],
];

const inspectionNavigation: ReadonlyArray<NavigationEntry> = [
  ["/inspect", "Inspector", "diagnostics"],
  ["/architecture", "Architecture", "runtime"],
  ["/publication", "Publication", "workspace"],
  ["/runtime", "Runtime", "runtime"],
  ["/context", "nav.context", "context"],
  ["/capabilities", "nav.capabilities", "capabilities"],
  ["/semantic", "nav.semantic", "semantic"],
  ["/diagnostics", "nav.diagnostics", "diagnostics"],
];

const utilityNavigation: ReadonlyArray<NavigationEntry> = [
  ["/settings", "Settings", "settings"],
];

const navigation = [...productNavigation, ...inspectionNavigation, ...utilityNavigation];

const operationRoute: Record<string, string> = {
  "bridge.describe": "/",
  "framework.doctor": "/diagnostics",
  "project.inspect": "/project",
  "capabilities.inspect": "/capabilities",
  "context.inspect": "/context",
  "semantic.catalog": "/semantic",
  "publication.preview": "/publication",
  "runtime.sessions.list": "/runtime",
  "runtime.session.get": "/runtime",
  "runtime.events.list": "/runtime",
  "runtime.handoff.inspect": "/runtime",
  "run.receipt.get": "/runtime",
  "session.resume.preflight": "/runtime",
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
  const navLabel = (label: NavigationLabel) => {
    if (label === "Runtime") return "Runtime";
    if (label === "Inspector") return locale() === "zh-CN" ? "检查项目" : "Inspector";
    if (label === "Architecture") return locale() === "zh-CN" ? "架构观测" : "Architecture";
    if (label === "Publication") return locale() === "zh-CN" ? "出版" : "Publication";
    if (label === "Control Plane") return locale() === "zh-CN" ? "控制台" : "Control Plane";
    if (label === "Settings") return locale() === "zh-CN" ? "设置" : "Settings";
    return t(label);
  };
  const coreStatus = createMemo(() => {
    if (studio.bridgeAvailable()) return locale() === "zh-CN" ? "Core 已绑定" : "Core bound";
    return locale() === "zh-CN" ? "Core 未绑定" : "Core unbound";
  });
  const coreStatusTitle = createMemo(() => {
    if (studio.bridgeAvailable()) return locale() === "zh-CN" ? "查看 Host Bridge 诊断" : "Open Host Bridge diagnostics";
    return locale() === "zh-CN" ? "选择 Local Core、Remote Core 或只读 Demo" : "Choose Local Core, Remote Core, or read-only demo";
  });

  const go = (path: string) => {
    setPaletteOpen(false);
    setQuery("");
    navigate(path);
  };

  const renderNavigation = (items: ReadonlyArray<NavigationEntry>) => (
    <For each={items}>
      {([path, label, icon]) => (
        <A
          href={path}
          class="wui-sidebar__item nf-nav-item"
          data-active={location.pathname === path ? "true" : undefined}
          aria-current={location.pathname === path ? "page" : undefined}
        >
          <span class="wui-sidebar__icon nf-nav-glyph" aria-hidden="true"><StudioIcon name={icon} /></span>
          <span class="wui-sidebar__label">{navLabel(label)}</span>
        </A>
      )}
    </For>
  );

  return (
    <div class="nf-app-shell">
      <aside class="wui-sidebar nf-sidebar" aria-label={t("nav.primaryLabel")}>
        <A href="/" class="wui-sidebar__header nf-brand">
          <img class="nf-brand-mark" src="/quillframe-mark.svg" width="30" height="30" alt="" aria-hidden="true" />
          <span class="wui-sidebar__brand-label">
            <strong>{t("app.brand")}</strong>
            <small>{t("app.readOnly")}</small>
          </span>
        </A>
        <nav class="wui-sidebar__content nf-nav-list">
          <div class="nf-nav-section" data-nav-tier="product">{renderNavigation(productNavigation)}</div>
          <div class="nf-nav-section" data-nav-tier="inspect">{renderNavigation(inspectionNavigation)}</div>
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
            <A
              href={studio.bridgeAvailable() ? "/diagnostics" : "/"}
              class="wui-badge wui-badge--outline nf-host-chip"
              data-surface={studio.surface()}
              data-host-label={t("host.cloud")}
              title={coreStatusTitle()}
              aria-label={coreStatusTitle()}
            >
              <span class="nf-host-dot" aria-hidden="true" />
              <span>{coreStatus()}</span>
            </A>
            <button class="wui-button wui-button--outline nf-command-trigger" type="button" onClick={() => setPaletteOpen(true)} aria-label={t("top.command")}>
              <StudioIcon name="command" class="nf-control-icon" />
              <span class="nf-command-label">{t("top.command")}</span><kbd>⌘K</kbd>
            </button>
            <A class="wui-button wui-button--ghost wui-button--icon" href="/settings" aria-label={navLabel("Settings")} title={navLabel("Settings")}>
              <StudioIcon name="settings" class="nf-control-icon" />
            </A>
            <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setTheme(!dark())} aria-label={t("top.theme")}>
              <StudioIcon name={dark() ? "sun" : "moon"} class="nf-control-icon" />
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
        <For each={productNavigation}>
          {([path, label, icon]) => (
            <A
              href={path}
              class="wui-bottom-nav__item nf-bottom-nav-item"
              data-active={location.pathname === path ? "true" : undefined}
              aria-current={location.pathname === path ? "page" : undefined}
            >
              <span class="wui-bottom-nav__icon" aria-hidden="true"><StudioIcon name={icon} /></span>
              <small class="wui-bottom-nav__label">{navLabel(label)}</small>
            </A>
          )}
        </For>
      </nav>

      <Show when={paletteOpen()}>
        <div class="wui-command-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setPaletteOpen(false)}>
          <section class="wui-command nf-command" role="dialog" aria-modal="true" aria-label={t("command.title")}>
            <div class="wui-command__input-wrapper">
              <span class="wui-command__icon" aria-hidden="true"><StudioIcon name="search" /></span>
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
              <For each={navigation.filter(([path, label]) => matches(`${path} ${navLabel(label)}`))}>
                {([path, label, icon]) => (
                  <button type="button" class="wui-command__item" onClick={() => go(path)}>
                    <span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name={icon} /></span>
                    <span class="wui-command__item-label">{navLabel(label)}</span>
                  </button>
                )}
              </For>

              <div class="wui-command__group-label">{t("command.supported")}</div>
              <For each={supported().filter(matches)}>
                {(operation) => (
                  <button type="button" class="wui-command__item" onClick={() => go(operationRoute[operation] ?? "/") }>
                    <span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name="check" /></span>
                    <span class="wui-command__item-label">{operation}</span>
                  </button>
                )}
              </For>

              <div class="wui-command__group-label">{t("command.deferred")}</div>
              <For each={deferred().filter(([operation]) => matches(operation))}>
                {([operation, info]) => (
                  <div class="wui-command__item" data-disabled title={info.reason}>
                    <span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name="minus" /></span>
                    <span class="wui-command__item-label">{operation}</span>
                    <span class="wui-command__item-shortcut">{info.dependency ?? "Core"}</span>
                  </div>
                )}
              </For>
              <Show when={q() && !navigation.some(([path, label]) => matches(`${path} ${navLabel(label)}`)) && !supported().some(matches) && !deferred().some(([operation]) => matches(operation))}>
                <div class="wui-command__empty">{t("command.noMatches")}</div>
              </Show>
            </div>
          </section>
        </div>
      </Show>
    </div>
  );
};
