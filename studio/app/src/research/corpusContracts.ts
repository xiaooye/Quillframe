export type CorpusRecord = Record<string, unknown>;
export type CorpusProfile = "general" | "adult_explicit";

export interface CorpusSelectionItem {
  work_id: string;
  title: string;
  creator?: string;
  rights_class?: string;
  selected: boolean;
}

export interface CorpusSelectionProjection {
  collection_id?: string;
  study_id: string;
  profile: CorpusProfile;
  status?: string;
  private_local_only?: true;
  proposal_fingerprint: string;
  eligibility_counts: CorpusEligibilityCounts;
  items: CorpusSelectionItem[];
}

export interface CorpusEligibilityCounts {
  excluded?: number;
  quarantined?: number;
}

export interface CorpusProgress {
  status: string;
  compatibility_work_count: number;
  available_pool_count?: number;
  activated_count?: number;
  analysed_count?: number;
  semantic_attempts?: number;
}

const record = (value: unknown): value is CorpusRecord => !!value && typeof value === "object" && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const fingerprint = (value: unknown): value is string => typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);

export function parseCorpusRecord(value: unknown): CorpusRecord {
  if (!record(value) || !text(value.schema) || value.authority === true || value.canon_authority === true
    || value.framework_write_authority === true) throw new Error("corpus_projection_invalid");
  return value;
}

function parseCorpusItem(value: unknown): CorpusRecord {
  if (!record(value) || value.authority === true || value.canon_authority === true || value.framework_write_authority === true) {
    throw new Error("corpus_projection_invalid");
  }
  return value;
}

function firstText(value: CorpusRecord, keys: string[]): string | undefined {
  for (const key of keys) if (text(value[key])) return value[key] as string;
  return undefined;
}

function firstArray(value: CorpusRecord, keys: string[]): unknown[] {
  for (const key of keys) if (Array.isArray(value[key])) return value[key] as unknown[];
  return [];
}

export function collectionId(value: unknown): string | undefined {
  const projection = parseCorpusRecord(value);
  return firstText(projection, ["collection_id", "id"]);
}

const aggregateCountKeys = {
  excluded: ["excluded_count", "excluded_works", "excluded"],
  quarantined: ["quarantined_count", "quarantined_works", "quarantined"],
} as const;

function aggregateCount(containers: CorpusRecord[], keys: readonly string[]): number | undefined {
  const reported: number[] = [];
  for (const container of containers) for (const key of keys) {
    if (!Object.hasOwn(container, key)) continue;
    const value = container[key];
    if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) throw new Error("corpus_aggregate_counts_invalid");
    reported.push(value);
  }
  if (new Set(reported).size > 1) throw new Error("corpus_aggregate_counts_invalid");
  return reported[0];
}

/** Only closed, non-negative aggregate counts cross the private eligibility boundary. */
export function corpusEligibilityCounts(value: unknown): CorpusEligibilityCounts {
  const projection = parseCorpusRecord(value);
  const containers = [projection, ...["eligibility_counts", "eligibility", "aggregate_counts"]
    .map((key) => projection[key]).filter(record)];
  const excluded = aggregateCount(containers, aggregateCountKeys.excluded);
  const quarantined = aggregateCount(containers, aggregateCountKeys.quarantined);
  return { ...(excluded === undefined ? {} : { excluded }), ...(quarantined === undefined ? {} : { quarantined }) };
}

const privateLabelKeys = new Set(["display_label", "title", "display_name", "filename", "creator", "author"]);
const privateLocatorKey = /(?:^|_)(?:path|locator)(?:_|$)/i;

export function parseCorpusSelection(value: unknown, options: { allowPrivateLabels?: boolean } = {}): CorpusSelectionProjection {
  const projection = parseCorpusRecord(value);
  if (projection.status === "insufficient_eligible_works") {
    throw new Error("corpus_selection_insufficient_eligible_works");
  }
  const allowPrivateLabels = options.allowPrivateLabels === true;
  const privateLocalOnly = projection.private_local_only === true;
  if (allowPrivateLabels ? !privateLocalOnly : Object.hasOwn(projection, "private_local_only")) {
    throw new Error("corpus_selection_private_boundary_invalid");
  }
  if (Object.hasOwn(projection, "exclusion_counts") || Object.hasOwn(projection, "eligibility_details")) {
    throw new Error("corpus_selection_private_boundary_invalid");
  }
  if (Object.keys(projection).some((key) => privateLocatorKey.test(key))) throw new Error("corpus_selection_private_boundary_invalid");
  const collection = firstText(projection, ["collection_id"]);
  const study = firstText(projection, ["study_id", "selection_id"]);
  const profile = projection.profile;
  const proposal = firstText(projection, ["proposal_fingerprint", "proposal_hash", "selection_fingerprint", "fingerprint"]);
  const source = firstArray(projection, ["items", "works", "selection", "selected_works"]);
  if (!study || profile !== "general" && profile !== "adult_explicit"
    || !proposal || !fingerprint(proposal) || source.length !== 120) {
    throw new Error("corpus_selection_projection_invalid");
  }
  const items = source.map((raw): CorpusSelectionItem => {
    if (!record(raw)) throw new Error("corpus_selection_projection_invalid");
    if (Object.keys(raw).some((key) => privateLocatorKey.test(key))) throw new Error("corpus_selection_private_boundary_invalid");
    if (!allowPrivateLabels && Object.keys(raw).some((key) => privateLabelKeys.has(key))) {
      throw new Error("corpus_selection_private_boundary_invalid");
    }
    const workId = firstText(raw, ["work_id", "public_work_id", "id"]);
    if (!workId) throw new Error("corpus_selection_projection_invalid");
    const displayLabel = firstText(raw, ["display_label", "title", "display_name", "filename"]);
    if (allowPrivateLabels && !displayLabel) throw new Error("corpus_selection_private_boundary_invalid");
    return {
      work_id: workId,
      title: allowPrivateLabels ? displayLabel! : workId,
      creator: allowPrivateLabels ? firstText(raw, ["creator", "author"]) : undefined,
      rights_class: firstText(raw, ["rights_class"]),
      selected: raw.selected !== false,
    };
  });
  if (new Set(items.map((item) => item.work_id)).size !== items.length) throw new Error("corpus_selection_projection_invalid");
  const status = firstText(projection, ["status", "state"]);
  return { ...(collection ? { collection_id: collection } : {}), study_id: study, profile,
    ...(status ? { status } : {}),
    ...(privateLocalOnly ? { private_local_only: true as const } : {}), proposal_fingerprint: proposal,
    eligibility_counts: corpusEligibilityCounts(projection), items };
}

export function corpusProgress(value: unknown): CorpusProgress {
  const projection = parseCorpusRecord(value);
  const runner = record(projection.runner) ? projection.runner : {};
  const status = firstText(projection, ["status", "state"]) ?? firstText(runner, ["status", "state"]) ?? "unknown";
  const progress = record(projection.progress) ? projection.progress : record(runner.progress) ? runner.progress : runner;
  const workStates = record(projection.work_states) ? projection.work_states : record(runner.work_states) ? runner.work_states : {};
  const cohortStates = record(projection.cohort_states) ? projection.cohort_states
    : record(runner.cohort_states) ? runner.cohort_states : {};
  const containers = [progress, projection, runner];
  const firstCount = (keys: string[]): number | undefined => {
    for (const container of containers) for (const key of keys) {
      const candidate = container[key];
      if (Number.isSafeInteger(candidate) && (candidate as number) >= 0) return candidate as number;
    }
    return undefined;
  };
  const cohortCount = (key: string): number | undefined => {
    const candidate = cohortStates[key];
    return Number.isSafeInteger(candidate) && (candidate as number) >= 0 ? candidate as number : undefined;
  };
  const compatibilityWorkCount = firstCount(["compatibility_work_count"])
    ?? firstCount(["completed", "completed_count", "processed_count", "completed_works"])
    ?? (Number.isSafeInteger(workStates.studied) && (workStates.studied as number) >= 0 ? workStates.studied as number : undefined)
    ?? (Number.isSafeInteger(workStates.complete) && (workStates.complete as number) >= 0 ? workStates.complete as number : undefined)
    ?? 0;
  const availableUnanalysed = cohortCount("available_unanalysed");
  const activated = firstCount(["activated_count"]) ?? cohortCount("activated");
  const analysed = firstCount(["analysed_count"]) ?? cohortCount("analysed");
  const cohortTotal = availableUnanalysed === undefined || activated === undefined || analysed === undefined
    ? undefined : availableUnanalysed + activated + analysed;
  const availablePool = firstCount(["available_pool_count"]) ?? cohortTotal;
  const semanticAttempts = firstCount(["semantic_attempts"]);
  return {
    status,
    compatibility_work_count: compatibilityWorkCount,
    ...(availablePool === undefined ? {} : { available_pool_count: availablePool }),
    ...(activated === undefined ? {} : { activated_count: activated }),
    ...(analysed === undefined ? {} : { analysed_count: analysed }),
    ...(semanticAttempts === undefined ? {} : { semantic_attempts: semanticAttempts }),
  };
}

export function previewFingerprint(value: unknown): string | undefined {
  const projection = parseCorpusRecord(value);
  return ["preview_fingerprint", "atlas_fingerprint", "bundle_fingerprint", "fingerprint"]
    .map((key) => projection[key]).find(fingerprint) as string | undefined;
}

export function stylePreviewToken(value: unknown): string | undefined {
  const projection = parseCorpusRecord(value);
  const valueToken = projection.preview_token;
  return typeof valueToken === "string" && /^style-preview-[0-9a-f]{64}$/.test(valueToken)
    ? valueToken : undefined;
}

export function corpusVersion(value: unknown): string | undefined {
  const projection = parseCorpusRecord(value);
  return firstText(projection, ["corpus_version", "atlas_fingerprint", "version", "release_id", "public_study_id"]);
}

export function previewBundle(value: unknown): CorpusRecord | undefined {
  const projection = parseCorpusRecord(value);
  return record(projection.bundle) ? projection.bundle : undefined;
}

export function parsePublicCorpusList(value: unknown): CorpusRecord[] {
  if (Array.isArray(value)) return value.map((item) => parseCorpusItem(item));
  const projection = parseCorpusRecord(value);
  const items = firstArray(projection, ["items", "releases", "versions"]);
  if (items.length > 500) throw new Error("public_corpus_list_invalid");
  return items.map((item) => parseCorpusItem(item));
}

const hiddenKey = /(^|_)(content|text|excerpt|raw|body|passage|quote|sample|snippet|prose|novel|path|source_path|collection_path|local_path|preview_token|artifact_dir|exclusion_counts|eligibility_details)(_|$)/i;
const pathLikeValue = /^(?:[A-Za-z]:[\\/]|\\\\|\/(?:Users|home|tmp|var|private|etc)(?:\/|$))/i;

/** Keep Corpus views metadata-only even if a future Core projection grows. */
export function corpusMetadataView(value: unknown, depth = 0): unknown {
  if (depth > 6) return "<nested metadata omitted>";
  if (Array.isArray(value)) return value.slice(0, 120).map((item) => corpusMetadataView(item, depth + 1));
  if (typeof value === "string" && pathLikeValue.test(value)) return "<not displayed in Studio>";
  if (!record(value)) return value;
  return Object.fromEntries(Object.entries(value).map(([key, child]) => [
    key,
    hiddenKey.test(key) ? "<not displayed in Studio>" : corpusMetadataView(child, depth + 1),
  ]));
}
