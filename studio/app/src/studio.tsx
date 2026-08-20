import { createContext, createResource, createSignal, onMount, ParentComponent, useContext } from "solid-js";
import {
  type BridgeCapabilities,
  type CoreSurface,
  bridgeClient,
  bridgeTransportAvailable,
  bridgeTransportName,
  operationError,
  studioSurface,
} from "./bridge";
import { parseProjectProjection, type ProjectProjection } from "./authoring/contracts";

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
  const [lastRunId, setLastRunIdSignal] = createSignal(stored(LAST_RUN_KEY));

  const setProjectId = (value: string) => {
    const next = value.trim();
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
      if (next) localStorage.setItem(LAST_RUN_KEY, next);
      else localStorage.removeItem(LAST_RUN_KEY);
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
    setProjectLoading(true);
    setProjectError(undefined);
    try {
      const response = await client.invoke<ProjectProjection>("project.inspect", { project_id: id });
      if (response.status !== "ok" || !response.data) {
        setProjectProjection(undefined);
        setProjectError(operationError(response));
        return;
      }
      setProjectProjection(await parseProjectProjection(response.data));
    } catch (error) {
      setProjectProjection(undefined);
      setProjectError(error instanceof Error ? error.message : String(error));
    } finally {
      setProjectLoading(false);
    }
  };

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
  };

  return <StudioContext.Provider value={value}>{props.children}</StudioContext.Provider>;
};

export function useStudio(): StudioValue {
  const value = useContext(StudioContext);
  if (!value) throw new Error("StudioProvider is missing");
  return value;
}
