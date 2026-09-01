export type WorkerLike = {
  onmessage: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  postMessage(message: unknown): void;
  terminate(): void;
};

export type WorkerFailureCode = "worker_busy" | "worker_failed" | "worker_disposed";

export type WorkerFailure = Error & { code: WorkerFailureCode };

function failure(code: WorkerFailureCode, message: string = code): WorkerFailure {
  const error = new Error(message) as WorkerFailure;
  error.code = code;
  return error;
}

export function retryableRuntime<T>(load: () => Promise<T>): () => Promise<T> {
  let cached: Promise<T> | undefined;

  return () => {
    if (cached) return cached;
    let promise: Promise<T>;
    try {
      promise = Promise.resolve(load());
    } catch (error) {
      promise = Promise.reject(error);
    }
    cached = promise;
    void promise.catch(() => {
      if (cached === promise) cached = undefined;
    });
    return promise;
  };
}

export type WorkerLease<TRequest> = {
  worker: WorkerLike;
  generation: number;
  post(request: TRequest): void;
};

export type RestartableWorker<TRequest> = {
  acquire(): WorkerLease<TRequest>;
  isCurrent(lease: WorkerLease<TRequest>): boolean;
  invalidate(lease: WorkerLease<TRequest>, reason?: Error): void;
  dispose(reason?: Error): void;
  getGeneration(): number;
};

export function createRestartableWorker<TRequest>(
  create: () => WorkerLike,
  _options: { onUnhandledError?: (error: unknown) => void } = {},
): RestartableWorker<TRequest> {
  let generation = 0;
  let current: WorkerLease<TRequest> | undefined;
  let disposed = false;
  const terminated = new WeakSet<WorkerLike>();
  let api!: RestartableWorker<TRequest>;

  const detachAndTerminate = (worker: WorkerLike) => {
    worker.onmessage = null;
    worker.onerror = null;
    if (terminated.has(worker)) return;
    terminated.add(worker);
    worker.terminate();
  };

  const invalidate = (lease: WorkerLease<TRequest>, _reason?: Error) => {
    if (disposed || current !== lease) return;
    current = undefined;
    generation += 1;
    detachAndTerminate(lease.worker);
  };

  api = {
    acquire() {
      if (disposed) throw failure("worker_disposed", "worker lifecycle is disposed");
      if (current) return current;
      const worker = create();
      const lease = {
        worker,
        generation: generation === 0 ? 1 : generation,
        post(request: TRequest) {
          if (!api.isCurrent(lease)) throw failure("worker_disposed", "worker lease is stale");
          try {
            worker.postMessage(request);
          } catch (error) {
            invalidate(lease, error instanceof Error ? error : new Error(String(error)));
            throw error;
          }
        },
      } satisfies WorkerLease<TRequest>;
      generation = lease.generation;
      current = lease;
      return lease;
    },

    isCurrent(lease) {
      return !disposed && current === lease && lease.generation === generation;
    },

    invalidate,

    dispose(_reason?: Error) {
      if (disposed) return;
      disposed = true;
      generation += 1;
      const lease = current;
      current = undefined;
      if (lease) detachAndTerminate(lease.worker);
    },

    getGeneration() {
      return generation;
    },
  };
  return api;
}

export function validateQuickDemoReceipt(value: unknown): boolean {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const receipt = value as Record<string, unknown>;
  const core = receipt.deterministic_core;
  const evidence = receipt.semantic_evidence;
  if (!core || typeof core !== "object" || Array.isArray(core)) return false;
  if (!evidence || typeof evidence !== "object" || Array.isArray(evidence)) return false;
  const coreRecord = core as Record<string, unknown>;
  const evidenceRecord = evidence as Record<string, unknown>;
  return receipt.schema === "quillframe_ch001_quick_demo_receipt_v1"
    && receipt.chapter_id === "CH001"
    && coreRecord.executed === false
    && Array.isArray(coreRecord.modules)
    && coreRecord.modules.every((item) => typeof item === "string")
    && typeof coreRecord.packet_fingerprint === "string"
    && typeof coreRecord.workflow_fingerprint === "string"
    && typeof coreRecord.stage === "string"
    && evidenceRecord.source === "recorded_fixture"
    && evidenceRecord.live_model_called === false
    && typeof evidenceRecord.summary === "string"
    && Array.isArray(evidenceRecord.findings)
    && evidenceRecord.findings.every((finding) => {
      if (!finding || typeof finding !== "object" || Array.isArray(finding)) return false;
      const item = finding as Record<string, unknown>;
      return typeof item.code === "string" && typeof item.severity === "string" && typeof item.owner === "string";
    })
    && receipt.live_model_called === false
    && receipt.uploads === 0
    && receipt.canon_mutated === false
    && receipt.authority === false;
}

export type LoadingOwner = {
  begin(): symbol;
  isOwner(token: symbol): boolean;
  finish(token: symbol): boolean;
};

export function createLoadingOwner(): LoadingOwner {
  let owner: symbol | undefined;
  return {
    begin() {
      owner = Symbol("loading-owner");
      return owner;
    },
    isOwner(token) {
      return owner === token;
    },
    finish(token) {
      if (owner !== token) return false;
      owner = undefined;
      return true;
    },
  };
}

export type BusyGate = { tryBegin(): boolean; finish(): void };

export function createBusyGate(): BusyGate {
  let busy = false;
  return {
    tryBegin() {
      if (busy) return false;
      busy = true;
      return true;
    },
    finish() {
      busy = false;
    },
  };
}

export type ExclusiveWorkerExecutor = {
  run<T>(
    load: () => Promise<T>,
    execute: (runtime: T) => Promise<void> | void,
    cleanup: (runtime: T) => void,
  ): { accepted: true; promise: Promise<void> } | { accepted: false };
};

export function createExclusiveWorkerExecutor(): ExclusiveWorkerExecutor {
  let busy = false;
  return {
    run<T>(load: () => Promise<T>, execute: (runtime: T) => Promise<void> | void, cleanup: (runtime: T) => void) {
      if (busy) return { accepted: false };
      busy = true;
      const promise = (async () => {
        let runtime: T | undefined;
        try {
          runtime = await load();
          await execute(runtime);
        } finally {
          if (runtime !== undefined) cleanup(runtime);
          busy = false;
        }
      })();
      return { accepted: true, promise };
    },
  };
}

export function isCurrentWorkerEvent(input: {
  disposed: boolean;
  lifecycle: { isCurrent(lease: any): boolean };
  lease: WorkerLease<any>;
  flight: { isCurrent(token: symbol): boolean };
  token: symbol;
  requestId: string;
  eventId: string;
}): boolean {
  return !input.disposed
    && input.lifecycle.isCurrent(input.lease)
    && input.flight.isCurrent(input.token)
    && input.requestId === input.eventId;
}

export function captureWorkerErrorOwnership(input: Parameters<typeof isCurrentWorkerEvent>[0]): boolean {
  return isCurrentWorkerEvent(input);
}

export function shouldCommitPublicationResult(input: {
  capturedEpoch: number;
  currentEpoch: number;
  capturedProfile: string;
  currentProfile: string;
}): boolean {
  return input.capturedEpoch === input.currentEpoch && input.capturedProfile === input.currentProfile;
}

export type Flight<T> = {
  token: symbol;
  promise: Promise<T>;
  resolve(value: T): void;
  reject(reason: unknown): void;
};

export type SingleFlight<T> = {
  tryBegin(): { accepted: true; flight: Flight<T> } | { accepted: false; error: WorkerFailure };
  isCurrent(token: symbol): boolean;
  finish(token: symbol): void;
  resolve(token: symbol, value: T): void;
  reject(token: symbol, reason: unknown): void;
  dispose(reason?: Error): void;
};

export function createSingleFlight<T>(): SingleFlight<T> {
  let current: Flight<T> | undefined;
  let disposed = false;

  const dispose = (reason?: Error) => {
    if (disposed) return;
    disposed = true;
    const pending = current;
    current = undefined;
    if (pending) pending.reject(reason && "code" in reason && reason.code === "worker_disposed" ? reason : failure("worker_disposed", reason?.message ?? "worker lifecycle is disposed"));
  };

  return {
    tryBegin() {
      if (disposed) return { accepted: false, error: failure("worker_disposed", "worker lifecycle is disposed") };
      if (current) return { accepted: false, error: failure("worker_busy", "worker request is already running") };
      const token = Symbol("worker-flight");
      let settled = false;
      let resolvePromise!: (value: T | PromiseLike<T>) => void;
      let rejectPromise!: (reason?: unknown) => void;
      const promise = new Promise<T>((resolve, reject) => {
        resolvePromise = resolve;
        rejectPromise = reject;
      });
      const flight: Flight<T> = {
        token,
        promise,
        resolve(value) {
          if (settled) return;
          settled = true;
          resolvePromise(value);
        },
        reject(reason) {
          if (settled) return;
          settled = true;
          rejectPromise(reason);
        },
      };
      current = flight;
      return { accepted: true, flight };
    },

    isCurrent(token) {
      return !disposed && current?.token === token;
    },

    finish(token) {
      if (current?.token === token) current = undefined;
    },

    resolve(token, value) {
      if (current?.token === token) current.resolve(value);
    },

    reject(token, reason) {
      if (current?.token === token) current.reject(reason);
    },

    dispose,
  };
}
