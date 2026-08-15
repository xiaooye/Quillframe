import { For, Show, createMemo, createSignal } from "solid-js";
import { JsonBlock, PageIntro } from "../components";
import { useI18n } from "../i18n";

const modes = ["DRAFT", "REVISE", "REVIEW", "PLAN"] as const;
type PlaygroundMode = (typeof modes)[number];

const contractPreview: Record<PlaygroundMode, readonly string[]> = {
  DRAFT: ["context.select", "character.action_propose", "scene.resolve_actions"],
  REVISE: ["revision.diagnose", "quality.compare"],
  REVIEW: ["reader.engagement_audit", "quality.production_review", "continuity.commitment_audit"],
  PLAN: ["scene.diverge", "plan.reconcile"],
};

interface PlaygroundResult {
  fingerprint: string;
  manifest: Record<string, unknown>;
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
  const { t } = useI18n();
  const [mode, setMode] = createSignal<PlaygroundMode>("DRAFT");
  const [input, setInput] = createSignal("");
  const [running, setRunning] = createSignal(false);
  const [preview, setPreview] = createSignal<PlaygroundResult>();
  const contracts = createMemo(() => contractPreview[mode()]);

  const runPreview = async () => {
    const source = input().trim();
    if (!source) return;
    setRunning(true);
    try {
      const fingerprint = await sha256(`${mode()}\n${source}`);
      const bytes = new TextEncoder().encode(source).length;
      setPreview({
        fingerprint,
        manifest: {
          schema: "novelforge_playground_context_preview_v1",
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
        execution: {
          executor: "deterministic_browser_mock",
          model_execution: false,
          network_required: false,
          persistence: false,
          authority: false,
          canon_write: false,
          framework_write: false,
        },
        evidence: [
          t("playground.evidenceEphemeral"),
          t("playground.evidenceNoModel"),
          t("playground.evidenceNoAuthority"),
        ],
        result: {
          status: "preview_complete",
          mode: mode(),
          selected_contracts: [...contracts()],
          subject_fingerprint: fingerprint,
          note: t("playground.mockResult"),
        },
      });
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
                <button class="wui-button wui-button--ghost" data-active={mode() === value ? "true" : undefined} type="button" onClick={() => setMode(value)}>
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
              onInput={(event) => setInput(event.currentTarget.value)}
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
          {(run) => (
            <div class="nf-playground-output-pane">
              <div class="nf-playground-trace">
                <div><span>01</span><strong>{t("playground.contextStep")}</strong></div>
                <div><span>02</span><strong>{t("playground.contractStep")}</strong></div>
                <div><span>03</span><strong>{t("playground.executionStep")}</strong></div>
                <div><span>04</span><strong>{t("playground.evidenceStep")}</strong></div>
                <div><span>05</span><strong>{t("playground.resultStep")}</strong></div>
              </div>

              <div class="nf-playground-panels">
                <details open class="nf-playground-panel">
                  <summary>{t("playground.contextStep")}</summary>
                  <JsonBlock value={run().manifest} />
                </details>
                <details class="nf-playground-panel">
                  <summary>{t("playground.contractStep")}</summary>
                  <div class="nf-playground-contract-list">
                    <For each={contracts()}>{(contract) => <code>{contract}</code>}</For>
                  </div>
                </details>
                <details class="nf-playground-panel">
                  <summary>{t("playground.executionStep")}</summary>
                  <JsonBlock value={run().execution} />
                </details>
                <details class="nf-playground-panel">
                  <summary>{t("playground.evidenceStep")}</summary>
                  <ul><For each={run().evidence}>{(item) => <li>{item}</li>}</For></ul>
                </details>
                <details open class="nf-playground-panel nf-playground-result-panel">
                  <summary>{t("playground.resultStep")}</summary>
                  <JsonBlock value={run().result} />
                </details>
              </div>
            </div>
          )}
        </Show>
      </section>
      <p class="nf-playground-footnote">{t("playground.footnote")}</p>
    </section>
  );
}