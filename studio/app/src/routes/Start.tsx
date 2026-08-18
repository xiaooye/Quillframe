import { createMemo, createSignal } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";

const initCommand = 'python quillframe.py project init ./my-novel --id my-novel --title "My Novel" --language en';

const copy = {
  "en-US": {
    eyebrow: "Choose a host · keep one project model",
    title: "Start a Quillframe project",
    body: "Choose the surface that fits your workflow. The CLI is the current project-creation path; Hosted Studio and Agent Skill are usable now within their read-only boundaries, while a packaged Desktop app remains planned.",
    cliMeta: "CLI · available now",
    cliTitle: "Create the project scaffold",
    cliBody: "From a Quillframe framework checkout, create a project with the current stdlib Project SDK through the top-level CLI.",
    cliAction: "Copy init command",
    cliNote: "This creates the scaffold. Pin the framework lock and required attestation before production work; scaffolding alone does not grant Canon authority.",
    desktopMeta: "Local app · planned",
    desktopTitle: "Desktop",
    desktopBody: "A packaged local app can wrap the same Studio/Core boundary later. No Desktop binary is claimed or shipped by this surface today.",
    desktopAction: "Not available yet",
    cloudMeta: "Cloud · available now",
    cloudTitle: "Hosted Studio",
    cloudBody: "Use browser-local Project Preflight and Playground without an account or backend. Authoritative project/runtime projections still require a bound Core.",
    cloudAction: "Open browser Playground",
    agentMeta: "Agent Skill · portable pattern ready",
    agentTitle: "Coding agent",
    agentBody: "Bootstrap Quillframe inside Claude Code, Codex, OpenCode, Cursor, or a custom agent through the portable skill and public boundaries.",
    agentAction: "Open Agent Integrations",
    modelMeta: "AI · optional",
    modelTitle: "Connect a model API",
    modelBody: "AI does not block ordinary authoring. When you want model-assisted work, Quillframe only asks for an API Endpoint and Access Token; model discovery and capability observation belong to the runtime.",
    modelAction: "Open AI & Models",
    modelNote: "No model selection is required during onboarding. Automatic model selection remains the default.",
    boundary: "These are delivery surfaces, not separate authorities. Core/project contracts remain the source of truth, and no UI or agent integration can synthesize Canon or write authority.",
    copied: "Copied",
  },
  "zh-CN": {
    eyebrow: "选择宿主 · 共用同一 Project 模型",
    title: "开始一个 Quillframe 项目",
    body: "选择最适合你工作流的入口。当前真正负责创建 Project 的是 CLI；Hosted Studio 与 Agent Skill 已可在各自的只读边界内使用，而打包后的 Desktop App 仍处于规划阶段。",
    cliMeta: "CLI · 当前可用",
    cliTitle: "创建 Project scaffold",
    cliBody: "在 Quillframe Framework checkout 中，通过顶层 CLI 调用当前 stdlib Project SDK 创建项目骨架。",
    cliAction: "复制 init 命令",
    cliNote: "这一步只创建 scaffold。进入 production work 前仍需锁定 Framework lock 并满足所需 attestation；初始化本身不会授予 Canon authority。",
    desktopMeta: "本地 App · 规划中",
    desktopTitle: "Desktop",
    desktopBody: "未来可以用打包后的本地 App 包住同一套 Studio/Core 边界；当前这个产品面不声称已经发布 Desktop binary。",
    desktopAction: "暂未开放",
    cloudMeta: "Cloud · 当前可用",
    cloudTitle: "Hosted Studio",
    cloudBody: "无需账号或后端即可使用浏览器本地 Project Preflight 与 Playground；权威 Project / Runtime 投影仍必须绑定 Core。",
    cloudAction: "打开浏览器 Playground",
    agentMeta: "Agent Skill · portable pattern ready",
    agentTitle: "Coding agent",
    agentBody: "通过 portable skill 与公共边界，把 Quillframe 接入 Claude Code、Codex、OpenCode、Cursor 或自定义 Agent。",
    agentAction: "打开 Agent Integrations",
    modelMeta: "AI · 可选",
    modelTitle: "连接模型 API",
    modelBody: "AI 不会阻塞普通写作。需要模型辅助时，Quillframe 只向你索取 API Endpoint 与 Access Token；模型发现与能力观察都交给运行时。",
    modelAction: "打开 AI 与模型",
    modelNote: "首次设置不要求选择模型；默认始终是自动选择模型。",
    boundary: "这些只是不同 delivery surface，不是不同 authority。Core / Project contract 仍是事实来源，任何 UI 或 Agent integration 都不能自行合成 Canon 或写入权限。",
    copied: "已复制",
  },
} as const;

export default function Start() {
  const { locale } = useI18n();
  const text = createMemo(() => copy[locale()]);
  const [copied, setCopied] = createSignal(false);

  const copyCommand = async () => {
    await navigator.clipboard.writeText(initCommand);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section class="nf-page nf-start-page">
      <PageIntro eyebrow={text().eyebrow} title={text().title} body={text().body} />

      <div class="nf-catalog-grid">
        <article
          class="wui-card nf-card nf-card-accent"
          style={{
            background: "color-mix(in oklab,var(--qf-lane-project-fill) 58%,var(--qf-studio-panel))",
            "border-color": "color-mix(in oklab,var(--qf-lane-project-stroke) 28%,var(--qf-studio-line-soft))",
          }}
        >
          <div class="wui-card__header">
            <span class="nf-card-label">{text().cliMeta}</span>
            <h2>{text().cliTitle}</h2>
          </div>
          <div class="wui-card__content">
            <p>{text().cliBody}</p>
            <pre class="wui-code-block"><code>{initCommand}</code></pre>
            <button class="wui-button wui-button--outline" type="button" onClick={() => void copyCommand()}>
              {copied() ? text().copied : text().cliAction}
            </button>
            <small>{text().cliNote}</small>
          </div>
        </article>

        <article
          class="wui-card nf-card"
          style={{ background: "color-mix(in oklab,var(--qf-studio-panel-subtle) 58%,var(--qf-studio-panel))" }}
        >
          <div class="wui-card__header">
            <span class="nf-card-label">{text().desktopMeta}</span>
            <h2>{text().desktopTitle}</h2>
          </div>
          <div class="wui-card__content">
            <p>{text().desktopBody}</p>
            <button class="wui-button wui-button--outline" type="button" disabled>{text().desktopAction}</button>
          </div>
        </article>

        <article
          class="wui-card nf-card"
          style={{
            background: "color-mix(in oklab,var(--qf-lane-runtime-fill) 52%,var(--qf-studio-panel))",
            "border-color": "color-mix(in oklab,var(--qf-lane-runtime-stroke) 24%,var(--qf-studio-line-soft))",
          }}
        >
          <div class="wui-card__header">
            <span class="nf-card-label">{text().cloudMeta}</span>
            <h2>{text().cloudTitle}</h2>
          </div>
          <div class="wui-card__content">
            <p>{text().cloudBody}</p>
            <A class="wui-button wui-button--outline" href="/workspace">{text().cloudAction}</A>
          </div>
        </article>

        <article
          class="wui-card nf-card"
          style={{
            background: "color-mix(in oklab,var(--qf-lane-editorial-fill) 52%,var(--qf-studio-panel))",
            "border-color": "color-mix(in oklab,var(--qf-lane-editorial-stroke) 24%,var(--qf-studio-line-soft))",
          }}
        >
          <div class="wui-card__header">
            <span class="nf-card-label">{text().agentMeta}</span>
            <h2>{text().agentTitle}</h2>
          </div>
          <div class="wui-card__content">
            <p>{text().agentBody}</p>
            <A class="wui-button wui-button--outline" href="/agents">{text().agentAction}</A>
          </div>
        </article>
      </div>

      <section class="nf-start-model-api" aria-labelledby="start-model-api-heading">
        <div>
          <span class="nf-eyebrow">{text().modelMeta}</span>
          <h2 id="start-model-api-heading">{text().modelTitle}</h2>
          <p>{text().modelBody}</p>
          <small>{text().modelNote}</small>
        </div>
        <A class="wui-button wui-button--outline" href="/settings?section=models">{text().modelAction}</A>
      </section>

      <div class="wui-alert" role="note">
        <div class="wui-alert__body">
          <strong class="wui-alert__title">authority=false</strong>
          <span class="wui-alert__description">{text().boundary}</span>
        </div>
      </div>
    </section>
  );
}
