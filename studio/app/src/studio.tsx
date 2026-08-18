import { createContext, createResource, createSignal, ParentComponent, useContext } from "solid-js";
import { BridgeDescription, BridgeResult, StudioSurface, bridgeTransportAvailable, invokeBridge, operationError, studioSurface } from "./bridge";

export interface ProjectInspectData {
  schema: "quillframe_project_projection_v1";
  project: {
    project_id: string;
    title: string;
    language: string;
    project_schema_version: number;
    created_at?: string;
    updated_at?: string;
  };
  counts?: Record<string, number>;
  authority: false;
}

interface StudioValue {
  surface: () => StudioSurface;
  bridgeAvailable: () => boolean;
  bridgeDescription: () => BridgeDescription | undefined;
  bridgeError: () => unknown;
  bridgeLoading: () => boolean;
  refreshBridge: () => void;
  projectId: () => string;
  setProjectId: (value: string) => void;
  /** @deprecated compatibility alias; value is a stable project id, never a filesystem root. */
  projectRoot: () => string;
  /** @deprecated compatibility alias; value is a stable project id, never a filesystem root. */
  setProjectRoot: (value: string) => void;
  projectResult: () => BridgeResult<ProjectInspectData> | undefined;
  projectLoading: () => boolean;
  projectError: () => string | undefined;
  inspectProject: (projectId?: string) => Promise<void>;
}

const StudioContext = createContext<StudioValue>();

export const StudioProvider: ParentComponent = (props) => {
  const surface = studioSurface();
  const hasBridge = bridgeTransportAvailable();
  const [bridge, { refetch }] = createResource(
    () => (hasBridge ? "bound" : undefined),
    async () => {
      const result = await invokeBridge<BridgeDescription>("bridge.describe");
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      return result.data;
    },
  );
  const [projectId, setProjectIdSignal] = createSignal(localStorage.getItem("quillframe.ui.lastProjectId") || "");
  const [projectResult, setProjectResult] = createSignal<BridgeResult<ProjectInspectData>>();
  const [projectLoading, setProjectLoading] = createSignal(false);
  const [projectError, setProjectError] = createSignal<string>();

  const setProjectId = (value: string) => {
    const next = value.trim();
    setProjectIdSignal(next);
    if (next) localStorage.setItem("quillframe.ui.lastProjectId", next);
  };

  const inspectProject = async (requested = projectId()) => {
    if (!hasBridge) {
      setProjectError("Quillframe Core host is not bound to this Studio surface");
      return;
    }
    const trimmed = requested.trim();
    if (!trimmed) {
      setProjectError("project_id is required");
      return;
    }
    setProjectId(trimmed);
    setProjectLoading(true);
    setProjectError(undefined);
    try {
      const result = await invokeBridge<ProjectInspectData>("project.inspect", { project_id: trimmed });
      setProjectResult(result);
      if (result.status !== "ok") setProjectError(operationError(result));
    } catch (error) {
      setProjectError(error instanceof Error ? error.message : String(error));
    } finally {
      setProjectLoading(false);
    }
  };

  const value: StudioValue = {
    surface: () => surface,
    bridgeAvailable: () => hasBridge,
    bridgeDescription: () => bridge(),
    bridgeError: () => bridge.error,
    bridgeLoading: () => hasBridge && bridge.loading,
    refreshBridge: () => { if (hasBridge) void refetch(); },
    projectId,
    setProjectId,
    projectRoot: projectId,
    setProjectRoot: setProjectId,
    projectResult,
    projectLoading,
    projectError,
    inspectProject,
  };

  return <StudioContext.Provider value={value}>{props.children}</StudioContext.Provider>;
};

export function useStudio(): StudioValue {
  const value = useContext(StudioContext);
  if (!value) throw new Error("StudioProvider is missing");
  return value;
}
