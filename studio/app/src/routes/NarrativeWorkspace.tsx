import { For, Match, Show, Switch, createMemo, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { CoreHostBoundary, JsonBlock, PageIntro, QueryError } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

type View = "story" | "context" | "simulation" | "verification";

type WorkspaceItem = {
  id: string;
  section: string;
  kind: string;
  label?: string | null;
  authority_class: string;
  lifecycle: string;
  story_order?: number | null;
  source_ref: string;
  authority: false;
};

type WorkspaceProjection = {
  schema: "novelforge_story_workspace_v1";
  workspace_fingerprint: string;
  project: { project_id: string; project_title: string; project_version?: string | null; layout: string };
  sections: Record<string, WorkspaceItem[]>;
  object_count: number;
  lifecycle_counts: Record<string, number>;
  authority: false;
};

type ContextTraceItem = {
  id: string;
  class?: unknown;
  authority?: unknown;
  inclusion_reason?: unknown;
  semantic_tier?: string | null;
  semantic_reason?: unknown;
  loaded: boolean;
  loaded_tier?: string | null;
  archived: boolean;
  exclusion_reasons: string[];
};

type ContextTraceProjection = {
  schema: "novelforge_context_trace_v1";
  trace_fingerprint: string;
  manifest_id?: string | null;
  stage?: string | null;
  items: ContextTraceItem[];
  selection_owner: "model";
  budget_owner: "deterministic_runtime";
  authority: false;
};

type SimulationProjection = {
  schema: "novelforge_scene_simulation_run_v1";
  run_id: string;
  scene_id: string;
  base_checkpoint_id: string;
  base_state_fingerprint: string;
  character_results: Array<{ character_id?: string; contract_id: string; result_fingerprint: string }>;
  event_ir_candidates: Array<{ event_id: string; event_fingerprint: string; story_order: number }>;
  branches: Array<{ branch_id: string; branch_fingerprint: string; selected: boolean; authority: false }>;
  run_fingerprint: string;
  agent_topology: string;
  authority: false;
};

type CandidateDeltaProjection = {
  schema: "novelforge_candidate_state_delta_v1";
  artifact_ref: string;
  candidate_fingerprint: string;
  delta_fingerprint: string;
  changes: Array<{
    domain: string;
    subject_id: string;
    field: string;
    before?: unknown;
    after?: unknown;
    evidence_refs: string[];
    event_ids: string[];
  }>;
  authority: false;
};

type Finding = {
  id?: string;
  category?: string;
  severity?: string;
  repair_owner?: string;
  subject_id?: string;
  description?: string;
  source_refs?: string[];
};

type VerificationProjection = {
  schema: "novelforge_narrative_verification_v1";
  candidate_fingerprint: string;
  verification_fingerprint: string;
  status: "clear" | "issues_found";
  deterministic_finding_count: number;
  semantic_finding_count: number;
  findings: Finding[];
  semantic_verdict: "clear" | "issues_found";
  authority: false;
};

const sectionOrder = ["structure", "timeline", "characters", "relationships", "world_state", "plans", "reader_expectations", "context", "branches", "other"];

const copy = {
  "en-US": {
    eyebrow: "Story Workspace",
    title: "Work with the story, not the runtime plumbing",
    body: "Inspect the story model, the exact context a run received, causal scene simulation, candidate state changes, and narrative verification. Every view is read-only and preserves Project authority.",
    noProject: "Open a Project first so Studio can scope every evidence file to that Project root.",
    story: "Story",
    context: "Context",
    simulation: "Simulation",
    verification: "Verification",
    file: "Project-relative evidence file",
    inspector: "Inspector result",
    memory: "Memory tiers result (optional)",
    semantic: "Context selection result (optional)",
    candidate: "Candidate state input",
    verifyInput: "Narrative verification input",
    load: "Load view",
    loadCandidate: "Load candidate delta",
    loading: "Loading…",
    objects: "objects",
    loaded: "loaded",
    excluded: "excluded",
    lifecycle: "Lifecycle",
    storyOrder: "Story order",
    reason: "Why it is here",
    excludedBecause: "Excluded because",
    characters: "Character simulations",
    events: "Causal events",
    branches: "Scenario branches",
    selected: "selected",
    candidateChanges: "Candidate changes",
    findings: "Findings",
    clear: "No narrative findings",
    repairOwner: "Repair owner",
    raw: "Raw Core projection",
    readOnly: "Read-only · authority=false",
    sourceNote: "Inputs are normalized Core evidence files inside the current Project. Studio never parses a private Project database into a second Canon store.",
  },
  "zh-CN": {
    eyebrow: "Story Workspace",
    title: "直接看故事，不看运行时管线",
    body: "在一个工作台里检查故事结构、一次 run 真正收到的 Context、场景因果模拟、候选状态变化和叙事验证。所有视图只读，并完整保留 Project authority。",
    noProject: "先打开一个 Project；Studio 才能把所有 evidence 文件严格限制在该 Project root 内。",
    story: "故事",
    context: "上下文",
    simulation: "场景模拟",
    verification: "叙事验证",
    file: "Project 内相对 evidence 文件",
    inspector: "Inspector 结果",
    memory: "Memory tiers 结果（可选）",
    semantic: "Context selection 结果（可选）",
    candidate: "Candidate state 输入",
    verifyInput: "Narrative verification 输入",
    load: "载入视图",
    loadCandidate: "载入候选变化",
    loading: "载入中…",
    objects: "个对象",
    loaded: "已载入",
    excluded: "已排除",
    lifecycle: "生命周期",
    storyOrder: "故事顺序",
    reason: "为什么在这里",
    excludedBecause: "排除原因",
    characters: "人物模拟",
    events: "因果事件",
    branches: "情景分支",
    selected: "已选择",
    candidateChanges: "候选状态变化",
    findings: "问题",
    clear: "没有发现叙事问题",
    repairOwner: "修复归属",
    raw: "Core 原始投影",
    readOnly: "只读 · authority=false",
    sourceNote: "输入只能是当前 Project 内的正规化 Core evidence 文件。Studio 不会解析项目私有数据库并建立第二份 Canon。",
  },
} as const;

function valueText(value: unknown) {
  if (value === undefined) return "—";
  if (value === null) return "null";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export default function NarrativeWorkspace() {
  const { locale } = useI18n();
  const studio = useStudio();
  const c = createMemo(() => copy[locale()]);
  const [view, setView] = createSignal<View>("story");
  const [loading, setLoading] = createSignal<string>();
  const [error, setError] = createSignal<string>();

  const [workspaceInput, setWorkspaceInput] = createSignal(".novelforge/story-workspace.json");
  const [inspectorInput, setInspectorInput] = createSignal(".novelforge/context-inspector.json");
  const [memoryInput, setMemoryInput] = createSignal("");
  const [semanticInput, setSemanticInput] = createSignal("");
  const [simulationInput, setSimulationInput] = createSignal(".novelforge/scene-simulation.json");
  const [candidateInput, setCandidateInput] = createSignal(".novelforge/candidate-state.json");
  const [verificationInput, setVerificationInput] = createSignal(".novelforge/narrative-verification.json");

  const [workspace, setWorkspace] = createSignal<WorkspaceProjection>();
  const [trace, setTrace] = createSignal<ContextTraceProjection>();
  const [simulation, setSimulation] = createSignal<SimulationProjection>();
  const [candidate, setCandidate] = createSignal<CandidateDeltaProjection>();
  const [verification, setVerification] = createSignal<VerificationProjection>();

  const root = () => studio.projectRoot().trim();

  const run = async <T,>(operation: string, args: Record<string, unknown>, sink: (value: T | undefined) => void) => {
    if (!root()) {
      setError(c().noProject);
      return;
    }
    setLoading(operation);
    setError(undefined);
    try {
      const result = await invokeBridge<T>(operation, { project_root: root(), ...args });
      if (result.status !== "ok" || !result.data) {
        sink(undefined);
        setError(JSON.stringify(result.error));
        return;
      }
      sink(result.data);
    } catch (caught) {
      sink(undefined);
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setLoading(undefined);
    }
  };

  const loadWorkspace = () => void run<WorkspaceProjection>("story.workspace", { input: workspaceInput().trim() }, setWorkspace);
  const loadTrace = () => {
    const args: Record<string, unknown> = { inspector: inspectorInput().trim() };
    if (memoryInput().trim()) args.memory_tiers = memoryInput().trim();
    if (semanticInput().trim()) args.semantic_result = semanticInput().trim();
    void run<ContextTraceProjection>("context.trace", args, setTrace);
  };
  const loadSimulation = () => void run<SimulationProjection>("scene.simulation.inspect", { input: simulationInput().trim() }, setSimulation);
  const loadCandidate = () => void run<CandidateDeltaProjection>("state.candidate.inspect", { input: candidateInput().trim() }, setCandidate);
  const loadVerification = () => void run<VerificationProjection>("continuity.verify", { input: verificationInput().trim() }, setVerification);

  const sectionEntries = createMemo(() => {
    const current = workspace();
    if (!current) return [] as Array<[string, WorkspaceItem[]]>;
    return sectionOrder
      .map((section) => [section, current.sections[section] ?? []] as [string, WorkspaceItem[]])
      .filter(([, items]) => items.length > 0);
  });

  return (
    <section class="nf-page nf-playground-page">
      <PageIntro eyebrow={c().eyebrow} title={c().title} body={c().body} />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <section class="wui-card wui-card--outlined nf-inspector-surface">
          <div class="nf-playground-modebar" role="tablist" aria-label={c().eyebrow}>
            <For each={["story", "context", "simulation", "verification"] as View[]}>
              {(item) => (
                <button
                  type="button"
                  role="tab"
                  class="wui-button wui-button--ghost"
                  aria-selected={view() === item}
                  data-active={view() === item ? "true" : undefined}
                  onClick={() => { setView(item); setError(undefined); }}
                >
                  {c()[item]}
                </button>
              )}
            </For>
          </div>
          <p class="nf-playground-footnote">{c().sourceNote}</p>
        </section>

        <QueryError message={error()} />

        <Switch>
          <Match when={view() === "story"}>
            <section class="wui-card wui-card--outlined nf-inspector-surface">
              <div class="nf-form-grid">
                <label class="nf-field-label">
                  <span>{c().file}</span>
                  <input class="wui-input" value={workspaceInput()} onInput={(event) => setWorkspaceInput(event.currentTarget.value)} spellcheck={false} />
                </label>
                <button class="wui-button wui-button--solid nf-form-action" type="button" disabled={loading() !== undefined || !workspaceInput().trim()} onClick={loadWorkspace}>
                  {loading() === "story.workspace" ? c().loading : c().load}
                </button>
              </div>
              <Show when={workspace()}>
                {(result) => (
                  <div>
                    <div class="nf-diagnostic-facts">
                      <div><span>Project</span><strong>{result().project.project_title}</strong></div>
                      <div><span>Layout</span><strong class="nf-mono">{result().project.layout}</strong></div>
                      <div><span>Objects</span><strong>{result().object_count}</strong></div>
                      <div><span>Authority</span><strong>{c().readOnly}</strong></div>
                    </div>
                    <div class="nf-pack-list">
                      <For each={sectionEntries()}>
                        {([section, items]) => (
                          <article class="nf-pack-row">
                            <div class="nf-pack-heading">
                              <div><strong>{section.replaceAll("_", " ")}</strong><small>{items.length} {c().objects}</small></div>
                              <span class="wui-badge wui-badge--outline">{section}</span>
                            </div>
                            <div class="nf-chip-row">
                              <For each={items}>
                                {(item) => (
                                  <span class="wui-badge wui-badge--outline" title={item.source_ref}>
                                    {item.label || item.id} · {item.lifecycle}{item.story_order === null || item.story_order === undefined ? "" : ` · #${item.story_order}`}
                                  </span>
                                )}
                              </For>
                            </div>
                          </article>
                        )}
                      </For>
                    </div>
                    <details class="nf-raw-evidence"><summary>{c().raw}</summary><JsonBlock value={result()} /></details>
                  </div>
                )}
              </Show>
            </section>
          </Match>

          <Match when={view() === "context"}>
            <section class="wui-card wui-card--outlined nf-inspector-surface">
              <div class="nf-form-grid">
                <label class="nf-field-label"><span>{c().inspector}</span><input class="wui-input" value={inspectorInput()} onInput={(event) => setInspectorInput(event.currentTarget.value)} spellcheck={false} /></label>
                <label class="nf-field-label"><span>{c().memory}</span><input class="wui-input" value={memoryInput()} onInput={(event) => setMemoryInput(event.currentTarget.value)} spellcheck={false} /></label>
                <label class="nf-field-label"><span>{c().semantic}</span><input class="wui-input" value={semanticInput()} onInput={(event) => setSemanticInput(event.currentTarget.value)} spellcheck={false} /></label>
                <button class="wui-button wui-button--solid nf-form-action" type="button" disabled={loading() !== undefined || !inspectorInput().trim()} onClick={loadTrace}>
                  {loading() === "context.trace" ? c().loading : c().load}
                </button>
              </div>
              <Show when={trace()}>
                {(result) => {
                  const loaded = () => result().items.filter((item) => item.loaded).length;
                  return (
                    <div>
                      <div class="nf-diagnostic-facts">
                        <div><span>Manifest</span><strong class="nf-mono">{result().manifest_id ?? "—"}</strong></div>
                        <div><span>{c().loaded}</span><strong>{loaded()}</strong></div>
                        <div><span>{c().excluded}</span><strong>{result().items.length - loaded()}</strong></div>
                        <div><span>Selection owner</span><strong>{result().selection_owner}</strong></div>
                      </div>
                      <div class="nf-pack-list">
                        <For each={result().items}>
                          {(item) => (
                            <article class="nf-pack-row">
                              <div class="nf-pack-heading">
                                <div><strong class="nf-mono">{item.id}</strong><small>{String(item.class ?? "context")}</small></div>
                                <span class={`wui-badge ${item.loaded ? "wui-badge--success" : "wui-badge--outline"}`}>{item.loaded ? c().loaded : c().excluded}</span>
                              </div>
                              <div class="nf-pack-description">
                                <strong>{c().reason}</strong><br />{String(item.semantic_reason ?? item.inclusion_reason ?? "—")}
                              </div>
                              <Show when={item.exclusion_reasons.length > 0}>
                                <div class="nf-pack-load-boundary"><span>{c().excludedBecause}</span><strong class="nf-mono">{item.exclusion_reasons.join(" · ")}</strong></div>
                              </Show>
                            </article>
                          )}
                        </For>
                      </div>
                      <details class="nf-raw-evidence"><summary>{c().raw}</summary><JsonBlock value={result()} /></details>
                    </div>
                  );
                }}
              </Show>
            </section>
          </Match>

          <Match when={view() === "simulation"}>
            <section class="wui-card wui-card--outlined nf-inspector-surface">
              <div class="nf-form-grid">
                <label class="nf-field-label"><span>{c().file}</span><input class="wui-input" value={simulationInput()} onInput={(event) => setSimulationInput(event.currentTarget.value)} spellcheck={false} /></label>
                <button class="wui-button wui-button--solid nf-form-action" type="button" disabled={loading() !== undefined || !simulationInput().trim()} onClick={loadSimulation}>
                  {loading() === "scene.simulation.inspect" ? c().loading : c().load}
                </button>
              </div>
              <Show when={simulation()}>
                {(result) => (
                  <div>
                    <div class="nf-diagnostic-facts">
                      <div><span>Scene</span><strong class="nf-mono">{result().scene_id}</strong></div>
                      <div><span>{c().characters}</span><strong>{result().character_results.length}</strong></div>
                      <div><span>{c().events}</span><strong>{result().event_ir_candidates.length}</strong></div>
                      <div><span>{c().branches}</span><strong>{result().branches.length}</strong></div>
                    </div>
                    <div class="nf-pack-list">
                      <article class="nf-pack-row">
                        <div class="nf-pack-heading"><div><strong>{c().characters}</strong><small>{result().agent_topology}</small></div></div>
                        <div class="nf-chip-row"><For each={result().character_results}>{(item) => <span class="wui-badge wui-badge--outline">{item.character_id ?? "character"} · {item.contract_id}</span>}</For></div>
                      </article>
                      <article class="nf-pack-row">
                        <div class="nf-pack-heading"><div><strong>{c().events}</strong><small>{result().base_checkpoint_id}</small></div></div>
                        <div class="nf-chip-row"><For each={result().event_ir_candidates}>{(item) => <span class="wui-badge wui-badge--outline">#{item.story_order} · {item.event_id}</span>}</For></div>
                      </article>
                      <article class="nf-pack-row">
                        <div class="nf-pack-heading"><div><strong>{c().branches}</strong><small>scenario ≠ Canon</small></div></div>
                        <div class="nf-chip-row"><For each={result().branches}>{(item) => <span class={`wui-badge ${item.selected ? "wui-badge--success" : "wui-badge--outline"}`}>{item.branch_id}{item.selected ? ` · ${c().selected}` : ""}</span>}</For></div>
                      </article>
                    </div>
                    <details class="nf-raw-evidence"><summary>{c().raw}</summary><JsonBlock value={result()} /></details>
                  </div>
                )}
              </Show>
            </section>
          </Match>

          <Match when={view() === "verification"}>
            <section class="wui-card wui-card--outlined nf-inspector-surface">
              <div class="nf-form-grid">
                <label class="nf-field-label"><span>{c().candidate}</span><input class="wui-input" value={candidateInput()} onInput={(event) => setCandidateInput(event.currentTarget.value)} spellcheck={false} /></label>
                <button class="wui-button wui-button--outline nf-form-action" type="button" disabled={loading() !== undefined || !candidateInput().trim()} onClick={loadCandidate}>{loading() === "state.candidate.inspect" ? c().loading : c().loadCandidate}</button>
                <label class="nf-field-label"><span>{c().verifyInput}</span><input class="wui-input" value={verificationInput()} onInput={(event) => setVerificationInput(event.currentTarget.value)} spellcheck={false} /></label>
                <button class="wui-button wui-button--solid nf-form-action" type="button" disabled={loading() !== undefined || !verificationInput().trim()} onClick={loadVerification}>{loading() === "continuity.verify" ? c().loading : c().load}</button>
              </div>

              <Show when={candidate()}>
                {(result) => (
                  <div>
                    <header class="nf-inspector-section-head"><div><span class="nf-card-label">Candidate Delta</span><h2>{c().candidateChanges}</h2></div><span class="wui-badge wui-badge--outline">{result().changes.length}</span></header>
                    <div class="nf-pack-list">
                      <For each={result().changes}>
                        {(change) => (
                          <article class="nf-pack-row">
                            <div class="nf-pack-heading"><div><strong>{change.subject_id} · {change.field}</strong><small>{change.domain}</small></div></div>
                            <div class="nf-pack-description"><code>{valueText(change.before)}</code> → <code>{valueText(change.after)}</code></div>
                          </article>
                        )}
                      </For>
                    </div>
                  </div>
                )}
              </Show>

              <Show when={verification()}>
                {(result) => (
                  <div>
                    <header class="nf-inspector-section-head">
                      <div><span class="nf-card-label">Narrative Verification</span><h2>{c().findings}</h2></div>
                      <span class={`wui-badge ${result().status === "clear" ? "wui-badge--success" : "wui-badge--outline"}`}>{result().status}</span>
                    </header>
                    <div class="nf-diagnostic-facts">
                      <div><span>Deterministic</span><strong>{result().deterministic_finding_count}</strong></div>
                      <div><span>Semantic</span><strong>{result().semantic_finding_count}</strong></div>
                      <div><span>Verdict</span><strong>{result().semantic_verdict}</strong></div>
                      <div><span>Authority</span><strong>{c().readOnly}</strong></div>
                    </div>
                    <Show when={result().findings.length > 0} fallback={<div class="nf-playground-empty"><strong>{c().clear}</strong></div>}>
                      <div class="nf-pack-list">
                        <For each={result().findings}>
                          {(finding) => (
                            <article class="nf-pack-row">
                              <div class="nf-pack-heading">
                                <div><strong>{finding.description ?? finding.category ?? "finding"}</strong><small>{finding.subject_id ?? "candidate"}</small></div>
                                <span class="wui-badge wui-badge--outline">{finding.severity ?? "info"}</span>
                              </div>
                              <div class="nf-pack-load-boundary"><span>{c().repairOwner}</span><strong>{finding.repair_owner ?? "—"}</strong></div>
                            </article>
                          )}
                        </For>
                      </div>
                    </Show>
                    <details class="nf-raw-evidence"><summary>{c().raw}</summary><JsonBlock value={result()} /></details>
                  </div>
                )}
              </Show>
            </section>
          </Match>
        </Switch>
      </Show>
    </section>
  );
}
