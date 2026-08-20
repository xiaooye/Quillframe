import { For, Show, createMemo, createSignal, onCleanup, onMount } from "solid-js";
import { Portal } from "solid-js/web";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import type {
  AcceptanceResult,
  CandidateRejectionResult,
  CandidateReviewProjection,
  CandidateVisibleProjection,
  CandidateRevisionRequestResult,
  CandidateRow,
  InspectorListProjection,
  SettlementPreflight,
  SettlementResult,
} from "../authoring/contracts";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";
import { createModalA11y } from "../modalA11y";

export default function Review() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const projectId = () => new URLSearchParams(location.search).get("project")?.trim() || studio.projectId();
  const operations = createMemo(() => studio.bridgeCapabilities()?.operations ?? []);
  const [rows, setRows] = createSignal<CandidateRow[]>([]);
  const [selectedId, setSelectedId] = createSignal("");
  const [review, setReview] = createSignal<CandidateReviewProjection>();
  const [visible, setVisible] = createSignal<CandidateVisibleProjection>();
  const [acceptance, setAcceptance] = createSignal<AcceptanceResult>();
  const [settlement, setSettlement] = createSignal<SettlementResult>();
  const [acceptDialogOpen, setAcceptDialogOpen] = createSignal(false);
  const [acceptExact, setAcceptExact] = createSignal(false);
  const [rejectExact, setRejectExact] = createSignal(false);
  const [revisionNote, setRevisionNote] = createSignal("");
  const [settleTarget, setSettleTarget] = createSignal("");
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  let acceptDialog: HTMLElement | undefined;
  let acceptCancelButton: HTMLButtonElement | undefined;
  let reviewRequestGeneration = 0;
  const selected = createMemo(() => rows().find((row) => row.candidate_id === selectedId()));
  const actionable = createMemo(() => review()?.candidate.effective_status === "review_draft");
  const exactFingerprint = createMemo(() => review()?.candidate.candidate_fingerprint || selected()?.content_fingerprint || "");

  const requestAcceptClose = () => {
    setAcceptDialogOpen(false);
    setAcceptExact(false);
  };
  const acceptModal = createModalA11y({
    getDialog: () => acceptDialog,
    getBackground: () => document.getElementById("app") ?? undefined,
    requestClose: requestAcceptClose,
    getInitialFocus: () => acceptCancelButton,
    getFallbackFocus: () => document.querySelector<HTMLElement>(".qf-review-actions button") ?? undefined,
  });
  onCleanup(() => acceptModal.dispose());
  const resetAcceptanceIntent = () => {
    if (acceptModal.isOpen()) acceptModal.close();
    else requestAcceptClose();
  };
  const openAcceptance = (trigger: HTMLElement) => {
    setAcceptExact(false);
    acceptModal.open(trigger);
    setAcceptDialogOpen(true);
  };

  const loadReview = async (candidateId: string) => {
    if (!projectId() || !candidateId || !operations().includes("candidate.review.get")) return;
    const requestGeneration = ++reviewRequestGeneration;
    setError(undefined);
    setReview(undefined);
    setVisible(undefined);
    try {
      const result = await invokeBridge<CandidateReviewProjection>("candidate.review.get", { project_id: projectId(), candidate_id: candidateId });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (requestGeneration !== reviewRequestGeneration || selectedId() !== candidateId) return;
      setReview(result.data);
      if (!settleTarget() && result.data.candidate.document_id) setSettleTarget(`chapter:${result.data.candidate.document_id}`);

      if (!operations().includes("candidate.visible.get")) {
        setError("candidate.visible.get is required before showing a Review Draft");
        return;
      }
      const released = await invokeBridge<CandidateVisibleProjection>("candidate.visible.get", { project_id: projectId(), candidate_id: candidateId });
      if (released.status !== "ok" || !released.data) throw new Error(operationError(released));
      if (requestGeneration !== reviewRequestGeneration || selectedId() !== candidateId) return;
      if (released.data.candidate_id !== result.data.candidate.candidate_id || released.data.candidate_fingerprint !== result.data.candidate.candidate_fingerprint) {
        throw new Error("candidate.visible.get returned a different candidate fingerprint");
      }
      setVisible(released.data);
    } catch (cause) {
      if (requestGeneration !== reviewRequestGeneration || selectedId() !== candidateId) return;
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const chooseCandidate = (candidateId: string) => {
    setSelectedId(candidateId);
    setAcceptance(undefined);
    setSettlement(undefined);
    setReview(undefined);
    setVisible(undefined);
    setRejectExact(false);
    setRevisionNote("");
    resetAcceptanceIntent();
    void loadReview(candidateId);
  };

  const load = async () => {
    if (!projectId() || !operations().includes("inspector.candidates.list")) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<InspectorListProjection<CandidateRow>>("inspector.candidates.list", { project_id: projectId(), limit: 100 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setRows(result.data.items);
      const next = selectedId() && result.data.items.some((item) => item.candidate_id === selectedId()) ? selectedId() : result.data.items[0]?.candidate_id ?? "";
      if (next) {
        setSelectedId(next);
        await loadReview(next);
      } else {
        setSelectedId("");
        setReview(undefined);
        setVisible(undefined);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  const accept = async () => {
    const detail = review();
    if (!detail || !acceptDialogOpen() || !acceptExact() || !exactFingerprint()) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<AcceptanceResult>("candidate.accept", {
        project_id: projectId(),
        candidate_id: detail.candidate.candidate_id,
        candidate_fingerprint: exactFingerprint(),
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "accept_exact_fingerprint", observed_gate: detail.candidate.user_visible_gate ?? null },
        idempotency_key: `studio-accept-${detail.candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setAcceptance(result.data);
      resetAcceptanceIntent();
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  const reject = async () => {
    const detail = review();
    if (!detail || !rejectExact() || !exactFingerprint()) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<CandidateRejectionResult>("candidate.reject", {
        project_id: projectId(),
        candidate_id: detail.candidate.candidate_id,
        candidate_fingerprint: exactFingerprint(),
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "reject_exact_fingerprint" },
        reason: "explicit Studio Review rejection",
        idempotency_key: `studio-reject-${detail.candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setRejectExact(false);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  const requestRevision = async () => {
    const detail = review();
    if (!detail || !revisionNote().trim() || !exactFingerprint()) return;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<CandidateRevisionRequestResult>("candidate.revision.request", {
        project_id: projectId(),
        candidate_id: detail.candidate.candidate_id,
        candidate_fingerprint: exactFingerprint(),
        revision_request: { instruction: revisionNote().trim(), source: "Studio Review" },
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "request_revision_exact_fingerprint" },
        idempotency_key: `studio-revision-request-${detail.candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setRevisionNote("");
      await loadReview(detail.candidate.candidate_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  const settle = async () => {
    const accepted = acceptance();
    const target = settleTarget().trim();
    if (!accepted || !target) return;
    setLoading(true); setError(undefined); setSettlement(undefined);
    try {
      const preflight = await invokeBridge<SettlementPreflight>("settlement.preflight", { project_id: projectId(), acceptance_id: accepted.acceptance_id, target_ref: target });
      if (preflight.status !== "ok" || !preflight.data || !preflight.data.settleable) throw new Error(operationError(preflight));
      const applied = await invokeBridge<SettlementResult>("settlement.apply", {
        project_id: projectId(),
        acceptance_id: accepted.acceptance_id,
        target_ref: target,
        expected_before_fingerprint: preflight.data.expected_before_fingerprint,
        idempotency_key: `studio-settle-${accepted.acceptance_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (applied.status !== "ok" || !applied.data) throw new Error(operationError(applied));
      setSettlement(applied.data);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  onMount(() => void load());

  return (
    <section class="nf-page qf-review-page">
      <PageIntro eyebrow="REVIEW" title={zh() ? "Review、Accept、Settlement 是三件不同的事。" : "Review, Accept and Settlement are three different things."} body={zh() ? "Review evidence 绑定 exact Candidate fingerprint。Reject、Request Revision、Accept 都是显式 Core command；Settlement 先做 authoritative preflight。" : "Review evidence is bound to the exact Candidate fingerprint. Reject, Request Revision and Accept are explicit Core commands; Settlement always performs authoritative preflight first."} />

      <div class="qf-review-layout">
        <aside class="qf-review-list" aria-label="Candidates">
          <div class="qf-section-head"><div><span class="nf-eyebrow">CANDIDATES</span><strong>{rows().length}</strong></div><button class="wui-button wui-button--outline" type="button" disabled={loading()} onClick={() => void load()}>{zh() ? "刷新" : "Refresh"}</button></div>
          <For each={rows()}>{(candidate) => <button type="button" class="qf-candidate-row" data-active={selectedId() === candidate.candidate_id ? "true" : undefined} onClick={() => chooseCandidate(candidate.candidate_id)}><strong>{candidate.candidate_id}</strong><span>{candidate.task_mode ?? "—"} · {candidate.status ?? "—"}</span><small>{candidate.user_visible_gate ? `gate ${candidate.user_visible_gate}` : "gate unknown"}</small></button>}</For>
          <Show when={!rows().length && !loading()}><p>{zh() ? "当前没有 Core Candidate。" : "No Core Candidate is currently available."}</p></Show>
        </aside>

        <article class="qf-review-main">
          <Show when={review()} fallback={<div class="qf-empty-workspace"><CoreRequirementNotice operation="candidate.review.get" /><strong>{zh() ? "选择一个有 fresh Review evidence 的 Candidate" : "Select a Candidate with fresh Review evidence"}</strong></div>}>
            {(detail) => <>
              <header class="qf-review-heading"><div><span class="nf-eyebrow">INCUMBENT ↔ CANDIDATE</span><h2>{detail().candidate.candidate_id}</h2></div><div class="qf-review-authority"><AuthorityLabel value={detail().candidate.effective_status} /><span class="qf-gate-label" data-gate={detail().candidate.user_visible_gate}>{`user-visible gate: ${detail().candidate.user_visible_gate ?? "—"}`}</span></div></header>
              <div class="qf-review-fingerprint"><span>Candidate fingerprint</span><code>{detail().candidate.candidate_fingerprint}</code></div>
              <p class="qf-success-note" role="status" aria-live="polite">
                <code>accepted={acceptance() ? "true" : "false"}</code>
                {" · "}
                <code>settled={settlement()?.status === "settled" ? "true" : "false"}</code>
              </p>

              <section class="qf-review-evidence" aria-labelledby="review-evidence-heading">
                <h3 id="review-evidence-heading">{zh() ? "Released Review Draft" : "Released Review Draft"}</h3>
                <Show when={visible()} fallback={<div class="qf-empty-workspace"><CoreRequirementNotice operation="candidate.visible.get" /><p>{zh() ? "正文仅在 exact production release 后通过 candidate.visible.get 显示。" : "Manuscript text is shown only through candidate.visible.get after an exact production release."}</p></div>}>
                  {(released) => <pre class="qf-review-draft" aria-label={zh() ? "Review Draft 正文" : "Review Draft manuscript"}><code>{released().content}</code></pre>}
                </Show>
                <div class="qf-review-evidence-grid">
                  <article><strong>Reader</strong><pre><code>{JSON.stringify(detail().evidence.reader, null, 2)}</code></pre></article>
                  <article><strong>Character</strong><pre><code>{JSON.stringify(detail().evidence.character, null, 2)}</code></pre></article>
                  <article><strong>Continuity</strong><pre><code>{JSON.stringify(detail().evidence.continuity, null, 2)}</code></pre></article>
                  <article><strong>Independent</strong><pre><code>{JSON.stringify(detail().evidence.independent, null, 2)}</code></pre></article>
                </div>
                <p><strong>private_reasoning_exposed:</strong> false</p>
              </section>

              <Show when={actionable()} fallback={<p class="qf-success-note" role="status">{detail().candidate.effective_status === "revision_requested" ? (zh() ? "已请求修改。Core 没有自动启动 REVISE；请从 AI Assistant 明确发起 REVISE。" : "Revision requested. Core did not auto-start REVISE; explicitly start REVISE from the AI Assistant.") : `${detail().candidate.effective_status}`}</p>}>
                <div class="qf-review-actions" aria-label={zh() ? "Review actions" : "Review actions"}>
                  <button class="wui-button wui-button--outline" type="button" disabled={!operations().includes("candidate.reject")} onClick={() => setRejectExact((value) => !value)}>Reject…</button>
                  <button class="wui-button wui-button--outline" type="button" disabled={!operations().includes("candidate.revision.request")} onClick={() => setRevisionNote((value) => value || " ")}>Request Revision…</button>
                  <button class="wui-button wui-button--solid" type="button" disabled={!operations().includes("candidate.accept") || detail().candidate.user_visible_gate !== "PASS"} onClick={(event) => openAcceptance(event.currentTarget)}>Accept…</button>
                </div>
                <Show when={rejectExact()}><section class="qf-authority-confirm"><h3>{zh() ? "确认 Reject" : "Confirm Reject"}</h3><p>{zh() ? "只终结这个 exact Review Draft；不改 Canon。" : "This terminates this exact Review Draft only; Canon is unchanged."}</p><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void reject()}>{zh() ? "Reject exact Candidate" : "Reject exact Candidate"}</button><button class="wui-button wui-button--ghost" type="button" onClick={() => setRejectExact(false)}>{zh() ? "取消" : "Cancel"}</button></div></section></Show>
                <Show when={revisionNote()}><section class="qf-authority-confirm"><h3>{zh() ? "Request Revision" : "Request Revision"}</h3><textarea class="wui-input" value={revisionNote()} onInput={(event) => setRevisionNote(event.currentTarget.value)} placeholder={zh() ? "说明需要修改什么" : "Describe what must change"} /><p>{zh() ? "Core 只记录 durable revision request，不会自动启动 REVISE。" : "Core records a durable revision request and does not auto-start REVISE."}</p><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !revisionNote().trim()} onClick={() => void requestRevision()}>{zh() ? "提交修改请求" : "Submit revision request"}</button><button class="wui-button wui-button--ghost" type="button" onClick={() => setRevisionNote("")}>{zh() ? "取消" : "Cancel"}</button></div></section></Show>
              </Show>

              <Show when={acceptDialogOpen()}><Portal><div class="qf-modal-overlay" role="presentation" onMouseDown={(event) => acceptModal.onOutsidePointer(event)}><section ref={(element) => { acceptDialog = element; }} class="qf-authority-dialog" role="alertdialog" aria-modal="true" aria-labelledby="accept-confirm-heading" aria-describedby="accept-confirm-description" tabIndex={-1} onKeyDown={(event) => acceptModal.onKeyDown(event)}><h3 id="accept-confirm-heading">{zh() ? "确认 Accept" : "Confirm Accept"}</h3><p id="accept-confirm-description">{zh() ? "Accept 只写 acceptance evidence，不执行 Settlement。" : "Accept writes acceptance evidence only; it does not perform Settlement."}</p><label><input type="checkbox" checked={acceptExact()} onChange={(event) => setAcceptExact(event.currentTarget.checked)} /> {zh() ? "我明确接受这个 exact fingerprint" : "I explicitly accept this exact fingerprint"}</label><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !acceptExact()} onClick={() => void accept()}>{zh() ? "Accept exact Candidate" : "Accept exact Candidate"}</button><button ref={(element) => { acceptCancelButton = element; }} class="wui-button wui-button--ghost" type="button" onClick={resetAcceptanceIntent}>{zh() ? "取消" : "Cancel"}</button></div></section></div></Portal></Show>

              <Show when={acceptance()}>{(receipt) => <section class="qf-accepted-state" aria-live="polite"><div><strong>Accepted ✓</strong><span>{settlement()?.status === "settled" ? "Settled" : "Not Settled"}</span></div><dl><dt>acceptance_id</dt><dd><code>{receipt().acceptance_id}</code></dd><dt>candidate</dt><dd><code>{receipt().candidate_fingerprint}</code></dd><dt>canon_mutated</dt><dd>{settlement()?.canon_mutated ? "true" : "false"}</dd></dl><label class="nf-field-label"><span>Settlement target_ref</span><input class="wui-input nf-mono" value={settleTarget()} onInput={(event) => setSettleTarget(event.currentTarget.value)} placeholder="chapter:CH001" /></label><button class="wui-button wui-button--solid" type="button" disabled={loading() || !settleTarget().trim() || !operations().includes("settlement.preflight") || !operations().includes("settlement.apply") || settlement()?.status === "settled"} onClick={() => void settle()}>{zh() ? "Preflight + Settle…" : "Preflight + Settle…"}</button><CoreRequirementNotice operation="settlement.preflight" compact /></section>}</Show>
            </>}
          </Show>
          <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Review</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
        </article>
      </div>
    </section>
  );
}
