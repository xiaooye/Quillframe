import test from "node:test";
import assert from "node:assert/strict";
import {
  createRestartableWorker,
  createSingleFlight,
  retryableRuntime,
  validateQuickDemoReceipt,
  createLoadingOwner,
  createBusyGate,
  createExclusiveWorkerExecutor,
  isCurrentWorkerEvent,
  shouldCommitPublicationResult,
  captureWorkerErrorOwnership,
} from "../src/workerLifecycle.ts";

function fakeWorker() {
  return {
    onmessage: null,
    onerror: null,
    posts: [],
    terminateCount: 0,
    postMessage(message) { this.posts.push(message); },
    terminate() { this.terminateCount += 1; },
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

test("D1-01 rejected runtime cache is evicted and successful runtime is reused", async () => {
  let calls = 0;
  const getRuntime = retryableRuntime(async () => {
    calls += 1;
    if (calls === 1) throw new Error("bootstrap failed");
    return { id: calls };
  });

  await assert.rejects(getRuntime(), /bootstrap failed/);
  const second = await getRuntime();
  const third = await getRuntime();
  assert.equal(calls, 2);
  assert.strictEqual(second, third);
});

test("D1-02 a stale runtime rejection cannot evict a newer load", async () => {
  const first = deferred();
  const second = deferred();
  let calls = 0;
  const getRuntime = retryableRuntime(() => {
    calls += 1;
    return calls === 1 ? first.promise : second.promise;
  });

  const old = getRuntime();
  first.reject(new Error("old failure"));
  await assert.rejects(old, /old failure/);
  const current = getRuntime();
  first.reject(new Error("old failure again"));
  second.resolve({ id: "new" });
  assert.deepEqual(await current, { id: "new" });
  assert.deepEqual(await getRuntime(), { id: "new" });
  assert.equal(calls, 2);
});

test("worker invalidation terminates A once and makes B current", () => {
  const workers = [];
  const lifecycle = createRestartableWorker(() => {
    const worker = fakeWorker();
    workers.push(worker);
    return worker;
  });

  const leaseA = lifecycle.acquire();
  lifecycle.invalidate(leaseA, new Error("A failed"));
  lifecycle.invalidate(leaseA, new Error("duplicate failure"));
  const leaseB = lifecycle.acquire();
  assert.notEqual(leaseA.generation, leaseB.generation);
  assert.equal(workers[0].terminateCount, 1);
  assert.equal(lifecycle.isCurrent(leaseA), false);
  assert.equal(lifecycle.isCurrent(leaseB), true);
});

test("single flight reserves synchronously and rejects the second caller", async () => {
  const flight = createSingleFlight();
  const first = flight.tryBegin();
  const second = flight.tryBegin();
  assert.equal(first.accepted, true);
  assert.equal(second.accepted, false);
  if (second.accepted) throw new Error("unreachable");
  assert.equal(second.error.code, "worker_busy");
  first.flight.resolve("done");
  assert.equal(await first.flight.promise, "done");
  flight.finish(first.flight.token);
  const next = flight.tryBegin();
  assert.equal(next.accepted, true);
});

test("dispose rejects pending flight, terminates worker once, and invalidates lease", async () => {
  const worker = fakeWorker();
  const lifecycle = createRestartableWorker(() => worker);
  const lease = lifecycle.acquire();
  const flight = createSingleFlight();
  const pending = flight.tryBegin();
  assert.equal(pending.accepted, true);
  flight.dispose(new Error("closed"));
  await assert.rejects(pending.flight.promise, /closed/);
  lifecycle.dispose(new Error("closed"));
  lifecycle.dispose(new Error("closed again"));
  assert.equal(worker.terminateCount, 1);
  assert.equal(lifecycle.isCurrent(lease), false);
});

test("D1-03 post failure invalidates and terminates the failed worker", () => {
  const worker = fakeWorker();
  worker.postMessage = () => { throw new Error("post failed"); };
  const lifecycle = createRestartableWorker(() => worker);
  const lease = lifecycle.acquire();
  assert.throws(() => lease.post({ kind: "run" }), /post failed/);
  assert.equal(lifecycle.isCurrent(lease), false);
  assert.equal(worker.terminateCount, 1);
});

test("D1-04 stale generation events cannot become current", () => {
  const workers = [];
  const lifecycle = createRestartableWorker(() => { const item = fakeWorker(); workers.push(item); return item; });
  const oldLease = lifecycle.acquire();
  lifecycle.invalidate(oldLease);
  const newLease = lifecycle.acquire();
  assert.equal(lifecycle.isCurrent(oldLease), false);
  assert.equal(lifecycle.isCurrent(newLease), true);
});

test("D1-05 single flight rejects busy before any async work", () => {
  const gate = createBusyGate();
  assert.equal(gate.tryBegin(), true);
  assert.equal(gate.tryBegin(), false);
  gate.finish();
  assert.equal(gate.tryBegin(), true);
});

test("D1-06 rejected bootstrap can be retried by the next explicit request", async () => {
  let calls = 0;
  const load = retryableRuntime(async () => {
    calls += 1;
    if (calls === 1) throw new Error("bootstrap");
    return "runtime";
  });
  await assert.rejects(load(), /bootstrap/);
  assert.equal(await load(), "runtime");
  assert.equal(calls, 2);
});

test("D1-07 synchronous double request has one owner", () => {
  const flight = createSingleFlight();
  const first = flight.tryBegin();
  const second = flight.tryBegin();
  assert.equal(first.accepted, true);
  assert.equal(second.accepted, false);
});

test("D1-08 dispose ignores stale completion and settles once", async () => {
  const flight = createSingleFlight();
  const started = flight.tryBegin();
  assert.equal(started.accepted, true);
  void started.flight.promise.catch(() => undefined);
  flight.dispose(new Error("disposed"));
  await assert.rejects(started.flight.promise, /disposed/);
  flight.resolve(started.flight.token, "late");
  flight.reject(started.flight.token, new Error("late"));
});

test("D1-09 Quick Demo receipt validator enforces CH001 truth boundaries", () => {
  const valid = {
    schema: "quillframe_ch001_quick_demo_receipt_v1",
    chapter_id: "CH001",
    deterministic_core: { executed: false, modules: ["native/quillframe-core"], packet_fingerprint: "sha256:x", workflow_fingerprint: "sha256:y", stage: "started" },
    semantic_evidence: { source: "recorded_fixture", live_model_called: false, summary: "ok", findings: [] },
    live_model_called: false, uploads: 0, canon_mutated: false, authority: false,
  };
  assert.equal(validateQuickDemoReceipt(valid), true);
  for (const [key, value] of [["chapter_id", "CH002"], ["uploads", 1], ["authority", true], ["live_model_called", true]]) {
    assert.equal(validateQuickDemoReceipt({ ...valid, [key]: value }), false, key);
  }
});

test("D1-10 loading ownership does not allow an old continuation to clear new work", () => {
  const loading = createLoadingOwner();
  const old = loading.begin();
  loading.finish(old);
  const current = loading.begin();
  assert.equal(loading.finish(old), false);
  assert.equal(loading.isOwner(current), true);
  assert.equal(loading.finish(current), true);
});

test("D1-11 worker lifecycle disposal is idempotent", () => {
  const worker = fakeWorker();
  const lifecycle = createRestartableWorker(() => worker);
  lifecycle.acquire();
  lifecycle.dispose();
  lifecycle.dispose();
  assert.equal(worker.terminateCount, 1);
});

test("D1-12 local completion can be reconciled without touching a rejected cache", async () => {
  let calls = 0;
  const load = retryableRuntime(async () => { calls += 1; throw new Error("no runtime"); });
  const promise = load();
  await assert.rejects(promise, /no runtime/);
  await assert.rejects(load(), /no runtime/);
  assert.equal(calls, 2);
});

test("D1 executor reserves synchronously, cleans local runtime once, and releases after reject", async () => {
  const runtime = deferred();
  const cleanup = [];
  const executor = createExclusiveWorkerExecutor();
  const first = executor.run(() => runtime.promise, async (value) => { cleanup.push(`execute:${value}`); }, (value) => { cleanup.push(`cleanup:${value}`); });
  assert.equal(first.accepted, true);
  const busy = executor.run(() => Promise.resolve("other"), async () => {}, () => {});
  assert.equal(busy.accepted, false);
  runtime.reject(new Error("bootstrap"));
  await assert.rejects(first.promise, /bootstrap/);
  const secondRuntime = await Promise.resolve("runtime-b");
  const second = executor.run(() => Promise.resolve(secondRuntime), async (value) => { cleanup.push(`execute:${value}`); throw new Error("execute failed"); }, (value) => { cleanup.push(`cleanup:${value}`); });
  assert.equal(second.accepted, true);
  await assert.rejects(second.promise, /execute failed/);
  assert.deepEqual(cleanup, ["execute:runtime-b", "cleanup:runtime-b"]);
});

test("D1 event ownership commits only matching live worker events", () => {
  const worker = fakeWorker();
  const lifecycle = createRestartableWorker(() => worker);
  const lease = lifecycle.acquire();
  const flight = createSingleFlight();
  const started = flight.tryBegin();
  assert.equal(started.accepted, true);
  void started.flight.promise.catch(() => undefined);
  const base = { disposed: false, lifecycle, lease, flight, token: started.flight.token, requestId: "b" };
  assert.equal(isCurrentWorkerEvent({ ...base, eventId: "a" }), false);
  assert.equal(isCurrentWorkerEvent({ ...base, eventId: "b" }), true);
  flight.dispose(new Error("closed"));
  assert.equal(isCurrentWorkerEvent({ ...base, eventId: "b" }), false);
});

test("D1 publication result ownership rejects stale epoch or profile", () => {
  assert.equal(shouldCommitPublicationResult({ capturedEpoch: 1, currentEpoch: 1, capturedProfile: "clean_text", currentProfile: "clean_text" }), true);
  assert.equal(shouldCommitPublicationResult({ capturedEpoch: 1, currentEpoch: 2, capturedProfile: "clean_text", currentProfile: "clean_text" }), false);
  assert.equal(shouldCommitPublicationResult({ capturedEpoch: 1, currentEpoch: 1, capturedProfile: "clean_text", currentProfile: "epub3" }), false);
});

test("D1 loading owner survives an old deferred continuation after B begins", async () => {
  const loading = createLoadingOwner();
  const first = deferred();
  let visible = false;
  const run = async (wait) => {
    const token = loading.begin();
    visible = true;
    try { await wait; } finally { if (loading.finish(token)) visible = false; }
  };
  const a = run(first.promise);
  await Promise.resolve();
  const b = loading.begin();
  visible = true;
  first.resolve();
  await a;
  assert.equal(loading.isOwner(b), true);
  assert.equal(visible, true);
  loading.finish(b);
});

test("D1-09 every Quick Demo truth field mutation is rejected", () => {
  const valid = {
    schema: "quillframe_ch001_quick_demo_receipt_v1", chapter_id: "CH001",
    deterministic_core: { executed: false, modules: ["native/quillframe-core"], packet_fingerprint: "packet", workflow_fingerprint: "workflow", stage: "started" },
    semantic_evidence: { source: "recorded_fixture", live_model_called: false, summary: "ok", findings: [{ code: "C", severity: "info", owner: "qf" }] },
    live_model_called: false, uploads: 0, canon_mutated: false, authority: false,
  };
  const mutations = [
    ["schema", "wrong"], ["chapter_id", "CH002"], ["live_model_called", true], ["uploads", 1],
    ["canon_mutated", true], ["authority", true],
    ["deterministic_core", { ...valid.deterministic_core, executed: true }],
    ["deterministic_core", { ...valid.deterministic_core, modules: [1] }],
    ["deterministic_core", { ...valid.deterministic_core, packet_fingerprint: 1 }],
    ["deterministic_core", { ...valid.deterministic_core, workflow_fingerprint: 1 }],
    ["deterministic_core", { ...valid.deterministic_core, stage: 1 }],
    ["semantic_evidence", { ...valid.semantic_evidence, source: "live" }],
    ["semantic_evidence", { ...valid.semantic_evidence, live_model_called: true }],
    ["semantic_evidence", { ...valid.semantic_evidence, findings: "bad" }],
    ["semantic_evidence", { ...valid.semantic_evidence, findings: [{ code: 1, severity: "info", owner: "qf" }] }],
    ["semantic_evidence", { ...valid.semantic_evidence, findings: [{ code: "C", severity: 1, owner: "qf" }] }],
    ["semantic_evidence", { ...valid.semantic_evidence, findings: [{ code: "C", severity: "info", owner: 1 }] }],
  ];
  assert.equal(validateQuickDemoReceipt(valid), true);
  for (const [key, value] of mutations) assert.equal(validateQuickDemoReceipt({ ...valid, [key]: value }), false, String(key));
});

test("D1 dispose pending rejection is observed without unhandledRejection", async () => {
  const unhandled = [];
  const handler = (reason) => unhandled.push(reason);
  process.on("unhandledRejection", handler);
  try {
    const flight = createSingleFlight();
    const started = flight.tryBegin();
    assert.equal(started.accepted, true);
    void started.flight.promise.catch(() => undefined);
    flight.dispose(new Error("disposed"));
    await Promise.resolve();
    assert.deepEqual(unhandled, []);
  } finally {
    process.off("unhandledRejection", handler);
  }
});

test("D1 active error captures ownership before invalidation while stale error only invalidates", () => {
  const worker = fakeWorker();
  const lifecycle = createRestartableWorker(() => worker);
  const lease = lifecycle.acquire();
  const flight = createSingleFlight();
  const started = flight.tryBegin();
  assert.equal(started.accepted, true);
  void started.flight.promise.catch(() => undefined);
  const active = captureWorkerErrorOwnership({ disposed: false, lifecycle, lease, flight, token: started.flight.token, requestId: "a", eventId: "a" });
  lifecycle.invalidate(lease);
  assert.equal(active, true);
  assert.equal(worker.terminateCount, 1);

  const workerB = fakeWorker();
  const lifecycleB = createRestartableWorker(() => workerB);
  const leaseB = lifecycleB.acquire();
  const stale = captureWorkerErrorOwnership({ disposed: false, lifecycle: lifecycleB, lease: leaseB, flight, token: started.flight.token, requestId: "a", eventId: "stale" });
  lifecycleB.invalidate(leaseB);
  assert.equal(stale, false);
  assert.equal(workerB.terminateCount, 1);
});
