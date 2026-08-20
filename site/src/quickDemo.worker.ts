/// <reference lib="webworker" />

import { loadPyodide, version as pyodideVersion } from "pyodide";
import fixtureSource from "../../demo/fixtures/ch001_quick_demo.json?raw";
import typesSource from "../../production_runtime/types.py?raw";
import workflowSource from "../../production_runtime/workflow.py?raw";
import { createExclusiveWorkerExecutor, retryableRuntime } from "./workerLifecycle";

type WorkerRequest = { kind: "run"; id: string };
type WorkerResponse =
  | { kind: "ready"; pyodide_version: string }
  | { kind: "result"; id: string; receipt: string }
  | { kind: "error"; id: string; error: string };

const worker = self as DedicatedWorkerGlobalScope;
type PyodideRuntime = Awaited<ReturnType<typeof loadPyodide>>;

const PYTHON_BOOTSTRAP = String.raw`
import json
import sys

sys.path.insert(0, "/tmp/quillframe-browser-core")
from production_runtime import workflow as workflow_module
from production_runtime.types import CharacterIntent, GenerationPacket, SceneIntent, TransitionConstraints
from production_runtime.workflow import NovelWorkflowEngine


def qf_run_ch001_quick_demo(fixture_json: str) -> str:
    fixture = json.loads(fixture_json)
    if fixture.get("schema") != "quillframe_ch001_quick_demo_fixture_v1":
        raise ValueError("unsupported quick-demo fixture")
    if fixture.get("chapter_id") != "CH001":
        raise ValueError("quick demo is limited to CH001")

    workflow_module._now = lambda: fixture["fixed_time"]
    packet = GenerationPacket.build(
        project_id=fixture["project_id"],
        run_id=fixture["run_id"],
        chapter_id=fixture["chapter_id"],
        context_freeze_fingerprint=fixture["context_freeze_fingerprint"],
        scene_intents=(SceneIntent(**fixture["scene_intent"]),),
        character_intents=(CharacterIntent(**fixture["character_intent"]),),
        transition_constraints=TransitionConstraints(**fixture["transition_constraints"]),
        task_profile_id=fixture["task_profile_id"],
    )
    workflow = NovelWorkflowEngine.start(
        project_id=fixture["project_id"],
        run_id=fixture["run_id"],
        chapter_id=fixture["chapter_id"],
        author_profile="guided",
    )
    snapshot = workflow.snapshot()
    expected = fixture["expected"]
    if packet.packet_fingerprint != expected["packet_fingerprint"]:
        raise ValueError("generation packet no longer matches the recorded demo fixture")
    if snapshot["snapshot_fingerprint"] != expected["workflow_fingerprint"]:
        raise ValueError("workflow snapshot no longer matches the recorded demo fixture")

    semantic = fixture["semantic_evidence"]
    if semantic.get("source") != "recorded_fixture" or semantic.get("live_model_called") is not False:
        raise ValueError("semantic evidence truth label is invalid")

    return json.dumps({
        "schema": "quillframe_ch001_quick_demo_receipt_v1",
        "chapter_id": "CH001",
        "deterministic_core": {
            "executed": True,
            "modules": ["production_runtime.workflow", "production_runtime.types"],
            "packet_fingerprint": packet.packet_fingerprint,
            "workflow_fingerprint": snapshot["snapshot_fingerprint"],
            "stage": snapshot["stage"],
        },
        "semantic_evidence": semantic,
        "live_model_called": False,
        "uploads": 0,
        "canon_mutated": False,
        "authority": False,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
`;

const getRuntime = retryableRuntime(async (): Promise<PyodideRuntime> => {
      const pyodide = await loadPyodide({
        indexURL: new URL("/pyodide/", worker.location.origin).href,
      });
      pyodide.FS.mkdirTree("/tmp/quillframe-browser-core/production_runtime");
      pyodide.FS.writeFile("/tmp/quillframe-browser-core/production_runtime/__init__.py", "");
      pyodide.FS.writeFile("/tmp/quillframe-browser-core/production_runtime/workflow.py", workflowSource);
      pyodide.FS.writeFile("/tmp/quillframe-browser-core/production_runtime/types.py", typesSource);
      await pyodide.runPythonAsync(PYTHON_BOOTSTRAP);
      worker.postMessage({ kind: "ready", pyodide_version: pyodideVersion } satisfies WorkerResponse);
      return pyodide;
});

const executor = createExclusiveWorkerExecutor();

worker.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  if (event.data?.kind !== "run") return;
  const { id } = event.data;
  const run = executor.run(
    getRuntime,
    async (pyodide) => {
      pyodide.globals.set("qf_fixture_json", fixtureSource);
      const receipt = await pyodide.runPythonAsync("qf_run_ch001_quick_demo(qf_fixture_json)");
      worker.postMessage({ kind: "result", id, receipt: String(receipt) } satisfies WorkerResponse);
    },
    (pyodide) => pyodide.globals.delete("qf_fixture_json"),
  );
  if (!run.accepted) {
    worker.postMessage({ kind: "error", id, error: "worker_busy" } satisfies WorkerResponse);
    return;
  }
  void run.promise.catch((value) => {
    worker.postMessage({
      kind: "error",
      id,
      error: value instanceof Error ? value.message : String(value),
    } satisfies WorkerResponse);
  });
};
