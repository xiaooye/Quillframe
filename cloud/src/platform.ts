export interface TransactionStorageLike {
  get<T = unknown>(key: string): Promise<T | undefined>;
  put<T = unknown>(key: string, value: T): Promise<void>;
  delete(key: string): Promise<boolean>;
  list?<T = unknown>(options?: { prefix?: string }): Promise<Map<string, T>>;
  setAlarm(time: number | Date): Promise<void>;
  deleteAlarm(): Promise<void>;
  rollback?(): void;
}

export interface StorageLike extends TransactionStorageLike {
  transaction<T>(fn: (tx: TransactionStorageLike) => Promise<T>): Promise<T>;
  deleteAll(): Promise<void>;
}

export class StorageTransactionError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

/**
 * The hosted runtime has one storage RMW seam.  Keeping this check at the
 * boundary makes a missing native transaction a typed startup failure rather
 * than silently turning a multi-key operation into independent writes.
 */
export function requireTransactionalStorage(storage: StorageLike): StorageLike {
  if (!storage || typeof storage.transaction !== "function") {
    throw new StorageTransactionError("storage_transaction_required", "Durable Object storage transaction is required");
  }
  return storage;
}

type NativeStorage = {
  get<T = unknown>(key: string): Promise<T | undefined>;
  put<T = unknown>(key: string, value: T): Promise<void>;
  delete(key: string): Promise<boolean>;
  deleteAll(): Promise<void>;
  list?<T = unknown>(options?: { prefix?: string }): Promise<Map<string, T>>;
  transaction<T>(fn: (tx: TransactionStorageLike) => Promise<T>): Promise<T>;
  setAlarm(time: number | Date): Promise<void>;
  deleteAlarm(): Promise<void>;
};

/** Thin adapter for native Durable Object storage; it deliberately has no KV fallback. */
export function adaptDurableObjectStorage(native: NativeStorage): StorageLike {
  if (!native || typeof native.transaction !== "function") {
    throw new StorageTransactionError("storage_transaction_required", "Durable Object storage transaction is required");
  }
  return {
    get: (key) => native.get(key),
    put: (key, value) => native.put(key, value),
    delete: (key) => native.delete(key),
    deleteAll: () => native.deleteAll(),
    list: native.list ? async <T = unknown>(options?: { prefix?: string }) => native.list!(options) as Promise<Map<string, T>> : undefined,
    setAlarm: async (time) => { await native.setAlarm(time); },
    deleteAlarm: async () => { await native.deleteAlarm(); },
    transaction: async (fn) => {
      try {
        return await native.transaction((tx) => fn(tx));
      } catch (error) {
        if (error && typeof error === "object" && "code" in error) throw error;
        throw new StorageTransactionError("storage_transaction_failed", "Durable Object storage transaction failed");
      }
    },
  };
}

export interface StateLike {
  storage: StorageLike;
  blockConcurrencyWhile?<T>(callback: () => Promise<T>): Promise<T> | void;
}

export interface R2ObjectBodyLike {
  arrayBuffer(): Promise<ArrayBuffer>;
  size?: number;
}

export interface R2PutResultLike {
  key: string;
  size: number;
  etag?: string;
}

export interface R2PutOptions {
  httpMetadata?: Record<string, string>;
  customMetadata?: Record<string, string>;
  onlyIf?: { etagDoesNotMatch?: string; etagMatches?: string };
}

export interface R2BucketLike {
  put(key: string, value: ArrayBuffer | Uint8Array, options?: R2PutOptions): Promise<R2PutResultLike | null>;
  get(key: string): Promise<R2ObjectBodyLike | null>;
  delete(key: string): Promise<void>;
}

export interface RpcNamespace<T> {
  getByName(name: string): T;
}

export interface FetchBinding {
  fetch(request: Request): Promise<Response>;
}

export type Clock = { now(): number };
export const systemClock: Clock = { now: () => Date.now() };

export interface CloudEnv {
  PUBLIC_ORIGIN: string;
  ASSETS?: FetchBinding;
  WORKOS_CLIENT_ID: string;
  WORKOS_API_KEY: string;
  WORKOS_REDIRECT_URI: string;
  SESSION_VAULT_KEY_B64: string;
  PROJECT_BUNDLE_KEY_B64: string;
  PROJECT_BUNDLE_KEY_ID?: string;
  PROJECT_BUNDLE_PREVIOUS_KEY_B64?: string;
  PROJECT_BUNDLE_PREVIOUS_KEY_ID?: string;
  WORKSPACE_COORDINATOR: RpcNamespace<WorkspaceCoordinatorStub>;
  SESSION_VAULT: RpcNamespace<SessionVaultStub>;
  PROJECT_BUNDLES: R2BucketLike;
  CORE_CONTAINER: RpcNamespace<FetchBinding>;
  CORE_PROOF_KEY_B64: string;
  CORE_PROOF_PREVIOUS_KEY_B64?: string;
  CORE_PROOF_KEY_ID: string;
  CORE_PROOF_PREVIOUS_KEY_ID?: string;
  ENDPOINT_EGRESS: FetchBinding;
  fetch?: typeof globalThis.fetch;
}

export interface WorkspaceCoordinatorStub {
  beginAuth(returnTo?: string): Promise<AuthTransaction>;
  consumeAuth(transactionId: string, state: string): Promise<AuthTransaction>;
  consumeCoreNonce(input: { session_id: string; project_id: string | null; nonce: string; proof_digest: string; issued_at: number; expires_at: number }): Promise<{ schema: "quillframe_core_nonce_receipt_v1"; consumed: true; authority: false }>;
  assertWorkspaceBinding(workspace_id: string): Promise<void>;
  prepareProjectVersion(input: ProjectVersionPreparationInput): Promise<ProjectVersionPreparationReceipt>;
  beginProjectVersionGc(input: ProjectVersionGcInput): Promise<ProjectVersionGcReceipt>;
  finishProjectVersionGc(input: ProjectVersionGcFinishInput): Promise<ProjectVersionGcReceipt>;
  readProjectVersionGcOperation(input: { project_id: string; operation_id: string }): Promise<{ receipt: ProjectVersionGcReceipt; retention_before: number } | undefined>;
  readProjectTombstoneOperation(input: { project_id: string; operation_id: string }): Promise<ProjectPointer | undefined>;
  createSession(input: { identity_id: string; workos_session_id?: string }): Promise<SessionCreation>;
  validateSession(cookieToken: string, csrfToken?: string): Promise<SessionProjection>;
  destroySession(cookieToken: string): Promise<{ destroyed: true; session_id: string; authority: false }>;
  readProjectPointer(projectId: string): Promise<ProjectPointer | undefined>;
  casProjectPointer(input: ProjectPointerCasInput): Promise<ProjectPointer>;
  casProjectTombstone(input: ProjectTombstoneInput): Promise<ProjectPointer>;
  destroyAll(): Promise<void>;
}

export interface SessionVaultStub {
  leaseSecret(input: SecretLeaseInput): Promise<SecretLeaseReceipt>;
  destroySession(input: { workspace_id: string; session_id: string }): Promise<{ destroyed: number; authority: false }>;
  destroyAll(): Promise<void>;
}

export interface ProjectPointer {
  schema: "quillframe_cloud_project_pointer_v1";
  workspace_id: string;
  project_id: string;
  pointer_version: number;
  state: "active" | "deleted";
  version_id?: string;
  object_key?: string;
  plaintext_fingerprint?: string;
  updated_at: number;
  authority: false;
}

export type ProjectPointerNext = {
  schema?: "quillframe_cloud_project_pointer_v1";
  workspace_id: string;
  project_id?: string;
  state: "active";
  version_id: string;
  object_key: string;
  plaintext_fingerprint: string;
  authority?: false;
};

export interface ProjectPointerCasInput {
  project_id: string;
  expected_pointer_version: number;
  next: ProjectPointerNext;
}

export interface ProjectTombstoneInput {
  project_id: string;
  expected_pointer_version: number;
  reason: string;
  operation_id: string;
}

export interface ProjectVersionPreparationInput {
  operation_id: string;
  input_fingerprint: string;
  workspace_id: string;
  project_id: string;
  expected_pointer_version: number;
  version_id: string;
  object_key: string;
  plaintext_fingerprint: string;
  byte_size: number;
}

export interface ProjectVersionPreparationReceipt {
  schema: "quillframe_cloud_project_version_preparation_v1";
  operation_id: string;
  input_fingerprint: string;
  workspace_id: string;
  project_id: string;
  expected_pointer_version: number;
  version_id: string;
  object_key: string;
  plaintext_fingerprint: string;
  byte_size: number;
  status: "prepared" | "replayed";
  authority: false;
}

export interface ProjectVersionGcInput {
  project_id: string;
  version_id: string;
  operation_id: string;
  retention_before: number;
}

export interface ProjectVersionGcFinishInput {
  project_id: string;
  version_id: string;
  operation_id: string;
  deleted: boolean;
}

export interface ProjectVersionGcReceipt {
  schema: "quillframe_cloud_project_version_gc_v1";
  operation_id: string;
  project_id: string;
  version_id: string;
  workspace_id: string;
  object_key: string;
  plaintext_fingerprint: string;
  byte_size: number;
  pointer_version: number;
  status: "pending" | "completed";
  authority: false;
}

export interface AuthTransaction {
  schema: "quillframe_auth_transaction_v1";
  transaction_id: string;
  state: string;
  code_verifier: string;
  code_challenge: string;
  return_to: string;
  expires_at: number;
  authority: false;
}

export interface SessionCreation {
  schema: "quillframe_cloud_session_creation_v1";
  workspace_id: string;
  workspace_handle: string;
  session_id: string;
  cookie_token: string;
  csrf_token: string;
  created_at: number;
  idle_expires_at: number;
  absolute_expires_at: number;
  authority: false;
}

export interface SessionProjection {
  schema: "quillframe_cloud_session_projection_v1";
  workspace_id: string;
  workspace_handle: string;
  session_id: string;
  workos_session_id?: string;
  idle_expires_at: number;
  absolute_expires_at: number;
  authority: false;
}

export interface SecretLeaseInput {
  workspace_id: string;
  session_id: string;
  purpose: "workos_access" | "workos_refresh" | "model_endpoint";
  secret: string;
}

export interface SecretLeaseReceipt {
  schema: "quillframe_secret_lease_receipt_v1";
  lease_id: string;
  workspace_id: string;
  session_id: string;
  purpose: SecretLeaseInput["purpose"];
  idle_expires_at: number;
  absolute_expires_at: number;
  encrypted: true;
  authority: false;
}
