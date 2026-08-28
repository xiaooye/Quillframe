import { base64Url, fromBase64, open, seal, sha256Hex } from "./crypto.js";
import { canonicalJsonBytes, parseCanonicalJsonBytes } from "./core-provenance.js";
import type { ProjectPointer, ProjectVersionGcReceipt, R2BucketLike, R2PutResultLike } from "./platform.js";
import { MAX_NATIVE_BACKUP_BODY } from "./core-limits.js";

export const PROJECT_BUNDLE_TRANSPORT_LIMIT = MAX_NATIVE_BACKUP_BODY;
const MAX_ENVELOPE_BYTES = 192 * 1024 * 1024;
const ID_RE = /^[A-Za-z0-9._:-]{1,128}$/;
const PROJECT_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
const FP_RE = /^sha256:[0-9a-f]{64}$/;

export type NativeBackupReceipt = {
  schema: "quillframe_native_backup_verification_v1";
  bundle_schema: "quillframe_backup_bundle_v1";
  body_fingerprint: string;
  bundle_fingerprint: string;
  project_id: string;
  scope: "novel";
  database_fingerprint: string;
  database_bytes: number;
  blob_count: number;
  byte_size: number;
  verified: true;
  authority: false;
};

export type HostedVersionReceipt = {
  schema: "quillframe_cloud_project_version_receipt_v2";
  workspace_id: string;
  project_id: string;
  version_id: string;
  object_key: string;
  body_fingerprint: string;
  plaintext_fingerprint: string;
  byte_size: number;
  ciphertext_fingerprint: string;
  encrypted: true;
  authority: false;
};

type BundleEnvelope = {
  schema: "quillframe_encrypted_project_bundle_v2";
  cipher: "AES-256-GCM";
  key_version: string;
  workspace_id: string;
  project_id: string;
  version_id: string;
  object_key: string;
  plaintext_fingerprint: string;
  plaintext_byte_size: number;
  iv: string;
  ciphertext: string;
  ciphertext_fingerprint: string;
  authority: false;
};

export type ProjectStoreKeyRing = { current_key_id?: string; previous_key_id?: string; previous_key_base64?: string };

export class ProjectStoreError extends Error {
  constructor(public readonly code: string, message = "project storage operation failed") { super(message); }
}

function fail(code: string, message = "project storage operation failed"): never { throw new ProjectStoreError(code, message); }
function exactKeys(value: unknown, keys: readonly string[]): boolean { return !!value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).sort().join(",") === [...keys].sort().join(","); }
function validProjectId(value: unknown): value is string { return typeof value === "string" && PROJECT_ID_RE.test(value); }
function validId(value: unknown): value is string { return typeof value === "string" && ID_RE.test(value); }
function validFingerprint(value: unknown): value is string { return typeof value === "string" && FP_RE.test(value); }
function validConditionalPutResult(value: unknown, expectedKey: string, expectedSize: number): value is R2PutResultLike {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const result = value as Partial<R2PutResultLike>;
  return result.key === expectedKey && Number.isSafeInteger(result.size) && result.size === expectedSize && (result.etag === undefined || typeof result.etag === "string");
}
function owned(value: Uint8Array): Uint8Array { return new Uint8Array(value); }
function standardBase64(value: Uint8Array): string { let binary = ""; for (const byte of value) binary += String.fromCharCode(byte); return btoa(binary); }

export function assertProjectBundleTransportSize(value: unknown): asserts value is number {
  if (!Number.isSafeInteger(value) || (value as number) <= 0 || (value as number) > PROJECT_BUNDLE_TRANSPORT_LIMIT) fail("project_bundle_transport_limit");
}

function decodeKey(value: string): Uint8Array {
  if (typeof value !== "string" || !/^[A-Za-z0-9+/]+={0,2}$/.test(value)) fail("project_key_config_invalid");
  let key: Uint8Array;
  try { key = fromBase64(value); } catch { fail("project_key_config_invalid"); }
  if (standardBase64(key) !== value || key.byteLength !== 32) fail("project_key_config_invalid");
  return key;
}

export function assertNativeBackupReceipt(value: unknown): asserts value is NativeBackupReceipt {
  const keys = ["schema", "bundle_schema", "body_fingerprint", "bundle_fingerprint", "project_id", "scope", "database_fingerprint", "database_bytes", "blob_count", "byte_size", "verified", "authority"] as const;
  if (!exactKeys(value, keys)) fail("project_verification_invalid");
  const receipt = value as NativeBackupReceipt;
  if (receipt.schema !== "quillframe_native_backup_verification_v1" || receipt.bundle_schema !== "quillframe_backup_bundle_v1" || !validFingerprint(receipt.body_fingerprint) || !validFingerprint(receipt.bundle_fingerprint) || receipt.body_fingerprint !== receipt.bundle_fingerprint || !validProjectId(receipt.project_id) || receipt.scope !== "novel" || !validFingerprint(receipt.database_fingerprint) || !Number.isSafeInteger(receipt.database_bytes) || !Number.isSafeInteger(receipt.blob_count) || receipt.blob_count < 0 || receipt.blob_count > 1022 || !Number.isSafeInteger(receipt.byte_size) || receipt.verified !== true || receipt.authority !== false) fail("project_verification_invalid");
  assertProjectBundleTransportSize(receipt.database_bytes);
  assertProjectBundleTransportSize(receipt.byte_size);
}

function validatePointer(pointer: ProjectPointer, workspaceId: string, projectId: string, allowDeleted = false): void {
  if (!pointer || pointer.schema !== "quillframe_cloud_project_pointer_v1" || pointer.workspace_id !== workspaceId || pointer.project_id !== projectId || (!allowDeleted && pointer.state !== "active") || allowDeleted && pointer.state !== "active" && pointer.state !== "deleted" || !validFingerprint(pointer.version_id) || !validFingerprint(pointer.plaintext_fingerprint) || typeof pointer.object_key !== "string" || pointer.object_key.length < 1 || pointer.object_key.length > 512 || pointer.authority !== false) fail("project_pointer_invalid");
}

export class EncryptedProjectStore {
  private readonly keys: Map<string, Uint8Array>;
  private readonly currentKeyId: string;

  constructor(private readonly bucket: R2BucketLike, currentKeyBase64: string, ring: ProjectStoreKeyRing = {}) {
    this.currentKeyId = ring.current_key_id ?? "current";
    if (!validId(this.currentKeyId)) fail("project_key_config_invalid");
    if ((ring.previous_key_id === undefined) !== (ring.previous_key_base64 === undefined) || ring.previous_key_id === this.currentKeyId) fail("project_key_config_invalid");
    this.keys = new Map([[this.currentKeyId, decodeKey(currentKeyBase64)]]);
    if (ring.previous_key_id !== undefined && ring.previous_key_base64 !== undefined) {
      if (!validId(ring.previous_key_id)) fail("project_key_config_invalid");
      this.keys.set(ring.previous_key_id, decodeKey(ring.previous_key_base64));
    }
  }

  async uploadVerified(input: { workspace_id: string; project_id: string; bundle: Uint8Array; verification: NativeBackupReceipt }): Promise<HostedVersionReceipt> {
    if (!validId(input.workspace_id) || !validProjectId(input.project_id)) fail("project_identity_invalid");
    if (!(input.bundle instanceof Uint8Array)) fail("project_bundle_transport_limit");
    assertProjectBundleTransportSize(input.bundle.byteLength);
    assertNativeBackupReceipt(input.verification);
    const bodyFingerprint = `sha256:${await sha256Hex(input.bundle)}`;
    if (input.verification.project_id !== input.project_id || input.verification.byte_size !== input.bundle.byteLength || input.verification.body_fingerprint !== bodyFingerprint) fail("project_verification_mismatch");
    const objectKey = await this.objectKey(input.workspace_id, input.project_id, bodyFingerprint);
    const encrypted = await seal(owned(input.bundle), this.keyBase64(this.currentKeyId), this.aad(input.workspace_id, input.project_id, bodyFingerprint, objectKey, this.currentKeyId));
    const ciphertextFingerprint = `sha256:${await sha256Hex(fromBase64(encrypted.ciphertext))}`;
    const envelope: BundleEnvelope = { schema: "quillframe_encrypted_project_bundle_v2", cipher: "AES-256-GCM", key_version: this.currentKeyId, workspace_id: input.workspace_id, project_id: input.project_id, version_id: bodyFingerprint, object_key: objectKey, plaintext_fingerprint: bodyFingerprint, plaintext_byte_size: input.bundle.byteLength, iv: encrypted.iv, ciphertext: encrypted.ciphertext, ciphertext_fingerprint: ciphertextFingerprint, authority: false };
    const bytes = canonicalJsonBytes(envelope);
    if (bytes.byteLength > MAX_ENVELOPE_BYTES) fail("project_envelope_limit");
    let result: unknown | null;
    try {
      result = await this.bucket.put(objectKey, bytes, { httpMetadata: { contentType: "application/vnd.quillframe.encrypted-project+json" }, customMetadata: { schema: envelope.schema, key_version: envelope.key_version }, onlyIf: { etagDoesNotMatch: "*" } });
    } catch { throw new ProjectStoreError("project_store_write_failed", "project object write failed"); }
    if (result === undefined) fail("project_conditional_put_unsupported");
    if (result === null) {
      const existing = await this.readEnvelope(objectKey, input.workspace_id, input.project_id, bodyFingerprint);
      const plaintext = await this.decryptEnvelope(existing);
      if (plaintext.byteLength !== input.bundle.byteLength || `sha256:${await sha256Hex(plaintext)}` !== bodyFingerprint || !this.bytesEqual(plaintext, input.bundle)) fail("project_version_conflict");
      return this.receiptFromEnvelope(existing);
    }
    if (!validConditionalPutResult(result, objectKey, bytes.byteLength)) fail("project_conditional_put_invalid");
    return this.receiptFromEnvelope(envelope);
  }

  async readVerified(workspaceId: string, projectId: string, pointer: ProjectPointer): Promise<Uint8Array> {
    if (!validId(workspaceId) || !validProjectId(projectId)) fail("project_identity_invalid");
    validatePointer(pointer, workspaceId, projectId);
    const versionId = pointer.version_id;
    const objectKey = pointer.object_key;
    if (typeof versionId !== "string" || typeof objectKey !== "string") fail("project_pointer_invalid");
    const expectedKey = await this.objectKey(workspaceId, projectId, versionId);
    if (objectKey !== expectedKey) fail("project_pointer_invalid");
    const envelope = await this.readEnvelope(expectedKey, workspaceId, projectId, versionId);
    const plaintext = await this.decryptEnvelope(envelope);
    if (`sha256:${await sha256Hex(plaintext)}` !== pointer.plaintext_fingerprint) fail("project_bundle_integrity_failed");
    return plaintext;
  }

  async deleteVerified(workspaceId: string, projectId: string, pointer: ProjectPointer): Promise<void> {
    if (!validId(workspaceId) || !validProjectId(projectId)) fail("project_identity_invalid");
    validatePointer(pointer, workspaceId, projectId, true);
    const versionId = pointer.version_id;
    const objectKey = pointer.object_key;
    if (typeof versionId !== "string" || typeof objectKey !== "string") fail("project_pointer_invalid");
    if (objectKey !== await this.objectKey(workspaceId, projectId, versionId)) fail("project_pointer_invalid");
    try { await this.bucket.delete(objectKey); } catch { throw new ProjectStoreError("project_gc_pending", "project object deletion is pending"); }
  }

  async deleteGcObject(workspaceId: string, projectId: string, receipt: ProjectVersionGcReceipt): Promise<void> {
    if (!validId(workspaceId) || !validProjectId(projectId) || !receipt || receipt.schema !== "quillframe_cloud_project_version_gc_v1" || receipt.project_id !== projectId || receipt.workspace_id !== workspaceId || !validFingerprint(receipt.version_id) || !validFingerprint(receipt.plaintext_fingerprint) || receipt.status !== "pending" || receipt.authority !== false) fail("project_gc_invalid");
    assertProjectBundleTransportSize(receipt.byte_size);
    const expectedKey = await this.objectKey(workspaceId, projectId, receipt.version_id);
    if (receipt.object_key !== expectedKey) fail("project_gc_invalid");
    try { await this.bucket.delete(expectedKey); } catch { throw new ProjectStoreError("project_gc_pending", "project object deletion is pending"); }
  }

  private keyBase64(id: string): string {
    const key = this.keys.get(id);
    if (!key) fail("project_key_version_unknown");
    return standardBase64(key);
  }

  private async readEnvelope(objectKey: string, workspaceId: string, projectId: string, versionId: string): Promise<BundleEnvelope> {
    const object = await this.bucket.get(objectKey);
    if (!object) fail("project_bundle_not_found");
    if (object.size !== undefined && (!Number.isSafeInteger(object.size) || object.size <= 0 || object.size > MAX_ENVELOPE_BYTES)) fail("project_envelope_limit");
    if (object.size === undefined) fail("project_envelope_size_unknown");
    const rawEnvelope = await object.arrayBuffer();
    if (rawEnvelope.byteLength > MAX_ENVELOPE_BYTES) fail("project_envelope_limit");
    let value: unknown;
    try { value = parseCanonicalJsonBytes(new Uint8Array(rawEnvelope), "body", MAX_ENVELOPE_BYTES); } catch { fail("project_envelope_invalid"); }
    if (!exactKeys(value, ["schema", "cipher", "key_version", "workspace_id", "project_id", "version_id", "object_key", "plaintext_fingerprint", "plaintext_byte_size", "iv", "ciphertext", "ciphertext_fingerprint", "authority"])) fail("project_envelope_invalid");
    const envelope = value as BundleEnvelope;
    if (envelope.schema !== "quillframe_encrypted_project_bundle_v2" || envelope.cipher !== "AES-256-GCM" || !validId(envelope.key_version) || !this.keys.has(envelope.key_version) || envelope.workspace_id !== workspaceId || envelope.project_id !== projectId || envelope.version_id !== versionId || envelope.object_key !== objectKey || !validFingerprint(envelope.plaintext_fingerprint) || envelope.plaintext_fingerprint !== versionId || !Number.isSafeInteger(envelope.plaintext_byte_size) || typeof envelope.iv !== "string" || typeof envelope.ciphertext !== "string" || typeof envelope.ciphertext_fingerprint !== "string" || envelope.authority !== false) fail("project_envelope_invalid");
    assertProjectBundleTransportSize(envelope.plaintext_byte_size);
    let iv: Uint8Array; let ciphertext: Uint8Array;
    try { iv = fromBase64(envelope.iv); ciphertext = fromBase64(envelope.ciphertext); } catch { fail("project_envelope_invalid"); }
    if (base64Url(iv) !== envelope.iv || iv.byteLength !== 12 || base64Url(ciphertext) !== envelope.ciphertext || ciphertext.byteLength < 16 || envelope.ciphertext_fingerprint !== `sha256:${await sha256Hex(ciphertext)}`) fail("project_envelope_integrity_failed");
    return envelope;
  }

  private async decryptEnvelope(envelope: BundleEnvelope): Promise<Uint8Array> {
    try {
      const plaintext = await open(envelope, this.keyBase64(envelope.key_version), this.aad(envelope.workspace_id, envelope.project_id, envelope.version_id, envelope.object_key, envelope.key_version));
      if (plaintext.byteLength !== envelope.plaintext_byte_size || `sha256:${await sha256Hex(plaintext)}` !== envelope.plaintext_fingerprint) fail("project_bundle_integrity_failed");
      return plaintext;
    } catch (error) {
      if (error instanceof ProjectStoreError) throw error;
      throw new ProjectStoreError("project_bundle_integrity_failed", "project object authentication failed");
    }
  }

  private receiptFromEnvelope(envelope: BundleEnvelope): HostedVersionReceipt {
    return { schema: "quillframe_cloud_project_version_receipt_v2", workspace_id: envelope.workspace_id, project_id: envelope.project_id, version_id: envelope.version_id, object_key: envelope.object_key, body_fingerprint: envelope.plaintext_fingerprint, plaintext_fingerprint: envelope.plaintext_fingerprint, byte_size: envelope.plaintext_byte_size, ciphertext_fingerprint: envelope.ciphertext_fingerprint, encrypted: true, authority: false };
  }

  private aad(workspaceId: string, projectId: string, versionId: string, objectKey: string, keyVersion: string): string { return `quillframe-project-v2\n${workspaceId}\n${projectId}\n${versionId}\n${objectKey}\n${keyVersion}`; }
  private async objectKey(workspaceId: string, projectId: string, versionId: string): Promise<string> { return `v2/${await sha256Hex(workspaceId)}/${projectId}/versions/${versionId}.qfbundle`; }
  private bytesEqual(left: Uint8Array, right: Uint8Array): boolean { return left.byteLength === right.byteLength && left.every((value, index) => value === right[index]); }
}
