import { createContext, createEffect, createResource, createSignal, on, onCleanup, onMount, ParentComponent, useContext } from "solid-js";
import {
  type BridgeCapabilities,
  type CoreSurface,
  bridgeClient,
  bridgeTransportAvailable,
  bridgeTransportName,
  operationError,
  studioSurface,
} from "./bridge";
import { parseChapterList, parseProjectProjection, parseProjectPreferenceList, type ChapterItem, type ChapterListProjection, type ProjectProjection, type ProjectPreference } from "./authoring/contracts";

interface StudioValue {
  surface: () => CoreSurface;
  transportName: () => ReturnType<typeof bridgeTransportName>;
  bridgeAvailable: () => boolean;
  bridgeCapabilities: () => BridgeCapabilities | undefined;
  bridgeDescription: () => {
    supported_operations: string[];
    deferred_operations: Record<string, { reason: string; dependency?: string }>;
  } | undefined;
  bridgeError: () => unknown;
  bridgeLoading: () => boolean;
  refreshBridge: () => void;
  projectId: () => string;
  setProjectId: (value: string) => void;
  projectProjection: () => ProjectProjection | undefined;
  projectLoading: () => boolean;
  projectError: () => string | undefined;
  inspectProject: (projectId?: string) => Promise<void>;
  lastRunId: () => string;
  setLastRunId: (runId: string) => void;
  chapters: () => ChapterItem[];
  chapterId: () => string;
  selectedChapter: () => ChapterItem | undefined;
  setChapterId: (value: string) => void;
  refreshChapters: () => Promise<void>;
  chapterError: () => string | undefined;
  chapterLoading: () => boolean;
  projectPreferences: () => ProjectPreference[];
  selectedPreferenceIds: () => string[];
  setSelectedPreferenceIds: (ids: string[]) => void;
  refreshPreferences: () => Promise<void>;
  preferenceError: () => string | undefined;
  preferenceLoading: () => boolean;
}

const StudioContext = createContext<StudioValue>();
const LAST_PROJECT_KEY = "quillframe.ui.lastProjectId";
const LAST_RUN_KEY = "quillframe.ui.lastRunId";

function stored(key: string): string {
  return typeof localStorage === "undefined" ? "" : localStorage.getItem(key) ?? "";
}

export const StudioProvider: ParentComponent = (props) => {
  const client = bridgeClient();
  const hasBridge = bridgeTransportAvailable();
  const [bridge, { refetch }] = createResource(
    () => (hasBridge && client ? "bound" : undefined),
    async () => client!.describe(),
  );
  const [projectId, setProjectIdSignal] = createSignal(stored(LAST_PROJECT_KEY));
  const [projectProjection, setProjectProjection] = createSignal<ProjectProjection>();
  const [projectLoading, setProjectLoading] = createSignal(false);
  const [projectError, setProjectError] = createSignal<string>();
  const [lastRunId, setLastRunIdSignal] = createSignal("");
  const [chapters, setChapters] = createSignal<ChapterItem[]>([]);
  const [chapterId, setChapterIdSignal] = createSignal("");
  const [chapterError, setChapterError] = createSignal<string>();
  const [chapterLoading, setChapterLoading] = createSignal(false);
  const [projectPreferences, setProjectPreferences] = createSignal<ProjectPreference[]>([]);
  const [selectedPreferenceIds, setSelectedPreferenceIdsSignal] = createSignal<string[]>([]);
  const [preferenceError, setPreferenceError] = createSignal<string>();
  const [preferenceLoading, setPreferenceLoading] = createSignal(false);
  let projectGeneration = 0;
  let chapterGeneration = 0;
  let preferenceGeneration = 0;

  const setProjectId = (value: string) => {
    const next = value.trim();
    if (next !== projectId()) {
      projectGeneration += 1; chapterGeneration += 1; preferenceGeneration += 1;
      setProjectProjection(undefined); setProjectError(undefined); setProjectLoading(false);
      setChapters([]); setChapterIdSignal(""); setChapterError(undefined); setChapterLoading(false);
      setLastRunIdSignal("");
      setProjectPreferences([]); setSelectedPreferenceIdsSignal([]); setPreferenceError(undefined); setPreferenceLoading(false);
    }
    setProjectIdSignal(next);
    if (typeof localStorage !== "undefined") {
      if (next) localStorage.setItem(LAST_PROJECT_KEY, next);
      else localStorage.removeItem(LAST_PROJECT_KEY);
    }
  };

  const setLastRunId = (value: string) => {
    const next = value.trim();
    setLastRunIdSignal(next);
    if (typeof localStorage !== "undefined") {
      if (next) localStorage.setItem(`${LAST_RUN_KEY}:${projectId()}:${chapterId()}`, next);
      else localStorage.removeItem(`${LAST_RUN_KEY}:${projectId()}:${chapterId()}`);
    }
  };

  const inspectProject = async (requested = projectId()) => {
    if (!client) {
      setProjectError("Quillframe Core host is not bound to this Studio surface");
      return;
    }
    const id = requested.trim();
    if (!id) {
      setProjectError("project_id is required");
      return;
    }
    setProjectId(id);
    const generation = ++projectGeneration;
    const current = () => generation === projectGeneration && projectId() === id;
    setProjectLoading(true);
    setProjectError(undefined);
    try {
      const response = await client.invoke<ProjectProjection>("project.inspect", { project_id: id });
      if (!current()) return;
      if (response.status !== "ok" || !response.data) {
        setProjectProjection(undefined);
        setProjectError(operationError(response));
        return;
      }
      const parsed = await parseProjectProjection(response.data);
      if (!current()) return;
      if (parsed.manifest.id !== id) throw new Error("project_response_binding_invalid");
      setProjectProjection(parsed);
    } catch (error) {
      if (!current()) return;
      setProjectProjection(undefined);
      setProjectError(error instanceof Error ? error.message : String(error));
    } finally {
      if (current()) setProjectLoading(false);
    }
  };

  const setChapterId = (id: string) => {
    const selected = chapters().find((chapter) => chapter.chapter_id === id);
    if (!selected) return;
    if (id !== chapterId()) setLastRunIdSignal(stored(`${LAST_RUN_KEY}:${projectId()}:${id}`));
    setChapterIdSignal(id);
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(`quillframe.ui.lastChapterId:${projectId()}`, id);
      localStorage.setItem(`quillframe.ui.lastDocumentId:${projectId()}`, selected.document_id);
    }
  };

  const refreshChapters = async () => {
    const id = projectId();
    const generation = ++chapterGeneration;
    const current = () => generation === chapterGeneration && projectId() === id;
    if (!client || !id || !bridge()?.operations.includes("chapter.list")) return;
    setChapterLoading(true); setChapterError(undefined);
    try {
      const result = await client.invoke<ChapterListProjection>("chapter.list", { project_id: id });
      if (!current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const parsed = parseChapterList(result.data, id);
      setChapters(parsed.items);
      const remembered = chapterId() || stored(`quillframe.ui.lastChapterId:${id}`);
      const selected = parsed.items.find((chapter) => chapter.chapter_id === remembered) ?? parsed.items[0];
      if (selected) setChapterId(selected.chapter_id);
      else setChapterIdSignal("");
    } catch (cause) {
      if (current()) { setChapters([]); setChapterIdSignal(""); setChapterError(cause instanceof Error ? cause.message : String(cause)); }
    } finally { if (current()) setChapterLoading(false); }
  };

  const setSelectedPreferenceIds = (ids: string[]) => {
    const eligible = new Set(projectPreferences().filter((item) => item.state === "active" && item.active_for_future_production).map((item) => item.hypothesis_id));
    setSelectedPreferenceIdsSignal([...new Set(ids)].filter((id) => eligible.has(id)));
  };

  const refreshPreferences = async () => {
    const id = projectId(); const generation = ++preferenceGeneration;
    const current = () => generation === preferenceGeneration && projectId() === id;
    if (!client || !id || !bridge()?.operations.includes("learning.preference.list")) return;
    setPreferenceLoading(true); setPreferenceError(undefined);
    try {
      const result = await client.invoke("learning.preference.list", { project_id: id, limit: 200 });
      if (!current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setProjectPreferences(parseProjectPreferenceList(result.data, id));
      setSelectedPreferenceIds(selectedPreferenceIds());
    } catch (cause) {
      if (current()) { setProjectPreferences([]); setSelectedPreferenceIdsSignal([]); setPreferenceError(cause instanceof Error ? cause.message : String(cause)); }
    } finally { if (current()) setPreferenceLoading(false); }
  };

  createEffect(on([projectId, bridge], () => { void refreshChapters(); }));
  createEffect(on([projectId, bridge], () => { void refreshPreferences(); }));
  onCleanup(() => { projectGeneration += 1; chapterGeneration += 1; preferenceGeneration += 1; });

  onMount(() => {
    if (hasBridge && projectId()) void inspectProject(projectId());
  });

  const value: StudioValue = {
    surface: () => studioSurface(),
    transportName: () => bridgeTransportName(),
    bridgeAvailable: () => hasBridge,
    bridgeCapabilities: () => bridge(),
    bridgeDescription: () => {
      const current = bridge();
      if (!current) return undefined;
      return {
        supported_operations: current.operations,
        deferred_operations: Object.fromEntries(current.deferredOperations.map((operation) => [operation, { reason: "Deferred by Core contract", dependency: "Core" }])),
      };
    },
    bridgeError: () => bridge.error,
    bridgeLoading: () => hasBridge && bridge.loading,
    refreshBridge: () => { if (hasBridge) void refetch(); },
    projectId,
    setProjectId,
    projectProjection,
    projectLoading,
    projectError,
    inspectProject,
    lastRunId,
    setLastRunId,
    chapters,
    chapterId,
    selectedChapter: () => chapters().find((chapter) => chapter.chapter_id === chapterId()),
    setChapterId,
    refreshChapters,
    chapterError,
    chapterLoading,
    projectPreferences,
    selectedPreferenceIds,
    setSelectedPreferenceIds,
    refreshPreferences,
    preferenceError,
    preferenceLoading,
  };

  return <StudioContext.Provider value={value}>{props.children}</StudioContext.Provider>;
};

export function useStudio(): StudioValue {
  const value = useContext(StudioContext);
  if (!value) throw new Error("StudioProvider is missing");
  return value;
}
