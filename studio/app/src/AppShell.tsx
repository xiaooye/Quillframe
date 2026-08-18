import { For, Show, createMemo, createSignal, onCleanup, onMount, ParentComponent } from "solid-js";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { bridgeTransportName, invokeBridge, operationError } from "./bridge";
import { useI18n } from "./i18n";
import { useStudio } from "./studio";
import { StudioIcon, type StudioIconName } from "./StudioIcon";

type NavEntry = { path: string; en: string; zh: string; icon: StudioIconName };

const creatorNavigation: NavEntry[] = [
  { path: "/", en: "Desk", zh: "书桌", icon: "home" },
  { path: "/manuscript", en: "Manuscript", zh: "手稿", icon: "workspace" },
  { path: "/plan", en: "Plan", zh: "计划", icon: "project" },
  { path: "/story", en: "Story", zh: "故事", icon: "project" },
  { path: "/review", en: "Review", zh: "审阅", icon: "check" },
  { path: "/research", en: "Research & Corpus", zh: "研究与语料", icon: "context" },
  { path: "/learning", en: "Learning", zh: "学习", icon: "semantic" },
  { path: "/publication", en: "Publish", zh: "出版", icon: "workspace" },
];

const inspectorNavigation: NavEntry[] = [
  { path: "/inspect", en: "Inspector", zh: "检查器", icon: "diagnostics" },
  { path: "/runtime", en: "Sessions & Runs", zh: "会话与运行", icon: "runtime" },
  { path: "/context", en: "Context", zh: "上下文", icon: "context" },
  { path: "/agents", en: "Agents / Models", zh: "Agent / 模型", icon: "agents" },
  { path: "/semantic", en: "Semantic Jobs", zh: "语义任务", icon: "semantic" },
  { path: "/control", en: "Control Plane", zh: "控制平面", icon: "capabilities" },
  { path: "/capabilities", en: "Capabilities", zh: "能力", icon: "capabilities" },
  { path: "/diagnostics", en: "Diagnostics", zh: "诊断", icon: "diagnostics" },
  { path: "/architecture", en: "Architecture", zh: "架构", icon: "runtime" },
];

const operationRoute: Record<string, string> = {
  "project.create": "/start", "project.list": "/start", "project.inspect": "/project",
  "document.list": "/manuscript", "document.get": "/manuscript", "document.revision.save": "/manuscript",
  "document.revisions.list": "/manuscript", "document.revision.compare": "/manuscript",
  "author.run.start": "/manuscript", "candidate.list": "/review", "candidate.get": "/review",
  "candidate.accept": "/review", "settlement.preflight": "/review", "settlement.apply": "/review",
  "publication.preview": "/publication", "publication.build": "/publication",
  "story.inspect": "/story", "plan.inspect": "/plan", "model.connect": "/start", "model.list": "/agents",
  "database.doctor": "/diagnostics",
};

export const AppShell: ParentComponent = (props) => {
  const { locale, setLocale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = createSignal(false);
  const [query, setQuery] = createSignal("");
  const [inspectorOpen, setInspectorOpen] = createSignal(false);
  const [aiOpen, setAiOpen] = createSignal(false);
  const [aiInstruction, setAiInstruction] = createSignal("");
  const [aiMode, setAiMode] = createSignal("RESEARCH");
  const [aiStatus, setAiStatus] = createSignal<string>();
  const [aiBusy, setAiBusy] = createSignal(false);
  const [dark, setDark] = createSignal(window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);
  const zh = createMemo(() => locale() === "zh-CN");
  const label = (entry: NavEntry) => zh() ? entry.zh : entry.en;
  const currentProject = () => localStorage.getItem("quillframe.ui.lastProjectId") || "";

  const setTheme = (next: boolean) => { setDark(next); document.documentElement.classList.toggle("dark", next); };
  setTheme(dark());
  const keyHandler = (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setPaletteOpen((open) => !open); }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "i") { event.preventDefault(); setAiOpen((open) => !open); }
    if (event.key === "Escape") { setPaletteOpen(false); setInspectorOpen(false); }
  };
  onMount(() => window.addEventListener("keydown", keyHandler));
  onCleanup(() => window.removeEventListener("keydown", keyHandler));

  const supported = createMemo(() => studio.bridgeDescription()?.supported_operations ?? []);
  const deferred = createMemo(() => Object.entries(studio.bridgeDescription()?.deferred_operations ?? {}));
  const q = createMemo(() => query().trim().toLowerCase());
  const matches = (value: string) => !q() || value.toLowerCase().includes(q());
  const navActive = (path: string) => location.pathname === path;
  const go = (path: string) => { setPaletteOpen(false); setQuery(""); navigate(path + (path !== "/start" && currentProject() && ["/manuscript", "/plan", "/story", "/review", "/research", "/learning", "/publication"].includes(path) ? `?project=${encodeURIComponent(currentProject())}` : "")); };

  const runAssistant = async () => {
    const project = currentProject();
    if (!project || !aiInstruction().trim()) { setAiStatus(zh() ? "请先打开 Project，并输入任务。" : "Open a project and enter an instruction first."); return; }
    setAiBusy(true); setAiStatus(undefined);
    try {
      const result = await invokeBridge<{ run_id?: string; status?: string }>("author.run.start", {
        project_id: project, task_mode: aiMode(), payload: { instruction: aiInstruction().trim(), requested_surface: "global_ai_dock" },
        idempotency_key: `studio-global-${crypto.randomUUID()}`,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setAiStatus(`${result.data.status || "awaiting_semantic"} · ${result.data.run_id || ""}`);
    } catch (cause) { setAiStatus(cause instanceof Error ? cause.message : String(cause)); }
    finally { setAiBusy(false); }
  };

  const renderNav = (entries: NavEntry[]) => <For each={entries}>{(entry) => (
    <A href={entry.path + (currentProject() && ["/manuscript", "/plan", "/story", "/review", "/research", "/learning", "/publication"].includes(entry.path) ? `?project=${encodeURIComponent(currentProject())}` : "")} class="wui-sidebar__item nf-nav-item" data-active={navActive(entry.path) ? "true" : undefined} aria-current={navActive(entry.path) ? "page" : undefined}>
      <span class="wui-sidebar__icon nf-nav-glyph" aria-hidden="true"><StudioIcon name={entry.icon} /></span><span class="wui-sidebar__label">{label(entry)}</span>
    </A>
  )}</For>;

  return (
    <div class="nf-app-shell" data-ai-open={aiOpen() ? "true" : undefined}>
      <aside class="wui-sidebar nf-sidebar" aria-label={zh() ? "创作导航" : "Authoring navigation"}>
        <A href="/" class="wui-sidebar__header nf-brand"><img class="nf-brand-mark" src="/quillframe-mark.svg" width="30" height="30" alt="" aria-hidden="true" /><span class="wui-sidebar__brand-label"><strong>Quillframe</strong><small>0.9 · authoring</small></span></A>
        <nav class="wui-sidebar__content nf-nav-list"><div class="nf-nav-section" data-nav-tier="product">{renderNav(creatorNavigation)}</div><button class="nf-inspector-toggle" type="button" onClick={() => setInspectorOpen((open) => !open)}>{zh() ? "检查与运行" : "Inspect & Runtime"}<span aria-hidden="true">{inspectorOpen() ? "−" : "+"}</span></button><Show when={inspectorOpen()}><div class="nf-nav-section" data-nav-tier="inspect">{renderNav(inspectorNavigation)}</div></Show></nav>
        <div class="wui-sidebar__footer nf-sidebar-foot"><span class="wui-badge wui-badge--outline">authority=false</span><small>{bridgeTransportName()}</small></div>
      </aside>

      <div class="nf-main-column">
        <header class="wui-app-bar nf-topbar" data-position="sticky"><div class="wui-app-bar__brand nf-topbar-context"><span class="nf-mobile-brand">Quillframe</span><Show when={currentProject()} fallback={<A href="/start">{zh() ? "新建 Project" : "New Project"}</A>}><strong>{currentProject()}</strong></Show></div><div class="wui-app-bar__actions nf-topbar-actions">
          <span class="wui-badge wui-badge--outline nf-host-chip" data-surface={studio.surface()}><span class="nf-host-dot" aria-hidden="true" />{studio.bridgeAvailable() ? (zh() ? "Core 已绑定" : "Core bound") : (zh() ? "Core 未绑定" : "Core unbound")}</span>
          <button class="wui-button wui-button--outline" type="button" onClick={() => setAiOpen((open) => !open)} aria-label={zh() ? "AI 助手" : "AI Assistant"}><StudioIcon name="agents" class="nf-control-icon" /><span>AI</span><kbd>⌘I</kbd></button>
          <button class="wui-button wui-button--outline nf-command-trigger" type="button" onClick={() => setPaletteOpen(true)} aria-label={zh() ? "命令" : "Commands"}><StudioIcon name="command" class="nf-control-icon" /><span class="nf-command-label">{zh() ? "命令" : "Command"}</span><kbd>⌘K</kbd></button>
          <A class="wui-button wui-button--ghost wui-button--icon" href="/settings" aria-label={zh() ? "设置" : "Settings"}><StudioIcon name="settings" class="nf-control-icon" /></A>
          <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setTheme(!dark())} aria-label={zh() ? "主题" : "Theme"}><StudioIcon name={dark() ? "sun" : "moon"} class="nf-control-icon" /></button>
          <button class="wui-button wui-button--ghost" type="button" onClick={() => setLocale(locale() === "en-US" ? "zh-CN" : "en-US")}>{locale() === "en-US" ? "中文" : "EN"}</button>
        </div></header>
        <main class="nf-content" id="main-content">{props.children}</main>
        <footer class="nf-footer"><span>Quillframe Core is the source of truth</span><span aria-hidden="true">·</span><span>persistence ≠ settlement</span></footer>
      </div>

      <Show when={aiOpen()}><aside class="nf-global-ai-dock" aria-label={zh() ? "AI 助手" : "AI Assistant"><div class="nf-ai-dock-heading"><div><span class="nf-eyebrow">AI ASSISTANT</span><h2>{zh() ? "项目助手" : "Project assistant"}</h2></div><button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setAiOpen(false)} aria-label={zh() ? "关闭" : "Close"}>×</button></div><p class="nf-subtle">{currentProject() || (zh() ? "没有当前 Project" : "No current project")}</p><select value={aiMode()} onChange={(event) => setAiMode(event.currentTarget.value)}><option>RESEARCH</option><option>AUDIT</option><option>DRAFT</option><option>REVISE</option></select><textarea value={aiInstruction()} onInput={(event) => setAiInstruction(event.currentTarget.value)} placeholder={zh() ? "描述任务；实际 Context 由 Core 决定。" : "Describe the task; Core owns actual Context selection."} /><button class="wui-button" type="button" disabled={aiBusy() || !currentProject() || !aiInstruction().trim()} onClick={() => void runAssistant()}>{aiBusy() ? (zh() ? "启动中…" : "Starting…") : (zh() ? "启动 Core Run" : "Start Core run")}</button><Show when={aiStatus()}><div class="nf-run-state"><strong>{aiStatus()}</strong><p>{zh() ? "若 production semantic worker 尚未绑定，状态会保持 semantic_pending；Studio 不会显示伪造的 Candidate。" : "If the production semantic worker is not bound, the run remains semantic_pending; Studio does not fabricate a Candidate."}</p></div></Show></aside></Show>

      <nav class="wui-bottom-nav nf-bottom-nav" aria-label={zh() ? "移动导航" : "Mobile navigation"}><For each={[creatorNavigation[0], creatorNavigation[1], creatorNavigation[4], creatorNavigation[7]]}>{(entry) => <A href={entry.path + (currentProject() && entry.path !== "/" ? `?project=${encodeURIComponent(currentProject())}` : "")} class="wui-bottom-nav__item nf-bottom-nav-item" data-active={navActive(entry.path) ? "true" : undefined}><span class="wui-bottom-nav__icon" aria-hidden="true"><StudioIcon name={entry.icon} /></span><small class="wui-bottom-nav__label">{label(entry)}</small></A>}</For></nav>

      <Show when={paletteOpen()}><div class="wui-command-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setPaletteOpen(false)}><section class="wui-command nf-command" role="dialog" aria-modal="true" aria-label={zh() ? "命令" : "Command palette"}><div class="wui-command__input-wrapper"><span class="wui-command__icon" aria-hidden="true"><StudioIcon name="search" /></span><input class="wui-command__input" autofocus value={query()} onInput={(event) => setQuery(event.currentTarget.value)} placeholder={zh() ? "搜索页面或 Core operation…" : "Search pages or Core operations…"} /></div><div class="wui-command__list"><div class="wui-command__group-label">{zh() ? "创作" : "Authoring"}</div><For each={creatorNavigation.filter((entry) => matches(`${entry.path} ${entry.en} ${entry.zh}`))}>{(entry) => <button type="button" class="wui-command__item" onClick={() => go(entry.path)}><span class="wui-command__item-icon"><StudioIcon name={entry.icon} /></span><span class="wui-command__item-label">{label(entry)}</span></button>}</For><div class="wui-command__group-label">Core operations</div><For each={supported().filter(matches)}>{(operation) => <button type="button" class="wui-command__item" onClick={() => go(operationRoute[operation] ?? "/inspect")}><span class="wui-command__item-icon"><StudioIcon name="check" /></span><span class="wui-command__item-label">{operation}</span></button>}</For><div class="wui-command__group-label">Deferred · truthful</div><For each={deferred().filter(([operation]) => matches(operation))}>{([operation, reason]) => <div class="wui-command__item" data-disabled title={reason}><span class="wui-command__item-icon"><StudioIcon name="minus" /></span><span class="wui-command__item-label">{operation}</span><span class="wui-command__item-shortcut">deferred</span></div>}</For></div></section></div></Show>
    </div>
  );
};
