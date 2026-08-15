import { For, createSignal } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";

const agentBootstrap = `# NovelForge project bootstrap

1. Read novelforge.toml.
2. Read novelforge.lock.json and use the exact Framework commit + bundle fingerprint.
3. Verify framework.attestation.json when the project provides it.
4. Load the pinned NovelForge HARNESS_MANIFEST.yaml, SKILL.md, and harness/HARNESS_AGENT.md.
5. Treat chat/session history as runtime context, never as Project or Canon authority.
6. Use agent-skills/novelforge/SKILL.md for the public read-only Host Bridge when a portable agent integration is needed.
7. Fail closed on unsupported bridge operations; do not bypass public boundaries through private runtime stores.
`;

const targets = ["Claude Code", "Codex", "OpenCode", "Cursor", "Custom agent"] as const;

export default function Agents() {
  const { t } = useI18n();
  const [copied, setCopied] = createSignal(false);

  const copyBootstrap = async () => {
    await navigator.clipboard.writeText(agentBootstrap);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section class="nf-page nf-agents-page">
      <PageIntro eyebrow={t("agents.eyebrow")} title={t("agents.title")} body={t("agents.body")} />

      <section
        class="wui-card wui-card--outlined nf-inspector-surface nf-agent-matrix"
        aria-labelledby="agent-matrix-heading"
        style={{
          background: "color-mix(in oklab,var(--nf-lane-validated-fill) 38%,var(--nf-studio-panel))",
          "border-color": "color-mix(in oklab,var(--nf-lane-validated-stroke) 22%,var(--nf-studio-line-soft))",
        }}
      >
        <header class="nf-agent-matrix-head">
          <div>
            <span class="nf-eyebrow">{t("agents.matrixEyebrow")}</span>
            <h2 id="agent-matrix-heading">{t("agents.matrixTitle")}</h2>
            <p>{t("agents.matrixBody")}</p>
          </div>
          <span class="wui-badge wui-badge--success">{t("agents.portableStatus")}</span>
        </header>
        <div class="nf-agent-targets">
          <For each={targets}>
            {(target) => (
              <div class="nf-agent-target">
                <strong>{target}</strong>
                <span>{target === "Custom agent" ? t("agents.targetBridge") : t("agents.targetBootstrap")}</span>
                <span class="wui-badge wui-badge--outline">{t("agents.targetPortable")}</span>
              </div>
            )}
          </For>
        </div>
      </section>

      <div class="nf-agent-grid">
        <section
          class="wui-card wui-card--outlined nf-inspector-surface nf-agent-capability"
          style={{ background: "color-mix(in oklab,var(--nf-lane-editorial-fill) 42%,var(--nf-studio-panel))" }}
        >
          <header><span class="nf-card-label">01</span><h2>{t("agents.skillTitle")}</h2></header>
          <p>{t("agents.skillBody")}</p>
          <code>agent-skills/novelforge/SKILL.md</code>
          <div class="nf-agent-facts">
            <span><strong>{t("agents.readOnly")}</strong><small>authority=false</small></span>
            <span><strong>Python 3.11+</strong><small>NOVELFORGE_ROOT</small></span>
          </div>
        </section>

        <section
          class="wui-card wui-card--outlined nf-inspector-surface nf-agent-capability"
          style={{ background: "color-mix(in oklab,var(--nf-lane-project-fill) 42%,var(--nf-studio-panel))" }}
        >
          <header><span class="nf-card-label">02</span><h2>{t("agents.detectTitle")}</h2></header>
          <p>{t("agents.detectBody")}</p>
          <div class="nf-agent-detect-list">
            <code>novelforge.toml</code>
            <code>novelforge.lock.json</code>
            <code>framework.attestation.json</code>
          </div>
        </section>

        <section
          class="wui-card wui-card--outlined nf-inspector-surface nf-agent-capability"
          style={{ background: "color-mix(in oklab,var(--nf-lane-runtime-fill) 42%,var(--nf-studio-panel))" }}
        >
          <header><span class="nf-card-label">03</span><h2>{t("agents.bridgeTitle")}</h2></header>
          <p>{t("agents.bridgeBody")}</p>
          <code>python scripts/novelforge_bridge.py describe</code>
          <div class="nf-chip-row">
            <span class="wui-badge wui-badge--success">Host Bridge v1</span>
            <span class="wui-badge wui-badge--outline">MCP-ready boundary</span>
          </div>
        </section>
      </div>

      <section class="wui-card wui-card--outlined nf-inspector-surface nf-agent-bootstrap" aria-labelledby="agent-bootstrap-heading">
        <header class="nf-agent-bootstrap-head">
          <div>
            <span class="nf-eyebrow">{t("agents.bootstrapEyebrow")}</span>
            <h2 id="agent-bootstrap-heading">{t("agents.bootstrapTitle")}</h2>
            <p>{t("agents.bootstrapBody")}</p>
          </div>
          <button class="wui-button wui-button--outline" type="button" onClick={() => void copyBootstrap()}>{copied() ? t("agents.copied") : t("agents.copyAction")}</button>
        </header>
        <pre class="nf-agent-code"><code>{agentBootstrap}</code></pre>
      </section>

      <p class="nf-agent-footnote">{t("agents.footnote")}</p>
    </section>
  );
}
