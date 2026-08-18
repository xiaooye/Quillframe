import { Show } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";

export default function Story() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const project = () => studio.projectProjection();
  return (
    <section class="nf-page qf-authoring-secondary">
      <PageIntro eyebrow="STORY" title={zh() ? "Story Bible 只展示 Core 已知的故事事实。" : "Story Bible shows only story truth Core actually exposes."} body={zh() ? "人物、关系、世界、Timeline 与 Canon authority 必须来自 typed Core projection；UI 不从文件名、正文片段或模型推测中合成 Story state。" : "Characters, relationships, world, timeline and Canon authority must come from typed Core projections; the UI never synthesizes Story state from filenames, prose snippets or model guesses."} />
      <Show when={project()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "打开 Project 后查看" : "Open a Project to continue"}</strong></div>}>
        {(value) => <div class="qf-editorial-sheet"><div class="qf-authoring-counts"><span><strong>{value().counts.characters ?? 0}</strong>{zh() ? "人物" : "characters"}</span><span><strong>{value().counts.relationships ?? 0}</strong>{zh() ? "关系" : "relationships"}</span><span><strong>{value().counts.canon_claims ?? 0}</strong>Canon claims</span></div><aside class="qf-awaiting-core" role="status"><div><strong>awaiting_external</strong><code>story.inspect</code></div><p>{zh() ? "需要 typed Character / Relationship / World / Timeline / Canon projection，并且每项带文字 authority label。" : "A typed Character / Relationship / World / Timeline / Canon projection is required, with textual authority labels on every item."}</p></aside></div>}
      </Show>
    </section>
  );
}
