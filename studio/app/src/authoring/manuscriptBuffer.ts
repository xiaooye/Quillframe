export type ManuscriptSaveState = "idle" | "dirty" | "saving" | "saved" | "conflict" | "failed";

export interface ManuscriptBuffer {
  project_id: string;
  document_id: string;
  content: string;
  parent_revision_id: string | null;
  content_fingerprint?: string;
  state: ManuscriptSaveState;
  dirty: boolean;
  error?: string;
}

export interface ManuscriptSaveRequest {
  project_id: string;
  document_id: string;
  content: string;
  expected_parent_revision_id: string | null;
}

interface SaveReceipt { revision_id: string; content_fingerprint: string; deduplicated: boolean }

async function contentFingerprint(content: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content));
  return `sha256:${Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

/** A transient editor buffer. Only an exact Core receipt advances its saved parent. */
export function createManuscriptBuffer(options: {
  save: (request: ManuscriptSaveRequest) => Promise<SaveReceipt>;
  changed: (buffer: ManuscriptBuffer | undefined) => void;
}) {
  let value: ManuscriptBuffer | undefined;
  let epoch = 0;
  let editVersion = 0;
  let savedVersion = 0;
  let inFlight: Promise<boolean> | undefined;
  const publish = () => options.changed(value && { ...value });

  const flush = (): Promise<boolean> => {
    if (!value) return Promise.resolve(false);
    if (inFlight) return inFlight;
    if (!value.dirty) return Promise.resolve(true);
    if (value.state === "conflict") return Promise.resolve(false);
    const requestEpoch = epoch;
    const task = async () => {
      while (value && requestEpoch === epoch && savedVersion !== editVersion) {
        const version = editVersion;
        const request: ManuscriptSaveRequest = {
          project_id: value.project_id, document_id: value.document_id,
          content: value.content, expected_parent_revision_id: value.parent_revision_id,
        };
        value = { ...value, state: "saving", error: undefined };
        publish();
        try {
          const result = await options.save(request);
          if (requestEpoch !== epoch || !value) return false;
          if (!result || typeof result.revision_id !== "string" || !result.revision_id.trim()
            || typeof result.deduplicated !== "boolean" || result.content_fingerprint !== await contentFingerprint(request.content)) {
            throw new Error("revision_save_receipt_binding_invalid");
          }
          if (requestEpoch !== epoch || !value) return false;
          savedVersion = version;
          const dirty = savedVersion !== editVersion;
          value = { ...value, parent_revision_id: result.revision_id, content_fingerprint: result.content_fingerprint,
            state: dirty ? "dirty" : "saved", dirty, error: undefined };
          publish();
        } catch (cause) {
          if (requestEpoch !== epoch || !value) return false;
          const error = cause instanceof Error ? cause.message : String(cause);
          value = { ...value, state: /revision conflict|ConflictError|before-state/i.test(error) ? "conflict" : "failed", dirty: true, error };
          publish();
          return false;
        }
      }
      return requestEpoch === epoch && !!value && !value.dirty;
    };
    inFlight = task().finally(() => { if (requestEpoch === epoch) inFlight = undefined; });
    return inFlight;
  };

  const flushAndRefresh = async (refresh: () => Promise<void>): Promise<boolean> => {
    const requestEpoch = epoch;
    if (!value) return false;
    do {
      if (!await flush() || requestEpoch !== epoch || !value) return false;
      await refresh();
      // Metadata reads can outlive the save. Any edits made during those reads
      // must be saved against the new parent before a caller may leave/rebind.
      if (requestEpoch !== epoch || !value) return false;
    } while (value.dirty);
    return requestEpoch === epoch && !!value && !value.dirty;
  };

  return {
    current: () => value && { ...value },
    bind: (source: Omit<ManuscriptBuffer, "state" | "dirty" | "error"> | undefined) => {
      epoch += 1; editVersion = 0; savedVersion = 0; inFlight = undefined;
      value = source && { ...source, state: "idle", dirty: false };
      publish();
    },
    edit: (content: string) => {
      if (!value || content === value.content) return;
      editVersion += 1;
      value = { ...value, content, dirty: true, state: value.state === "conflict" ? "conflict" : "dirty" };
      publish();
    },
    flush,
    flushAndRefresh,
    dispose: () => { epoch += 1; value = undefined; inFlight = undefined; },
  };
}
