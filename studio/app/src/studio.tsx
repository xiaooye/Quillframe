import { createContext, createResource, createSignal, onMount, ParentComponent, useContext } from "solid-js";
import {
  type BridgeCapabilities,
  type BridgeResult,
  type CoreSurface,
  bridgeClient,
  bridgeTransportAvailable,
  bridgeTransportName,
  operationError,
  studioSurface,
} from "./bridge";
import type { ProjectProjection } from "./authoring/contracts";

export interface ProjectHubProjection {
  schema: "quillframe_studio_project_hub_projection_v1";
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
  /** @deprecated Legacy UI alias. The value is a stable project id, never a filesystem root. */
  projectRoot: () => string;
  /** @deprecated Legacy UI alias. The value is a stable project id, never a filesystem root. */
  setProjectRoot: (value: string) => void;
  projectResult: () => BridgeResult<ProjectInspectData> | undefined;
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

function legacyProjection(core: ProjectProjection, resultFingerprint: string): ProjectInspectData {
  const project = core.project;
  return {
    valid: true,
    errors: [],
    project: {
      schema: "quillframe_studio_project_hub_projection_v1",
      authority: false,
      project: {
        id: project.project_id,
        title: project.title,
        version: null,
        language: project.language,
        layout: null,
        project_schema_version: String(project.project_schema_version),
      },
      framework_lock: {},
      logical_paths: {},
      policy_availability: {},
      unavailable: [
        "legacy_framework_lock_projection_not_exposed_by_current_Core",
        "legacy_logical_paths_projection_not_exposed_by_current_Core",
      ],
      projection_fingerprint: resultFingerprint,
    },
  };
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
  const [projectResult, setProjectResult] = createSignal<BridgeResult<ProjectInspectData>>();
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
        setProjectResult(undefined);
        setProjectError(operationError(response));
        return;
      }
      setProjectProjection(response.data);
      setProjectResult({ ...response, data: legacyProjection(response.data, response.result_fingerprint) });
    } catch (error) {
      setProjectProjection(undefined);
      setProjectResult(undefined);
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
    projectRoot: projectId,
    setProjectRoot: setProjectId,
    projectResult,
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
