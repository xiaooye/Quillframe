import { createContext, createResource, createSignal, ParentComponent, useContext } from "solid-js";
import { BridgeDescription, BridgeResult, StudioSurface, bridgeTransportAvailable, invokeBridge, studioSurface } from "./bridge";

export interface ProjectHubProjection {
  schema: "novelforge_studio_project_hub_projection_v1";
  authority: false;
  project: {
    id: string | null;
    title: string | null;
    version: string | null;
    language: string | null;
    layout: string | null;
    project_schema_version: string | null;
  };
  framework_lock: Record<string, unknown>;
  logical_paths: Record<string, { relative: string | null; exists: boolean; kind: string }>;
  policy_availability: Record<string, boolean>;
  unavailable: string[];
  projection_fingerprint: string;
}

export interface ProjectInspectData {
  valid: boolean;
  errors: unknown[];
  project: ProjectHubProjection;
}

interface StudioValue {
  surface: () => StudioSurface;
  bridgeAvailable: () => boolean;
  bridgeDescription: () => BridgeDescription | undefined;
  bridgeError: () => unknown;
  bridgeLoading: () => boolean;
  refreshBridge: () => void;
  projectRoot: () => string;
  setProjectRoot: (value: string) => void;
  projectResult: () => BridgeResult<ProjectInspectData> | undefined;
  projectLoading: () => boolean;
  projectError: () => string | undefined;
  inspectProject: (root?: string) => Promise<void>;
}

const StudioContext = createContext<StudioValue>();

export const StudioProvider: ParentComponent = (props) => {
  const surface = studioSurface();
  const hasBridge = bridgeTransportAvailable();
  const [bridge, { refetch }] = createResource(
    () => (hasBridge ? "bound" : undefined),
    async () => {
      const result = await invokeBridge<BridgeDescription>("bridge.describe");
      if (result.status !== "ok" || !result.data) throw new Error("bridge.describe did not return data");
      return result.data;
    },
  );
  const [projectRoot, setProjectRoot] = createSignal("");
  const [projectResult, setProjectResult] = createSignal<BridgeResult<ProjectInspectData>>();
  const [projectLoading, setProjectLoading] = createSignal(false);
  const [projectError, setProjectError] = createSignal<string>();

  const inspectProject = async (root = projectRoot()) => {
    if (!hasBridge) {
      setProjectError("NovelForge Core host is not bound to this Studio surface");
      return;
    }
    const trimmed = root.trim();
    if (!trimmed) {
      setProjectError("project_root is required");
      return;
    }
    setProjectRoot(trimmed);
    setProjectLoading(true);
    setProjectError(undefined);
    try {
      const result = await invokeBridge<ProjectInspectData>("project.inspect", { project_root: trimmed });
      setProjectResult(result);
      if (result.status !== "ok") setProjectError(JSON.stringify(result.error));
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
    refreshBridge: () => {
      if (hasBridge) void refetch();
    },
    projectRoot,
    setProjectRoot,
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
