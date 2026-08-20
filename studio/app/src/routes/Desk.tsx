import { Show } from "solid-js";
import { A } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { CoreRequirementNotice } from "../authoring/AuthoringUI";

export default function Desk() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const project = () => studio.projectProjection();
  const manuscriptHref = () => studio.projectId() ? `/manuscript?project=${encodeURIComponent(studio.projectId())}` : "/start";
  const reviewHref = () => studio.projectId() ? `/review?project=${encodeURIComponent(studio.projectId())}` : "/start";
  return (
    <section class="nf-page qf-desk-page">
      <PageIntro eyebrow="DESK" title={zh() ? "回到作品。" : "Back to the work."} body={zh() ? "Quillframe 的首页先回答：我现在写什么？不是 Runtime 有多少条记录。" : "Quillframe's home answers what you are writing now, not how many runtime records exist."} />

      <Show when={studio.bridgeAvailable()} fallback={<section class="qf-desk-hero qf-desk-unbound"><div><span class="nf-eyebrow">CORE UNBOUND</span><h2>{zh() ? "先连接一个真实 Core，再开始作品。" : "Bind a real Core before starting the work."}</h2><p>{zh() ? "Hosted Web 需要 hosted Core；Tauri 需要 local Core bridge。这里不会用 Demo state 冒充 Project。" : "Hosted Web needs hosted Core; Tauri needs a local Core bridge. Demo state never impersonates a Project here."}</p></div><A class="wui-button wui-button--solid" href="/start">{zh() ? "开始" : "Start"}</A></section>}>
        <Show when={project()} fallback={<section class="qf-desk-hero"><div><span class="nf-eyebrow">NEW WORK</span><h2>{zh() ? "建立 Project，然后直接进入正文。" : "Create a Project, then go straight to the manuscript."}</h2><p>{zh() ? "AI 是可选增强，不是打开编辑器的前置条件。" : "AI is optional assistance, not a prerequisite for opening the editor."}</p></div><A class="wui-button wui-button--solid" href="/start">{zh() ? "新建 / 打开 Project" : "New / Open Project"}</A></section>}>
          {(value) => <>
            <section class="qf-desk-hero">
              <div><span class="nf-eyebrow">CURRENT PROJECT</span><h2>{value().manifest.title}</h2><p><code>{value().manifest.id}</code> · {value().manifest.language}</p></div>
              <A class="wui-button wui-button--solid qf-primary-writing-action" href={manuscriptHref()}>{zh() ? "继续写正文" : "Continue Manuscript"}</A>
            </section>

            <div class="qf-desk-thread" aria-label={zh() ? "创作路径" : "Authoring path"}>
              <A href={manuscriptHref()}><span>01</span><strong>{zh() ? "正文" : "Manuscript"}</strong><small>{value().counts.documents ?? 0} documents · {value().counts.document_revisions ?? 0} revisions</small></A>
              <A href={`/plan?project=${encodeURIComponent(value().manifest.id)}`}><span>02</span><strong>{zh() ? "计划" : "Plan"}</strong><small>{value().counts.plans ?? 0} plans</small></A>
              <A href={`/story?project=${encodeURIComponent(value().manifest.id)}`}><span>03</span><strong>{zh() ? "故事" : "Story"}</strong><small>{value().counts.characters ?? 0} characters · {value().counts.canon_claims ?? 0} canon claims</small></A>
              <A href={reviewHref()}><span>04</span><strong>{zh() ? "审阅" : "Review"}</strong><small>{value().counts.candidates ?? 0} candidates · {value().counts.review_evidence ?? 0} review evidence</small></A>
            </div>

            <section class="qf-desk-contextual">
              <div><span class="nf-eyebrow">AI ASSISTANT</span><h2>{zh() ? "需要帮助时再打开。" : "Open it when you need help."}</h2><p>{zh() ? "⌘I 打开 Quillframe Agent Dock；真实 Run 会留下可检查的 Context 与 Runtime evidence。" : "⌘I opens the Quillframe Agent Dock; real Runs leave inspectable Context and runtime evidence."}</p></div>
              <div class="qf-inline-actions"><A class="wui-button wui-button--outline" href="/settings?section=models">{zh() ? "AI 与模型" : "AI & Models"}</A><A class="wui-button wui-button--ghost" href={`/context?project=${encodeURIComponent(value().manifest.id)}${studio.lastRunId() ? `&run=${encodeURIComponent(studio.lastRunId())}` : ""}`}>Context</A></div>
            </section>
          </>}
        </Show>
      </Show>

      <CoreRequirementNotice operation="project.list" compact />
    </section>
  );
}
