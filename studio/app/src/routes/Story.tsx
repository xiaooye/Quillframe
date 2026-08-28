import { For, Show, createEffect, createSignal, on, onCleanup } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";
import { parseStoryInspection, parseReaderExpectations, type StoryInspection, type StorySource, type ReaderExpectationsInspection } from "../authoring/contracts";

const displayValue = (value: unknown): string => value === null || value === undefined ? "—" : typeof value === "string" ? value : JSON.stringify(value, null, 2);

export default function Story() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];
  const [story, setStory] = createSignal<StoryInspection>();
  const [expectations, setExpectations] = createSignal<ReaderExpectationsInspection>();
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  let generation = 0;
  const load = async () => {
    const projectId = studio.projectId(); const requestGeneration = ++generation;
    const current = () => generation === requestGeneration && studio.projectId() === projectId;
    setStory(undefined); setExpectations(undefined); setError(undefined);
    if (!projectId) { setLoading(false); return; }
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        operations().includes("story.inspect") ? invokeBridge("story.inspect", { project_id: projectId }) : Promise.resolve(undefined),
        operations().includes("reader.expectations.inspect") ? invokeBridge("reader.expectations.inspect", { project_id: projectId }) : Promise.resolve(undefined),
        studio.refreshChapters(),
      ]);
      if (!current()) return;
      const errors: string[] = [];
      results.forEach((settled, index) => {
        try {
          if (settled.status === "rejected") throw settled.reason;
          const result = settled.value;
          if (!result) return;
          if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
          if (index === 0) setStory(parseStoryInspection(result.data, projectId));
          else setExpectations(parseReaderExpectations(result.data, projectId));
        } catch (cause) { errors.push(cause instanceof Error ? cause.message : String(cause)); }
      });
      if (errors.length) setError(errors.join(" · "));
    } catch (cause) { if (current()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (current()) setLoading(false); }
  };
  createEffect(on([() => studio.projectId(), operations], () => { void load(); }));
  onCleanup(() => { generation += 1; });
  const characterName = (id: string) => story()?.characters.find((item) => item.character_id === id)?.name ?? id;
  const canonNeedsReview = (stateKey: string) => studio.chapters().find((chapter) => `chapter:${chapter.chapter_id}` === stateKey)?.needs_review === true;
  const SourceEvidence = (props: { source: StorySource }) => (
    <div class="qf-story-source" data-source-state={props.source.source_state}>
      <strong>{props.source.source_state === "current" ? (zh() ? "来源当前有效" : "Source is current")
        : props.source.source_state === "stale" ? (zh() ? "来源已过期 · 需要重审" : "Source is stale · review required")
          : (zh() ? "来源未追踪" : "Source is untracked")}</strong>
      <Show when={props.source.source_chapter_id}>{(chapterId) => <span>{zh() ? "来源章节" : "Source chapter"}: {chapterId()}</span>}</Show>
      <Show when={props.source.source_state === "stale"}><p>{zh() ? "来源章节或其依赖已变化。历史接受记录仍保留，但需要重新核对这项状态是否成立。" : "The source chapter or its dependencies changed. The historical acceptance remains recorded; this state needs review against the current manuscript."}</p></Show>
      <Show when={props.source.source_state === "untracked"}><p>{zh() ? "尚无可追踪的来源章节，无法确认此状态是否仍然适用。" : "No source chapter is tracked, so continued applicability is unknown."}</p></Show>
    </div>
  );
  return (
    <section class="nf-page qf-authoring-secondary">
      <PageIntro eyebrow="STORY · CONTINUITY" title={zh() ? "看清已经发生的事，才知道下一章会改变什么。" : "See what is established before deciding what changes next."} body={zh() ? "人物、关系、时间线和章节依赖均来自 Core。事实、计划与模型观察分别标注；没有记录的内容保持空白。" : "Characters, relationships, timeline and chapter dependencies come from Core. Facts, plans and model observations keep distinct authority labels; missing records stay empty."} />
      <Show when={studio.projectId()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "打开小说项目后查看" : "Open a novel to continue"}</strong><a href="/start">{zh() ? "开始" : "Start"}</a></div>}>
        <div class="qf-section-head"><h2>{studio.projectProjection()?.manifest.title ?? studio.projectId()}</h2><button class="wui-button wui-button--outline" type="button" disabled={loading()} onClick={() => void load()}>{loading() ? (zh() ? "读取中…" : "Loading…") : (zh() ? "刷新故事资料" : "Refresh story")}</button></div>
        <CoreRequirementNotice operation="story.inspect" />
        <Show when={error()}>{(message) => <p role="alert">{message()}</p>}</Show>
        <section class="qf-story-section"><h2>{zh() ? "读者期待与兑现" : "Reader expectations and payoffs"}</h2><p class="qf-inspector-boundary">{zh() ? "期待账本记录问题、承诺与推进。模型阅读观察不等于真实读者数据，也不会自行变成故事事实。" : "The ledger tracks questions, promises and progress. Model reading observations are not real audience data and do not become story facts on their own."}</p><CoreRequirementNotice operation="reader.expectations.inspect" compact />
          <Show when={expectations()}>{(ledger) => <><For each={ledger().items}>{(item) => <article><header><h3>{item.description}</h3><AuthorityLabel value={item.status} /></header><p>{item.kind} · {item.scope}</p><dl><dt>{zh() ? "首次建立 / 最近推进" : "Opened / last advanced"}</dt><dd>{item.opened_order} / {item.last_touched_order}</dd><dt>{zh() ? "计划兑现顺序" : "Planned payoff order"}</dt><dd>{item.due_by_order ?? "—"}</dd></dl><details><summary>{zh() ? "记录引用与来源" : "Reference and source"}</summary><code>{item.expectation_id}</code><p>{item.source_ref ?? "—"}</p><code>{item.source_fingerprint ?? "—"}</code><p>version {item.version} · authority=false</p></details></article>}</For><Show when={!ledger().items.length}><p>{zh() ? "尚无已应用的期待记录。" : "No expectation entries have been applied yet."}</p></Show><Show when={ledger().observations.length}><details><summary>{zh() ? "已发布版本的模型阅读观察" : "Model observations for released versions"}</summary><For each={ledger().observations}>{(observation) => <article><header><h3>{observation.chapter_id}</h3><AuthorityLabel value={observation.state} /></header><p>model_proxy · {observation.candidate_id}</p><pre>{displayValue(observation.updates)}</pre><code>{observation.candidate_fingerprint}</code></article>}</For></details></Show></>}</Show>
        </section>
        <Show when={story()}>{(value) => <>
          <div class="qf-story-grid">
            <section class="qf-story-section"><h2>{zh() ? "人物" : "Characters"}</h2><For each={value().characters}>{(item) => <article><header><h3>{item.name}</h3><AuthorityLabel value={item.authority_class} /></header><SourceEvidence source={item} /><dl><dt>{zh() ? "当前欲望与目标" : "Agenda"}</dt><dd><pre>{displayValue(item.agenda)}</pre></dd><dt>{zh() ? "人物声音" : "Voice"}</dt><dd><pre>{displayValue(item.voice_notes)}</pre></dd></dl><details><summary>{zh() ? "状态与编号" : "State and identity"}</summary><code>{item.character_id}</code><pre>{displayValue(item.state)}</pre></details></article>}</For><Show when={!value().characters.length}><p>{zh() ? "尚无人物记录。" : "No character records yet."}</p></Show></section>
            <section class="qf-story-section"><h2>{zh() ? "关系" : "Relationships"}</h2><For each={value().relationships}>{(item) => <article><header><h3>{characterName(item.participant_a)} · {characterName(item.participant_b)}</h3><AuthorityLabel value={item.authority_class} /></header><SourceEvidence source={item} /><p>{item.relationship_type}</p><pre>{displayValue(item.state)}</pre><code>{item.relationship_id}</code></article>}</For><Show when={!value().relationships.length}><p>{zh() ? "尚无关系记录。" : "No relationship records yet."}</p></Show></section>
            <section class="qf-story-section"><h2>{zh() ? "时间线" : "Timeline"}</h2><p class="qf-inspector-boundary">{zh() ? "故事发生顺序不等于读者已经知情；写作上下文还需检查揭示边界。" : "Story order is not reader knowledge. Writing context must also respect reveal boundaries."}</p><For each={value().timeline}>{(item) => <article><header><h3>{item.title}</h3><AuthorityLabel value={item.authority_class} /></header><SourceEvidence source={item} /><p>{item.description}</p><small>{zh() ? "故事顺序" : "Story order"}: {item.story_order} · {item.source_ref ?? "—"}</small></article>}</For><Show when={!value().timeline.length}><p>{zh() ? "尚无时间线记录。" : "No timeline records yet."}</p></Show></section>
            <section class="qf-story-section"><h2>{zh() ? "世界设定" : "World"}</h2><For each={value().world}>{(item) => <article><header><h3>{item.name}</h3><AuthorityLabel value={item.authority_class} /></header><SourceEvidence source={item} /><p>{item.entity_type}</p><pre>{displayValue(item.truth)}</pre><code>{item.entity_id}</code></article>}</For><Show when={!value().world.length}><p>{zh() ? "尚无世界设定记录。" : "No world records yet."}</p></Show></section>
          </div>
          <section class="qf-story-section"><h2>{zh() ? "已结算事实" : "Settled state"}</h2><For each={value().canon}>{(item) => <article><header><h3>{item.state_key}</h3><AuthorityLabel value={item.authority_class} /></header><Show when={canonNeedsReview(item.state_key)}><p class="qf-story-source" data-source-state="stale">{zh() ? "Core 已标记此章需要重审。以下是保留的结算记录，当前正文或依赖需要重新确认。" : "Core marks this chapter for review. The retained settlement below does not establish that the current manuscript and dependencies remain valid."}</p></Show><pre>{displayValue(item.value)}</pre><details><summary>{zh() ? "事实来源" : "Evidence"}</summary><p>{item.evidence_ref ?? "—"}</p><code>{item.content_fingerprint}</code></details></article>}</For><Show when={!value().canon.length}><p>{zh() ? "尚未结算事实。接受稿件与结算是两个独立动作。" : "No settled state yet. Accepting a manuscript and settling it are separate actions."}</p></Show></section>
          <section class="qf-story-section"><h2>{zh() ? "章节依赖" : "Chapter dependencies"}</h2><For each={value().dependencies}>{(item) => <article><header><h3>{item.chapter_id} · {zh() ? "依赖" : "depends on"} {item.source_chapter_id}</h3><AuthorityLabel value={item.status} /></header><code>{item.source_fingerprint}</code></article>}</For><Show when={!value().dependencies.length}><p>{zh() ? "尚无已记录的跨章依赖。" : "No recorded cross-chapter dependencies."}</p></Show></section>
        </>}</Show>
      </Show>
    </section>
  );
}
