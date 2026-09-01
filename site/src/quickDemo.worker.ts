/// <reference lib="webworker" />

import fixtureSource from "../../demo/fixtures/ch001_quick_demo.json?raw";

type WorkerRequest = { kind: "run"; id: string };
type WorkerResponse =
  | { kind: "ready"; runtime_version: string }
  | { kind: "result"; id: string; receipt: string }
  | { kind: "error"; id: string; error: string };

const worker = self as DedicatedWorkerGlobalScope;
worker.postMessage({ kind: "ready", runtime_version: "recorded-rust-core-receipt-v1" } satisfies WorkerResponse);

worker.onmessage = (event: MessageEvent<WorkerRequest>) => {
  if (event.data?.kind !== "run") return;
  try {
    const fixture = JSON.parse(fixtureSource) as Record<string, any>;
    const expected = fixture.expected as Record<string, string>;
    const receipt = {
      schema: "quillframe_ch001_quick_demo_receipt_v1",
      chapter_id: "CH001",
      deterministic_core: {
        executed: false,
        modules: ["quillframe-core recorded acceptance"],
        packet_fingerprint: expected.packet_fingerprint,
        workflow_fingerprint: expected.workflow_fingerprint,
        stage: "DRAFT",
      },
      semantic_evidence: fixture.semantic_evidence,
      live_model_called: false,
      uploads: 0,
      canon_mutated: false,
      authority: false,
    };
    worker.postMessage({ kind: "result", id: event.data.id, receipt: JSON.stringify(receipt) } satisfies WorkerResponse);
  } catch (value) {
    worker.postMessage({ kind: "error", id: event.data.id, error: value instanceof Error ? value.message : String(value) } satisfies WorkerResponse);
  }
};
