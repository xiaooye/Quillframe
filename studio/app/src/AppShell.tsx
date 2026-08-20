import { For, Show, createMemo, createSignal, onCleanup, onMount, ParentComponent } from "solid-js";
import { Portal } from "solid-js/web";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { useI18n } from "./i18n";
import { useStudio } from "./studio";
import { StudioIcon, type StudioIconName } from "./StudioIcon";
import { invokeBridge, operationError } from "./bridge";
import {
  AUTHORING_INTENT_TASK_MODE,
  type AuthorRunStartResult,
  type AuthorRunStatusProjection,
  type WorkflowRunEvent,
  type WorkflowRunEventBatch,
  type AuthoringIntent,
  type ContextRuntimeProjection,
  type ModelServiceListProjection,
  type ProductionExecutionProjection,
} from "./authoring/contracts";
import { CoreRequirementNotice, RunProgress, WriterContextStrip } from "./authoring/AuthoringUI";
import { createModalA11y } from "./modalA11y";

type NavEntry = { path: string; en: string; zh: string; icon: StudioIconName; project?: boolean };

const primaryNavigation: NavEntry[] = [
  { path: "/start", en: "Start", zh: "开始", icon: "home" },
  { path: "/manuscript", en: "Write", zh: "写作", icon: "workspace", project: true },
  { path: "/review", en: "Review", zh: "审阅", icon: "check", project: true },
  { path: "/publication", en: "Publish", zh: "发布", icon: "project", project: true },
];

const supportNavigation: NavEntry[] = [
  { path: "/plan", en: "Plan", zh: "计划", icon: "project", project: true },
  { path: "/story", en: "Story", zh: "故事", icon: "semantic", project: true },
  { path: "/research", en: "Research", zh: "研究", icon: "search", project: true },
];

const advancedNavigation: NavEntry[] = [
  { path: "/", en: "Desk", zh: "书桌", icon: "home" },
  { path: "/learning", en: "Learning", zh: "学习", icon: "agents", project: true },
  { path: "/runtime", en: "Sessions & Runs", zh: "会话与运行", icon: "runtime", project: true },
  { path: "/context", en: "Context", zh: "Context", icon: "context", project: true },
  { path: "/capabilities", en: "Capabilities", zh: "能力", icon: "capabilities" },
  { path: "/diagnostics", en: "Diagnostics", zh: "诊断", icon: "diagnostics" },
  { path: "/architecture", en: "Architecture", zh: "架构", icon: "runtime" },
];

const routeByOperation: Record<string, string> = {
  "project.create": "/start",
  "project.list": "/start",
  "project.inspect": "/",
  "document.create": "/manuscript",
  "document.list": "/manuscript",
  "document.open": "/manuscript",
  "document.revision.save": "/manuscript",
  "document.revision.compare": "/manuscript",
  "author.run.start": "/manuscript",
  "author.run.status": "/runtime",
  "author.run.execute": "/manuscript",
  "inspector.context.runtime": "/context",
  "inspector.runs.list": "/runtime",
  "inspector.candidates.list": "/review",
  "candidate.review.get": "/review",
  "candidate.accept": "/review",
  "candidate.reject": "/review",
  "candidate.revision.request": "/review",
  "settlement.preflight": "/review",
  "settlement.apply": "/review",
  "model.service.add": "/settings?section=models",
  "model.service.list": "/settings?section=models",
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
  const [authorProfile, setAuthorProfile] = createSignal<"guided" | "expert">("guided");
  const [instruction, setInstruction] = createSignal("");
  const [run, setRun] = createSignal<AuthorRunStartResult>();
  const [runStatus, setRunStatus] = createSignal("");
  const [productionStatus, setProductionStatus] = createSignal<string>();
  const [readerGrip, setReaderGrip] = createSignal<"low" | "medium" | "high" | "very_high">("high");
  const [contextProjection, setContextProjection] = createSignal<ContextRuntimeProjection>();
  const [aiError, setAiError] = createSignal<string>();
  const [aiBusy, setAiBusy] = createSignal(false);
  const [workflowCursor, setWorkflowCursor] = createSignal(-1);
  let paletteDialog: HTMLElement | undefined;
  let paletteInput: HTMLInputElement | undefined;

  const requestPaletteClose = () => {
    setQuery("");
    setPaletteOpen(false);
  };
  const paletteA11y = createModalA11y({
    getDialog: () => paletteDialog,
    getBackground: () => document.getElementById("app") ?? undefined,
    requestClose: requestPaletteClose,
    getInitialFocus: () => paletteInput,
    getFallbackFocus: () => document.querySelector<HTMLElement>(".nf-command-trigger") ?? undefined,
  });
  const openPalette = (trigger?: HTMLElement) => {
    if (paletteOpen()) return;
    if (aiOpen()) setAiOpen(false);
    paletteA11y.open(trigger);
    setPaletteOpen(true);
  };
  const closePalette = () => paletteA11y.close();
  const toggleAiDock = () => {
    if (paletteOpen()) {
      closePalette();
      return;
    }
    setAiOpen((open) => !open);
  };
  onCleanup(() => paletteA11y.dispose());

  const capabilities = () => studio.bridgeCapabilities();
  const supported = createMemo(() => capabilities()?.operations ?? []);
  const currentProject = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const currentDocument = () => {
    const fromUrl = new URLSearchParams(location.search).get("document")?.trim();
    if (fromUrl) return fromUrl;
    const projectId = currentProject();
    if (!projectId || typeof localStorage === "undefined") return undefined;
    return localStorage.getItem(`quillframe.ui.lastDocumentId:${projectId}`)?.trim() || undefined;
  };

  const setTheme = (next: boolean) => {
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
  };
  setTheme(dark());

  const keyHandler = (event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (paletteOpen()) closePalette();
      else openPalette();
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "i") {
      event.preventDefault();
      toggleAiDock();
    }
    if (event.key === "Escape") {
      if (paletteOpen()) closePalette();
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
          chapter_id: "CH001",
          author_profile: authorProfile(),
          instruction: instruction().trim(),
          intent: intent(),
          requested_surface: "studio_ai_assistant_dock",
        },
        idempotency_key: `studio-ai-${crypto.randomUUID()}`,
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setRun(response.data);
      setRunStatus(response.data.status);
      setWorkflowCursor(response.data.workflow?.cursor ?? -1);
      studio.setLastRunId(response.data.run_id);
    } catch (error) {
      setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      setAiBusy(false);
    }
  };

  const executeRun = async () => {
    const projectId = currentProject();
    const activeRun = run();
    const runId = activeRun?.run_id || studio.lastRunId();
    if (!projectId || !runId || !instruction().trim()) return;
    if (activeRun && !["DRAFT", "REVISE"].includes(activeRun.task_mode)) {
      setAiError(zh() ? "当前 production executor 只拥有 DRAFT / REVISE；AUDIT / RESEARCH 必须使用各自 Core contract。" : "The production executor owns DRAFT / REVISE only; AUDIT / RESEARCH require their own Core contracts.");
      return;
    }
    setAiBusy(true);
    setAiError(undefined);
    try {
      const services = await invokeBridge<ModelServiceListProjection>("model.service.list");
      if (services.status !== "ok" || !services.data) throw new Error(operationError(services));
      const service = services.data.items.find((item) => item.credential_present && item.service_id);
      if (!service?.service_id) throw new Error(zh() ? "没有带可用 credential 的 Model Service。请先到 AI 与模型连接 Endpoint + Access Token。" : "No Model Service with a usable credential is connected. Add Endpoint + Access Token in AI & Models first.");
      const response = await invokeBridge<ProductionExecutionProjection>("author.run.execute", {
        project_id: projectId,
        run_id: runId,
        service_id: service.service_id,
        instruction: instruction().trim(),
        document_id: currentDocument(),
        reader_grip: readerGrip(),
        rule_material: [{
          id: "studio-current-request",
          authority: "current_request",
          statement: instruction().trim(),
        }],
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setProductionStatus(response.data.status);
      setRunStatus(response.data.status);
      await refreshRunEvidence();
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
      if (supported().includes("author.run.status")) {
        const response = await invokeBridge<AuthorRunStatusProjection>("author.run.status", { project_id: projectId, run_id: runId });
        if (response.status === "ok" && response.data) setRunStatus(response.data.status);
      }
      if (supported().includes("author.run.events")) {
        const response = await invokeBridge<WorkflowRunEventBatch>("author.run.events", { run_id: runId, cursor: workflowCursor() });
        if (response.status === "ok" && response.data) {
          setWorkflowCursor(response.data.next_cursor);
          const last = response.data.events.at(-1);
          if (last?.event_type) setRunStatus(last.event_type);
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

  const resumeRun = async () => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    if (!projectId || !runId) return;
    setAiBusy(true); setAiError(undefined);
    try {
      const response = await invokeBridge<WorkflowRunEvent>("author.run.resume", {
        project_id: projectId,
        run_id: runId,
        cursor: workflowCursor(),
        idempotency_key: `studio-resume-${crypto.randomUUID()}`,
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setRunStatus(response.data.event_type);
      setWorkflowCursor(response.data.cursor);
    } catch (error) {
      setAiError(error instanceof Error ? error.message : String(error));
    } finally { setAiBusy(false); }
  };

  const cancelRun = async () => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    if (!projectId || !runId) return;
    setAiBusy(true); setAiError(undefined);
    try {
      const response = await invokeBridge<WorkflowRunEvent>("author.run.cancel", {
        project_id: projectId,
        run_id: runId,
        cursor: workflowCursor(),
        idempotency_key: `studio-cancel-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setRunStatus(response.data.event_type);
      setWorkflowCursor(response.data.cursor);
    } catch (error) {
      setAiError(error instanceof Error ? error.message : String(error));
    } finally { setAiBusy(false); }
  };

  const go = (path: string) => {
    closePalette();
    const entry = [...primaryNavigation, ...supportNavigation, ...advancedNavigation].find((item) => item.path === path);
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
          <span class="wui-sidebar__brand-label"><strong>Quillframe</strong><small>Writer Mode · 1.0 preview</small></span>
        </A>
        <nav class="wui-sidebar__content nf-nav-list">
          <div class="nf-nav-section" data-nav-tier="primary"><small class="nf-nav-tier-label">{zh() ? "创作流程" : "AUTHOR FLOW"}</small>{renderNav(primaryNavigation)}</div>
          <div class="nf-nav-section" data-nav-tier="support"><small class="nf-nav-tier-label">{zh() ? "故事支持" : "STORY SUPPORT"}</small>{renderNav(supportNavigation)}</div>
          <button class="qf-inspector-disclosure" type="button" aria-expanded={inspectorOpen()} onClick={() => setInspectorOpen((open) => !open)}>
            <span>{zh() ? "高级与检查" : "Advanced & Inspect"}</span><span aria-hidden="true">{inspectorOpen() ? "−" : "+"}</span>
          </button>
          <Show when={inspectorOpen()}><div class="nf-nav-section" data-nav-tier="advanced">{renderNav(advancedNavigation)}</div></Show>
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
            <Show when={studio.projectProjection()?.manifest} fallback={<A href="/start">{zh() ? "新建 / 打开 Project" : "New / Open Project"}</A>}>
              {(project) => <strong>{project().title}</strong>}
            </Show>
          </div>
          <div class="wui-app-bar__actions nf-topbar-actions">
            <span class="wui-badge wui-badge--outline nf-host-chip" data-surface={studio.surface()} title={studio.transportName()}>
              <span class="nf-host-dot" aria-hidden="true" />
              <span>{studio.bridgeAvailable() ? (zh() ? "Core 已绑定" : "Core bound") : (zh() ? "Core 未绑定" : "Core unbound")}</span>
            </span>
            <button class="wui-button wui-button--outline qf-ai-toggle" type="button" onClick={toggleAiDock} aria-expanded={aiOpen()} aria-controls="qf-ai-dock">
              <StudioIcon name="agents" class="nf-control-icon" /><span>AI</span><kbd>⌘I</kbd>
            </button>
            <button class="wui-button wui-button--outline nf-command-trigger" type="button" onClick={(event) => openPalette(event.currentTarget)} aria-label={zh() ? "命令面板" : "Command palette"}>
              <StudioIcon name="command" class="nf-control-icon" /><span class="nf-command-label">{zh() ? "命令" : "Command"}</span><kbd>⌘K</kbd>
            </button>
            <A class="wui-button wui-button--ghost wui-button--icon" href="/settings" aria-label={zh() ? "设置" : "Settings"}><StudioIcon name="settings" class="nf-control-icon" /></A>
            <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setTheme(!dark())} aria-label={zh() ? "切换主题" : "Toggle theme"}><StudioIcon name={dark() ? "sun" : "moon"} class="nf-control-icon" /></button>
            <button class="wui-button wui-button--ghost" type="button" onClick={() => setLocale(locale() === "en-US" ? "zh-CN" : "en-US")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{locale() === "en-US" ? "中文" : "EN"}</button>
          </div>
        </header>
        <main class="nf-content qf-writer-content" id="main-content" tabIndex={-1}>{props.children}</main>
      </div>

      <Show when={aiOpen()}>
        <aside id="qf-ai-dock" class="qf-ai-dock" aria-label={zh() ? "AI Assistant Dock" : "AI Assistant Dock"}>
          <header class="qf-ai-dock__header">
            <div><span class="nf-eyebrow">AI ASSISTANT</span><h2>{zh() ? "项目助手" : "Project assistant"}</h2></div>
            <button class="wui-button wui-button--ghost wui-button--icon" type="button" onClick={() => setAiOpen(false)} aria-label={zh() ? "关闭 AI 助手" : "Close AI Assistant"}>×</button>
          </header>
          <p class="qf-ai-dock__boundary">{zh() ? "这是 Quillframe Agent surface，不是 provider chat。Context、执行与审查由 Core 决定。" : "This is a Quillframe Agent surface, not a provider chat. Core owns Context, execution and review."}</p>
          <div class="qf-inline-actions qf-ai-scope-row"><span class="wui-badge wui-badge--outline">CH001</span><label class="nf-field-label"><span>{zh() ? "协作模式" : "Author profile"}</span><select class="wui-input" value={authorProfile()} onChange={(event) => setAuthorProfile(event.currentTarget.value as "guided" | "expert")}><option value="guided">{zh() ? "引导模式" : "Guided"}</option><option value="expert">{zh() ? "专家模式" : "Expert"}</option></select></label></div>
          <label class="nf-field-label"><span>{zh() ? "意图" : "Intent"}</span><select class="wui-input" value={intent()} onChange={(event) => setIntent(event.currentTarget.value as AuthoringIntent)}><option value="write">{zh() ? "写作 · DRAFT" : "Write · DRAFT"}</option><option value="revise">{zh() ? "修改 · REVISE" : "Revise · REVISE"}</option><option value="review">{zh() ? "审阅 · AUDIT" : "Review · AUDIT"}</option><option value="continuity">{zh() ? "连续性 · AUDIT" : "Continuity · AUDIT"}</option><option value="research">{zh() ? "研究 · RESEARCH" : "Research · RESEARCH"}</option></select></label>
          <label class="nf-field-label"><span>{zh() ? "任务" : "Task"}</span><textarea class="wui-input qf-ai-instruction" value={instruction()} onInput={(event) => setInstruction(event.currentTarget.value)} placeholder={zh() ? "描述你要完成的创作任务。不要手工拼 Context。" : "Describe the authoring task. Do not hand-assemble Context."} /></label>
          <div class="qf-inline-actions">
            <button class="wui-button wui-button--solid" type="button" disabled={aiBusy() || !currentProject() || !instruction().trim() || !supported().includes("author.run.start")} onClick={() => void startRun()}>{aiBusy() ? (zh() ? "处理中…" : "Working…") : (zh() ? "注册 Core Run" : "Register Core run")}</button>
            <button class="wui-button wui-button--outline" type="button" disabled={aiBusy() || !(run()?.run_id || studio.lastRunId()) || !instruction().trim() || !supported().includes("author.run.execute") || !supported().includes("model.service.list")} onClick={() => void executeRun()}>{zh() ? "Execute production" : "Execute production"}</button>
          </div>
          <label class="nf-field-label"><span>{zh() ? "Reader grip（本次请求）" : "Reader grip (this request)"}</span><select class="wui-input" value={readerGrip()} onChange={(event) => setReaderGrip(event.currentTarget.value as "low" | "medium" | "high" | "very_high")}><option value="medium">medium</option><option value="high">high</option><option value="very_high">very_high</option><option value="low">low</option></select></label>
          <CoreRequirementNotice operation="author.run.start" compact />
          <CoreRequirementNotice operation="author.run.execute" compact />
          <Show when={aiError()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Agent</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
          <Show when={run() || studio.lastRunId()}>
            <section class="qf-ai-run" aria-live="polite">
              <div class="qf-ai-run__identity"><div><span>{zh() ? "Run" : "Run"}</span><code>{run()?.run_id || studio.lastRunId()}</code></div><strong>{runStatus() || run()?.status || "unknown"}</strong></div>
              <Show when={run()?.message}><p>{run()?.message}</p></Show>
              <RunProgress waiting zh={zh()} />
              <button class="wui-button wui-button--outline" type="button" disabled={aiBusy()} onClick={() => void refreshRunEvidence()}>{zh() ? "刷新 Core evidence" : "Refresh Core evidence"}</button>
              <div class="qf-inline-actions"><button class="wui-button wui-button--outline" type="button" disabled={aiBusy() || !supported().includes("author.run.resume")} onClick={() => void resumeRun()}>{zh() ? "恢复" : "Resume"}</button><button class="wui-button wui-button--ghost" type="button" disabled={aiBusy() || !supported().includes("author.run.cancel")} onClick={() => void cancelRun()}>{zh() ? "取消运行" : "Cancel run"}</button></div>
              <CoreRequirementNotice operation="author.run.status" compact />
              <Show when={productionStatus() === "awaiting_external"}><p class="qf-success-note">{zh() ? "已到真实 independent handoff boundary；Studio 不会用同一 runtime 自审替代外部独立审查。" : "Reached the real independent handoff boundary; Studio will not substitute same-runtime self-review for external independent review."}</p></Show>
              <WriterContextStrip projection={contextProjection()} zh={zh()} />
            </section>
          </Show>
        </aside>
      </Show>

      <nav class="wui-bottom-nav nf-bottom-nav qf-writer-bottom-nav" aria-label={zh() ? "Writer Mode 移动导航" : "Writer Mode mobile navigation"}>
        <For each={primaryNavigation}>
          {(entry) => <A href={projectHref(entry, currentProject())} class="wui-bottom-nav__item nf-bottom-nav-item" data-active={active(entry.path) ? "true" : undefined} aria-current={active(entry.path) ? "page" : undefined}><span class="wui-bottom-nav__icon" aria-hidden="true"><StudioIcon name={entry.icon} /></span><small class="wui-bottom-nav__label">{label(entry)}</small></A>}
        </For>
      </nav>

      <Show when={paletteOpen()}>
        <Portal>
          <div class="wui-command-overlay" role="presentation" onMouseDown={(event) => paletteA11y.onOutsidePointer(event)}>
            <section ref={(element) => { paletteDialog = element; }} class="wui-command nf-command" role="dialog" aria-modal="true" aria-labelledby="studio-command-heading" tabIndex={-1} onKeyDown={paletteA11y.onKeyDown}>
            <h2 id="studio-command-heading" class="wui-sr-only">{zh() ? "命令面板" : "Command palette"}</h2>
            <div class="wui-command__input-wrapper"><span class="wui-command__icon" aria-hidden="true"><StudioIcon name="search" /></span><input ref={(element) => { paletteInput = element; }} class="wui-command__input" value={query()} onInput={(event) => setQuery(event.currentTarget.value)} placeholder={zh() ? "搜索页面或 Core operation…" : "Search pages or Core operations…"} /></div>
            <div class="wui-command__list">
              <div class="wui-command__group-label">Author flow</div>
              <For each={[...primaryNavigation, ...supportNavigation, ...advancedNavigation].filter((entry) => matches(`${entry.path} ${entry.en} ${entry.zh}`))}>{(entry) => <button type="button" class="wui-command__item" onClick={() => go(entry.path)}><span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name={entry.icon} /></span><span class="wui-command__item-label">{label(entry)}</span></button>}</For>
              <div class="wui-command__group-label">Core operations</div>
              <For each={supported().filter(matches)}>{(operation) => <button type="button" class="wui-command__item" onClick={() => go(routeByOperation[operation] ?? "/runtime")}><span class="wui-command__item-icon" aria-hidden="true"><StudioIcon name="check" /></span><span class="wui-command__item-label">{operation}</span></button>}</For>
              <Show when={q() && ![...primaryNavigation, ...supportNavigation, ...advancedNavigation].some((entry) => matches(`${entry.path} ${entry.en} ${entry.zh}`)) && !supported().some(matches)}><div class="wui-command__empty">{zh() ? "没有匹配项" : "No matches"}</div></Show>
            </div>
            </section>
          </div>
        </Portal>
      </Show>
    </div>
  );
};
