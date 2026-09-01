import { For, createMemo, createSignal } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";

const agentBootstrap = `# Quillframe project bootstrap

1. Read quillframe.toml.
2. Validate the exact four-key manifest: schema quillframe_project_v1_0, id, title, language. Chapter identities are resolved through chapter.list within the novel.
3. Project context v1_0 with scope=novel, manifest_fingerprint, .quillframe/data, and authority=false.
4. Reject legacy metadata instead of reading or adapting it.
5. Load the pinned Quillframe HARNESS_MANIFEST.yaml, SKILL.md, and harness/HARNESS_AGENT.md.
6. Treat chat/session history as runtime context, never as Project or Canon authority.
7. Use agent-skills/quillframe/SKILL.md for the public read-only Host Bridge when a portable agent integration is needed.
8. Fail closed on unsupported bridge operations; do not bypass public boundaries through private runtime stores.
9. Default to one manager run. Add external workers, handoffs, or independent gates only through the pinned runtime-routing and control-plane contracts.
10. Treat session, event, handoff, and run-receipt state as Core-owned. If a safe public projection is unavailable, keep it unavailable rather than inferring it.
`;

const targets = ["Claude Code", "Codex", "OpenCode", "Cursor", "Custom agent"] as const;

const runtimeCopy = {
  "en-US": {
    eyebrow: "Execution model",
    title: "One run, explicit state, observable boundaries",
    body: "Quillframe uses the useful common denominator of modern agent runtimes without adopting their private storage or orchestration vocabulary. Deterministic control stays outside the model; agency enters only where the task actually needs judgment.",
    status: "QUILLFRAME-NATIVE",
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
    body: "Quillframe 吸收现代 Agent runtime 已经验证过的共同模式，但不复制它们的私有存储或编排词汇。确定性控制留在模型之外；只有任务确实需要判断时，才引入 agency。",
    status: "QUILLFRAME 原生",
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
          background: "color-mix(in oklab,var(--qf-lane-validated-fill) 38%,var(--qf-studio-panel))",
          "border-color": "color-mix(in oklab,var(--qf-lane-validated-stroke) 22%,var(--qf-studio-line-soft))",
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
        style={{ background: "color-mix(in oklab,var(--qf-lane-runtime-fill) 28%,var(--qf-studio-panel))" }}
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
          style={{ background: "color-mix(in oklab,var(--qf-lane-editorial-fill) 42%,var(--qf-studio-panel))" }}
        >
          <header><span class="nf-card-label">01</span><h2>{t("agents.skillTitle")}</h2></header>
          <p>{t("agents.skillBody")}</p>
          <code>agent-skills/quillframe/SKILL.md</code>
          <div class="nf-agent-facts">
            <span><strong>{t("agents.readOnly")}</strong><small>authority=false</small></span>
            <span><strong>Rust 1.88+</strong><small>QUILLFRAME_ROOT</small></span>
          </div>
        </section>

        <section
          class="wui-card wui-card--outlined nf-inspector-surface nf-agent-capability"
          style={{ background: "color-mix(in oklab,var(--qf-lane-project-fill) 42%,var(--qf-studio-panel))" }}
        >
          <header><span class="nf-card-label">02</span><h2>{t("agents.detectTitle")}</h2></header>
          <p>{t("agents.detectBody")}</p>
          <div class="nf-agent-detect-list">
            <code>quillframe.toml</code>
            <code>quillframe_project_context_v1_0</code>
            <code>scope=novel · .quillframe/data</code>
            <code>manifest_fingerprint</code>
          </div>
        </section>

        <section
          class="wui-card wui-card--outlined nf-inspector-surface nf-agent-capability"
          style={{ background: "color-mix(in oklab,var(--qf-lane-runtime-fill) 42%,var(--qf-studio-panel))" }}
        >
          <header><span class="nf-card-label">03</span><h2>{t("agents.bridgeTitle")}</h2></header>
          <p>{t("agents.bridgeBody")}</p>
          <code>cargo run -p quillframe-host -- invoke bridge.describe</code>
          <div class="nf-chip-row">
            <span class="wui-badge wui-badge--success">Host Bridge v11</span>
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
