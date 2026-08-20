export type ObservabilityDisplayStatus =
  | "pass"
  | "warn"
  | "blocked"
  | "not_applicable"
  | "pending"
  | "unavailable";

export interface SourceIdentity {
  schema: string;
  fingerprint?: string;
}

export interface CoreOwnedStatus {
  status_owner: "core_or_source_projection";
  status: ObservabilityDisplayStatus;
  source: SourceIdentity;
  what_validated: string[];
  what_not_validated: string[];
  evidence_refs?: string[];
  blocking_codes?: string[];
  repair_owner?: string;
  reviewer_provenance?: Record<string, unknown>;
  fresh_realization_required?: boolean;
}

export interface ProductionLaneProjection {
  id:
    | "candidate"
    | "surface"
    | "reader_engagement"
    | "independent_production_review"
    | "continuity"
    | "production_readiness"
    | "canon";
  label: string;
  state?: CoreOwnedStatus;
}

export interface SemanticCatalogPack {
  id: string;
  description?: string;
  contracts: string[];
  load_when?: string;
}

export interface SemanticCatalogProjection {
  schema?: string;
  loading_policy?: string;
  packs?: SemanticCatalogPack[];
  model_execution?: boolean;
  [key: string]: unknown;
}

export interface FrameworkDoctorProjection {
  schema?: string;
  framework_version?: string;
  ok?: boolean;
  missing?: unknown[];
  forbidden_contracts?: unknown[];
  model_execution?: boolean;
  [key: string]: unknown;
}

export function asSemanticPacks(value: unknown): SemanticCatalogPack[] {
  if (!value || typeof value !== "object") return [];
  const packs = (value as SemanticCatalogProjection).packs;
  if (!Array.isArray(packs)) return [];
  return packs.filter((pack): pack is SemanticCatalogPack => {
    return Boolean(
      pack &&
      typeof pack === "object" &&
      typeof pack.id === "string" &&
      Array.isArray(pack.contracts) &&
      pack.contracts.every((contract) => typeof contract === "string"),
    );
  });
}

export function sourceBooleanStatus(value: boolean | undefined): ObservabilityDisplayStatus {
  if (value === true) return "pass";
  if (value === false) return "blocked";
  return "unavailable";
}

export function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}
