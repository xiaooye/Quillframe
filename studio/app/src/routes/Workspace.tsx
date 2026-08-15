import { For, Match, Show, Switch, createMemo, createSignal } from "solid-js";
import { invokeBridge } from "../bridge";
import { JsonBlock, PageIntro } from "../components";
import { useI18n } from "../i18n";
import { asSemanticPacks, type SemanticCatalogProjection } from "../observability";
import { useStudio } from "../studio";

const modes = ["DRAFT", "REVISE", "AUDIT", "PLAN-CHAPTER"] as const;
type PlaygroundMode = (typeof modes)[number];

const steps = ["context", "contracts", "execution", "evidence", "result"] as const;
type PlaygroundStep = (typeof steps)[number];
type ContractPreviewStatus = "candidate" | "registered" | "not_registered" | "unavailable";

const contractPreview: Record<PlaygroundMode, readonly string[]> = {
  DRAFT: ["context.select", "character.action_propose", "scene.resolve_actions"],
  REVISE: ["revision.diagnose", "reader.engagement_audit", "character.integrity", "quality.compare"],
  AUDIT: ["quality.production_review", "reader.engagement_audit", "continuity.commitment_audit"],
  "PLAN-CHAPTER": ["context.select", "plan.reconcile", "scene.diverge"],
};

const inspectorCopy = {
  "en-US": {
    run: "Run preview",
    runId: "Run ID",
    complete: "Preview complete",
    runtime: "Runtime",
    browserLocal: "Browser-local",
    persistence: "Persistence",
    ephemeral: "Ephemeral",
    authority: "Authority",
    none: "None",
    candidate: "Candidate only",
    registered: "Registered",
    notRegistered: "Not registered",
    unavailable: "Registry unavailable",
    catalogChecked: "Contract candidates were compared with the live semantic.catalog projection. Registration is evidence of presence only; no semantic routing or quality judgment occurred.",
    catalogUnavailable: "A bound Core was present, but semantic.catalog could not be used for this preview. Contract candidates remain unverified by the registry.",
    catalogNotBound: "No Core is bound, so contract candidates come only from the explicit Playground mode mapping.",
    stepHint: "Select a step to inspect the state, routing evidence, and result boundary produced by this preview.",
  },
  "zh-CN": {
    run: "运行预览",
    runId: "Run ID",
    complete: "预览完成",
    runtime: "Runtime",
    browserLocal: "浏览器本地",
    persistence: "持久化",
    ephemeral: "临时",
    authority: "Authority",
    none: "无",
    candidate: "仅候选",
    registered: "已注册",
    notRegistered: "未注册",
    unavailable: "Registry 不可用",
    catalogChecked: "这些契约候选已与 live semantic.catalog 投影进行比对。注册只能证明契约存在；本次没有执行 semantic routing，也没有产生质量判断。",
    catalogUnavailable: "当前已绑定 Core，但本次预览无法使用 semantic.catalog；这些契约候选没有获得 registry 验证。",
    catalogNotBound: "当前没有绑定 Core，因此契约候选只来自显式的 Playground mode mapping。",
    stepHint: "选择一个步骤，检查这次预览产生的状态、路由证据与结果边界。",
  },
} as const;

interface PlaygroundResult {
  fingerprint: string;
  run: Record<string, unknown>;
  manifest: Record<string, unknown>;
  contracts: { id: string; status: ContractPreviewStatus }[];
  execution: Record<string, unknown>;
  evidence: string[];
  result: Record<string, unknown>;
}

async function sha256(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return "sha256:" + Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export default function Workspace() {
  const { t, locale } = useI18n();
  const studio = useStudio();
  const [mode, setMode] = createSignal<PlaygroundMode>("DRAFT");
  const [input, setInput] = createSignal("");
  const [running, setRunning] = createSignal(false);
  const [preview, setPreview] = createSignal<PlaygroundResult>();
  const [activeStep, setActiveStep] = createSignal<PlaygroundStep>("context");
  const contracts = createMemo(() => contractPreview[mode()]);
  const copy = createMemo(() => inspectorCopy[locale()]);

  const stepLabel = (step: PlaygroundStep) => {
    if (step === "context") return t("playground.contextStep");
    if (step === "contracts") return t("playground.contractStep");
    if (step === "execution") return t("playground.executionStep");
    if (step === "evidence") return t("playground.evidenceStep");
    return t("playground.resultStep");
  };

  const contractStatusLabel = (status: ContractPreviewStatus) => {
    if (status === "registered") return copy().registered;
    if (status === "not_registered") return copy().notRegistered;
    if (status === "unavailable") return copy().unavailable;
    return copy().candidate;
  };

  const runPreview = async () => {
    const source = input().trim();
    if (!source) return;
    setRunning(true);
    try {
      const fingerprint = await sha256(`${mode()}\n${source}`);
      const runId = `preview-${fingerprint.slice(7, 19)}`;
      const bytes = new TextEncoder().encode(source).length;
      let catalogCheck: "not_bound" | "checked" | "unavailable" = studio.bridgeAvailable() ? "unavailable" : "not_bound";
      let catalogSchema: string | null = null;
      let registeredContracts: Set<string> | undefined;

      if (studio.bridgeAvailable()) {
        try {
          const response = await invokeBridge<SemanticCatalogProjection>("semantic.catalog");
          if (response.status === "ok" && response.data) {
            const packs = asSemanticPacks(response.data);
            registeredContracts = new Set(packs.flatMap((pack) => pack.contracts));
            catalogSchema = typeof response.data.schema === "string" ? response.data.schema : "semantic.catalog";
            catalogCheck = "checked";
          }
        } catch {
          catalogCheck = "unavailable";
        }
      }

      const contractCandidates = contracts().map((id) => ({
        id,
        status: registeredContracts ? (registeredContracts.has(id) ? "registered" as const : "not_registered" as const) : (catalogCheck === "unavailable" ? "unavailable" as const : "candidate" as const),
      }));
      const registeredCandidates = catalogCheck === "checked" ? contractCandidates.filter((item) => item.status === "registered").map((item) => item.id) : null;
      const catalogEvidence = catalogCheck === "checked" ? copy().catalogChecked : catalogCheck === "unavailable" ? copy().catalogUnavailable : copy().catalogNotBound;

      setPreview({
        fingerprint,
        run: {
          schema: "novelforge_playground_run_preview_v1",
          run_id: runId,
          task_mode: mode(),
          status: "preview_complete",
          runtime: studio.bridgeAvailable() ? "browser_with_read_only_core" : "browser_ephemeral",
          model_execution: false,
          persistence: false,
          resumable: false,
          authority: false,
        },
        manifest: {
          schema: "novelforge_playground_context_preview_v1",
          run_id: runId,
          task_mode: mode(),
          source: "browser_ephemeral",
          input_bytes: bytes,
          blocks: [
            {
              id: "PLAYGROUND-INPUT",
              authority: "one_off",
              stage_visibility: ["preview"],
              fingerprint,
            },
          ],
        },
        contracts: contractCandidates,
        execution: {
          executor: "deterministic_browser_preview",
          agent_topology: "none",
          model_execution: false,
          semantic_routing: false,
          contract_selection: "illustrative_mode_preview",
          contract_registry_check: catalogCheck,
          contract_registry_schema: catalogSchema,
          tool_calls: 0,
          handoffs: 0,
          approvals: 0,
          guardrails: 0,
          core_queries: catalogCheck === "checked" ? ["semantic.catalog"] : [],
          persistence: false,
          resumable: false,
          run_receipt_emitted: false,
          authority: false,
          canon_write: false,
          framework_write: false,
          settlement_authority: false,
          events: [
            { seq: 1, type: "input.accepted", status: "complete" },
            { seq: 2, type: "context.manifest.previewed", status: "complete" },
            { seq: 3, type: "semantic.catalog", status: catalogCheck },
            { seq: 4, type: "semantic.contract_candidates.previewed", status: "complete" },
            { seq: 5, type: "model.execution", status: "skipped" },
            { seq: 6, type: "evidence.previewed", status: "complete" },
            { seq: 7, type: "run.receipt", status: "not_emitted" },
          ],
        },
        evidence: [
          catalogEvidence,
          t("playground.evidenceEphemeral"),
          t("playground.evidenceNoModel"),
          t("playground.evidenceNoAuthority"),
        ],
        result: {
          schema: "novelforge_playground_result_preview_v1",
          run_id: runId,
          status: "preview_complete",
          mode: mode(),
          contract_candidates: contractCandidates.map((item) => item.id),
          registered_contract_candidates: registeredCandidates,
          selected_contracts: null,
          subject_fingerprint: fingerprint,
          semantic_routing_performed: false,
          run_receipt_emitted: false,
          authority: false,
          note: t("playground.mockResult"),
        },
      });
      setActiveStep("context");
    } finally {
      setRunning(false);
    }
  };

  return (
    <section class="nf-page nf-playground-page">
      <PageIntro eyebrow={t("playground.eyebrow")} title={t("playground.title")} body={t("playground.body")} />

      <section class="wui-card wui-card--outlined nf-inspector-surface nf-playground-shell">
        <div class="nf-playground-input-pane">
          <div class="nf-playground-modebar" role="group" aria-label={t("playground.modeLabel")}>
            <For each={modes}>
              {(value) => (
                <button class="wui-button wui-button--ghost" data-active={mode() === value ? "true" : undefined} type="button" onClick={() => { setMode(value); setPreview(undefined); }}>
                  {value}
                </button>
              )}
            </For>
          </div>
          <label class="nf-playground-editor">
            <span class="nf-field-label">{t("playground.inputLabel")}</span>
            <textarea
              class="wui-textarea"
              value={input()}
              onInput={(event) => { setInput(event.currentTarget.value); setPreview(undefined); }}
              placeholder={t("playground.inputPlaceholder")}
              spellcheck={false}
            />
          </label>
          <div class="nf-playground-runbar">
            <div>
              <span class="nf-card-label">{t("playground.contractsLabel")}</span>
              <div class="nf-chip-row">
                <For each={contracts()}>{(contract) => <span class="wui-badge wui-badge--outline nf-mono">{contract}</span>}</For>
              </div>
            </div>
            <button class="wui-button wui-button--solid" type="button" disabled={running() || !input().trim()} onClick={() => void runPreview()}>
              {running() ? t("common.loading") : t("playground.runAction")}
            </button>
          </div>
        </div>

        <Show when={preview()} fallback={<div class="nf-playground-empty"><strong>{t("playground.emptyTitle")}</strong><p>{t("playground.emptyBody")}</p></div>}>
          {(currentRun) => (
            <div class="nf-playground-output-pane">
              <header class="nf-console-head">
                <div>
                  <span class="nf-card-label">{copy().run}</span>
                  <h2 class="nf-mono">{String(currentRun().run.run_id)}</h2>
                </div>
                <span class="wui-badge wui-badge--success">{copy().complete}</span>
              </header>

              <div class="nf-diagnostic-facts" aria-label={copy().run}>
                <div><span>{copy().runId}</span><strong class="nf-mono">{String(currentRun().run.run_id).replace("preview-", "")}</strong></div>
                <div><span>{t("playground.modeLabel")}</span><strong class="nf-mono">{mode()}</strong></div>
                <div><span>{copy().runtime}</span><strong>{copy().browserLocal}</strong></div>
                <div><span>{copy().persistence}</span><strong>{copy().ephemeral}</strong></div>
                <div><span>{copy().authority}</span><strong>{copy().none}</strong></div>
              </div>

              <div class="nf-playground-trace" role="tablist" aria-label={copy().stepHint}>
                <For each={steps}>
                  {(step, index) => (
                    <button
                      class="wui-button wui-button--ghost nf-playground-step"
                      type="button"
                      role="tab"
                      aria-selected={activeStep() === step}
                      data-active={activeStep() === step ? "true" : undefined}
                      onClick={() => setActiveStep(step)}
                    >
                      <span>{String(index() + 1).padStart(2, "0")}</span>
                      <strong>{stepLabel(step)}</strong>
                    </button>
                  )}
                </For>
              </div>

              <div class="nf-playground-panels">
                <section class="nf-playground-panel" role="tabpanel" aria-label={stepLabel(activeStep())}>
                  <header class="nf-inspector-section-head">
                    <div>
                      <span class="nf-card-label">{copy().stepHint}</span>
                      <h2>{stepLabel(activeStep())}</h2>
                    </div>
                    <span class="wui-badge wui-badge--outline">{copy().complete}</span>
                  </header>
                  <div class="nf-console-body">
                    <Switch>
                      <Match when={activeStep() === "context"}>
                        <JsonBlock value={currentRun().manifest} />
                      </Match>
                      <Match when={activeStep() === "contracts"}>
                        <div class="nf-playground-contract-list">
                          <For each={currentRun().contracts}>{(contract) => <code>{contract.id} · {contractStatusLabel(contract.status)}</code>}</For>
                        </div>
                        <p class="nf-playground-footnote">{t("playground.footnote")}</p>
                      </Match>
                      <Match when={activeStep() === "execution"}>
                        <JsonBlock value={currentRun().execution} />
                      </Match>
                      <Match when={activeStep() === "evidence"}>
                        <ul><For each={currentRun().evidence}>{(item) => <li>{item}</li>}</For></ul>
                      </Match>
                      <Match when={activeStep() === "result"}>
                        <JsonBlock value={currentRun().result} />
                      </Match>
                    </Switch>
                  </div>
                </section>
              </div>
            </div>
          )}
        </Show>
      </section>
      <p class="nf-playground-footnote">{t("playground.footnote")}</p>
    </section>
  );
}
