import { For, createMemo, createSignal } from "solid-js";
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
8. Default to one manager run. Add external workers, handoffs, or independent gates only through the pinned runtime-routing and control-plane contracts.
9. Treat session, event, handoff, and run-receipt state as Core-owned. If a safe public projection is unavailable, keep it unavailable rather than inferring it.
`;

const targets = ["Claude Code", "Codex", "OpenCode", "Cursor", "Custom agent"] as const;

const runtimeCopy = {
  "en-US": {
    eyebrow: "Execution model",
    title: "One run, explicit state, observable boundaries",
    body: "NovelForge uses the useful common denominator of modern agent runtimes without adopting their private storage or orchestration vocabulary. Deterministic control stays outside the model; agency enters only where the task actually needs judgment.",
    status: "NOVELFORGE-NATIVE",
    patterns: [
      ["Run + Trace", "A run owns an ordered observable chain. Studio inspects steps instead of scraping terminal logs.", "run → events"],
      ["Context + State", "Context is explicit, stage-scoped, and fingerprintable. Chat history never becomes hidden authority.", "manifest → state"],
      ["Contracts + Tools", "Semantic contracts describe allowed reasoning boundaries; registration alone is never a quality verdict.", "contracts → execution"],
      ["Handoff + Approval", "Workers and independent gates are typed transitions, not invisible agent swaps or implicit delegation.", "handoff → gate"],
      ["Evidence + Receipt", "Outputs carry evidence and run receipts. Settlement and Canon remain separate authority operations.", "evidence → receipt"],
    ],
  },
  "zh-CN": {
    eyebrow: "执行模型",
    title: "一次 Run，显式状态，可观察边界",
    body: "NovelForge 吸收现代 Agent runtime 已经验证过的共同模式，但不复制它们的私有存储或编排词汇。确定性控制留在模型之外；只有任务确实需要判断时，才引入 agency。",
    status: "NOVELFORGE 原生",
    patterns: [
      ["Run + Trace", "一次 Run 拥有有序、可观察的执行链。Studio 检查步骤，不靠抓终端日志猜运行过程。", "run → events"],
      ["Context + State", "上下文保持显式、分阶段、可指纹绑定；聊天历史不会悄悄变成 authority。", "manifest → state"],
      ["Contracts + Tools", "Semantic contract 描述允许的推理边界；契约已注册本身绝不等于质量结论。", "contracts → execution"],
      ["Handoff + Approval", "Worker 与独立 Gate 都是类型化转移，不允许隐形换 Agent 或暗中委派。", "handoff → gate"],
      ["Evidence + Receipt", "输出携带 evidence 与 run receipt；Settlement / Canon 继续是独立 authority 操作。", "evidence → receipt"],
    ],
  },
} as const;

export default function Agents() {
  const { t, locale } = useI18n();
  const [copied, setCopied] = createSignal(false);
  const runtime = createMemo(() => runtimeCopy[locale()]);

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

      <section
        class="wui-card wui-card--outlined nf-inspector-surface nf-agent-matrix"
        aria-labelledby="agent-runtime-heading"
        style={{ background: "color-mix(in oklab,var(--nf-lane-runtime-fill) 28%,var(--nf-studio-panel))" }}
      >
        <header class="nf-agent-matrix-head">
          <div>
            <span class="nf-eyebrow">{runtime().eyebrow}</span>
            <h2 id="agent-runtime-heading">{runtime().title}</h2>
            <p>{runtime().body}</p>
          </div>
          <span class="wui-badge wui-badge--outline">{runtime().status}</span>
        </header>
        <div class="nf-agent-targets">
          <For each={runtime().patterns}>
            {(pattern) => (
              <div class="nf-agent-target">
                <strong>{pattern[0]}</strong>
                <span>{pattern[1]}</span>
                <span class="wui-badge wui-badge--outline nf-mono">{pattern[2]}</span>
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
