import { For, Show, createMemo, createSignal, onCleanup, onMount, ParentComponent } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { useI18n } from "./i18n";
import { useStudio } from "./studio";
import { StudioIcon, type StudioIconName } from "./StudioIcon";
import { invokeBridge, operationError } from "./bridge";
import {
  AUTHORING_INTENT_TASK_MODE,
  type AuthorRunStartResult,
  type AuthoringIntent,
  type ContextRuntimeProjection,
  type InspectorListProjection,
} from "./authoring/contracts";
import { CoreRequirementNotice, RunProgress, WriterContextStrip } from "./authoring/AuthoringUI";

type NavEntry = { path: string; en: string; zh: string; icon: StudioIconName; project?: boolean };

const writerNavigation: NavEntry[] = [
  { path: "/", en: "Desk", zh: "书桌", icon: "home" },
  { path: "/manuscript", en: "Manuscript", zh: "正文", icon: "workspace", project: true },
  { path: "/plan", en: "Plan", zh: "计划", icon: "project", project: true },
  { path: "/story", en: "Story", zh: "故事", icon: "semantic", project: true },
  { path: "/review", en: "Review", zh: "审阅", icon: "check", project: true },
  { path: "/research", en: "Research & Corpus", zh: "研究与语料", icon: "search", project: true },
  { path: "/learning", en: "Learning", zh: "学习", icon: "agents", project: true },
  { path: "/publication", en: "Publish", zh: "出版", icon: "project", project: true },
];

const inspectorNavigation: NavEntry[] = [
  { path: "/inspect", en: "Inspector", zh: "检查器", icon: "diagnostics", project: true },
  { path: "/runtime", en: "Sessions & Runs", zh: "会话与运行", icon: "runtime", project: true },
  { path: "/context", en: "Context", zh: "Context", icon: "context", project: true },
  { path: "/capabilities", en: "Capabilities", zh: "能力", icon: "capabilities" },
  { path: "/diagnostics", en: "Diagnostics", zh: "诊断", icon: "diagnostics" },
  { path: "/architecture", en: "Architecture", zh: "架构", icon: "runtime" },
];

const routeByOperation: Record<string, string> = {
  "project.create": "/start",
  "project.inspect": "/",
  "document.create": "/manuscript",
  "document.revision.save": "/manuscript",
  "document.revision.compare": "/manuscript",
  "author.run.start": "/manuscript",
  "inspector.context.runtime": "/context",
  "inspector.runs.list": "/runtime",
  "inspector.candidates.list": "/review",
  "candidate.accept": "/review",
  "settlement.apply": "/review",
  "publication.preview": "/publication",
  "publication.build": "/publication",
};

function projectHref(entry: NavEntry, projectId: string): string {
  if (!entry.project || !projectId) return entry.path;
  const separator = entry.path.includes("?") ? "&" : "?";
  return `${entry.path}${separator}project=${encodeURIComponent(projectId)}`;
}

export const AppShell: ParentComponent = (props) => {
  const { locale, setLocale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const navigate = useNavigate();
  const zh = () => locale() === "zh-CN";
  const [paletteOpen, setPaletteOpen] = createSignal(false);
  const [inspectorOpen, setInspectorOpen] = createSignal(false);
  const [aiOpen, setAiOpen] = createSignal(false);
  const [query, setQuery] = createSignal("");
  const [dark, setDark] = createSignal(window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);
  const [intent, setIntent] = createSignal<AuthoringIntent>("write");
  const [instruction, setInstruction] = createSignal("");
  const [run, setRun] = createSignal<AuthorRunStartResult>();
  const [runStatus, setRunStatus] = createSignal("");
  const [contextProjection, setContextProjection] = createSignal<ContextRuntimeProjection>();
  const [aiError, setAiError] = createSignal<string>();
  const [aiBusy, setAiBusy] = createSignal(false);

  const capabilities = () => studio.bridgeCapabilities();
  const supported = createMemo(() => capabilities()?.operations ?? []);
  const currentProject = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const currentDocument = () => new URLSearchParams(location.search).get("document")?.trim() || undefined;

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
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "i") {
      event.preventDefault();
      setAiOpen((open) => !open);
    }
    if (event.key === "Escape") {
      setPaletteOpen(false);
      if (window.matchMedia("(max-width: 1080px)").matches) setAiOpen(false);
    }
  };
  onMount(() => window.addEventListener("keydown", keyHandler));
  onCleanup(() => window.removeEventListener("keydown", keyHandler));

  const label = (entry: NavEntry) => zh() ? entry.zh : entry.en;
  const active = (path: string) => location.pathname === path;
  const q = createMemo(() => query().trim().toLowerCase());
  const matches = (value: string) => !q() || value.toLowerCase().includes(q());

  const startRun = async () => {
    const projectId = currentProject();
    if (!projectId || !instruction().trim()) return;
    setAiBusy(true);
    setAiError(undefined);
    setRun(undefined);
    setContextProjection(undefined);
    try {
      const response = await invokeBridge<AuthorRunStartResult>("author.run.start", {
        project_id: projectId,
        task_mode: AUTHORING_INTENT_TASK_MODE[intent()],
        target_ref: currentDocument(),
        payload: {
          instruction: instruction().trim(),
          intent: intent(),
          requested_surface: "studio_ai_assistant_dock",
        },
        idempotency_key: `studio-ai-${crypto.randomUUID()}`,
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setRun(response.data);
      setRunStatus(response.data.status);
      studio.setLastRunId(response.data.run_id);
    } catch (error) {
      setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      setAiBusy(false);
    }
  };

  const refreshRunEvidence = async () => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    if (!projectId || !runId) return;
    setAiBusy(true);
    setAiError(undefined);
    try {
      if (supported().includes("inspector.runs.list")) {
        const response = await invokeBridge<InspectorListProjection<{ run_id: string; status?: string }>>("inspector.runs.list", { project_id: projectId });
        if (response.status === "ok" && response.data) {
          const persisted = response.data.items.find((item) => item.run_id === runId);
          if (persisted?.status) setRunStatus(persisted.status);
        }
      }
      if (supported().includes("inspector.context.runtime")) {
        const response = await invokeBridge<ContextRuntimeProjection>("inspector.context.runtime", { project_id: projectId, run_id: runId });
        if (response.status === "ok" && response.data) setContextProjection(response.data);
      }
    } catch (error) {
      setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      setAiBusy(false);
    }
  };

  const go = (path: string) => {
    setPaletteOpen(false);
    setQuery("");
    const entry = [...writerNavigation, ...inspectorNavigation].find((item) => item.path === path);
    navigate(entry ? projectHref(entry, currentProject()) : path);
  };

  const renderNav = (entries: NavEntry[]) => (
    <For each={entries}>
      {(entry) => (
        <A href={projectHref(entry, currentProject())} class="wui-sidebar__item nf-nav-item" data-active={active(entry.path) ? "true" : undefined} aria-current={active(entry.path) ? "page" : undefined}>
          <span class="wui-sidebar__icon nf-nav-glyph" aria-hidden="true"><StudioIcon name={entry.icon} /></span>
          <span class="wui-sidebar__label">{label(entry)}</span>
        </A>
      )}
    </For>
  );

  return (
    <div class="nf-app-shell qf-writer-shell" data-ai-open={aiOpen() ? "true" : undefined}>
      <aside class="wui-sidebar nf-sidebar qf-writer-sidebar" aria-label={zh() ? "Writer Mode 导航" : "Writer Mode navigation"}>
        <A href="/" class="wui-sidebar__header nf-brand">
          <img class="nf-brand-mark" src="/quillframe-mark.svg" width="30" height="30" alt="" aria-hidden="true" />
          <span class="wui-sidebar__brand-label"><strong>Quillframe</strong><small>Writer Mode · 0.9</small></span>
        </A>
        <nav class="wui-sidebar__content nf-nav-list">
          <div class="nf-nav-section" data-nav-tier="writer">{renderNav(writerNavigation)}</div>
          <button class="qf-inspector-disclosure" type="button" aria-expanded={inspectorOpen()} onClick={() => setInspectorOpen((open) => !open)}>
            <span>{zh() ? "检查与运行" : "Inspect & Runtime"}</span><span aria-hidden="true">{inspectorOpen() ? "−" : "+"}</span>
          </button>
          <Show when={inspectorOpen()}><div class="nf-nav-section" data-nav-tier="inspect">{renderNav(inspectorNavigation)}</div></Show>
        </nav>
        <div class="wui-sidebar__footer nf-sidebar-foot">
          <span class="wui-badge wui-badge--outline">authority=false</span>
          <small>{studio.transportName()}</small>
        </div>
      </aside>

      <div class="nf-main-column qf-writer-main">
        <header class="wui-app-bar nf-topbar qf-writer-topbar" data-position="sticky">
          <div class="wui-app-bar__brand nf-topbar-context">
            <span class="nf-mobile-brand">Quillframe</span>
            <Show when={studio.projectProjection()?.project} fallback={<A href="/start">{zh() ? "新建 / 打开 Project" : "New / Open Project"}</A>}>
              {(project) => <strong>{project().title}</strong>}
            </Show>
          </div>
          <div class="wui-app-bar__actions nf-topbar-actions">
            <span class="wui-badge wui-badge--outline nf-host-chip" data-surface={studio.surface()} title={studio.transportName()}>
              <span class="nf-host-dot" aria-hidden="true" />
              <span>{studio.bridgeAvailable() ? (zh() ? "Core 已绑定" : "Core bound") : (zh() ? "Core 未绑定" : "Core unbound")}</span>
            </span>
            <button class="wui-button wui-button--outline qf-ai-toggle" type="button" onClick={() => setAiOpen((open) => !open)} aria-expanded={aiOpen()} aria-controls="qf-ai-dock">
              <StudioIcon name="agents" class="nf-control-icon" /><span>AI</span><kbd>⌘I</kbd>
            </button>
            <button class="wui-button wui-button--outline nf-command-trigger" type="button" onClick={() => setPaletteOpen(true)} aria-label={zh() ? "命令面板" : "Command palette"}>
              <StudioIcon name="command" class="nf-control-icon" /><span class="nf-command-label">{zh() ? "命令" : "Command"}</span><kbd>⌘K</kbd>
            </button>
            <A class="wui-button wui-button--ghost wui-button--icon" href="/settings" aria-label={zh() ? "设置" : "Settings"}><StudioIcon name="settings" class="nf-control-icon" /></A>
            <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setTheme(!dark())} aria-label={zh() ? "切换主题" : "Toggle theme"}><StudioIcon name={dark() ? "sun" : "moon"} class="nf-control-icon" /></button>
            <button class="wui-button wui-button--ghost" type="button" onClick={() => setLocale(locale() === "en-US" ? "zh-CN" : "en-US")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{locale() === "en-US" ? "中文" : "EN"}</button>
          </div>
        </header>
        <main class="nf-content qf-writer-content" id="main-content">{props.children}</main>
      </div>

      <Show when={aiOpen()}>
        <aside id="qf-ai-dock" class="qf-ai-dock" aria-label={zh() ? "AI Assistant Dock" : "AI Assistant Dock"}>
          <header class="qf-ai-dock__header">
            <div><span class="nf-eyebrow">AI ASSISTANT</span><h2>{zh() ? "项目助手" : "Project assistant"}</h2></div>
            <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setAiOpen(false)} aria-label={zh() ? "关闭 AI 助手" : "Close AI Assistant"}>×</button>
          </header>
          <p class="qf-ai-dock__boundary">{zh() ? "这是 Quillframe Agent surface，不是 provider chat。Context、执行与审查由 Core 决定。" : "This is a Quillframe Agent surface, not a provider chat. Core owns Context, execution and review."}</p>
          <label class="nf-field-label"><span>{zh() ? "意图" : "Intent"}</span><select class="wui-input" value={intent()} onChange={(event) => setIntent(event.currentTarget.value as AuthoringIntent)}><option value="write">{zh() ? "写作 · DRAFT" : "Write · DRAFT"}</option><option value="revise">{zh() ? "修改 · REVISE" : "Revise · REVISE"}</option><option value="review">{zh() ? "审阅 · AUDIT" : "Review · AUDIT"}</option><option value="continuity">{zh() ? "连续性 · AUDIT" : "Continuity · AUDIT"}</option><option value="research">{zh() ? "研究 · RESEARCH" : "Research · RESEARCH"}</option></select></label>
          <label class="nf-field-label"><span>{zh() ? "任务" : "Task"}</span><textarea class="wui-input qf-ai-instruction" value={instruction()} onInput={(event) => setInstruction(event.currentTarget.value)} placeholder={zh() ? "描述你要完成的创作任务。不要手工拼 Context。" : "Describe the authoring task. Do not hand-assemble Context."} /></label>
          <button class="wui-button wui-button--solid" type="button" disabled={aiBusy() || !currentProject() || !instruction().trim() || !supported().includes("author.run.start")} onClick={() => void startRun()}>{aiBusy() ? (zh() ? "处理中…" : "Working…") : (zh() ? "启动 Core Run" : "Start Core run")}</button>
          <CoreRequirementNotice operation="author.run.start" compact />
          <Show when={aiError()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Agent</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
          <Show when={run() || studio.lastRunId()}>
            <section class="qf-ai-run" aria-live="polite">
              <div class="qf-ai-run__identity"><div><span>{zh() ? "Run" : "Run"}</span><code>{run()?.run_id || studio.lastRunId()}</code></div><strong>{runStatus() || run()?.status || "unknown"}</strong></div>
              <Show when={run()?.message}><p>{run()?.message}</p></Show>
              <RunProgress waiting zh={zh()} />
              <button class="wui-button wui-button--outline" type="button" disabled={aiBusy()} onClick={() => void refreshRunEvidence()}>{zh() ? "刷新 Core evidence" : "Refresh Core evidence"}</button>
              <CoreRequirementNotice operation="run.events.list" compact />
              <WriterContextStrip projection={contextProjection()} zh={zh()} />
            </section>
          </Show>
        </aside>
      </Show>

      <nav class="wui-bottom-nav nf-bottom-nav qf-writer-bottom-nav" aria-label={zh() ? "Writer Mode 移动导航" : "Writer Mode mobile navigation"}>
        <For each={[writerNavigation[0], writerNavigation[1], writerNavigation[4], writerNavigation[7]]}>
          {(entry) => <A href={projectHref(entry, currentProject())} class="wui-bottom-nav__item nf-bottom-nav-item" data-active={active(entry.path) ? "true" : undefined} aria-current={active(entry.path) ? "page" : undefined}><span class="wui-bottom-nav__icon" aria-hidden="true"><StudioIcon name={entry.icon} /></span><small class="wui-bottom-nav__label">{label(entry)}</small></A>}
        </For>
      </nav>

      <Show when={paletteOpen()}>
        <div class="wui-command-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setPaletteOpen(false)}>
          <section class="wui-command nf-command" role="dialog" aria-modal="true" aria-label={zh() ? "命令面板" : "Command palette"}>
            <div class="wui-command__input-wrapper"><span class="wui-command__icon" aria-hidden="true"><StudioIcon name="search" /></span><input class="wui-command__input" autofocus value={query()} onInput={(event) => setQuery(event.currentTarget.value)} placeholder={zh() ? "搜索页面或 Core operation…" : "Search pages or Core operations…"} /></div>
            <div class="wui-command__list">
              <div class="wui-command__group-label">Writer Mode</div>
              <For each={writerNavigation.filter((entry) => matches(`${entry.path} ${entry.en} ${entry.zh}`))}>{(entry) => <button type="button" class="wui-command__item" onClick={() => go(entry.path)}><span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name={entry.icon} /></span><span class="wui-command__item-label">{label(entry)}</span></button>}</For>
              <div class="wui-command__group-label">Core operations</div>
              <For each={supported().filter(matches)}>{(operation) => <button type="button" class="wui-command__item" onClick={() => go(routeByOperation[operation] ?? "/inspect")}><span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name="check" /></span><span class="wui-command__item-label">{operation}</span></button>}</For>
              <Show when={q() && !writerNavigation.some((entry) => matches(`${entry.path} ${entry.en} ${entry.zh}`)) && !supported().some(matches)}><div class="wui-command__empty">{zh() ? "没有匹配项" : "No matches"}</div></Show>
            </div>
          </section>
        </div>
      </Show>
    </div>
  );
};
