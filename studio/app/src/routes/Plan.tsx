import { Show } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Plan() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const project = () => studio.projectProjection();
  return (
    <section class="nf-page qf-authoring-secondary">
      <PageIntro eyebrow="PLAN" title={zh() ? "计划应该像创作桌面，不像数据库后台。" : "Planning should feel like a writing desk, not a database console."} body={zh() ? "当前 Core 只通过 project.inspect 暴露 plan 数量；没有稳定的 Plan/Scene Card projection 或 mutation contract，所以 Studio 不会在前端自建第二套计划数据。" : "Core currently exposes only plan counts through project.inspect. No stable Plan/Scene Card projection or mutation contract exists, so Studio does not build a second planning store in the frontend."} />
      <Show when={project()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "打开 Project 后查看" : "Open a Project to continue"}</strong></div>}>
        {(value) => <div class="qf-editorial-sheet"><span class="nf-eyebrow">CORE SNAPSHOT</span><h2>{value().project.title}</h2><div class="qf-authoring-counts"><span><strong>{value().counts.plans ?? 0}</strong>{zh() ? "计划" : "plans"}</span><span><strong>{value().counts.story_nodes ?? 0}</strong>{zh() ? "故事节点" : "story nodes"}</span></div><aside class="qf-awaiting-core" role="status"><div><strong>awaiting_external</strong><code>plan.inspect / plan mutation contracts</code></div><p>{zh() ? "需要 Core 返回 typed Plan + Scene Card projection，并为每一种写操作定义 authority/CAS/idempotency。" : "Core must expose typed Plan + Scene Card projections and operation-specific authority/CAS/idempotency for writes."}</p></aside></div>}
      </Show>
    </section>
  );
}
