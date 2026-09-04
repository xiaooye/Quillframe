import { For, Show, createEffect, createMemo, createSignal, on, onCleanup } from "solid-js";
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
  ChapterListProjection,
  DocumentListProjection,
  InspectorListProjection,
  SettlementPreflight,
  SettlementResult,
} from "../authoring/contracts";
import {
  parseReviewAcceptanceResult,
  parseReviewSettlementPreflight,
  parseReviewSettlementResult,
  recoverReviewLifecycleReceipts,
  resolveReviewSettlementTarget,
  projectReaderEvidence,
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
  const [settlementPreflight, setSettlementPreflight] = createSignal<SettlementPreflight>();
  const [settlementConsent, setSettlementConsent] = createSignal(false);
  const [acceptDialogOpen, setAcceptDialogOpen] = createSignal(false);
  const [acceptExact, setAcceptExact] = createSignal(false);
  const [rejectExact, setRejectExact] = createSignal(false);
  const [revisionNote, setRevisionNote] = createSignal("");
  const [settleTarget, setSettleTarget] = createSignal<string>();
  const [targetError, setTargetError] = createSignal<string>();
  const [receiptError, setReceiptError] = createSignal<string>();
  const [receiptWindowFull, setReceiptWindowFull] = createSignal(false);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  let acceptDialog: HTMLElement | undefined;
  let acceptCancelButton: HTMLButtonElement | undefined;
  let reviewRequestGeneration = 0;
  let listRequestGeneration = 0;
  let listProjectId = "";
  let settlementIntent: { request: string; idempotency_key: string } | undefined;
  const actionable = createMemo(() => review()?.candidate.effective_status === "review_draft");
  const exactFingerprint = createMemo(() => review()?.candidate.candidate_fingerprint || "");
  const readerEvidence = createMemo(() => projectReaderEvidence(review()?.evidence.reader, exactFingerprint()));

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
  onCleanup(() => {
    reviewRequestGeneration += 1;
    listRequestGeneration += 1;
    acceptModal.dispose();
  });
  const resetAcceptanceIntent = () => {
    if (acceptModal.isOpen()) acceptModal.close();
    else requestAcceptClose();
  };
  const openAcceptance = (trigger: HTMLElement) => {
    if (loading() || !visible() || !actionable()) return;
    setAcceptExact(false);
    acceptModal.open(trigger);
    setAcceptDialogOpen(true);
  };

  const clearReview = () => {
    setReview(undefined);
    setVisible(undefined);
    setAcceptance(undefined);
    setSettlement(undefined);
    setSettlementPreflight(undefined); setSettlementConsent(false); settlementIntent = undefined;
    setSettleTarget(undefined);
    setTargetError(undefined);
    setReceiptError(undefined);
    setReceiptWindowFull(false);
    setRejectExact(false);
    setRevisionNote("");
    resetAcceptanceIntent();
  };
  const messageFor = (cause: unknown) => cause instanceof Error ? cause.message : String(cause);
  const currentAction = (detail: CandidateReviewProjection, generation: number) => generation === reviewRequestGeneration
    && projectId() === detail.project_id && selectedId() === detail.candidate.candidate_id
    && review()?.candidate.candidate_fingerprint === detail.candidate.candidate_fingerprint;

  const loadReview = async (candidateId: string) => {
    const requestedProject = projectId();
    const requestGeneration = ++reviewRequestGeneration;
    clearReview();
    if (!requestedProject || !candidateId || !operations().includes("candidate.review.get")) return;
    const changed = () => requestGeneration !== reviewRequestGeneration || projectId() !== requestedProject || selectedId() !== candidateId;
    setLoading(true);
    setError(undefined);
    try {
      const result = await invokeBridge<CandidateReviewProjection>("candidate.review.get", { project_id: requestedProject, candidate_id: candidateId });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (changed()) return;
      const detail = result.data;
      if (detail.schema !== "quillframe_candidate_review_projection_v1" || detail.project_id !== requestedProject
        || detail.candidate.candidate_id !== candidateId || detail.candidate_revision.content_fingerprint !== detail.candidate.candidate_fingerprint) {
        throw new Error("review_candidate_binding_invalid");
      }
      setReview(detail);
      const [released, documents, receipts, chapters] = await Promise.allSettled([
        operations().includes("candidate.visible.get")
          ? invokeBridge<CandidateVisibleProjection>("candidate.visible.get", { project_id: requestedProject, candidate_id: candidateId })
          : Promise.reject(new Error("candidate.visible.get is required before showing a Review Draft")),
        operations().includes("document.list")
          ? invokeBridge<DocumentListProjection>("document.list", { project_id: requestedProject, limit: 500 })
          : Promise.reject(new Error("document.list is required to verify the settlement target")),
        detail.candidate.persisted_status !== "accepted" ? Promise.resolve(null) : operations().includes("inspector.receipts.list")
          ? invokeBridge<InspectorListProjection>("inspector.receipts.list", { project_id: requestedProject, limit: 500 })
          : Promise.reject(new Error("inspector.receipts.list is required to restore lifecycle receipts")),
        operations().includes("chapter.list")
          ? invokeBridge<ChapterListProjection>("chapter.list", { project_id: requestedProject })
          : Promise.reject(new Error("chapter.list is required to verify the chapter association")),
      ] as const);
      if (changed()) return;
      try {
        if (released.status === "rejected") throw released.reason;
        if (released.value.status !== "ok" || !released.value.data) throw new Error(operationError(released.value));
        const body = released.value.data;
        if (body.schema !== "quillframe_user_visible_candidate_v1" || body.project_id !== requestedProject
          || body.candidate_id !== candidateId || body.candidate_fingerprint !== detail.candidate.candidate_fingerprint
          || body.document_id !== detail.candidate.document_id || body.revision_id !== detail.candidate_revision.revision_id
          || body.content_access !== "production_release_only" || typeof body.content !== "string"
          || !["quillframe_production_release_v1", "quillframe_production_release_v2"].includes(String(body.production_release?.schema))
          || body.production_release.ready_for_user_visible_review !== true
          || body.production_release.candidate_fingerprint !== detail.candidate.candidate_fingerprint
          || body.private_reasoning_exposed !== false || body.authority !== false || body.canon_authority !== false) {
          throw new Error("review_visible_candidate_binding_invalid");
        }
        setVisible(body);
      } catch (cause) { setError(messageFor(cause)); }
      let target: string | undefined;
      try {
        if (documents.status === "rejected") throw documents.reason;
        if (documents.value.status !== "ok" || !documents.value.data) throw new Error(operationError(documents.value));
        if (chapters.status === "rejected") throw chapters.reason;
        if (chapters.value.status !== "ok" || !chapters.value.data) throw new Error(operationError(chapters.value));
        target = resolveReviewSettlementTarget(documents.value.data, detail, chapters.value.data);
        setSettleTarget(target);
      } catch (cause) { setTargetError(messageFor(cause)); }
      try {
        if (receipts.status === "rejected") throw receipts.reason;
        if (!receipts.value) return;
        if (receipts.value.status !== "ok" || !receipts.value.data) throw new Error(operationError(receipts.value));
        const restored = recoverReviewLifecycleReceipts(receipts.value.data, detail, target);
        setAcceptance(restored.acceptance);
        setSettlement(restored.settlement);
        setReceiptWindowFull(restored.receipt_window_full);
        if (detail.candidate.persisted_status === "accepted" && !restored.acceptance) setReceiptError("review_acceptance_receipt_unavailable");
      } catch (cause) { setReceiptError(messageFor(cause)); }
    } catch (cause) {
      if (changed()) return;
      setError(messageFor(cause));
    } finally {
      if (!changed()) setLoading(false);
    }
  };

  const chooseCandidate = (candidateId: string) => {
    if (loading()) return;
    setSelectedId(candidateId);
    void loadReview(candidateId);
  };

  const load = async () => {
    const requestedProject = projectId();
    const requestGeneration = ++listRequestGeneration;
    const retainedCandidate = listProjectId === requestedProject ? selectedId() : "";
    if (listProjectId !== requestedProject) {
      setRows([]);
      setSelectedId("");
      listProjectId = requestedProject;
    }
    reviewRequestGeneration += 1;
    clearReview();
    const changed = () => requestGeneration !== listRequestGeneration || projectId() !== requestedProject;
    if (!requestedProject || !operations().includes("inspector.candidates.list")) {
      setLoading(false);
      return;
    }
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<InspectorListProjection<CandidateRow>>("inspector.candidates.list", { project_id: requestedProject, limit: 100 });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (changed()) return;
      if (result.data.schema !== "quillframe_inspector_projection_v1" || result.data.kind !== "candidates"
        || result.data.project_id !== requestedProject || result.data.authority !== false || !Array.isArray(result.data.items)) {
        throw new Error("review_candidates_projection_invalid");
      }
      setRows(result.data.items);
      const next = result.data.items.some((item) => item.candidate_id === retainedCandidate) ? retainedCandidate : result.data.items[0]?.candidate_id ?? "";
      if (next) {
        setSelectedId(next);
        await loadReview(next);
      } else {
        setSelectedId("");
      }
    } catch (cause) { if (!changed()) setError(messageFor(cause)); }
    finally { if (!changed()) setLoading(false); }
  };

  const accept = async () => {
    const detail = review();
    if (!detail || loading() || !visible() || !actionable() || !acceptDialogOpen() || !acceptExact() || !exactFingerprint()
      || detail.project_id !== projectId() || !operations().includes("candidate.accept")) return;
    const generation = reviewRequestGeneration;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<AcceptanceResult>("candidate.accept", {
        project_id: detail.project_id,
        candidate_id: detail.candidate.candidate_id,
        candidate_fingerprint: detail.candidate.candidate_fingerprint,
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "accept_exact_fingerprint", observed_gate: detail.candidate.user_visible_gate ?? null },
        idempotency_key: `studio-accept-${detail.candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (!currentAction(detail, generation)) return;
      const accepted = parseReviewAcceptanceResult(result.data, detail);
      setAcceptance(accepted);
      setReview({
        ...detail,
        candidate: {
          ...detail.candidate,
          status: "accepted",
          persisted_status: "accepted",
          effective_status: "accepted",
        },
      });
      setRows((current) => current.map((row) => row.candidate_id === detail.candidate.candidate_id
        ? { ...row, status: "accepted" }
        : row));
      resetAcceptanceIntent();
    } catch (cause) { if (currentAction(detail, generation)) setError(messageFor(cause)); }
    finally { if (currentAction(detail, generation)) setLoading(false); }
  };

  const reject = async () => {
    const detail = review();
    if (!detail || loading() || !visible() || !actionable() || !rejectExact() || !exactFingerprint()
      || detail.project_id !== projectId() || !operations().includes("candidate.reject")) return;
    const generation = reviewRequestGeneration;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<CandidateRejectionResult>("candidate.reject", {
        project_id: detail.project_id,
        candidate_id: detail.candidate.candidate_id,
        candidate_fingerprint: detail.candidate.candidate_fingerprint,
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "reject_exact_fingerprint" },
        reason: "explicit Studio Review rejection",
        idempotency_key: `studio-reject-${detail.candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (!currentAction(detail, generation)) return;
      setRejectExact(false);
      await load();
    } catch (cause) { if (currentAction(detail, generation)) setError(messageFor(cause)); }
    finally { if (currentAction(detail, generation)) setLoading(false); }
  };

  const requestRevision = async () => {
    const detail = review();
    if (!detail || loading() || !visible() || !actionable() || !revisionNote().trim() || !exactFingerprint()
      || detail.project_id !== projectId() || !operations().includes("candidate.revision.request")) return;
    const generation = reviewRequestGeneration;
    setLoading(true); setError(undefined);
    try {
      const result = await invokeBridge<CandidateRevisionRequestResult>("candidate.revision.request", {
        project_id: detail.project_id,
        candidate_id: detail.candidate.candidate_id,
        candidate_fingerprint: detail.candidate.candidate_fingerprint,
        revision_request: { instruction: revisionNote().trim(), source: "Studio Review" },
        authorized_by: "studio_user",
        authorization: { source: "Studio Review", explicit_action: "request_revision_exact_fingerprint" },
        idempotency_key: `studio-revision-request-${detail.candidate.candidate_id}-${crypto.randomUUID()}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      if (!currentAction(detail, generation)) return;
      setRevisionNote("");
      await loadReview(detail.candidate.candidate_id);
    } catch (cause) { if (currentAction(detail, generation)) setError(messageFor(cause)); }
    finally { if (currentAction(detail, generation)) setLoading(false); }
  };

  const prepareSettlement = async () => {
    const detail = review();
    const accepted = acceptance();
    const target = settleTarget();
    if (!detail || !accepted || !target || loading() || !visible() || detail.project_id !== projectId()
      || settlement()?.status === "settled" || !operations().includes("settlement.preflight")) return;
    const generation = reviewRequestGeneration;
    const current = () => currentAction(detail, generation) && acceptance()?.acceptance_id === accepted.acceptance_id && settleTarget() === target;
    setLoading(true); setError(undefined); setSettlement(undefined); setSettlementPreflight(undefined); setSettlementConsent(false);
    try {
      const preflight = await invokeBridge<SettlementPreflight>("settlement.preflight", { project_id: detail.project_id, acceptance_id: accepted.acceptance_id, target_ref: target });
      if (preflight.status !== "ok" || !preflight.data) throw new Error(operationError(preflight));
      const verifiedPreflight = parseReviewSettlementPreflight(preflight.data, detail, accepted, target);
      if (!current()) return;
      setSettlementPreflight(verifiedPreflight);
    } catch (cause) { if (current()) setError(messageFor(cause)); }
    finally { if (current()) setLoading(false); }
  };

  const settle = async () => {
    const detail = review(); const accepted = acceptance(); const target = settleTarget(); const preflight = settlementPreflight();
    if (!detail || !accepted || !target || !preflight || !settlementConsent() || loading() || !visible() || detail.project_id !== projectId()
      || settlement()?.status === "settled" || !operations().includes("settlement.apply")) return;
    const generation = reviewRequestGeneration;
    const current = () => currentAction(detail, generation) && acceptance()?.acceptance_id === accepted.acceptance_id && settleTarget() === target && settlementPreflight() === preflight;
    setLoading(true); setError(undefined);
    try {
      const verifiedPreflight = parseReviewSettlementPreflight(preflight, detail, accepted, target);
      const requestKey = JSON.stringify({ acceptance_id: accepted.acceptance_id, target, before: verifiedPreflight.expected_before_fingerprint, preflight: verifiedPreflight.preflight_fingerprint });
      if (!settlementIntent || settlementIntent.request !== requestKey) settlementIntent = { request: requestKey, idempotency_key: `studio-settle-${accepted.acceptance_id}-${crypto.randomUUID()}` };
      const applied = await invokeBridge<SettlementResult>("settlement.apply", {
        project_id: detail.project_id,
        acceptance_id: accepted.acceptance_id,
        target_ref: target,
        expected_before_fingerprint: verifiedPreflight.expected_before_fingerprint,
        expected_preflight_fingerprint: verifiedPreflight.preflight_fingerprint,
        idempotency_key: settlementIntent.idempotency_key,
        user_authorized: true,
      });
      if (applied.status !== "ok" || !applied.data) throw new Error(operationError(applied));
      if (!current()) return;
      setSettlement(parseReviewSettlementResult(applied.data, detail, accepted, target, verifiedPreflight.expected_before_fingerprint));
      setSettlementConsent(false);
      await studio.refreshChapters();
    } catch (cause) { if (current()) setError(messageFor(cause)); }
    finally { if (current()) setLoading(false); }
  };

  createEffect(on([projectId, operations], () => void load()));

  return (
    <section class="nf-page qf-review-page">
      <PageIntro eyebrow="REVIEW · READER EXPERIENCE" title={zh() ? "什么值得保留，什么让人想放下这章？" : "What is worth preserving, and where might a reader stop?"} body={zh() ? "先看具体阅读反馈与文本证据，再决定是否接受。审查、作者接受、事实结算是三个独立动作；每项证据必须对应眼前这个版本。" : "Read specific reactions and textual evidence before deciding whether to accept. Review, author acceptance and settlement are separate actions, each bound to the exact version in front of you."} />

      <div class="qf-review-layout">
        <aside class="qf-review-list" aria-label="Candidates">
          <div class="qf-section-head"><div><span class="nf-eyebrow">CANDIDATES</span><strong>{rows().length}</strong></div><button class="wui-button wui-button--outline" type="button" disabled={loading()} onClick={() => void load()}>{zh() ? "刷新" : "Refresh"}</button></div>
          <For each={rows()}>{(candidate) => <button type="button" class="qf-candidate-row" disabled={loading()} data-active={selectedId() === candidate.candidate_id ? "true" : undefined} onClick={() => chooseCandidate(candidate.candidate_id)}><strong>{candidate.candidate_id}</strong><span>{candidate.task_mode ?? "—"} · {candidate.status ?? "—"}</span><small>{candidate.user_visible_gate ? `gate ${candidate.user_visible_gate}` : "gate unknown"}</small></button>}</For>
          <Show when={!rows().length && !loading()}><p>{zh() ? "当前没有 Core Candidate。" : "No Core Candidate is currently available."}</p></Show>
        </aside>

        <article class="qf-review-main">
          <Show when={review()} fallback={<div class="qf-empty-workspace"><CoreRequirementNotice operation="candidate.review.get" /><strong>{zh() ? "选择一个有 fresh Review evidence 的 Candidate" : "Select a Candidate with fresh Review evidence"}</strong></div>}>
            {(detail) => <>
              <header class="qf-review-heading"><div><span class="nf-eyebrow">INCUMBENT ↔ CANDIDATE</span><h2>{detail().candidate.candidate_id}</h2></div><div class="qf-review-authority"><AuthorityLabel value={detail().candidate.effective_status} /><span class="qf-gate-label" data-gate={detail().candidate.user_visible_gate}>{`user-visible gate: ${detail().candidate.user_visible_gate ?? "—"}`}</span></div></header>
              <div class="qf-review-fingerprint"><span>Candidate fingerprint</span><code>{detail().candidate.candidate_fingerprint}</code></div>
              <p class="qf-success-note" role="status" aria-live="polite">
                <code>accepted={acceptance() ? "true" : detail().candidate.persisted_status === "accepted" ? "unknown" : "false"}</code>
                {" · "}
                <code>settled={settlement()?.status === "settled" ? "true" : "unknown"}</code>
              </p>
              <Show when={receiptError() && detail().candidate.persisted_status === "accepted"}>
                <p class="wui-alert" role="status">{zh() ? "Core 标记此候选已接受，但无法恢复精确的接受收据，暂不能结算。请刷新或检查 Core 收据。" : "Core marks this candidate Accepted, but its exact acceptance receipt could not be restored. Settlement is unavailable; refresh or inspect the Core receipts."} <code>{receiptError()}</code></p>
              </Show>
              <Show when={receiptWindowFull()}>
                <p role="status">{zh() ? "收据查询已达到 500 条上限。未返回的记录仍为未知，不能据此认定没有接受或结算。" : "The receipt query reached its 500-record limit. Missing records remain unknown and do not prove that acceptance or settlement never occurred."}</p>
              </Show>

              <section class="qf-review-evidence" aria-labelledby="review-evidence-heading">
                <h3 id="review-evidence-heading">{zh() ? "Released Review Draft" : "Released Review Draft"}</h3>
                <Show when={visible()} fallback={<div class="qf-empty-workspace"><CoreRequirementNotice operation="candidate.visible.get" /><p>{zh() ? "正文仅在 exact production release 后通过 candidate.visible.get 显示。" : "Manuscript text is shown only through candidate.visible.get after an exact production release."}</p></div>}>
                  {(released) => <pre class="qf-review-draft" aria-label={zh() ? "Review Draft 正文" : "Review Draft manuscript"}><code>{released().content}</code></pre>}
                </Show>
                <section class="qf-reader-evidence" aria-labelledby="reader-reaction-heading">
                  <h3 id="reader-reaction-heading">{zh() ? "读者视角的具体反馈" : "Specific reader reactions"}</h3>
                  <p class="qf-inspector-boundary">{zh() ? "模型盲读意见，不代表真实读者留存数据或平台成绩。" : "Model reader feedback, not measured reader retention or platform performance."}</p>
                  <Show when={readerEvidence().bound} fallback={<p>{zh() ? "尚无与当前正文指纹对应的读者反馈。" : "No reader feedback is bound to this exact manuscript fingerprint."}</p>}>
                    <Show when={readerEvidence().strongest_positive}>{(text) => <article><h4>{zh() ? "最值得保留的阅读乐趣" : "The strongest reading pleasure to preserve"}</h4><p>{text()}</p></article>}</Show>
                    <Show when={readerEvidence().strongest_problem}>{(text) => <article><h4>{zh() ? "最需要解决的阅读阻力" : "The main obstacle to continued reading"}</h4><p>{text()}</p></article>}</Show>
                    <Show when={readerEvidence().summary}>{(text) => <pre>{text()}</pre>}</Show>
                    <Show when={readerEvidence().evidence_refs.length}><h4>{zh() ? "文本证据与引用" : "Textual evidence and references"}</h4><ul><For each={readerEvidence().evidence_refs}>{(ref) => <li>{ref}</li>}</For></ul></Show>
                  </Show>
                  <a class="wui-button wui-button--ghost" href={`/learning?project=${encodeURIComponent(projectId())}&candidate=${encodeURIComponent(detail().candidate.candidate_id)}`}>{zh() ? "记录作者或读者反馈" : "Record author or reader feedback"}</a>
                </section>
                <details><summary>{zh() ? "查看审查来源与精确回执" : "Inspect review provenance and exact receipts"}</summary><div class="qf-review-evidence-grid">
                  <article><strong>Reader</strong><pre><code>{JSON.stringify(detail().evidence.reader, null, 2)}</code></pre></article>
                  <article><strong>Character</strong><pre><code>{JSON.stringify(detail().evidence.character, null, 2)}</code></pre></article>
                  <article><strong>Surface Rules</strong><pre><code>{JSON.stringify(detail().evidence.surface_rules, null, 2)}</code></pre></article>
                  <article><strong>Continuity</strong><pre><code>{JSON.stringify(detail().evidence.continuity, null, 2)}</code></pre></article>
                  <article><strong>Independent</strong><pre><code>{JSON.stringify(detail().evidence.independent, null, 2)}</code></pre></article>
                </div></details>
                <p><strong>private_reasoning_exposed:</strong> false</p>
              </section>

              <Show when={actionable()} fallback={<p class="qf-success-note" role="status">{detail().candidate.effective_status === "revision_requested" ? (zh() ? "已请求修改。Core 没有自动启动 REVISE；请从 AI Assistant 明确发起 REVISE。" : "Revision requested. Core did not auto-start REVISE; explicitly start REVISE from the AI Assistant.") : `${detail().candidate.effective_status}`}</p>}>
                <div class="qf-review-actions" aria-label={zh() ? "Review actions" : "Review actions"}>
                  <button class="wui-button wui-button--outline" type="button" disabled={loading() || !visible() || !operations().includes("candidate.reject")} onClick={() => setRejectExact((value) => !value)}>Reject…</button>
                  <button class="wui-button wui-button--outline" type="button" disabled={loading() || !visible() || !operations().includes("candidate.revision.request")} onClick={() => setRevisionNote((value) => value || " ")}>Request Revision…</button>
                  <button class="wui-button wui-button--solid" type="button" disabled={loading() || !visible() || !operations().includes("candidate.accept") || detail().candidate.user_visible_gate !== "PASS"} onClick={(event) => openAcceptance(event.currentTarget)}>Accept…</button>
                </div>
                <Show when={rejectExact()}><section class="qf-authority-confirm"><h3>{zh() ? "确认 Reject" : "Confirm Reject"}</h3><p>{zh() ? "只终结这个 exact Review Draft；不改 Canon。" : "This terminates this exact Review Draft only; Canon is unchanged."}</p><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading()} onClick={() => void reject()}>{zh() ? "Reject exact Candidate" : "Reject exact Candidate"}</button><button class="wui-button wui-button--ghost" type="button" onClick={() => setRejectExact(false)}>{zh() ? "取消" : "Cancel"}</button></div></section></Show>
                <Show when={revisionNote()}><section class="qf-authority-confirm"><h3>{zh() ? "Request Revision" : "Request Revision"}</h3><textarea class="wui-input" value={revisionNote()} onInput={(event) => setRevisionNote(event.currentTarget.value)} placeholder={zh() ? "说明需要修改什么" : "Describe what must change"} /><p>{zh() ? "Core 只记录 durable revision request，不会自动启动 REVISE。" : "Core records a durable revision request and does not auto-start REVISE."}</p><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !revisionNote().trim()} onClick={() => void requestRevision()}>{zh() ? "提交修改请求" : "Submit revision request"}</button><button class="wui-button wui-button--ghost" type="button" onClick={() => setRevisionNote("")}>{zh() ? "取消" : "Cancel"}</button></div></section></Show>
              </Show>

              <Show when={acceptDialogOpen()}><Portal><div class="qf-modal-overlay" role="presentation" onMouseDown={(event) => acceptModal.onOutsidePointer(event)}><section ref={(element) => { acceptDialog = element; }} class="qf-authority-dialog" role="alertdialog" aria-modal="true" aria-labelledby="accept-confirm-heading" aria-describedby="accept-confirm-description" tabIndex={-1} onKeyDown={(event) => acceptModal.onKeyDown(event)}><h3 id="accept-confirm-heading">{zh() ? "确认 Accept" : "Confirm Accept"}</h3><p id="accept-confirm-description">{zh() ? "Accept 只写 acceptance evidence，不执行 Settlement。" : "Accept writes acceptance evidence only; it does not perform Settlement."}</p><label><input type="checkbox" checked={acceptExact()} onChange={(event) => setAcceptExact(event.currentTarget.checked)} /> {zh() ? "我明确接受这个 exact fingerprint" : "I explicitly accept this exact fingerprint"}</label><div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={loading() || !acceptExact()} onClick={() => void accept()}>{zh() ? "Accept exact Candidate" : "Accept exact Candidate"}</button><button ref={(element) => { acceptCancelButton = element; }} class="wui-button wui-button--ghost" type="button" onClick={resetAcceptanceIntent}>{zh() ? "取消" : "Cancel"}</button></div></section></div></Portal></Show>

              <Show when={acceptance()}>{(receipt) => <section class="qf-accepted-state" aria-live="polite">
                <div><strong>Accepted ✓</strong><span>{settlement()?.status === "settled" ? (zh() ? "已结算" : "Settled") : (zh() ? "结算尚未确认" : "Settlement unconfirmed")}</span></div>
                <dl><dt>acceptance_id</dt><dd><code>{receipt().acceptance_id}</code></dd><dt>candidate</dt><dd><code>{receipt().candidate_fingerprint}</code></dd><dt>canon_mutated</dt><dd>{settlement() ? String(settlement()!.canon_mutated) : "unknown"}</dd></dl>
                <label class="nf-field-label"><span>Settlement target_ref</span><input class="wui-input nf-mono" value={settleTarget() ?? ""} readOnly aria-describedby="review-settlement-target-note" placeholder={zh() ? "等待 Core 章节关联" : "Core chapter association required"} /></label>
                <p id="review-settlement-target-note">{settleTarget()
                  ? (zh() ? "目标来自 Core 中此稿件的章节关联，不能手填覆盖。" : "The target comes from this manuscript's Core chapter association and cannot be overridden here.")
                  : (zh() ? "Core 未提供此稿件的精确章节关联。结算已阻断，不能用文档编号推测目标。" : "Core has not supplied an exact chapter association for this manuscript. Settlement is blocked; the document ID cannot substitute for that association.")}</p>
                <Show when={targetError()}><p role="status"><code>{targetError()}</code></p></Show>
                <Show when={settlement()?.status === "settlement_incomplete"}><p role="status">{zh() ? "本次结算没有写入 Canon；前置状态已改变。刷新后可重新检查，不会自动重试。" : "This settlement attempt did not write Canon because the before-state changed. Refresh to check again; no retry runs automatically."}</p></Show>
                <button class="wui-button wui-button--outline" type="button" disabled={loading() || !visible() || !settleTarget() || !operations().includes("settlement.preflight") || settlement()?.status === "settled"} onClick={() => void prepareSettlement()}>{zh() ? "检查本次拟结算内容" : "Inspect proposed settlement"}</button>
                <CoreRequirementNotice operation="settlement.preflight" compact />
                <Show when={settlement()?.status === "settled" ? undefined : settlementPreflight()}>{(pending) => <section class="qf-story-section" aria-label={pending().target_ref}><h3>{zh() ? "本次拟写入的状态与读者记忆" : "State and reader memory proposed for this settlement"}</h3><p>{zh() ? "请核对以下内容。正文接受不会自动授权这些状态变更；提交将绑定这次预检的完整指纹。" : "Review the proposal below. Manuscript acceptance alone does not authorize these state changes; confirmation binds the complete preflight fingerprint."}</p><Show when={settlementPreflight()?.narrative_proposal} fallback={<p>{zh() ? "没有附加故事状态提案。" : "No additional narrative state proposal."}</p>}><details open><summary>{zh() ? "故事状态提案与文本证据" : "Narrative changes and textual evidence"}</summary><pre>{JSON.stringify(settlementPreflight()!.narrative_proposal, null, 2)}</pre></details></Show><Show when={settlementPreflight()?.reader_observations?.length}><details open><summary>{zh() ? "读者期待的推进与兑现观察" : "Reader expectation progress and payoff observations"}</summary><pre>{JSON.stringify(settlementPreflight()!.reader_observations, null, 2)}</pre></details></Show><p><code>{settlementPreflight()?.preflight_fingerprint ?? settlementPreflight()?.expected_before_fingerprint}</code></p><label class="qf-inline-actions"><input type="checkbox" checked={settlementConsent()} disabled={loading()} onChange={(event) => setSettlementConsent(event.currentTarget.checked)} />{zh() ? "我确认结算以上版本、状态提案与读者观察" : "I authorize settlement of this version, state proposal and reader observations"}</label><button class="wui-button wui-button--solid" type="button" disabled={loading() || !settlementConsent() || !operations().includes("settlement.apply")} onClick={() => void settle()}>{zh() ? "确认并结算" : "Confirm and settle"}</button></section>}</Show>
                <Show when={settlement()?.status === "settled"}><a class="wui-button wui-button--solid" href={`/publication?project=${encodeURIComponent(projectId())}&acceptance=${encodeURIComponent(receipt().acceptance_id)}`}>{zh() ? "导出已结算章节" : "Export settled chapter"}</a></Show>
              </section>}</Show>
            </>}
          </Show>
          <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">Review</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
        </article>
      </div>
    </section>
  );
}
