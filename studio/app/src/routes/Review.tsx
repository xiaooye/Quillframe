import { For, Show, createMemo, createSignal, onMount } from "solid-js";
import { A, useSearchParams } from "@solidjs/router";
import { invokeBridge, operationError } from "../bridge";
import { useI18n } from "../i18n";

interface CandidateListItem {
  candidate_id: string; document_id?: string | null; revision_id?: string | null; run_id?: string | null;
  task_mode: string; candidate_kind: string; status: string; content_fingerprint: string; user_visible_gate: string;
  acceptance_id?: string | null; settlement_status?: string | null;
}
interface CandidateList { items: CandidateListItem[]; }
interface CandidateProjection {
  candidate: CandidateListItem;
  revision: null | { revision_id: string; document_id: string; parent_revision_id?: string | null; content: string; content_fingerprint: string; authority_class: string };
  reviews: Array<{ review_id: string; evidence_kind: string; result: unknown; independent: number; stale: number; reviewer_fingerprint?: string | null }>;
  acceptance: null | { acceptance_id: string; candidate_id: string; candidate_fingerprint: string; authorized_by: string };
  settlements: Array<{ settlement_id: string; target_ref: string; before_fingerprint: string; after_fingerprint?: string | null; status: string; receipt_json: string }>;
}
interface RevisionCompare { diff: string[]; }
interface AcceptResult { acceptance_id: string; accepted: boolean; settled: boolean; canon_mutated: boolean; }
interface SettlementPreflight { expected_before_fingerprint: string; target_ref: string; ready: boolean; current_state: unknown; }
interface SettlementResult { settlement_id?: string; status?: string; [key: string]: unknown; }

export default function Review() {
  const { locale } = useI18n();
  const zh = createMemo(() => locale() === "zh-CN");
  const [params] = useSearchParams();
  const projectId = createMemo(() => String(params.project || localStorage.getItem("quillframe.ui.lastProjectId") || ""));
  const [items, setItems] = createSignal<CandidateListItem[]>([]);
  const [selected, setSelected] = createSignal<CandidateProjection>();
  const [diff, setDiff] = createSignal<string[]>([]);
  const [preflight, setPreflight] = createSignal<SettlementPreflight>();
  const [busy, setBusy] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const [message, setMessage] = createSignal<string>();
  const t = (en: string, cn: string) => zh() ? cn : en;

  const load = async (preferred?: string) => {
    if (!projectId()) return;
    const result = await invokeBridge<CandidateList>("candidate.list", { project_id: projectId(), limit: 100 });
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    setItems(result.data.items);
    const candidateId = preferred || selected()?.candidate.candidate_id || result.data.items[0]?.candidate_id;
    if (candidateId) await selectCandidate(candidateId);
  };

  const selectCandidate = async (candidateId: string) => {
    setError(undefined); setPreflight(undefined); setDiff([]);
    const result = await invokeBridge<CandidateProjection>("candidate.get", { project_id: projectId(), candidate_id: candidateId });
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    setSelected(result.data);
    const revision = result.data.revision;
    if (revision?.parent_revision_id) {
      const compared = await invokeBridge<RevisionCompare>("document.revision.compare", {
        project_id: projectId(), left_revision_id: revision.parent_revision_id, right_revision_id: revision.revision_id,
      });
      if (compared.status === "ok" && compared.data) setDiff(compared.data.diff);
    }
  };

  const accept = async () => {
    const candidate = selected()?.candidate;
    if (!candidate) return;
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge<AcceptResult>("candidate.accept", {
        project_id: projectId(), candidate_id: candidate.candidate_id, candidate_fingerprint: candidate.content_fingerprint,
        authorized_by: "studio_user", authorization: { interaction: "explicit_accept_click", surface: "review" },
        idempotency_key: `studio-accept-${candidate.candidate_id}`, user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setMessage(t("Accepted ✓ · Not Settled", "Accepted ✓ · 尚未 Settled"));
      await load(candidate.candidate_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  };

  const prepareSettlement = async () => {
    const projection = selected();
    const acceptanceId = projection?.acceptance?.acceptance_id;
    const documentId = projection?.candidate.document_id;
    if (!acceptanceId || !documentId) return;
    setBusy(true); setError(undefined);
    try {
      const targetRef = `manuscript:${documentId}`;
      const result = await invokeBridge<SettlementPreflight>("settlement.preflight", { project_id: projectId(), acceptance_id: acceptanceId, target_ref: targetRef });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setPreflight(result.data);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  };

  const settle = async () => {
    const projection = selected();
    const acceptanceId = projection?.acceptance?.acceptance_id;
    const prepared = preflight();
    if (!acceptanceId || !prepared?.ready) return;
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      const result = await invokeBridge<SettlementResult>("settlement.apply", {
        project_id: projectId(), acceptance_id: acceptanceId, target_ref: prepared.target_ref,
        expected_before_fingerprint: prepared.expected_before_fingerprint,
        idempotency_key: `studio-settle-${acceptanceId}-${prepared.expected_before_fingerprint}`,
        user_authorized: true,
      });
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setMessage(String(result.data.status || "settled"));
      setPreflight(undefined);
      await load(projection.candidate.candidate_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setBusy(false); }
  };

  onMount(() => { void load().catch((cause) => setError(cause instanceof Error ? cause.message : String(cause))); });

  return (
    <section class="nf-page nf-review-page nf-authoring-canvas">
      <header class="nf-manuscript-header"><div><span class="nf-eyebrow">REVIEW · {projectId() || "no project"}</span><h1>{t("Review candidates", "审阅 Candidate")}</h1><p>{t("Review is a gate, not a synonym for acceptance or settlement.", "Review 是 gate，不等于 Accept，更不等于 Settlement。")}</p></div><A class="wui-button wui-button--ghost" href={`/manuscript?project=${encodeURIComponent(projectId())}`}>{t("Back to manuscript", "返回手稿")}</A></header>

      <Show when={projectId()} fallback={<div class="wui-alert"><div class="wui-alert__body"><strong>{t("No project selected.", "尚未选择 Project。")}</strong></div></div>}>
        <div class="nf-review-layout">
          <aside class="nf-binder" aria-label={t("Candidate list", "Candidate 列表")}>
            <For each={items()} fallback={<div class="nf-empty-state"><strong>{t("No qualified candidates", "没有已通过 user-visible gate 的 Candidate")}</strong><p>{t("A registered author run may still be semantic_pending. Studio does not manufacture review data.", "已注册的 author run 可能仍是 semantic_pending；Studio 不会制造 review 数据。")}</p></div>}>
              {(item) => <button type="button" class="nf-binder-item" data-active={selected()?.candidate.candidate_id === item.candidate_id ? "true" : undefined} onClick={() => void selectCandidate(item.candidate_id)}><span>{item.task_mode} · {item.candidate_kind}</span><small>{item.status} · {item.user_visible_gate}</small></button>}
            </For>
          </aside>

          <main class="nf-review-main">
            <Show when={selected()}>{(projection) => <>
              <div class="nf-authority-banner">
                <div><span class="nf-eyebrow">CANDIDATE</span><strong>{projection().candidate.candidate_id}</strong></div>
                <div class="nf-inline-actions"><span class="wui-badge wui-badge--outline">{projection().candidate.status}</span><span class="wui-badge wui-badge--outline">gate: {projection().candidate.user_visible_gate}</span><Show when={projection().acceptance}><span class="wui-badge wui-badge--outline">Accepted ✓</span></Show><Show when={!projection().settlements.some((s) => s.status === "settled") && projection().acceptance}><strong>{t("Not Settled", "尚未 Settled")}</strong></Show></div>
              </div>

              <section class="nf-editorial-section"><div class="nf-section-heading"><span class="nf-eyebrow">DIFF</span><h2>{t("Incumbent → Candidate", "Incumbent → Candidate")}</h2></div><Show when={diff().length} fallback={<p class="nf-subtle">{t("No parent revision diff is available for this candidate.", "该 Candidate 没有可用的 parent revision diff。")}</p>}><pre class="wui-code-block nf-diff"><code>{diff().join("\n")}</code></pre></Show></section>

              <section class="nf-editorial-section"><div class="nf-section-heading"><span class="nf-eyebrow">FINDINGS</span><h2>{t("Independent review evidence", "Independent review evidence")}</h2></div><For each={projection().reviews} fallback={<p>{t("No review evidence found.", "没有找到 review evidence。")}</p>}>{(review) => <details class="nf-review-evidence"><summary>{review.evidence_kind} · independent={String(Boolean(review.independent))} · stale={String(Boolean(review.stale))}</summary><pre class="wui-code-block"><code>{JSON.stringify(review.result, null, 2)}</code></pre></details>}</For></section>

              <section class="nf-editorial-section"><div class="nf-section-heading"><span class="nf-eyebrow">AUTHORITY</span><h2>{t("Accept, then settle explicitly", "先 Accept，再显式 Settle")}</h2></div>
                <div class="nf-transaction-steps"><span data-done={projection().candidate.status === "accepted"}>1 · Review gate PASS</span><span data-done={Boolean(projection().acceptance)}>2 · Accepted ✓</span><span data-done={projection().settlements.some((s) => s.status === "settled")}>3 · Settled</span></div>
                <Show when={!projection().acceptance}><button class="wui-button" type="button" disabled={busy() || projection().candidate.status !== "review_draft" || projection().candidate.user_visible_gate !== "PASS"} onClick={() => void accept()}>{t("Accept candidate", "Accept Candidate")}</button></Show>
                <Show when={projection().acceptance && !projection().settlements.some((s) => s.status === "settled")}>
                  <div class="nf-inline-actions"><button class="wui-button wui-button--outline" type="button" disabled={busy()} onClick={() => void prepareSettlement()}>{t("Prepare settlement", "准备 Settlement")}</button><button class="wui-button" type="button" disabled={busy() || !preflight()?.ready} onClick={() => void settle()}>{t("Settle explicitly", "显式 Settle")}</button></div>
                  <Show when={preflight()}>{(prepared) => <div class="nf-settlement-preflight"><strong>{t("Exact before-state frozen", "Exact before-state 已冻结")}</strong><code>{prepared().expected_before_fingerprint}</code><small>{prepared().target_ref}</small><p>{t("If this state changes before Apply, Core must return settlement_incomplete. Studio will not auto-retry the side effect.", "若 Apply 前 before-state 发生变化，Core 必须返回 settlement_incomplete；Studio 不会自动重试副作用。")}</p></div>}</Show>
                </Show>
                <For each={projection().settlements}>{(settlement) => <div class="nf-status-line"><strong>{settlement.status}</strong><span>{settlement.target_ref}</span><code>{settlement.settlement_id}</code></div>}</For>
              </section>
            </>}</Show>
          </main>
        </div>
      </Show>

      <Show when={message()}><div class="wui-alert" role="status"><div class="wui-alert__body"><strong>{message()}</strong></div></div></Show>
      <Show when={error()}><div class="wui-alert" role="alert"><div class="wui-alert__body"><strong>{error()}</strong></div></div></Show>
    </section>
  );
}
