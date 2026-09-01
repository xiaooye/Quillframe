export interface UserTastePolicy {
  schema: "quillframe_user_taste_auto_activation_policy_v1";
  policy_id: string;
  enabled: boolean;
  policy_version: number;
  source_kinds: Array<"corpus" | "feedback" | "user_edit">;
  authorization_ref: string | null;
  authorized_at: string | null;
  revoked_at: string | null;
  authority_scope: "user_taste_only";
  framework_write: false;
  canon_write: false;
  fingerprint: string;
}

export interface UserTastePreference {
  hypothesis_id: string;
  scope: "user_taste";
  project_id: string | null;
  dimension: string;
  statement: string;
  mechanism: string;
  state: "candidate" | "active" | "contested" | "superseded" | "deprecated";
  confidence: number;
  applicability: Record<string, unknown>;
  evidence_ids: string[];
  contradiction_ids: string[];
  version: number;
}

export interface UserTasteTransition {
  preference: UserTastePreference;
  receipt: {
    schema: "quillframe_user_taste_activation_receipt_v1";
    hypothesis_id: string;
    action: "pause" | "withdraw";
    before_version: number;
    after_version: number;
    reason: string;
    authority: false;
  };
}

const record = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const fingerprint = (value: unknown): value is string => typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);
const nullableText = (value: unknown): value is string | null => value === null || text(value);
const states = new Set(["candidate", "active", "contested", "superseded", "deprecated"]);
const sourceKinds = new Set(["corpus", "feedback", "user_edit"]);

export function parseUserTastePolicy(value: unknown): UserTastePolicy {
  if (!record(value) || value.schema !== "quillframe_user_taste_auto_activation_policy_v1"
    || !text(value.policy_id) || typeof value.enabled !== "boolean"
    || !Number.isSafeInteger(value.policy_version) || (value.policy_version as number) < 0
    || !Array.isArray(value.source_kinds) || !value.source_kinds.length
    || value.source_kinds.some((kind) => typeof kind !== "string" || !sourceKinds.has(kind))
    || new Set(value.source_kinds).size !== value.source_kinds.length
    || !nullableText(value.authorization_ref) || !nullableText(value.authorized_at) || !nullableText(value.revoked_at)
    || value.authority_scope !== "user_taste_only" || value.framework_write !== false || value.canon_write !== false
    || !fingerprint(value.fingerprint)) throw new Error("user_taste_policy_invalid");
  return value as unknown as UserTastePolicy;
}

export function parseUserTastePreference(value: unknown): UserTastePreference {
  if (!record(value) || !text(value.hypothesis_id) || value.scope !== "user_taste"
    || value.project_id !== null && !text(value.project_id) || !text(value.dimension)
    || !text(value.statement) || typeof value.mechanism !== "string" || !states.has(String(value.state))
    || typeof value.confidence !== "number" || !Number.isFinite(value.confidence)
    || !record(value.applicability) || !Array.isArray(value.evidence_ids) || !value.evidence_ids.every(text)
    || !Array.isArray(value.contradiction_ids) || !value.contradiction_ids.every(text)
    || !Number.isSafeInteger(value.version) || (value.version as number) < 1) throw new Error("user_taste_preference_invalid");
  return value as unknown as UserTastePreference;
}

export function parseUserTastePreferences(value: unknown): UserTastePreference[] {
  if (!Array.isArray(value) || value.length > 500) throw new Error("user_taste_preference_list_invalid");
  const items = value.map(parseUserTastePreference);
  if (new Set(items.map((item) => item.hypothesis_id)).size !== items.length) throw new Error("user_taste_preference_list_invalid");
  return items;
}

export function parseUserTasteTransition(
  value: unknown,
  expected: { hypothesis_id: string; expected_version: number; action: "pause" | "withdraw"; reason: string },
): UserTasteTransition | { status: "unsupported"; performed: false } {
  if (record(value) && value.schema === "quillframe_user_taste_operation_v1" && value.status === "unsupported" && value.performed === false) {
    return value as { status: "unsupported"; performed: false };
  }
  if (!record(value) || !record(value.receipt)) throw new Error("user_taste_transition_invalid");
  const preference = parseUserTastePreference(value.preference);
  const receipt = value.receipt;
  if (receipt.schema !== "quillframe_user_taste_activation_receipt_v1"
    || receipt.hypothesis_id !== expected.hypothesis_id || receipt.action !== expected.action
    || receipt.before_version !== expected.expected_version || receipt.after_version !== expected.expected_version + 1
    || receipt.reason !== expected.reason || receipt.authority !== false
    || preference.hypothesis_id !== expected.hypothesis_id || preference.version !== expected.expected_version + 1
    || preference.state !== (expected.action === "pause" ? "contested" : "deprecated")) {
    throw new Error("user_taste_transition_invalid");
  }
  return value as unknown as UserTasteTransition;
}
