import { For, Show, createMemo, createSignal, onMount } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type { AcceptanceResult, CandidateRow, InspectorListProjection } from "../authoring/contracts";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";

export default function Review() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const operations = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);
  const [rows, setRows] = createSignal<CandidateRow[]>([]);
  const [selectedId, setSelectedId] = createSignal("");
  const [acceptance, setAcceptance] = createSignal<AcceptanceResult>();
  const [confirmAccept, setConfirmAccept] = createSignal(false);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const selected = createMemo(() => rows().find((row) => row.candidate_id === selectedId()));

  const load = async () => {
    if (!projectId() || !operations().includes("inspector.candidates.list")) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<InspectorListProjection<CandidateRow>>("inspector.candidates.list", { project_id: projectId(), limit: 100 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setRows(result.data.items);
      if (!selectedId() && result.data.items[0]) setSelectedId(result.data.items[0].candidate_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  const accept = async () => {
    const candidate = selected();
    if (!candidate?.content_fingerprint || !confirmAccept()) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<AcceptanceResult>("candidate.accept", {
        project_id: projectId(),
        candidate_id: candidate.candidate_id,
        candidate_fingerprint: candidate.content_fingerprint,
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "accept", observed_gate: candidate.user_visible_gate ?? null },
        idempotency_key: `studio-accept-${candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setAcceptance(result.data);
      setConfirmAccept(false);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  onMount(() => void load());

  return (
    <section class="nf-page qf-review-page">
      <PageIntro eyebrow="REVIEW" title={zh() ? "Review、Accept、Settlement 是三件不同的事。" : "Review, Accept and Settlement are three different things."} body={zh() ? "Candidate 必须先通过 Core 的 user-visible gate 与独立审查。Accept 只建立 Accepted evidence；Canon 只有显式 Settlement transaction 才能改变。" : "A Candidate must first pass Core's user-visible gate and independent review. Accept creates Accepted evidence only; Canon changes only through an explicit Settlement transaction."} />

      <div class="qf-review-layout">
        <aside class="qf-review-list" aria-label={zh() ? "Candidates" : "Candidates"}>
          <div class="qf-section-head"><div><span class="nf-eyebrow">CANDIDATES</span><strong>{rows().length}</strong></div><button class="wui-button wui-button--outline" type="button" disabled={loading()} onClick={() => void load()}>{zh() ? "刷新" : "Refresh"}</button></div>
          <For each={rows()}>{(candidate) => <button type="button" class="qf-candidate-row" data-active={selectedId() === candidate.candidate_id ? "true" : undefined} onClick={() => { setSelectedId(candidate.candidate_id); setAcceptance(undefined); setConfirmAccept(false); }}><strong>{candidate.candidate_id}</strong><span>{candidate.task_mode ?? "—"} · {candidate.status ?? "—"}</span><small>{candidate.user_visible_gate ? `gate ${candidate.user_visible_gate}` : "gate unknown"}</small></button>}</For>
          <Show when={!rows().length && !loading()}><p>{zh() ? "当前没有 Core Candidate。" : "No Core Candidate is currently available."}</p></Show>
        </aside>

        <article class="qf-review-main">
          <Show when={selected()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "选择 Candidate" : "Select a Candidate"}</strong></div>}>
            {(candidate) => <>
              <header class="qf-review-heading"><div><span class="nf-eyebrow">INCUMBENT ↔ CANDIDATE</span><h2>{candidate().candidate_id}</h2></div><div class="qf-review-authority"><AuthorityLabel value={candidate().status ?? "unknown"} /><span class="qf-gate-label" data-gate={candidate().user_visible_gate}>{candidate().user_visible_gate ? `user-visible gate: ${candidate().user_visible_gate}` : "gate unavailable"}</span></div></header>
              <div class="qf-review-fingerprint"><span>Candidate fingerprint</span><code>{candidate().content_fingerprint ?? "—"}</code></div>

              <section class="qf-review-evidence" aria-labelledby="review-evidence-heading"><h3 id="review-evidence-heading">{zh() ? "Diff 与审查证据" : "Diff & review evidence"}</h3><p>{zh() ? "当前 inspector.candidates.list 只给 metadata，不能支持 Incumbent vs Candidate prose、Reader evidence、Character integrity、Continuity 或 Independent semantic review。" : "The current candidate list exposes metadata only; it cannot support Incumbent vs Candidate prose, Reader evidence, Character integrity, Continuity or Independent semantic review."}</p><CoreRequirementNotice operation="candidate.review.get" /></section>

              <div class="qf-review-actions" aria-label={zh() ? "Review actions" : "Review actions"}>
                <button class="wui-button wui-button--outline" type="button" disabled aria-disabled="true">{zh() ? "Reject" : "Reject"}</button>
                <button class="wui-button wui-button--outline" type="button" disabled aria-disabled="true">{zh() ? "Request Revision" : "Request Revision"}</button>
                <button class="wui-button wui-button--solid" type="button" disabled={!operations().includes("candidate.accept") || candidate().status !== "review_draft" || candidate().user_visible_gate !== "PASS" || !candidate().content_fingerprint} onClick={() => setConfirmAccept(true)}>{zh() ? "Accept…" : "Accept…"}</button>
              </div>
              <Show when={confirmAccept()}><section class="qf-authority-confirm" role="alertdialog" aria-modal="false" aria-labelledby="accept-confirm-heading"><h3 id="accept-confirm-heading">{zh() ? "确认 Accept" : "Confirm Accept"}</h3><p>{zh() ? "Accept 会写入 acceptance evidence，并把 Candidate 标为 accepted；它不会执行 Settlement。" : "Accept writes acceptance evidence and marks the Candidate accepted; it does not perform Settlement."}</p><label><input type="checkbox" checked={confirmAccept()} onChange={(event) => setConfirmAccept(event.currentTarget.checked)} /> {zh() ? "我明确接受这个 exact fingerprint" : "I explicitly accept this exact fingerprint"}</label><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void accept()}>{zh() ? "Accept exact Candidate" : "Accept exact Candidate"}</button><button class="wui-button wui-button--ghost" type="button" onClick={() => setConfirmAccept(false)}>{zh() ? "取消" : "Cancel"}</button></div></section></Show>

              <Show when={acceptance()}>{(receipt) => <section class="qf-accepted-state" aria-live="polite"><div><strong>Accepted ✓</strong><span>Not Settled</span></div><dl><dt>acceptance_id</dt><dd><code>{receipt().acceptance_id}</code></dd><dt>candidate</dt><dd><code>{receipt().candidate_fingerprint}</code></dd><dt>canon_mutated</dt><dd>false</dd></dl><button class="wui-button wui-button--solid" type="button" disabled aria-disabled="true">Settle…</button><CoreRequirementNotice operation="settlement.preflight" /></section>}</Show>
            </>}
          </Show>
          <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Review</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
        </article>
      </div>
      <aside class="qf-awaiting-core" role="status"><div><strong>awaiting_external</strong><code>candidate.reject / candidate.revision.request</code></div><p>{zh() ? "Reject 与 Request Revision 需要各自的 operation-specific Core command；当前按钮禁用，不会用 feedback.observe 冒充 Candidate state mutation。" : "Reject and Request Revision each require an operation-specific Core command; the buttons stay disabled rather than using feedback.observe to impersonate Candidate state mutation."}</p></aside>
    </section>
  );
}
