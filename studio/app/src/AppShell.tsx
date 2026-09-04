import { For, Show, createEffect, createMemo, createSignal, on, onCleanup, onMount, ParentComponent } from "solid-js";
import { Portal } from "solid-js/web";
import { A, useLocation, useNavigate } from "@solidjs/router";
import { useI18n } from "./i18n";
import { useStudio } from "./studio";
import { HostedAccountButton } from "./HostedSessionBoundary";
import { StudioIcon, type StudioIconName } from "./StudioIcon";
import { invokeBridge, operationError } from "./bridge";
import {
  AUTHORING_INTENT_TASK_MODE,
  connectedModelService,
  pendingIndependentReview,
  projectExecutionJournal,
  projectRepairSource,
  type AuthorRunStartResult,
  type AuthorRunStatusProjection,
  type FailedCandidateRepairSource,
  type WorkflowRunEvent,
  type WorkflowRunEventBatch,
  type AuthoringIntent,
  type ContextRuntimeProjection,
  type ModelServiceListProjection,
  type ProductionExecutionProjection,
} from "./authoring/contracts";
import { CoreRequirementNotice, WriterContextStrip } from "./authoring/AuthoringUI";
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
  "chapter.list": "/manuscript",
  "chapter.create": "/manuscript",
  "plan.inspect": "/plan",
  "plan.save": "/plan",
  "story.inspect": "/story",
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
  "publication.artifact.get": "/publication",
  "publication.collection.build": "/publication",
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
  const [productionExecution, setProductionExecution] = createSignal<ProductionExecutionProjection>();
  const [runEvidence, setRunEvidence] = createSignal<AuthorRunStatusProjection>();
  const [readerGrip, setReaderGrip] = createSignal<"low" | "medium" | "high" | "very_high">("high");
  const [contextProjection, setContextProjection] = createSignal<ContextRuntimeProjection>();
  const [aiError, setAiError] = createSignal<string>();
  const [aiBusy, setAiBusy] = createSignal(false);
  const [controlBusy, setControlBusy] = createSignal(false);
  const [executionPending, setExecutionPending] = createSignal(false);
  const [workflowCursor, setWorkflowCursor] = createSignal(-1);
  const [workflowEvents, setWorkflowEvents] = createSignal<WorkflowRunEvent[]>([]);
  let aiGeneration = 0;
  let controlGeneration = 0;
  let executionGeneration = 0;
  let startIntent: { binding: string; idempotency_key: string } | undefined;
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
  const currentChapter = () => studio.projectId() === currentProject() ? studio.selectedChapter() : undefined;
  const currentDocument = () => currentChapter()?.document_id;
  const beginAiRequest = () => {
    const generation = ++aiGeneration;
    const projectId = currentProject(); const chapterId = currentChapter()?.chapter_id;
    return () => generation === aiGeneration && projectId === currentProject() && chapterId === currentChapter()?.chapter_id;
  };
  createEffect(on(currentProject, (projectId) => { if (projectId && studio.projectId() !== projectId) void studio.inspectProject(projectId); }));
  const resetRunView = () => {
    aiGeneration += 1; setRun(undefined); setRunStatus(""); setRunEvidence(undefined); setProductionExecution(undefined);
    controlGeneration += 1; executionGeneration += 1; setControlBusy(false); setExecutionPending(false);
    setContextProjection(undefined); setWorkflowCursor(-1); setWorkflowEvents([]); setAiError(undefined); setAiBusy(false);
    startIntent = undefined;
  };
  createEffect(on([currentProject, () => currentChapter()?.chapter_id], resetRunView));
  createEffect(on(() => studio.lastRunId(), (selectedRunId) => {
    if (selectedRunId !== run()?.run_id) resetRunView();
  }));
  onCleanup(() => { aiGeneration += 1; controlGeneration += 1; executionGeneration += 1; });
  const pendingReview = createMemo(() => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    const evidence = runEvidence();
    return pendingIndependentReview({
      project_id: projectId,
      run_id: runId,
      status: runStatus(),
      events: evidence?.project_id === projectId && evidence.run_id === runId ? evidence.events : [],
    }, productionExecution());
  });
  const executionJournal = createMemo(() => projectExecutionJournal(runEvidence(), {
    project_id: currentProject(), run_id: run()?.run_id || studio.lastRunId(), document_id: currentDocument() ?? "",
  }));
  const repairSource = createMemo(() => projectRepairSource(runEvidence(), {
    project_id: currentProject(), run_id: run()?.run_id || studio.lastRunId(), document_id: currentDocument() ?? "",
  }));
  const isRepairRun = () => (run()?.task_mode || runEvidence()?.task_mode) === "REVISE";
  const executionRoleLabel = (role: string) => {
    const labels: Record<string, [string, string]> = {
      context_profile_deriver: ["准备上下文摘要", "Prepare context profiles"],
      character_state_prepare: ["准备人物状态", "Prepare character state"],
      registered_character_action: ["推演人物行动", "Resolve character action"],
      registered_scene_resolution: ["推演场景变化", "Resolve scene changes"],
      registered_scene_projection: ["整理场景结果", "Project scene outcome"],
      registered_reader_pressure: ["检查读者期待", "Inspect reader expectations"],
      story_canon_preflight: ["核对故事事实", "Check story facts"],
      character_simulation: ["推演人物行动", "Resolve character action"],
      scene_simulation: ["推演场景变化", "Resolve scene changes"],
      reader_pressure: ["检查读者期待", "Inspect reader expectations"],
      reader_engagement: ["读者视角审阅", "Review reader engagement"],
      continuity: ["核对连续性", "Check continuity"],
      event_first_raw_draft: ["旧版内部草稿（已退役）", "Legacy internal draft (retired)"],
      surface_realization: ["形成正文表达", "Realize manuscript prose"],
      registered_reader_engagement: ["读者视角审阅", "Review reader engagement"],
      registered_candidate_self_audit: ["检查候选稿", "Audit candidate draft"],
      registered_repair_editor: ["制定修订与保留方案", "Plan repair and preservation"],
      registered_repair_comparison: ["对比缺陷修复与目标保留", "Compare repair and preservation"],
      registered_reader_expectations: ["提议读者期待变化", "Propose expectation changes"],
      registered_narrative_state: ["提议故事状态变化", "Propose narrative state changes"],
    };
    return labels[role]?.[zh() ? 0 : 1] ?? role;
  };
  const executionCallStateLabel = (state: string) => {
    const labels: Record<string, [string, string]> = {
      dispatched: ["已发出，等待确认", "Dispatched; awaiting confirmation"],
      confirmed: ["结果已确认", "Result confirmed"],
      unconfirmed: ["结果未确认", "Result unconfirmed"],
      cancelled: ["已取消", "Cancelled"],
    };
    return labels[state]?.[zh() ? 0 : 1] ?? state;
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

  const startRun = async (repair?: FailedCandidateRepairSource) => {
    const projectId = currentProject();
    const chapter = currentChapter();
    if (!projectId || !chapter || !repair && !instruction().trim() || executionPending() || controlBusy()) return;
    if (!repair && intent() === "revise") {
      setAiError(zh() ? "请刷新失败运行，再选择“修订此版本”，以绑定原稿和诊断。" : "Refresh the failed run, then choose Repair this version to bind its exact draft and diagnosis.");
      return;
    }
    const requestedIntent = repair ? "revise" : intent();
    const selectedPreferenceIds = [...studio.selectedPreferenceIds()];
    const current = beginAiRequest();
    const binding = JSON.stringify({ projectId, chapter, intent: requestedIntent, profile: authorProfile(), instruction: instruction().trim(), selectedPreferenceIds, repair });
    if (!startIntent || startIntent.binding !== binding) startIntent = { binding, idempotency_key: `studio-ai-${crypto.randomUUID()}` };
    setAiBusy(true);
    setAiError(undefined);
    setRun(undefined);
    setRunStatus("");
    setProductionExecution(undefined);
    setRunEvidence(undefined);
    setContextProjection(undefined);
    try {
      const response = await invokeBridge<AuthorRunStartResult>("author.run.start", {
        project_id: projectId,
        task_mode: AUTHORING_INTENT_TASK_MODE[requestedIntent],
        target_ref: chapter.document_id,
        payload: {
          chapter_id: chapter.chapter_id,
          author_profile: authorProfile(),
          instruction: instruction().trim(),
          reader_grip: readerGrip(),
          rule_material: [{ id: "studio-current-request", authority: "current_request", statement: instruction().trim() }],
          intent: requestedIntent,
          ...(repair ? { repair_source: repair } : { selected_preference_ids: selectedPreferenceIds }),
          requested_surface: "studio_ai_assistant_dock",
        },
        idempotency_key: startIntent.idempotency_key,
      });
      if (!current()) return;
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      if (response.data.target_ref !== chapter.document_id || !response.data.run_id || response.data.raw_draft_visible !== false || response.data.candidate_visible !== false) throw new Error("run_start_binding_invalid");
      setRun(response.data);
      if (repair) setIntent("revise");
      setRunStatus(response.data.status);
      setWorkflowCursor(response.data.workflow?.cursor ?? -1);
      studio.setLastRunId(response.data.run_id);
      startIntent = undefined;
    } catch (error) {
      if (current()) setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      if (current()) setAiBusy(false);
    }
  };

  const executeRun = async () => {
    const projectId = currentProject();
    const activeRun = run();
    const runId = activeRun?.run_id || studio.lastRunId();
    const chapter = currentChapter();
    if (!projectId || !chapter || !runId || !isRepairRun() && !instruction().trim() || executionPending() || controlBusy()) return;
    const current = beginAiRequest();
    const requestedInstruction = instruction().trim();
    const requestedGrip = readerGrip();
    if (activeRun && !["DRAFT", "REVISE"].includes(activeRun.task_mode)) {
      setAiError(zh() ? "当前 production executor 只拥有 DRAFT / REVISE；AUDIT / RESEARCH 必须使用各自 Core contract。" : "The production executor owns DRAFT / REVISE only; AUDIT / RESEARCH require their own Core contracts.");
      return;
    }
    setAiBusy(true);
    const executionRequest = ++executionGeneration;
    setExecutionPending(true);
    setAiError(undefined);
    try {
      const status = await invokeBridge<AuthorRunStatusProjection>("author.run.status", { project_id: projectId, run_id: runId });
      if (!current()) return;
      if (status.status !== "ok" || !status.data) throw new Error(operationError(status));
      if (status.data.project_id !== projectId || status.data.run_id !== runId || status.data.target_ref !== chapter.document_id
        || !["DRAFT", "REVISE"].includes(status.data.task_mode)) throw new Error("run_chapter_binding_invalid");
      const services = await invokeBridge<ModelServiceListProjection>("model.service.list");
      if (!current()) return;
      if (services.status !== "ok" || !services.data) throw new Error(operationError(services));
      const selectedModel = studio.selectedModel();
      const service = selectedModel
        ? services.data.items.find((item) => item.service_id === selectedModel.serviceId
          && (item.enabled === true || item.enabled === 1)
          && item.discovery_state === "connected"
          && item.models?.some((model) => model.model_id === selectedModel.modelId))
        : connectedModelService(services.data.items);
      if (!service?.service_id) throw new Error(selectedModel
        ? (zh() ? "所选模型已不可用；请到 AI 与模型重新选择。" : "The selected model is no longer available; choose another model in AI & Models.")
        : (zh() ? "没有已启用且已连接的 Model Service。请先到 AI 与模型连接服务；无需认证的本地服务可留空 Access Token。" : "No enabled, connected Model Service is available. Connect one in AI & Models; local services without authentication may leave Access Token empty."));
      const response = await invokeBridge<ProductionExecutionProjection>("author.run.execute", {
        project_id: projectId,
        run_id: runId,
        service_id: service.service_id,
        ...(selectedModel ? { model_id: selectedModel.modelId } : {}),
        document_id: chapter.document_id,
        ...(status.data.task_mode === "REVISE" ? { inherit_repair_request: true } : {
          instruction: requestedInstruction,
          reader_grip: requestedGrip,
          rule_material: [{ id: "studio-current-request", authority: "current_request", statement: requestedInstruction }],
        }),
      });
      if (!current()) return;
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      if (response.data.project_id !== projectId || response.data.run_id !== runId || response.data.raw_draft_visible !== false) throw new Error("run_execution_binding_invalid");
      setProductionExecution(response.data);
      setRunEvidence(undefined);
      setRunStatus(response.data.status);
      await refreshRunEvidence();
    } catch (error) {
      if (current()) setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      if (executionRequest === executionGeneration) setExecutionPending(false);
      if (current()) setAiBusy(false);
    }
  };

  const refreshRunEvidence = async () => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    if (!projectId || !runId) return;
    const current = beginAiRequest();
    setAiBusy(true);
    setAiError(undefined);
    try {
      if (supported().includes("author.run.status")) {
        const response = await invokeBridge<AuthorRunStatusProjection>("author.run.status", { project_id: projectId, run_id: runId });
        if (!current()) return;
        if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
        if (response.status === "ok" && response.data) {
          if (response.data.project_id !== projectId || response.data.run_id !== runId || response.data.target_ref !== currentDocument()) throw new Error("run_status_binding_invalid");
          setRunEvidence(response.data);
          setRunStatus(response.data.status);
        }
      }
      if (supported().includes("author.run.events")) {
        const response = await invokeBridge<WorkflowRunEventBatch>("author.run.events", { project_id: projectId, run_id: runId, cursor: workflowCursor() });
        if (!current()) return;
        if (response.status === "ok" && response.data) {
          if (response.data.project_id !== projectId || response.data.run_id !== runId || response.data.authority !== false
            || response.data.events.some((event) => event.project_id !== projectId || event.run_id !== runId || event.chapter_id !== currentChapter()?.chapter_id || event.authority !== false)) throw new Error("run_events_binding_invalid");
          setWorkflowEvents((existing) => [...existing, ...response.data!.events.filter((event) => !existing.some((row) => row.cursor === event.cursor))]);
          setWorkflowCursor(response.data.next_cursor);
        }
      }
      if (supported().includes("inspector.context.runtime")) {
        const response = await invokeBridge<ContextRuntimeProjection>("inspector.context.runtime", { project_id: projectId, run_id: runId });
        if (!current()) return;
        if (response.status === "ok" && response.data) setContextProjection(response.data);
      }
    } catch (error) {
      if (current()) setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      if (current()) setAiBusy(false);
    }
  };

  const resumeRun = async () => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    if (!projectId || !runId || controlBusy() || executionPending() || executionJournal()?.active_executor === true || executionJournal()?.run_status === "failed_gate") return;
    const current = beginAiRequest();
    const controlRequest = ++controlGeneration;
    setControlBusy(true);
    setAiBusy(true); setAiError(undefined);
    try {
      const response = await invokeBridge<WorkflowRunEvent>("author.run.resume", {
        project_id: projectId,
        run_id: runId,
        cursor: workflowCursor(),
        idempotency_key: `studio-resume-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (!current()) return;
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      if (response.data.project_id !== projectId || response.data.run_id !== runId || response.data.chapter_id !== currentChapter()?.chapter_id
        || !Number.isSafeInteger(response.data.cursor) || response.data.authority !== false) throw new Error("run_resume_binding_invalid");
      setWorkflowCursor(response.data.cursor);
      await refreshRunEvidence();
    } catch (error) {
      if (current()) setAiError(error instanceof Error ? error.message : String(error));
    } finally { if (controlRequest === controlGeneration) setControlBusy(false); if (current()) setAiBusy(false); }
  };

  const cancelRun = async () => {
    const projectId = currentProject();
    const runId = run()?.run_id || studio.lastRunId();
    if (!projectId || !runId || controlBusy()) return;
    const current = beginAiRequest();
    const controlRequest = ++controlGeneration;
    setControlBusy(true);
    setAiBusy(true); setAiError(undefined);
    try {
      const response = await invokeBridge<WorkflowRunEvent>("author.run.cancel", {
        project_id: projectId,
        run_id: runId,
        cursor: workflowCursor(),
        idempotency_key: `studio-cancel-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (!current()) return;
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      if (response.data.project_id !== projectId || response.data.run_id !== runId || response.data.chapter_id !== currentChapter()?.chapter_id
        || !Number.isSafeInteger(response.data.cursor) || response.data.authority !== false) throw new Error("run_cancel_binding_invalid");
      setWorkflowCursor(response.data.cursor);
      await refreshRunEvidence();
      if (controlRequest === controlGeneration && runStatus() === "cancelled") { executionGeneration += 1; setExecutionPending(false); }
    } catch (error) {
      if (current()) setAiError(error instanceof Error ? error.message : String(error));
    } finally { if (controlRequest === controlGeneration) setControlBusy(false); if (current()) setAiBusy(false); }
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
          <HostedAccountButton />
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
          <div class="qf-inline-actions qf-ai-scope-row"><span class="wui-badge wui-badge--outline">{currentChapter()?.chapter_id ?? (zh() ? "先选择章节" : "Select a chapter")}</span><label class="nf-field-label"><span>{zh() ? "协作模式" : "Author profile"}</span><select class="wui-input" value={authorProfile()} onChange={(event) => setAuthorProfile(event.currentTarget.value as "guided" | "expert")}><option value="guided">{zh() ? "引导模式" : "Guided"}</option><option value="expert">{zh() ? "专家模式" : "Expert"}</option></select></label></div>
          <Show when={currentChapter()}>{(chapter) => <p>{chapter().title} · <code>{chapter().document_id}</code></p>}</Show>
          <label class="nf-field-label"><span>{zh() ? "意图" : "Intent"}</span><select class="wui-input" value={intent()} onChange={(event) => setIntent(event.currentTarget.value as AuthoringIntent)}><option value="write">{zh() ? "写作 · DRAFT" : "Write · DRAFT"}</option><option value="revise">{zh() ? "修改 · REVISE" : "Revise · REVISE"}</option><option value="review">{zh() ? "审阅 · AUDIT" : "Review · AUDIT"}</option><option value="continuity">{zh() ? "连续性 · AUDIT" : "Continuity · AUDIT"}</option><option value="research">{zh() ? "研究 · RESEARCH" : "Research · RESEARCH"}</option></select></label>
          <label class="nf-field-label"><span>{zh() ? "任务" : "Task"}</span><textarea class="wui-input qf-ai-instruction" value={instruction()} onInput={(event) => setInstruction(event.currentTarget.value)} placeholder={zh() ? "描述你要完成的创作任务。不要手工拼 Context。" : "Describe the authoring task. Do not hand-assemble Context."} /></label>
          <details><summary>{zh() ? "下一次任务采用的项目偏好" : "Project preferences for the next run"}</summary><p>{zh() ? "只有主动选中的已启用偏好会随新任务提交。注册任务后，选择不会修改已冻结的输入。" : "Only explicitly selected active preferences accompany a new run. Changing the selection does not rewrite an already registered run."}</p><div class="qf-preference-selection"><For each={studio.projectPreferences().filter((preference) => preference.active_for_future_production)}>{(preference) => <label><input type="checkbox" disabled={aiBusy()} checked={studio.selectedPreferenceIds().includes(preference.hypothesis_id)} onChange={(event) => studio.setSelectedPreferenceIds(event.currentTarget.checked ? [...studio.selectedPreferenceIds(), preference.hypothesis_id] : studio.selectedPreferenceIds().filter((id) => id !== preference.hypothesis_id))} /><span>{preference.statement}</span></label>}</For></div><Show when={!studio.projectPreferences().some((preference) => preference.active_for_future_production)}><p>{zh() ? "暂无已启用的项目偏好。" : "No active project preferences yet."}</p></Show><Show when={studio.preferenceError()}>{(message) => <p role="alert">{message()}</p>}</Show><A href="/learning">{zh() ? "管理反馈与偏好" : "Manage feedback and preferences"}</A></details>
          <div class="qf-inline-actions">
            <button class="wui-button wui-button--solid" type="button" disabled={aiBusy() || executionPending() || controlBusy() || !currentProject() || !currentChapter() || !instruction().trim() || !supported().includes("author.run.start")} onClick={() => void startRun()}>{aiBusy() ? (zh() ? "处理中…" : "Working…") : (zh() ? "注册 Core Run" : "Register Core run")}</button>
            <button class="wui-button wui-button--outline" type="button" disabled={aiBusy() || executionPending() || controlBusy() || !currentChapter() || !(run()?.run_id || studio.lastRunId()) || !isRepairRun() && !instruction().trim() || runStatus() === "failed_gate" || !supported().includes("author.run.execute") || !supported().includes("model.service.list")} onClick={() => void executeRun()}>{zh() ? "执行生产流程" : "Execute production"}</button>
          </div>
          <Show when={repairSource()}>{(source) => <div class="qf-ai-dock__boundary"><p>{zh() ? "此版本未通过检查，正文尚未公开。修订会新建运行，绑定原稿和诊断，沿用原任务、读者目标及规则；不会重放失败运行。" : "This version failed a gate and remains private. Repair creates a new run bound to the exact draft and diagnosis, retaining the original request, reader target and rules."}</p><button class="wui-button wui-button--outline" type="button" disabled={aiBusy() || executionPending() || controlBusy() || !supported().includes("author.run.start")} onClick={() => void startRun(source())}>{zh() ? "修订此版本" : "Repair this version"}</button></div>}</Show>
          <Show when={isRepairRun()}><p class="qf-ai-dock__boundary">{zh() ? "本次修订使用 Core 冻结的原任务与规则；任务框和 Reader grip 的改动不会替换修订目标。修复后还需对比保留效果并重新审查。" : "This repair uses the original request and rules frozen by Core. Task and Reader grip edits do not replace its objectives. Repair still requires preservation comparison and fresh review."}</p></Show>
          <label class="nf-field-label"><span>{zh() ? "Reader grip（本次请求）" : "Reader grip (this request)"}</span><select class="wui-input" value={readerGrip()} onChange={(event) => setReaderGrip(event.currentTarget.value as "low" | "medium" | "high" | "very_high")}><option value="medium">medium</option><option value="high">high</option><option value="very_high">very_high</option><option value="low">low</option></select></label>
          <CoreRequirementNotice operation="author.run.start" compact />
          <CoreRequirementNotice operation="author.run.execute" compact />
          <Show when={aiError()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Agent</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
          <Show when={run() || studio.lastRunId()}>
            <section class="qf-ai-run" aria-live="polite">
              <div class="qf-ai-run__identity"><div><span>{zh() ? "Run" : "Run"}</span><code>{run()?.run_id || studio.lastRunId()}</code></div><strong>{runStatus() || run()?.status || "unknown"}</strong></div>
              <Show when={run()?.message}><p>{run()?.message}</p></Show>
              <Show when={executionJournal()}>{(journal) => <section class="qf-ai-journal" aria-label={zh() ? "Core 持久执行日志" : "Persisted Core execution journal"}>
                <h3>{zh() ? "实际调用进度" : "Recorded model calls"}</h3>
                <p class="qf-ai-dock__boundary">{zh() ? "这是最近读取的 Core 快照。点击刷新获取最新状态；调用数不是完成百分比，也不代表稿件已通过审阅。" : "This is the latest retrieved Core snapshot. Refresh for current state; call counts are not a completion percentage or review approval."}</p>
                <div class="qf-journal-counts"><div><span>{zh() ? "结果已确认" : "Confirmed results"}</span><strong>{journal().confirmed_call_count}</strong></div><div><span>{zh() ? "调用已发出" : "Calls dispatched"}</span><strong>{journal().dispatched_call_count}</strong></div><div><span>{zh() ? "调用预算上限" : "Model call budget"}</span><strong>{journal().model_call_budget ?? (zh() ? "未提供" : "Not provided")}</strong></div></div>
                <Show when={journal().latest_stage_failure}>{(failure) => <div class="qf-journal-last" role="status"><h4>{zh() ? "最近的阶段失败记录" : "Latest recorded stage failure"}</h4><code>{failure().mechanism} · {failure().code}</code><p>{failure().code === "semantic_output_invalid" ? (zh() ? "Core 已收到结果，但该阶段未通过。恢复可能复用同一结果，需要先检查错误；已确认调用数不代表阶段通过。" : "Core received a result, but the stage did not pass. Resuming may reuse the same result; inspect the error first. Confirmed call counts do not establish a stage pass.") : (zh() ? "Core 记录了此阶段错误。已确认调用不等于阶段通过；能否恢复仍由 Core 检查。" : "Core recorded this stage error. A confirmed call is not a stage pass; Core still determines whether resumption is permitted.")}</p><small>{zh() ? "这是保留的失败记录，后续状态以最新 Core 回执为准。" : "This retained failure record does not replace subsequent Core receipts."}</small></div>}</Show>
                <Show when={journal().run_status === "failed_gate"}><div class="qf-journal-last" role="status">
                  <h4>{zh() ? "Core 门禁未通过" : "Core gate did not pass"}</h4>
                  <Show when={journal().latest_gate_rejection} fallback={<p>{zh() ? "Core 已拒绝此运行；先处理阻断原因，再注册新运行。" : "Core rejected this run; resolve the blocker, then register a new run."}</p>}>{(rejection) => <><code>{rejection().mechanism}</code><p>{executionRoleLabel(rejection().mechanism)}{zh() ? "未通过；先处理阻断原因，再注册新运行。" : " did not pass; resolve the blocker, then register a new run."}</p></>}</Show>
                  <small>{zh() ? "已确认调用数不代表阶段通过。此运行不能恢复，仍可刷新 Core 状态。" : "Confirmed call counts do not establish a stage pass. This run cannot resume; you can still refresh Core status."}</small>
                </div></Show>
                <p>{journal().active_executor ? (zh() ? "Core 报告执行器租约有效，恢复已停用；仍可刷新状态或取消运行。" : "Core reports an active executor lease, so resuming is disabled. You can still refresh status or cancel the run.") : (zh() ? "Core 当前未报告有效的执行器租约。" : "Core does not currently report an active executor lease.")}</p>
                <Show when={journal().pending_calls.length} fallback={<p>{zh() ? "日志中暂无待确认调用；这不表示整条生产流程已完成。" : "No call is awaiting confirmation in this snapshot; this does not establish that production is complete."}</p>}>
                  <h4>{zh() ? "待确认阶段" : "Stages awaiting confirmation"}</h4>
                  <ul class="qf-journal-stages"><For each={journal().pending_calls}>{(call) => <li><strong>{executionRoleLabel(call.runtime_role)}</strong><span>{executionCallStateLabel(call.state)}</span><code>{call.stage_key}</code><Show when={call.error_code}>{(code) => <small>Core: {code()}</small>}</Show></li>}</For></ul>
                </Show>
                <Show when={!journal().pending_calls.length && journal().last_call}>{(call) => <div class="qf-journal-last"><h4>{zh() ? "最近记录的阶段" : "Latest recorded stage"}</h4><strong>{executionRoleLabel(call().runtime_role)}</strong><span>{executionCallStateLabel(call().state)}</span><code>{call().stage_key}</code></div>}</Show>
                <Show when={journal().pending_calls.some((call) => call.state === "unconfirmed") || !journal().active_executor && journal().pending_calls.length > 0}><p class="qf-ai-dock__boundary" role="status">{zh() ? "存在未确认的调用结果，不能据此认定模型成功或失败。此处不会自动重试，避免重复调用。" : "A call outcome remains unconfirmed; model success or failure is unknown. This view never retries it automatically."}</p></Show>
                <Show when={journal().run_status === "interrupted" || journal().last_call?.error_code === "executor_interrupted" || journal().pending_calls.some((call) => call.error_code === "executor_interrupted")}><p class="qf-ai-dock__boundary" role="status">{zh() ? "Core 记录了执行中断。已确认结果会保留，是否可以恢复仍由 Core 检查。" : "Core records an execution interruption. Confirmed results remain recorded; Core determines whether resumption is permitted."}</p></Show>
                <Show when={journal().run_status === "budget_exhausted"}><p class="qf-ai-dock__boundary" role="status">{zh() ? "Core 报告调用预算已耗尽。Studio 不会自动提高预算或继续发起调用。" : "Core reports that the model call budget is exhausted. Studio does not raise the budget or issue further calls automatically."}</p></Show>
                <Show when={journal().cancel_requested}><p class="qf-ai-dock__boundary" role="status">{zh() ? "Core 已记录取消请求；取消状态以 Core 的后续回执为准。" : "Core has recorded the cancellation request; its receipts determine the cancellation state."}</p></Show>
              </section>}</Show>
              <Show when={workflowEvents().length}><details><summary>{zh() ? "持久化工作流事件" : "Persisted workflow events"}</summary><ol class="qf-run-progress" aria-label={zh() ? "Core 持久化运行事件" : "Persisted Core run events"}><For each={workflowEvents()}>{(event) => <li><code>{event.cursor}</code><span>{event.stage}</span><strong>{event.event_type}</strong></li>}</For></ol></details></Show>
              <Show when={!executionJournal() && !workflowEvents().length}><p>{zh() ? "尚未读取可核对的执行日志或 Core 事件。点击刷新读取实际状态；不会根据等待时间推测完成情况。" : "No verifiable execution journal or Core events have been read. Refresh to retrieve actual state; elapsed time does not establish progress."}</p></Show>
              <Show when={executionPending()}><p role="status">{zh() ? "执行请求尚未返回；仍可刷新状态或取消运行。" : "The execution request is pending; you can still refresh status or cancel the run."}</p></Show>
              <button class="wui-button wui-button--outline" type="button" disabled={controlBusy()} onClick={() => void refreshRunEvidence()}>{zh() ? "刷新 Core evidence" : "Refresh Core evidence"}</button>
              <div class="qf-inline-actions"><button class="wui-button wui-button--outline" type="button" disabled={aiBusy() || controlBusy() || executionPending() || executionJournal()?.active_executor === true || executionJournal()?.run_status === "failed_gate" || !supported().includes("author.run.resume")} onClick={() => void resumeRun()}>{zh() ? "恢复" : "Resume"}</button><button class="wui-button wui-button--ghost" type="button" disabled={controlBusy() || !supported().includes("author.run.cancel")} onClick={() => void cancelRun()}>{zh() ? "取消运行" : "Cancel run"}</button></div>
              <CoreRequirementNotice operation="author.run.status" compact />
              <Show when={pendingReview() === "independent_provenance"}><p class="qf-ai-dock__boundary" role="status">{zh() ? "Core 正在等待独立审查所需的 provenance；尚未创建审查请求，候选正文仍不可见。Studio 不会编造来源或审稿凭据。" : "Core is waiting for independent-review provenance. No review request has been prepared and the candidate remains hidden. Studio does not invent provenance or review receipts."}</p></Show>
              <Show when={pendingReview() === "independent_semantic_review"}><p class="qf-ai-dock__boundary" role="status">{zh() ? "Core 正在等待独立语义审查。候选正文通过发布门禁后才可见，接受作品仍需单独操作。" : "Core is waiting for an independent semantic review. The candidate remains hidden until the release gate passes; acceptance remains a separate action."}</p></Show>
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
