function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

export class TransactionRolledBackError extends Error {
  constructor() { super("transaction was rolled back"); this.code = "transaction_rolled_back"; }
}

class TransactionView {
  constructor(owner, values) {
    this.owner = owner;
    this.values = values;
    this.alarm = owner.alarm;
    this.rolledBack = false;
  }

  ensureOpen() {
    if (this.rolledBack) throw new TransactionRolledBackError();
  }

  async get(key) {
    this.ensureOpen();
    return clone(this.values.get(key));
  }

  async put(key, value) {
    this.ensureOpen();
    this.values.set(key, clone(value));
  }

  async delete(key) {
    this.ensureOpen();
    return this.values.delete(key);
  }

  async list({ prefix = "" } = {}) {
    this.ensureOpen();
    return new Map([...this.values]
      .filter(([key]) => key.startsWith(prefix))
      .map(([key, value]) => [key, clone(value)]));
  }

  async setAlarm(value) {
    this.ensureOpen();
    this.owner.consumeAlarmFailure();
    this.alarm = value;
  }

  async deleteAlarm() {
    this.ensureOpen();
    this.owner.consumeAlarmFailure();
    this.alarm = undefined;
  }

  rollback() {
    this.ensureOpen();
    this.rolledBack = true;
  }
}

export class SerialTransactionStorage {
  values = new Map();
  alarm = undefined;
  active = 0;
  maxActive = 0;
  externalIoDuringTransaction = 0;
  #queue = Promise.resolve();
  #commitBarrier = undefined;
  #nextCommitFailure = undefined;
  #nextAlarmFailure = undefined;

  async get(key) { return clone(this.values.get(key)); }
  async put(key, value) { this.values.set(key, clone(value)); }
  async delete(key) { return this.values.delete(key); }
  async deleteAll() { this.values.clear(); }
  async setAlarm(value) { this.alarm = value; }
  async deleteAlarm() { this.alarm = undefined; }
  async list({ prefix = "" } = {}) {
    return new Map([...this.values]
      .filter(([key]) => key.startsWith(prefix))
      .map(([key, value]) => [key, clone(value)]));
  }

  async transaction(callback) {
    const run = this.#queue.then(async () => {
      this.active += 1;
      this.maxActive = Math.max(this.maxActive, this.active);
      const snapshot = new Map([...this.values].map(([key, value]) => [key, clone(value)]));
      const tx = new TransactionView(this, snapshot);
      try {
        const result = await callback(tx);
        if (tx.rolledBack) throw new TransactionRolledBackError();
        if (this.#commitBarrier) {
          const barrier = this.#commitBarrier;
          this.#commitBarrier = undefined;
          barrier.enteredResolve();
          await barrier.wait;
        }
        if (this.#nextCommitFailure) {
          const failure = this.#nextCommitFailure;
          this.#nextCommitFailure = undefined;
          throw failure;
        }
        this.values.clear();
        for (const [key, value] of snapshot) this.values.set(key, clone(value));
        this.alarm = tx.alarm;
        // The transaction result is an in-memory receipt/error owned by the
        // caller; cloning it would erase custom error prototypes/codes.
        return result;
      } catch (error) {
        // A callback failure must not leave a one-shot test barrier armed for
        // the next transaction; the serial queue remains reusable.
        if (this.#commitBarrier) {
          const barrier = this.#commitBarrier;
          this.#commitBarrier = undefined;
          barrier.enteredResolve();
          barrier.release();
        }
        throw error;
      } finally {
        this.active -= 1;
      }
    });
    this.#queue = run.catch(() => undefined);
    return run;
  }

  installCommitBarrier() {
    if (this.#commitBarrier) throw new Error("commit barrier already installed");
    let enteredResolve;
    let release;
    const entered = new Promise((resolve) => { enteredResolve = resolve; });
    const wait = new Promise((resolve) => { release = resolve; });
    this.#commitBarrier = { enteredResolve, entered, wait };
    return { entered, release };
  }

  failNextCommit(error = new Error("injected transaction commit failure")) {
    this.#nextCommitFailure = error;
  }

  failNextAlarm(error = new Error("injected alarm failure")) {
    this.#nextAlarmFailure = error;
  }

  consumeAlarmFailure() {
    if (this.#nextAlarmFailure) {
      const failure = this.#nextAlarmFailure;
      this.#nextAlarmFailure = undefined;
      throw failure;
    }
  }

  markExternalIo() {
    if (this.active > 0) this.externalIoDuringTransaction += 1;
  }
}

export class MemoryStorage extends SerialTransactionStorage {}

export class MemoryState {
  constructor(storage = new MemoryStorage()) { this.storage = storage; }
  blockConcurrencyWhile(callback) { return callback(); }
}

export class SerialTransactionState extends MemoryState {}

export const keyBase64 = (fill = 7) => Buffer.alloc(32, fill).toString("base64");

export class MemoryBucket {
  values = new Map();
  supportsConditional = true;
  async put(key, value, options = {}) {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
    if (options.onlyIf && !this.supportsConditional) return undefined;
    if (options.onlyIf?.etagDoesNotMatch === "*" && this.values.has(key)) return null;
    this.values.set(key, { bytes: new Uint8Array(bytes), options: structuredClone(options) });
    return { key, size: bytes.byteLength };
  }
  async get(key) {
    const item = this.values.get(key);
    if (!item) return null;
    return { size: item.bytes.byteLength, arrayBuffer: async () => item.bytes.slice().buffer };
  }
  async delete(key) { this.values.delete(key); }
}
