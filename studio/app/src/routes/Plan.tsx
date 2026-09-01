import { For, Show, createEffect, createSignal, on, onCleanup, onMount } from "solid-js";
import { useBeforeLeave } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";
import { parsePlanInspection, parsePlanSave, type PlanItem, type ReaderIntent } from "../authoring/contracts";

const planTemplate = (target: string) => target === "book"
  ? JSON.stringify({ reader_promise: "", protagonist_agency: "", central_conflict: "", progression: [], endgame_reserve: [], anti_exhaustion_limits: [] }, null, 2)
  : JSON.stringify({ scenes: [{ scene_id: "SC001", ordinal: 1, viewpoint: "", location: "", entry_state: "", objective: "", opposition: "", turn: "", exit_state: "", emotion_target: "", reader_effect: "" }] }, null, 2);

function typedPlanBody(target: string, content: string, readerIntent: ReaderIntent): Record<string, unknown> {
  let parsed: unknown;
  try { parsed = JSON.parse(content); } catch { throw new Error("plan_structure_must_be_valid_json"); }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("plan_structure_must_be_an_object");
  if (target === "book") return { kind: "book", body: parsed };
  const required = ["reader_question", "visible_reward", "character_choice", "cost", "net_change", "next_chapter_pull"] as const;
  if (required.some((key) => !readerIntent[key]?.trim())) throw new Error("chapter_reader_intent_is_incomplete");
  return { kind: "chapter", body: { reader_contract: {
    reader_question: readerIntent.reader_question, visible_reward: readerIntent.visible_reward,
    character_choice: readerIntent.character_choice, cost: readerIntent.cost, net_change: readerIntent.net_change,
    next_pull: readerIntent.next_chapter_pull,
  }, scenes: (parsed as { scenes?: unknown }).scenes } };
}

export default function Plan() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];
  const [target, setTarget] = createSignal("book");
  const [title, setTitle] = createSignal("");
  const [content, setContent] = createSignal("");
  const [readerIntent, setReaderIntent] = createSignal<ReaderIntent>({});
  const [expectationRefs, setExpectationRefs] = createSignal("");
  const [saved, setSaved] = createSignal<PlanItem>();
  const [binding, setBinding] = createSignal<{ project_id: string; target_ref: string }>();
  const [dirty, setDirty] = createSignal(false);
  const [loading, setLoading] = createSignal(false);
  const [saving, setSaving] = createSignal(false);
  const [error, setError] = createSignal<string>();
  let generation = 0;
  let editVersion = 0;
  let disposed = false;
  let saveIntent: { request: string; idempotency_key: string } | undefined;
  const bound = () => binding()?.project_id === studio.projectId() && binding()?.target_ref === target();
  const targetTitle = () => target() === "book" ? (zh() ? "全书计划" : "Book plan")
    : studio.chapters().find((chapter) => `chapter:${chapter.chapter_id}` === target())?.title ?? target();
  const discardConfirmed = () => !dirty() || window.confirm(zh() ? "计划尚未保存。放弃本地修改？" : "This plan has unsaved edits. Discard them?");

  const load = async () => {
    const projectId = studio.projectId(); const targetRef = target(); const requestGeneration = ++generation;
    const current = () => !disposed && generation === requestGeneration && studio.projectId() === projectId && target() === targetRef;
    setBinding(undefined); setSaved(undefined); setTitle(""); setContent(""); setDirty(false); setError(undefined); setSaving(false);
    setReaderIntent({}); setExpectationRefs("");
    editVersion += 1; saveIntent = undefined;
    if (!projectId || !operations().includes("plan.inspect")) { setLoading(false); return; }
    setLoading(true);
    try {
      const result = await invokeBridge("plan.inspect", { project_id: projectId, target_ref: targetRef });
      if (!current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const plans = parsePlanInspection(result.data, projectId, targetRef).items;
      if (plans.filter((item) => item.status === "active").length > 1) throw new Error("plan_active_binding_ambiguous");
      const plan = plans.find((item) => item.status === "active") ?? [...plans].sort((left, right) => right.version - left.version)[0];
      setSaved(plan); setTitle(plan?.title ?? targetTitle()); setContent(plan?.content ?? planTemplate(targetRef));
      setReaderIntent({ ...plan?.reader_intent }); setExpectationRefs(plan?.expectation_refs?.join("\n") ?? "");
      setBinding({ project_id: projectId, target_ref: targetRef });
    } catch (cause) { if (current()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (current()) setLoading(false); }
  };

  const save = async () => {
    if (!bound() || saving() || !dirty() || !title().trim() || !operations().includes("plan.save")) return;
    let typedBody: Record<string, unknown>;
    try { typedBody = typedPlanBody(target(), content(), readerIntent()); } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); return; }
    const expected = { project_id: studio.projectId(), target_ref: target(), title: title().trim(), content: content(), expected_version: saved()?.version ?? 0,
      reader_intent: { ...readerIntent() }, expectation_refs: expectationRefs().split(/\s+/u).filter(Boolean) };
    const requestVersion = editVersion; const requestGeneration = generation;
    const current = () => !disposed && generation === requestGeneration && bound() && studio.projectId() === expected.project_id && target() === expected.target_ref;
    const serialized = JSON.stringify(expected);
    if (!saveIntent || saveIntent.request !== serialized) saveIntent = { request: serialized, idempotency_key: `studio-plan-${crypto.randomUUID()}` };
    setSaving(true); setError(undefined);
    try {
      const result = await invokeBridge("plan.save", { ...expected, typed_body: typedBody, idempotency_key: saveIntent.idempotency_key, user_authorized: true });
      if (!current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const plan = parsePlanSave(result.data, expected);
      setSaved(plan); saveIntent = undefined;
      // Advance the CAS version, but never overwrite text entered during POST.
      if (requestVersion === editVersion) { setTitle(plan.title); setDirty(false); }
    } catch (cause) { if (current()) setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { if (current()) setSaving(false); }
  };

  const chooseTarget = (value: string) => {
    if (value === target() || saving() || !discardConfirmed()) return;
    if (value !== "book" && !studio.chapters().some((chapter) => `chapter:${chapter.chapter_id}` === value)) return;
    setTarget(value);
    const chapter = studio.chapters().find((item) => `chapter:${item.chapter_id}` === value);
    if (chapter) studio.setChapterId(chapter.chapter_id);
  };
  createEffect(on([() => studio.projectId(), target, operations], () => { if (!bound() || !dirty()) void load(); }));
  const beforeUnload = (event: BeforeUnloadEvent) => { if (dirty()) { event.preventDefault(); event.returnValue = ""; } };
  onMount(() => window.addEventListener("beforeunload", beforeUnload));
  useBeforeLeave((event) => { if (!discardConfirmed()) event.preventDefault(); });
  onCleanup(() => { disposed = true; generation += 1; window.removeEventListener("beforeunload", beforeUnload); });
  const edit = () => { editVersion += 1; setDirty(true); };
  const intentFields: Array<{ key: keyof ReaderIntent; zh: string; en: string }> = [
    { key: "reader_question", zh: "读者当前关心的问题", en: "The reader's current question" },
    { key: "visible_reward", zh: "本章可感知的回报", en: "The chapter's visible reward" },
    { key: "character_choice", zh: "人物的主动选择", en: "The character's active choice" },
    { key: "cost", zh: "选择的代价", en: "The cost of that choice" },
    { key: "net_change", zh: "局面的实际变化", en: "What changes" },
    { key: "next_chapter_pull", zh: "牵引下一章的期待", en: "What draws the reader onward" },
  ];
  return (
    <section class="nf-page qf-plan-page">
      <PageIntro eyebrow="PLAN · READER INTENT" title={zh() ? "先想清楚，读者为什么期待下一章。" : "Know what makes the next chapter worth reading."} body={zh() ? "把人物欲望、阻力与读者回报写进计划。近期章节写具体，远期留出调整空间；计划不等于已经发生的故事事实。" : "Plan the character's desire, resistance and reader payoff. Detail the near term and leave room further ahead; a plan is not an established story fact."} />
      <Show when={studio.projectId()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "先打开小说项目" : "Open a novel first"}</strong><a href="/start">{zh() ? "开始" : "Start"}</a></div>}>
        <div class="qf-plan-workspace">
          <aside class="qf-plan-guide">
            <label class="nf-field-label"><span>{zh() ? "计划范围" : "Plan target"}</span><select class="wui-input" value={target()} disabled={saving()} onChange={(event) => { chooseTarget(event.currentTarget.value); event.currentTarget.value = target(); }}><option value="book">{zh() ? "全书" : "Whole novel"}</option><For each={studio.chapters()}>{(chapter) => <option value={`chapter:${chapter.chapter_id}`}>{chapter.title} · {chapter.chapter_id}</option>}</For></select></label>
            <h2>{target() === "book" ? (zh() ? "这本书的阅读乐趣" : "The pleasure this novel promises") : (zh() ? "这一章的阅读任务" : "This chapter's reader promise")}</h2>
            <Show when={target() === "book"} fallback={<ul class="qf-craft-prompts"><li>{zh() ? "读者眼下最关心什么？" : "What does the reader most want to know now?"}</li><li>{zh() ? "人物主动选择了什么，付出什么代价？" : "What does the character choose, and what does it cost?"}</li><li>{zh() ? "本章提供什么情绪或信息回报？" : "What emotional or informational payoff arrives here?"}</li><li>{zh() ? "局面发生什么实际变化？" : "What actually changes by the end?"}</li><li>{zh() ? "哪些期待得到推进，什么牵引下一章？" : "Which expectations advance, and what draws the reader onward?"}</li></ul>}>
              <ul class="qf-craft-prompts"><li>{zh() ? "目标读者与主要阅读乐趣" : "Intended readers and their central reading pleasure"}</li><li>{zh() ? "主角欲望、人物魅力与核心冲突" : "Protagonist desire, appeal and central conflict"}</li><li>{zh() ? "题材、平台、文风与篇幅意图" : "Genre, platform, voice and intended length"}</li><li>{zh() ? "近期具体推进，远期可调整方向" : "Concrete near-term movement, flexible long-term direction"}</li></ul>
            </Show>
            <p class="qf-inspector-boundary">{zh() ? "这些是写作提示，不是每章必须打卡的公式。平静的章节也可以提供重要回报。" : "These are prompts, not a required formula for every chapter. A quiet chapter can deliver an important payoff."}</p>
            <a class="wui-button wui-button--ghost" href="/story">{zh() ? "查看故事事实与期待" : "Open story facts and expectations"}</a>
          </aside>
          <article class="qf-editorial-sheet qf-plan-editor">
            <div class="qf-section-head"><h2>{targetTitle()}</h2><AuthorityLabel value="active_plan ≠ Canon" /></div>
            <CoreRequirementNotice operation="plan.inspect" /><CoreRequirementNotice operation="plan.save" compact />
            <label class="nf-field-label"><span>{zh() ? "计划标题" : "Plan title"}</span><input class="wui-input" value={title()} disabled={!bound() || loading()} onInput={(event) => { setTitle(event.currentTarget.value); edit(); }} /></label>
            <label class="nf-field-label"><span>{zh() ? "结构化计划（JSON）" : "Structured plan (JSON)"}</span><textarea class="wui-input qf-plan-text nf-mono" value={content()} disabled={!bound() || loading()} onInput={(event) => { setContent(event.currentTarget.value); edit(); }} placeholder={planTemplate(target())} /></label>
            <fieldset class="qf-reader-intent"><legend>{zh() ? "阅读意图 · 作者填写，可留空" : "Reader intent · optional author input"}</legend><div class="qf-intent-fields"><For each={intentFields}>{(field) => <label class="nf-field-label"><span>{zh() ? field.zh : field.en}</span><textarea class="wui-input" rows={2} value={readerIntent()[field.key] ?? ""} disabled={!bound() || loading()} onInput={(event) => { const text = event.currentTarget.value; setReaderIntent((current) => ({ ...current, [field.key]: text })); edit(); }} /></label>}</For></div></fieldset>
            <label class="nf-field-label"><span>{zh() ? "关联的期待记录 ID（每行一个）" : "Linked expectation IDs (one per line)"}</span><textarea class="wui-input nf-mono" rows={2} value={expectationRefs()} disabled={!bound() || loading()} onInput={(event) => { setExpectationRefs(event.currentTarget.value); edit(); }} /></label>
            <div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={!bound() || saving() || !dirty() || !title().trim() || !operations().includes("plan.save")} onClick={() => void save()}>{saving() ? (zh() ? "保存中…" : "Saving…") : (zh() ? "保存计划" : "Save plan")}</button><button class="wui-button wui-button--ghost" type="button" disabled={saving() || loading()} onClick={() => { if (discardConfirmed()) void load(); }}>{zh() ? "重新读取" : "Reload"}</button><span role="status" aria-live="polite">{loading() ? (zh() ? "读取中…" : "Loading…") : dirty() ? (zh() ? "有未保存修改" : "Unsaved edits") : saved() ? `${zh() ? "已保存版本" : "Saved version"} ${saved()!.version}` : (zh() ? "尚未保存计划" : "No saved plan yet")}</span></div>
            <Show when={error()}>{(message) => <p role="alert">{message()} {zh() ? "本地修改仍保留；不会覆盖更新的 Core 版本。" : "Local edits are retained; a newer Core version will not be overwritten."}</p>}</Show>
            <Show when={saved()?.horizon}>{(horizon) => <details><summary>{zh() ? "Core 记录的滚动规划边界" : "Rolling planning boundary recorded by Core"}</summary><pre class="qf-diff">{JSON.stringify(horizon(), null, 2)}</pre></details>}</Show>
          </article>
        </div>
      </Show>
    </section>
  );
}
