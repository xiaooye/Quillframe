import { For, createEffect, createMemo, createSignal } from "solid-js";
import brandMark from "../../assets/brand/novelforge-mark.svg?url";
import type { Locale } from "./content";

type Props = { initialLocale: Locale };

type SupportedOperation = {
  id: string;
  basis: string;
  args: string[];
  labelZh: string;
  labelEn: string;
};

type HostProfile = {
  id: string;
  name: string;
  glyph: string;
  fitZh: string;
  fitEn: string;
  summaryZh: string;
  summaryEn: string;
};

const supportedOperations: SupportedOperation[] = [
  { id: "bridge.describe", basis: "Studio machine contract", args: [], labelZh: "发现桥接能力", labelEn: "Discover bridge capabilities" },
  { id: "framework.doctor", basis: "novelforge.py doctor", args: [], labelZh: "检查 Framework 健康", labelEn: "Inspect Framework health" },
  { id: "project.inspect", basis: "Project Adapter + Project Hub projection", args: ["project_root"], labelZh: "检查 Project", labelEn: "Inspect a Project" },
  { id: "capabilities.inspect", basis: "novelforge_host_capabilities_v1", args: [], labelZh: "检查宿主能力", labelEn: "Inspect host capabilities" },
  { id: "context.inspect", basis: "novelforge_context_inspector_v2", args: ["project_root", "manifest"], labelZh: "检查 Context Manifest", labelEn: "Inspect Context Manifest" },
  { id: "semantic.catalog", basis: "semantic contract catalog CLI", args: [], labelZh: "查看语义契约目录", labelEn: "Inspect semantic contract catalog" },
];

const deferredOperations = [
  "runtime.sessions.list",
  "run.receipt.get",
  "session.resume",
  "command.invoke",
  "project.mutate",
];

const hostProfiles: HostProfile[] = [
  {
    id: "claude-code",
    name: "Claude Code",
    glyph: "C",
    fitZh: "通用桥接 recipe",
    fitEn: "generic bridge recipe",
    summaryZh: "NovelForge 当前不捆绑 Claude-specific adapter。宿主只要能读取 workspace 文件并安全执行本地 CLI，就可以按 portable skill + Host Bridge 的只读路径接入。",
    summaryEn: "NovelForge does not currently bundle a Claude-specific adapter. If the host can read workspace files and safely run a local CLI, use the portable skill plus read-only Host Bridge path.",
  },
  {
    id: "codex",
    name: "Codex",
    glyph: "X",
    fitZh: "通用桥接 recipe",
    fitEn: "generic bridge recipe",
    summaryZh: "把 NovelForge 当成有公开边界的本地工具，而不是让 coding agent 直接读 private runtime。先读 Skill，再 self-test / describe，最后只调用 advertised operations。",
    summaryEn: "Treat NovelForge as a local tool with a public boundary, not as permission to inspect private runtime state. Read the Skill, self-test and describe first, then invoke only advertised operations.",
  },
  {
    id: "cursor",
    name: "Cursor",
    glyph: "↗",
    fitZh: "通用桥接 recipe",
    fitEn: "generic bridge recipe",
    summaryZh: "如果当前 agent 模式能读仓库并运行本地命令，就复用同一份 Agent Skill。NovelForge 不为 UI 宿主制造第二套 Canon 或 Settlement authority。",
    summaryEn: "When the active agent mode can read the repository and run local commands, reuse the same Agent Skill. NovelForge does not create a second Canon or Settlement authority for a UI host.",
  },
  {
    id: "opencode",
    name: "OpenCode",
    glyph: "O",
    fitZh: "通用桥接 recipe",
    fitEn: "generic bridge recipe",
    summaryZh: "接入条件不是品牌名，而是 capability：能读取 skill package、执行 Python CLI、保留结构化结果，并接受 unsupported 时 fail closed。",
    summaryEn: "Compatibility is capability-based rather than brand-based: read the skill package, run the Python CLI, preserve structured results, and fail closed when an operation is unsupported.",
  },
  {
    id: "custom",
    name: "Custom agent",
    glyph: "◇",
    fitZh: "直接 Host Bridge",
    fitEn: "direct Host Bridge",
    summaryZh: "自定义 orchestrator 可以直接消费 versioned request/result envelope，但仍应先 describe，不导入 private Python modules，也不直接读取 Core persistence。",
    summaryEn: "A custom orchestrator can consume the versioned request/result envelope directly, but should still describe first, avoid private Python imports, and never read Core persistence directly.",
  },
];

function initialDark() {
  const saved = localStorage.getItem("novelforge.appearance");
  if (saved === "dark") return true;
  if (saved === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export default function AgentIntegrationEntry(props: Props) {
  const [locale, setLocale] = createSignal<Locale>(props.initialLocale);
  const [dark, setDark] = createSignal(initialDark());
  const [selected, setSelected] = createSignal(0);
  const [selectedHost, setSelectedHost] = createSignal(0);
  const [copied, setCopied] = createSignal<"self-test" | "describe" | "request" | "host" | undefined>();
  const zh = () => locale() === "zh-CN";
  const current = createMemo(() => supportedOperations[selected()]);
  const currentHost = createMemo(() => hostProfiles[selectedHost()]);

  createEffect(() => {
    document.documentElement.lang = zh() ? "zh-CN" : "en";
    document.documentElement.dataset.locale = locale();
    document.documentElement.classList.toggle("dark", dark());
    localStorage.setItem("novelforge.locale", locale());
    localStorage.setItem("novelforge.appearance", dark() ? "dark" : "light");
  });

  const request = createMemo(() => {
    const operation = current();
    const args: Record<string, string> = {};
    for (const key of operation.args) {
      args[key] = key === "project_root" ? "/path/to/project" : "context-manifest.json";
    }
    return JSON.stringify({
      schema: "novelforge_studio_host_bridge_request_v1",
      request_id: "REQ-EXAMPLE-001",
      operation: operation.id,
      surface: "agent_package",
      args,
      authority: false,
    }, null, 2);
  });

  const selfTest = "python agent-skills/novelforge/scripts/novelforge_bridge.py self-test";
  const describe = "python agent-skills/novelforge/scripts/novelforge_bridge.py describe";
  const hostInstruction = createMemo(() => `${zh() ? "NovelForge 宿主 recipe" : "NovelForge host recipe"}: ${currentHost().name}

1. Read agent-skills/novelforge/SKILL.md before invoking NovelForge.
2. Run: ${selfTest}
3. Run: ${describe}
4. Treat supported_operations as the live operation vocabulary; do not guess private APIs.
5. Every bridge request must carry authority: false and preserve request/result fingerprints.
6. Never read .novelforge/runtime.db or import private NovelForge runtime/persistence modules as a shortcut.
7. If an operation is unsupported, stop and report that boundary; do not manufacture a write path.

provider_specific_adapter: not_bundled
bridge_mode: generic_read_only
canon_authority: false
settlement_authority: false`);

  const copyText = async (kind: "self-test" | "describe" | "request" | "host", value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      window.setTimeout(() => setCopied(undefined), 1400);
    } catch {
      setCopied(undefined);
    }
  };

  return (
    <div class="site-shell product-entry agent-integration-entry">
      <header class="wui-app-bar product-appbar" data-position="sticky">
        <a href="/" class="wui-app-bar__brand brand-link" aria-label={zh() ? "NovelForge 首页" : "NovelForge home"}>
          <span class="brand-mark-wrap"><img src={brandMark} alt="" width="32" height="32" aria-hidden="true" /></span>
          <span>NovelForge</span>
          <span class="wui-badge wui-badge--soft version-chip">0.8.x</span>
        </a>
        <nav class="wui-app-bar__nav desktop-nav" aria-label={zh() ? "Agent 集成导航" : "Agent integration navigation"}>
          <a class="wui-app-bar__link" href="/">{zh() ? "产品" : "Product"}</a>
          <a class="wui-app-bar__link" href="/inspect">{zh() ? "检查项目" : "Inspect"}</a>
          <a class="wui-app-bar__link" href="/playground">Playground</a>
          <a class="wui-app-bar__link active" href="/agents" aria-current="page">{zh() ? "Agent 集成" : "Agents"}</a>
          <a class="wui-app-bar__link" href="/docs">{zh() ? "文档" : "Docs"}</a>
        </nav>
        <div class="wui-app-bar__actions header-actions">
          <a class="wui-button wui-button--solid studio-cta" href="https://studio.novelforge.wei-dev.com" target="_blank" rel="noreferrer">✦ Studio</a>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setLocale(zh() ? "en-US" : "zh-CN")} aria-label={zh() ? "切换到英文" : "Switch to Chinese"}>{zh() ? "EN" : "简"}</button>
          <button class="wui-button wui-button--ghost wui-button--icon-only" type="button" onClick={() => setDark((value) => !value)} aria-label={zh() ? "切换明暗主题" : "Toggle appearance"}><span aria-hidden="true">{dark() ? "☼" : "◐"}</span></button>
        </div>
      </header>

      <main id="main-content" class="page-width section-compact agent-integration-main">
        <section class="agent-integration-hero">
          <div class="agent-integration-hero-copy">
            <div class="agent-integration-badges">
              <span class="wui-badge wui-badge--soft">AGENT SKILL</span>
              <span class="wui-badge wui-badge--outline">host bridge v1</span>
              <span class="wui-badge wui-badge--outline">authority=false</span>
            </div>
            <h1>{zh() ? "让你的 Agent 接入 NovelForge，而不是绕过 NovelForge。" : "Let your agent use NovelForge without bypassing NovelForge."}</h1>
            <p>{zh() ? "NovelForge 已经有一个可移植、只读的 Agent Skill。它通过公开 Host Bridge 发现能力、检查 Project / Context / semantic contracts，并把不支持的写操作明确留在 Core 一侧。" : "NovelForge ships a portable, read-only Agent Skill. It uses the public Host Bridge to discover capabilities and inspect Project, Context, and semantic contracts while keeping unsupported writes behind Core-owned boundaries."}</p>
          </div>
          <div class="agent-integration-summary wui-card">
            <div><small>{zh() ? "产品模型" : "PRODUCT MODEL"}</small><strong>one product · many hosts</strong></div>
            <div><span>6</span><small>{zh() ? "当前只读操作" : "read operations"}</small></div>
            <div><span>0</span><small>{zh() ? "桥接层写权限" : "bridge write authority"}</small></div>
            <div><span>✓</span><small>{zh() ? "unsupported fail closed" : "unsupported fails closed"}</small></div>
          </div>
        </section>

        <section class="agent-path-grid" aria-label={zh() ? "Agent 接入路径" : "Agent integration paths"}>
          <article class="agent-path-card" data-lane="project">
            <span class="agent-path-icon">✦</span>
            <small>{zh() ? "最短路径" : "SHORTEST PATH"}</small>
            <h2>Portable Agent Skill</h2>
            <p>{zh() ? "把 agent-skills/novelforge 作为宿主可读的 skill package。操作说明和 client script 一起移动，不要求导入 NovelForge 私有 Python internals。" : "Use agent-skills/novelforge as a host-readable skill package. Instructions and client script travel together without importing NovelForge private Python internals."}</p>
            <code>agent-skills/novelforge/SKILL.md</code>
          </article>
          <article class="agent-path-card" data-lane="runtime">
            <span class="agent-path-icon">⌘</span>
            <small>{zh() ? "底层边界" : "PUBLIC BOUNDARY"}</small>
            <h2>CLI Host Bridge</h2>
            <p>{zh() ? "任何能安全调用本地 CLI 的宿主都可以先 describe，再按 versioned request/result envelope 发只读请求。" : "Any host that can safely invoke a local CLI can describe the bridge first, then use its versioned request/result envelope for read-only queries."}</p>
            <code>novelforge_studio_host_bridge_request_v1</code>
          </article>
          <article class="agent-path-card" data-lane="evidence">
            <span class="agent-path-icon">◇</span>
            <small>{zh() ? "自定义宿主" : "CUSTOM HOST"}</small>
            <h2>Provider-neutral adapter</h2>
            <p>{zh() ? "NovelForge 不把 Canon、Settlement 或写权限绑定到具体 Agent provider。宿主只是 delivery surface；真正的 authority 仍由 Project 与 Core contract 决定。" : "NovelForge does not bind Canon, Settlement, or write authority to a specific agent provider. The host is a delivery surface; Project and Core contracts still own authority."}</p>
            <code>capability ≠ authority</code>
          </article>
        </section>

        <section class="agent-host-workbench" aria-labelledby="agent-host-heading">
          <div class="agent-host-heading">
            <div>
              <small>{zh() ? "宿主 recipe" : "HOST RECIPES"}</small>
              <h2 id="agent-host-heading">{zh() ? "Claude Code、Codex、Cursor、OpenCode：用同一条公开边界。" : "Claude Code, Codex, Cursor, OpenCode: one public boundary."}</h2>
              <p>{zh() ? "这里的 profile 是接入 recipe，不是假装已经发布 provider-specific 插件。选择你的 coding agent，复制一段最小宿主说明；真正可用能力仍以 bridge.describe 返回值为准。" : "These profiles are integration recipes, not claims that provider-specific plugins already ship. Pick a coding agent and copy a minimal host instruction; bridge.describe remains the source of truth for available operations."}</p>
            </div>
            <span class="agent-host-safety">✓ {zh() ? "provider-specific adapter：未捆绑" : "provider-specific adapter: not bundled"}</span>
          </div>

          <div class="agent-host-tabs" role="tablist" aria-label={zh() ? "Coding Agent 宿主" : "Coding agent hosts"}>
            <For each={hostProfiles}>{(host, index) => (
              <button type="button" role="tab" aria-selected={selectedHost() === index()} data-active={selectedHost() === index()} onClick={() => setSelectedHost(index())}>
                <span class="agent-host-glyph" aria-hidden="true">{host.glyph}</span>
                <span><strong>{host.name}</strong><small>{zh() ? host.fitZh : host.fitEn}</small></span>
              </button>
            )}</For>
          </div>

          <div class="agent-host-detail">
            <article class="agent-host-profile">
              <div class="agent-host-profile-badges">
                <span class="wui-badge wui-badge--soft">{currentHost().name}</span>
                <span class="wui-badge wui-badge--outline">generic read-only bridge</span>
              </div>
              <h3>{zh() ? "能力匹配，不制造新的权威层。" : "Match capabilities without inventing another authority layer."}</h3>
              <p>{zh() ? currentHost().summaryZh : currentHost().summaryEn}</p>
              <ul class="agent-host-facts">
                <li><span>{zh() ? "入口" : "Entry"}</span><strong>agent-skills/novelforge/SKILL.md</strong></li>
                <li><span>{zh() ? "执行" : "Execution"}</span><strong>{zh() ? "本地 Python CLI" : "local Python CLI"}</strong></li>
                <li><span>{zh() ? "能力发现" : "Discovery"}</span><strong>bridge.describe</strong></li>
                <li><span>{zh() ? "写权限" : "Write authority"}</span><strong>0 · authority=false</strong></li>
              </ul>
            </article>

            <article class="agent-host-instruction">
              <div class="agent-host-instruction-head">
                <div><small>{zh() ? "可复制宿主说明" : "COPYABLE HOST INSTRUCTION"}</small><strong>{zh() ? `交给 ${currentHost().name} 的最小边界` : `Minimal boundary for ${currentHost().name}`}</strong></div>
                <button type="button" class="wui-button wui-button--soft" onClick={() => copyText("host", hostInstruction())}>{copied() === "host" ? "✓" : zh() ? "复制说明" : "Copy instruction"}</button>
              </div>
              <pre><code>{hostInstruction()}</code></pre>
              <p class="agent-host-note"><span aria-hidden="true">♡</span><span>{zh() ? "这段说明不会赋予 Canon / Settlement 权限，也不会把 provider session memory 变成故事事实。" : "This instruction grants no Canon or Settlement authority and does not turn provider session memory into story truth."}</span></p>
            </article>
          </div>
        </section>

        <section class="agent-onboarding-grid">
          <article class="wui-card agent-onboarding-card">
            <div class="agent-section-heading">
              <div><small>{zh() ? "三步开始" : "THREE STEPS"}</small><h2>{zh() ? "先证明边界，再让 Agent 使用它。" : "Prove the boundary before your agent uses it."}</h2></div>
              <span class="agent-kawaii" aria-hidden="true">ฅ^•ﻌ•^ฅ</span>
            </div>

            <div class="agent-command-list">
              <div class="agent-command-row">
                <span>01</span>
                <div><strong>{zh() ? "运行 self-test" : "Run the self-test"}</strong><small>{zh() ? "验证 bridge schema、authority=false、无 direct Core store access。" : "Verify bridge schema, authority=false, and no direct Core store access."}</small><code>{selfTest}</code></div>
                <button type="button" class="wui-button wui-button--ghost" onClick={() => copyText("self-test", selfTest)}>{copied() === "self-test" ? "✓" : zh() ? "复制" : "Copy"}</button>
              </div>
              <div class="agent-command-row">
                <span>02</span>
                <div><strong>{zh() ? "让宿主先 discover" : "Discover before invoking"}</strong><small>{zh() ? "supported_operations 是实时操作词表；不要猜 private API。" : "supported_operations is the live vocabulary; do not guess private APIs."}</small><code>{describe}</code></div>
                <button type="button" class="wui-button wui-button--ghost" onClick={() => copyText("describe", describe)}>{copied() === "describe" ? "✓" : zh() ? "复制" : "Copy"}</button>
              </div>
              <div class="agent-command-row">
                <span>03</span>
                <div><strong>{zh() ? "发送 versioned request" : "Send a versioned request"}</strong><small>{zh() ? "每个 request 都显式携带 authority:false，并保留 request/result fingerprint。" : "Every request explicitly carries authority:false and retains request/result fingerprints."}</small><code>invoke --request request.json</code></div>
                <button type="button" class="wui-button wui-button--ghost" onClick={() => copyText("request", request())}>{copied() === "request" ? "✓" : zh() ? "复制 JSON" : "Copy JSON"}</button>
              </div>
            </div>
          </article>

          <article class="wui-card agent-request-builder">
            <div class="agent-section-heading">
              <div><small>REQUEST BUILDER</small><h2>{zh() ? "选一个当前真的支持的操作。" : "Choose an operation that actually exists today."}</h2></div>
              <span class="wui-badge wui-badge--success">read-only</span>
            </div>
            <div class="agent-operation-tabs" role="tablist" aria-label={zh() ? "支持的操作" : "Supported operations"}>
              <For each={supportedOperations}>{(operation, index) => (
                <button type="button" role="tab" aria-selected={selected() === index()} data-active={selected() === index()} onClick={() => setSelected(index())}>
                  <strong>{operation.id}</strong><small>{zh() ? operation.labelZh : operation.labelEn}</small>
                </button>
              )}</For>
            </div>
            <div class="agent-request-meta">
              <span>Core basis</span>
              <strong>{current().basis}</strong>
            </div>
            <pre class="agent-request-json"><code>{request()}</code></pre>
          </article>
        </section>

        <section class="agent-contract-grid">
          <article class="agent-contract-card agent-contract-card--ready">
            <div><span>✓</span><small>{zh() ? "当前公开" : "AVAILABLE NOW"}</small></div>
            <h2>{zh() ? "宿主可以看什么" : "What a host can inspect"}</h2>
            <ul><For each={supportedOperations}>{(operation) => <li><code>{operation.id}</code><span>{zh() ? operation.labelZh : operation.labelEn}</span></li>}</For></ul>
          </article>
          <article class="agent-contract-card agent-contract-card--deferred">
            <div><span>○</span><small>{zh() ? "明确延后" : "EXPLICITLY DEFERRED"}</small></div>
            <h2>{zh() ? "现在不能假装已经有" : "What the bridge refuses to fake"}</h2>
            <ul><For each={deferredOperations}>{(operation) => <li><code>{operation}</code><span>{zh() ? "Core public contract 尚未满足" : "awaiting a safe Core public contract"}</span></li>}</For></ul>
          </article>
          <article class="agent-contract-card agent-contract-card--authority">
            <div><span>♡</span><small>AUTHORITY FIREWALL</small></div>
            <h2>{zh() ? "接得上，不等于有权写。" : "Connected does not mean authorized to write."}</h2>
            <ul>
              <li><strong>Canon</strong><span>bridge authority = false</span></li>
              <li><strong>Settlement</strong><span>{zh() ? "仍由 Core workflow 拥有" : "still Core-workflow owned"}</span></li>
              <li><strong>Private runtime store</strong><span>{zh() ? "禁止直接读取" : "direct access forbidden"}</span></li>
              <li><strong>Host paths</strong><span>{zh() ? "结果默认去除绝对路径" : "absolute paths are redacted"}</span></li>
            </ul>
          </article>
        </section>

        <section class="agent-integration-footer-callout">
          <div><span>✦</span><div><small>{zh() ? "下一步" : "NEXT"}</small><h2>{zh() ? "先用真实只读边界完成互操作，再等 Core 暴露安全的写命令。" : "Ship real read interoperability first; add writes only when Core exposes safe commands."}</h2></div></div>
          <div class="agent-integration-footer-actions"><a class="wui-button wui-button--soft" href="/inspect">{zh() ? "检查一个 Project" : "Inspect a Project"} →</a><a class="wui-button wui-button--ghost" href="/docs">📚 {zh() ? "打开文档" : "Open docs"}</a></div>
        </section>
      </main>

      <footer class="site-footer agent-integration-footer">
        <div class="page-width footer-grid">
          <div class="footer-brand-block"><div class="footer-brand"><img src={brandMark} alt="" /><strong>NovelForge</strong></div><p>{zh() ? "Agent 是宿主，不是故事权威。" : "The agent is a host, not story authority."}</p></div>
          <div class="footer-links"><a href="/playground">Local Playground</a><a href="/inspect">{zh() ? "检查项目" : "Project Inspector"}</a></div>
          <div class="footer-links"><a href="/docs">{zh() ? "文档" : "Docs"}</a><a href="/">{zh() ? "返回产品站" : "Back to product"}</a></div>
        </div>
      </footer>
    </div>
  );
}
