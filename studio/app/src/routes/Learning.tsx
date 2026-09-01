import { For, Show, createEffect, createSignal, on, onCleanup } from "solid-js";
import { useLocation } from "@solidjs/router";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";
import { connectedModelService, parseProjectFeedback, parseProjectFeedbackList, parseProjectPreference, parseProjectPreferenceReceipt,
  type CandidateRow, type InspectorListProjection, type ModelServiceListProjection, type ProjectLearningFeedback, type ProjectPreference } from "../authoring/contracts";
import { parseUserTastePolicy, parseUserTastePreferences, parseUserTasteTransition,
  type UserTastePolicy, type UserTastePreference } from "../learning/userTasteContracts";

export default function Learning() {
  const { locale } = useI18n();
  const studio = useStudio();
  const location = useLocation();
  const zh = () => locale() === "zh-CN";
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];
  const [rows, setRows] = createSignal<ProjectLearningFeedback[]>([]);
  const [candidates, setCandidates] = createSignal<CandidateRow[]>([]);
  const [candidateId, setCandidateId] = createSignal("");
  const [feedbackText, setFeedbackText] = createSignal("");
  const [sourceType, setSourceType] = createSignal<"author" | "human_reader" | "model_reader">("author");
  const [sourceId, setSourceId] = createSignal("");
  const [evidenceKind, setEvidenceKind] = createSignal("correction");
  const [feedbackDetail, setFeedbackDetail] = createSignal<ProjectLearningFeedback>();
  const [preferenceDetail, setPreferenceDetail] = createSignal<ProjectPreference>();
  const [activationConsent, setActivationConsent] = createSignal(false);
  const [receipt, setReceipt] = createSignal<Record<string, unknown>>();
  const [tastePolicy, setTastePolicy] = createSignal<UserTastePolicy>();
  const [tastePolicyEnabled, setTastePolicyEnabled] = createSignal(false);
  const [tastePolicySources, setTastePolicySources] = createSignal<string[]>(["corpus", "feedback", "user_edit"]);
  const [tastePolicyConsent, setTastePolicyConsent] = createSignal(false);
  const [tastePreferences, setTastePreferences] = createSignal<UserTastePreference[]>([]);
  const [tasteReasons, setTasteReasons] = createSignal<Record<string, string>>({});
  const [tasteLoading, setTasteLoading] = createSignal(false);
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);
  const [busy, setBusy] = createSignal(false);
  let listGeneration = 0;
  let tasteGeneration = 0;
  let actionGeneration = 0;
  let detailGeneration = 0;
  let disposed = false;
  let observationIntent: { request: string; event_id: string } | undefined;
  let preferenceIntent: { request: string; idempotency_key: string } | undefined;
  const message = (cause: unknown) => cause instanceof Error ? cause.message : String(cause);
  const sourceLabel = (value?: string) => value === "author" ? (zh() ? "作者" : "Author")
    : value === "human_reader" ? (zh() ? "真实读者提供" : "Human reader feedback")
    : value === "model_reader" ? (zh() ? "模型代理，非真实读者" : "Model proxy, not a human reader") : (zh() ? "来源未标注" : "Source not recorded");
  const selectedCandidate = () => candidates().find((candidate) => candidate.candidate_id === candidateId());
  const beginAction = () => {
    const generation = ++actionGeneration; const projectId = studio.projectId();
    return { projectId, current: () => !disposed && actionGeneration === generation && studio.projectId() === projectId };
  };

  const loadUserTaste = async () => {
    const generation = ++tasteGeneration;
    const current = () => !disposed && generation === tasteGeneration;
    const getPolicy = operations().includes("learning.auto_activation_policy.get");
    const listTaste = operations().includes("learning.user_taste.list");
    if (!getPolicy && !listTaste) { setTastePolicy(undefined); setTastePreferences([]); return; }
    setTasteLoading(true); setError(undefined);
    const results = await Promise.allSettled([
      getPolicy ? invokeBridge("learning.auto_activation_policy.get") : Promise.resolve(undefined),
      listTaste ? invokeBridge("learning.user_taste.list") : Promise.resolve(undefined),
    ]);
    if (!current()) return;
    const errors: string[] = [];
    results.forEach((settled, index) => {
      try {
        if (settled.status === "rejected") throw settled.reason;
        const result = settled.value;
        if (!result) return;
        if (result.status !== "ok" || result.data === null) throw new Error(operationError(result));
        if (index === 0) {
          const policy = parseUserTastePolicy(result.data);
          setTastePolicy(policy); setTastePolicyEnabled(policy.enabled); setTastePolicySources([...policy.source_kinds]);
          setTastePolicyConsent(false);
        } else setTastePreferences(parseUserTastePreferences(result.data));
      } catch (cause) { errors.push(message(cause)); }
    });
    if (errors.length) setError(errors.join(" · "));
    if (current()) setTasteLoading(false);
  };

  const toggleTasteSource = (source: string, enabled: boolean) => {
    setTastePolicySources((current) => enabled ? [...new Set([...current, source])] : current.filter((item) => item !== source));
    setTastePolicyConsent(false);
  };

  const saveTastePolicy = async () => {
    const policy = tastePolicy();
    if (busy() || !policy || !tastePolicySources().length || !operations().includes("learning.auto_activation_policy.set")) return;
    if (tastePolicyEnabled() && !tastePolicyConsent()) return;
    const generation = ++actionGeneration;
    setBusy(true); setError(undefined);
    try {
      const result = await invokeBridge("learning.auto_activation_policy.set", { payload: {
        enabled: tastePolicyEnabled(), source_kinds: tastePolicySources(), expected_version: policy.policy_version,
        authorization_ref: tastePolicyEnabled() ? "studio_user_explicit_authorization" : "studio_user_revocation",
      } });
      if (disposed || generation !== actionGeneration) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const saved = parseUserTastePolicy(result.data);
      setTastePolicy(saved); setTastePolicyEnabled(saved.enabled); setTastePolicySources([...saved.source_kinds]); setTastePolicyConsent(false);
      await loadUserTaste();
    } catch (cause) { if (!disposed && generation === actionGeneration) setError(message(cause)); }
    finally { if (!disposed && generation === actionGeneration) setBusy(false); }
  };

  const changeUserTaste = async (preference: UserTastePreference, action: "pause" | "withdraw") => {
    const operation = `learning.user_taste.${action}`;
    const reason = (tasteReasons()[preference.hypothesis_id] ?? "").trim();
    if (busy() || !reason || !operations().includes(operation)) return;
    const generation = ++actionGeneration;
    const args = { hypothesis_id: preference.hypothesis_id, expected_version: preference.version, reason };
    setBusy(true); setError(undefined);
    try {
      const result = await invokeBridge(operation, args);
      if (disposed || generation !== actionGeneration) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const parsed = parseUserTasteTransition(result.data, { ...args, action });
      if ("status" in parsed) throw new Error("user_taste_transition_unsupported");
      setReceipt(parsed.receipt as unknown as Record<string, unknown>);
      setTasteReasons((current) => ({ ...current, [preference.hypothesis_id]: "" }));
      await loadUserTaste();
    } catch (cause) { if (!disposed && generation === actionGeneration) setError(message(cause)); }
    finally { if (!disposed && generation === actionGeneration) setBusy(false); }
  };

  const load = async () => {
    const projectId = studio.projectId(); const generation = ++listGeneration;
    const current = () => !disposed && generation === listGeneration && studio.projectId() === projectId;
    if (!projectId) return;
    setLoading(true); setError(undefined);
    try {
      const results = await Promise.allSettled([
        operations().includes("learning.feedback.list") ? invokeBridge("learning.feedback.list", { project_id: projectId, limit: 200 }) : Promise.resolve(undefined),
        operations().includes("inspector.candidates.list") ? invokeBridge<InspectorListProjection<CandidateRow>>("inspector.candidates.list", { project_id: projectId, limit: 200 }) : Promise.resolve(undefined),
        studio.refreshPreferences(),
      ]);
      if (!current()) return;
      const errors: string[] = [];
      results.forEach((settled, index) => {
        try {
          if (settled.status === "rejected") throw settled.reason;
          const result = settled.value;
          if (!result) return;
          if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
          if (index === 0) setRows(parseProjectFeedbackList(result.data, projectId));
          else if (index === 1) {
            const data = result.data as InspectorListProjection<CandidateRow>;
            if (data.schema !== "quillframe_inspector_projection_v1" || data.project_id !== projectId || data.kind !== "candidates" || data.authority !== false || !Array.isArray(data.items)) throw new Error("learning_candidates_binding_invalid");
            const eligible = data.items.filter((item) => ["review_draft", "accepted"].includes(item.effective_status ?? item.status ?? "")
              && item.document_id && item.run_id && /^sha256:[0-9a-f]{64}$/.test(item.candidate_fingerprint ?? item.content_fingerprint ?? ""));
            setCandidates(eligible);
            const requested = new URLSearchParams(location.search).get("candidate");
            if (!eligible.some((item) => item.candidate_id === candidateId())) setCandidateId(eligible.find((item) => item.candidate_id === requested)?.candidate_id ?? eligible[0]?.candidate_id ?? "");
          }
        } catch (cause) { errors.push(message(cause)); }
      });
      if (errors.length) setError(errors.join(" · "));
    } catch (cause) { if (current()) setError(message(cause)); }
    finally { if (current()) setLoading(false); }
  };

  const observe = async () => {
    const candidate = selectedCandidate(); const feedback = feedbackText().trim();
    if (busy() || !candidate?.run_id || !candidate.document_id || !feedback || !operations().includes("learning.feedback.observe")) return;
    const request = beginAction();
    const args = { project_id: request.projectId, feedback_text: feedback, evidence_kind: evidenceKind(), candidate_id: candidate.candidate_id,
      candidate_fingerprint: candidate.candidate_fingerprint ?? candidate.content_fingerprint!, document_id: candidate.document_id, run_id: candidate.run_id,
      source_type: sourceType(), source_id: sourceType() === "author" ? "studio_user" : sourceId().trim() };
    if (!args.source_id) { setError(zh() ? "请标明反馈来源。" : "Identify the feedback source."); return; }
    const serialized = JSON.stringify(args);
    if (!observationIntent || observationIntent.request !== serialized) observationIntent = { request: serialized, event_id: `studio-feedback-${crypto.randomUUID()}` };
    const eventId = observationIntent.event_id;
    setBusy(true); setError(undefined);
    try {
      const result = await invokeBridge("learning.feedback.observe", { ...args, event_id: eventId });
      if (!request.current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      const parsed = parseProjectFeedback(result.data, request.projectId, eventId);
      if (parsed.candidate_id !== args.candidate_id || parsed.candidate_fingerprint !== args.candidate_fingerprint || parsed.document_id !== args.document_id || parsed.run_id !== args.run_id || parsed.feedback_text !== feedback
        || parsed.source_type !== args.source_type || parsed.source_id !== args.source_id) throw new Error("learning_feedback_observation_binding_invalid");
      setFeedbackDetail(parsed); observationIntent = undefined;
      if (feedbackText().trim() === feedback) setFeedbackText("");
      await load();
    } catch (cause) { if (request.current()) setError(message(cause)); }
    finally { if (request.current()) setBusy(false); }
  };

  const connectedService = async () => {
    const result = await invokeBridge<ModelServiceListProjection>("model.service.list");
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    const service = connectedModelService(result.data.items);
    if (!service) throw new Error(zh() ? "请先在 AI 与模型连接可用服务。" : "Connect an available service in AI & Models first.");
    return service.service_id;
  };

  const runFeedback = async (row: ProjectLearningFeedback, resume = false) => {
    const operation = resume ? "learning.feedback.resume" : "learning.feedback.execute";
    if (busy() || row.advisory_only || row.source_type === "model_reader" || !operations().includes(operation) || !operations().includes("model.service.list")) return;
    const request = beginAction(); setBusy(true); setError(undefined);
    try {
      const serviceId = await connectedService();
      if (!request.current()) return;
      const result = await invokeBridge(operation, { project_id: request.projectId, event_id: row.event_id, service_id: serviceId });
      if (!request.current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setFeedbackDetail(parseProjectFeedback(result.data, request.projectId, row.event_id));
      await load();
    } catch (cause) { if (request.current()) setError(message(cause)); }
    finally { if (request.current()) setBusy(false); }
  };

  const getFeedback = async (eventId: string) => {
    const generation = ++detailGeneration; const projectId = studio.projectId();
    try {
      const result = await invokeBridge("learning.feedback.get", { project_id: projectId, event_id: eventId });
      if (disposed || generation !== detailGeneration || studio.projectId() !== projectId) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setFeedbackDetail(parseProjectFeedback(result.data, projectId, eventId));
    } catch (cause) { if (!disposed && generation === detailGeneration && studio.projectId() === projectId) setError(message(cause)); }
  };

  const getPreference = async (hypothesisId: string) => {
    const generation = ++detailGeneration; const projectId = studio.projectId();
    setActivationConsent(false); setPreferenceDetail(undefined);
    try {
      const result = await invokeBridge("learning.preference.get", { project_id: projectId, hypothesis_id: hypothesisId });
      if (disposed || generation !== detailGeneration || studio.projectId() !== projectId) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setPreferenceDetail(parseProjectPreference(result.data, projectId, hypothesisId));
    } catch (cause) { if (!disposed && generation === detailGeneration && studio.projectId() === projectId) setError(message(cause)); }
  };

  const reviewPreference = async (preference: ProjectPreference) => {
    if (busy() || !operations().includes("learning.preference.review")) return;
    const request = beginAction(); setBusy(true); setError(undefined); setActivationConsent(false);
    try {
      const serviceId = await connectedService();
      if (!request.current()) return;
      const result = await invokeBridge("learning.preference.review", { project_id: request.projectId, hypothesis_id: preference.hypothesis_id, expected_version: preference.version, service_id: serviceId });
      if (!request.current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setPreferenceDetail(parseProjectPreference(result.data, request.projectId, preference.hypothesis_id));
      await load();
    } catch (cause) { if (request.current()) setError(message(cause)); }
    finally { if (request.current()) setBusy(false); }
  };

  const changePreference = async (preference: ProjectPreference, action: "activate" | "deactivate") => {
    if (busy() || !operations().includes(`learning.preference.${action}`) || action === "activate" && !activationConsent()) return;
    const request = beginAction();
    const args = { project_id: request.projectId, hypothesis_id: preference.hypothesis_id, expected_version: preference.version, authorized_by: "studio_user" };
    const serialized = JSON.stringify({ ...args, action });
    if (!preferenceIntent || preferenceIntent.request !== serialized) preferenceIntent = { request: serialized, idempotency_key: `studio-preference-${crypto.randomUUID()}` };
    const idempotencyKey = preferenceIntent.idempotency_key;
    setBusy(true); setError(undefined);
    try {
      const result = await invokeBridge(`learning.preference.${action}`, { ...args, user_authorized: true, idempotency_key: idempotencyKey });
      if (!request.current()) return;
      if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
      setReceipt(parseProjectPreferenceReceipt(result.data, { ...args, action, idempotency_key: idempotencyKey }));
      preferenceIntent = undefined; setActivationConsent(false);
      await load();
      if (request.current()) await getPreference(preference.hypothesis_id);
    } catch (cause) { if (request.current()) setError(message(cause)); }
    finally { if (request.current()) setBusy(false); }
  };

  createEffect(on(() => studio.projectId(), () => {
    actionGeneration += 1; detailGeneration += 1; setRows([]); setCandidates([]); setCandidateId(""); setFeedbackText("");
    setFeedbackDetail(undefined); setPreferenceDetail(undefined); setReceipt(undefined); setActivationConsent(false); setBusy(false);
    observationIntent = undefined; preferenceIntent = undefined;
  }));
  createEffect(on([() => studio.projectId(), operations], () => { void load(); }));
  createEffect(on(operations, () => { void loadUserTaste(); }));
  onCleanup(() => { disposed = true; listGeneration += 1; tasteGeneration += 1; actionGeneration += 1; detailGeneration += 1; });

  return (
    <section class="nf-page qf-learning-page">
      <PageIntro eyebrow="LEARNING · AUTHOR CONTROL" title={zh() ? "让具体反馈，变成可选择的创作经验。" : "Turn specific feedback into choices for future writing."} body={zh() ? "反馈先绑定具体版本，由模型解释为候选偏好；评估、作用域与激活仍是独立步骤。项目偏好留在项目内；跨项目 user_taste 只有在明确长期授权与完整门槛同时成立时才可自动激活。" : "Feedback binds to a specific version before a model interprets possible preferences. Review, scope and activation remain separate. Project preferences stay in-project; cross-project user taste can auto-activate only under explicit standing authorization and all required gates."} />
      <section class="qf-editorial-sheet" aria-labelledby="user-taste-policy-title">
        <div class="qf-section-head"><div><h2 id="user-taste-policy-title">{zh() ? "跨项目品味 · 长期自动激活策略" : "Cross-project taste · standing auto-activation policy"}</h2><p>{zh() ? "这项授权只允许已经通过 user_taste 证据、反证和提升门槛的候选进入激活流程。当前明确要求始终优先；它不会训练模型，也不会提升通用 Framework 规则。" : "This authorization only lets candidates that already pass user-taste evidence, contradiction and promotion gates enter activation. Your current explicit request always wins. It neither trains a model nor promotes generic Framework rules."}</p></div><button class="wui-button wui-button--outline" type="button" disabled={tasteLoading() || busy()} onClick={() => void loadUserTaste()}>{zh() ? "刷新" : "Refresh"}</button></div>
        <CoreRequirementNotice operation="learning.auto_activation_policy.get" compact />
        <Show when={tastePolicy()} fallback={<p>{zh() ? "Core 尚未提供长期 user_taste 策略投影。" : "Core has not exposed the standing user-taste policy projection."}</p>}>{(policy) => <>
          <label class="qf-inline-actions"><input type="checkbox" checked={tastePolicyEnabled()} disabled={busy()} onChange={(event) => { setTastePolicyEnabled(event.currentTarget.checked); setTastePolicyConsent(false); }} />{zh() ? "允许符合全部门槛的 user_taste 候选自动激活" : "Allow fully qualified user-taste candidates to activate automatically"}</label>
          <fieldset class="qf-intent-fields" disabled={busy()}><legend>{zh() ? "允许的证据来源" : "Allowed evidence sources"}</legend>{[
            ["corpus", zh() ? "受治理语料研究" : "Governed corpus research"],
            ["feedback", zh() ? "明确反馈" : "Explicit feedback"],
            ["user_edit", zh() ? "用户修改" : "User edits"],
          ].map(([source, label]) => <label class="qf-inline-actions"><input type="checkbox" checked={tastePolicySources().includes(source)} onChange={(event) => toggleTasteSource(source, event.currentTarget.checked)} />{label}</label>)}</fieldset>
          <p class="nf-mono">v{policy().policy_version} · {policy().enabled ? (zh() ? "已授权" : "authorized") : (zh() ? "未授权 / 已撤回" : "not authorized / revoked")}</p>
          <Show when={tastePolicyEnabled()}><label class="qf-inline-actions"><input type="checkbox" checked={tastePolicyConsent()} disabled={busy()} onChange={(event) => setTastePolicyConsent(event.currentTarget.checked)} />{zh() ? "我明确授权这项跨项目长期策略；我可以随时撤回" : "I explicitly authorize this cross-project standing policy and can revoke it at any time"}</label></Show>
          <button class="wui-button wui-button--solid" type="button" disabled={busy() || !tastePolicySources().length || tastePolicyEnabled() && !tastePolicyConsent() || !operations().includes("learning.auto_activation_policy.set")} onClick={() => void saveTastePolicy()}>{tastePolicyEnabled() ? (zh() ? "保存长期授权" : "Save standing authorization") : (zh() ? "撤回长期授权" : "Revoke standing authorization")}</button>
        </>}</Show>
      </section>
      <section class="qf-editorial-sheet" aria-labelledby="user-taste-candidates-title">
        <div class="qf-section-head"><div><h2 id="user-taste-candidates-title">{zh() ? "user_taste 候选与已激活偏好" : "User-taste candidates and active preferences"}</h2><p>{zh() ? "暂停会把偏好转为有争议状态；撤回会弃用它。两项操作都保留证据链和版本。" : "Pause moves a preference to contested; withdraw deprecates it. Both preserve provenance and version history."}</p></div><AuthorityLabel value={tastePolicy()?.enabled ? "policy_enabled" : "policy_disabled"} /></div>
        <CoreRequirementNotice operation="learning.user_taste.list" compact />
        <For each={tastePreferences()}>{(preference) => <article><header><h3>{preference.statement}</h3><AuthorityLabel value={preference.state} /></header><p>{preference.mechanism || "—"}</p><p class="nf-mono">user_taste · {preference.dimension} · v{preference.version}</p><details><summary>{zh() ? "适用边界与证据引用" : "Applicability and evidence references"}</summary><pre>{JSON.stringify({ applicability: preference.applicability, evidence_ids: preference.evidence_ids }, null, 2)}</pre></details><Show when={preference.contradiction_ids.length}><p>{zh() ? "未解决反证" : "Unresolved contradictions"}: {preference.contradiction_ids.join(" · ")}</p></Show><Show when={!['deprecated', 'superseded'].includes(preference.state)}><label class="nf-field-label"><span>{zh() ? "暂停 / 撤回原因（必填）" : "Reason to pause or withdraw (required)"}</span><input class="wui-input" value={tasteReasons()[preference.hypothesis_id] ?? ""} disabled={busy()} onInput={(event) => setTasteReasons((current) => ({ ...current, [preference.hypothesis_id]: event.currentTarget.value }))} /></label><div class="qf-inline-actions"><Show when={preference.state === "active"}><button class="wui-button wui-button--outline" type="button" disabled={busy() || !(tasteReasons()[preference.hypothesis_id] ?? "").trim() || !operations().includes("learning.user_taste.pause")} onClick={() => void changeUserTaste(preference, "pause")}>{zh() ? "暂停这条偏好" : "Pause this preference"}</button></Show><button class="wui-button wui-button--outline" type="button" disabled={busy() || !(tasteReasons()[preference.hypothesis_id] ?? "").trim() || !operations().includes("learning.user_taste.withdraw")} onClick={() => void changeUserTaste(preference, "withdraw")}>{zh() ? "撤回这条偏好" : "Withdraw this preference"}</button></div></Show></article>}</For>
        <Show when={!tasteLoading() && !tastePreferences().length}><p>{zh() ? "还没有跨项目 user_taste 候选。项目偏好仍留在下方，不会被自动抬升作用域。" : "No cross-project user-taste candidates yet. Project preferences remain below and are never widened automatically."}</p></Show>
      </section>
      <Show when={error()}>{(value) => <p role="alert">{value()}</p>}</Show>
      <Show when={studio.projectId()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "先打开小说项目" : "Open a novel first"}</strong><a href="/start">{zh() ? "开始" : "Start"}</a></div>}>
        <div class="qf-section-head"><h2>{zh() ? "反馈与偏好" : "Feedback and preferences"}</h2><button class="wui-button wui-button--outline" type="button" disabled={loading() || busy()} onClick={() => void load()}>{zh() ? "刷新" : "Refresh"}</button></div>
        <Show when={studio.preferenceError()}>{(value) => <p role="alert">{value()}</p>}</Show>
        <section class="qf-editorial-sheet qf-feedback-form"><h2>{zh() ? "记录一条具体反馈" : "Record specific feedback"}</h2><CoreRequirementNotice operation="learning.feedback.observe" compact />
          <label class="nf-field-label"><span>{zh() ? "反馈对应的稿件版本" : "Manuscript version"}</span><select class="wui-input" value={candidateId()} disabled={busy()} onChange={(event) => setCandidateId(event.currentTarget.value)}><option value="">{zh() ? "选择可审阅的稿件版本" : "Choose a released candidate"}</option><For each={candidates()}>{(candidate) => <option value={candidate.candidate_id}>{candidate.candidate_id} · {candidate.document_id}</option>}</For></select></label>
          <div class="qf-intent-fields"><label class="nf-field-label"><span>{zh() ? "来源类型" : "Feedback source"}</span><select class="wui-input" value={sourceType()} disabled={busy()} onChange={(event) => setSourceType(event.currentTarget.value as "author" | "human_reader" | "model_reader")}><option value="author">{zh() ? "作者本人" : "Author"}</option><option value="human_reader">{zh() ? "真实读者提供" : "Human reader"}</option><option value="model_reader">{zh() ? "模型代理（非真人）" : "Model proxy (not human)"}</option></select></label><label class="nf-field-label"><span>{zh() ? "反馈类别" : "Feedback kind"}</span><select class="wui-input" value={evidenceKind()} disabled={busy()} onChange={(event) => setEvidenceKind(event.currentTarget.value)}><option value="correction">{zh() ? "具体修改意见" : "Correction"}</option><option value="explicit_rule">{zh() ? "明确写作要求" : "Explicit instruction"}</option><option value="comparison">{zh() ? "版本比较" : "Comparison"}</option><option value="rejection">{zh() ? "不接受的原因" : "Reason for rejection"}</option><option value="acceptance">{zh() ? "值得保留的原因" : "Reason to preserve"}</option></select></label></div>
          <Show when={sourceType() !== "author"}><label class="nf-field-label"><span>{zh() ? "来源名称或标识" : "Source name or identifier"}</span><input class="wui-input" value={sourceId()} disabled={busy()} onInput={(event) => setSourceId(event.currentTarget.value)} /></label></Show>
          <label class="nf-field-label"><span>{zh() ? "反馈原文与具体证据" : "Feedback text and specific evidence"}</span><textarea class="wui-input" rows={5} value={feedbackText()} onInput={(event) => setFeedbackText(event.currentTarget.value)} placeholder={zh() ? "哪里吸引你，哪里失去兴趣？请说明对应的文本、感受和修改意图。" : "What held your interest, and where did it fade? Identify the text, reaction and intended change."} /></label>
          <button class="wui-button wui-button--solid" type="button" disabled={busy() || !selectedCandidate() || !feedbackText().trim() || !operations().includes("learning.feedback.observe")} onClick={() => void observe()}>{zh() ? "记录反馈，不自动启用偏好" : "Record feedback without activating preferences"}</button>
          <Show when={sourceType() === "model_reader"}><p role="status">{zh() ? "模型代理反馈仅记为 advisory 观察，不进入人类反馈学习链，也不能据此启用偏好。" : "Model feedback is stored as an advisory observation only. It cannot enter the human-feedback learning path or authorize preference activation."}</p></Show>
        </section>
        <div class="qf-story-grid">
          <section class="qf-story-section"><h2>{zh() ? "已记录反馈" : "Recorded feedback"}</h2><CoreRequirementNotice operation="learning.feedback.list" compact /><For each={rows()}>{(row) => <article><header><strong>{sourceLabel(row.source_type)}</strong><AuthorityLabel value={row.status} /></header><p>{row.source_id ?? "—"} · {row.evidence_kind} · {row.candidate_id}</p><code>{row.candidate_fingerprint}</code><div class="qf-inline-actions"><button class="wui-button wui-button--ghost" type="button" disabled={busy() || !operations().includes("learning.feedback.get")} onClick={() => void getFeedback(row.event_id)}>{zh() ? "查看反馈与解释" : "Read feedback and interpretation"}</button><Show when={row.status === "awaiting_semantic"}><button class="wui-button wui-button--outline" type="button" disabled={busy() || !operations().includes("learning.feedback.execute")} onClick={() => void runFeedback(row)}>{zh() ? "用模型解释反馈" : "Interpret with a model"}</button></Show><Show when={["awaiting_external", "ready_to_apply"].includes(row.status)}><button class="wui-button wui-button--outline" type="button" disabled={busy() || !operations().includes("learning.feedback.resume")} onClick={() => void runFeedback(row, true)}>{zh() ? "恢复已确认结果" : "Resume confirmed result"}</button></Show></div><Show when={row.semantic_call?.pending_reason}><p>{row.semantic_call!.pending_reason}</p></Show></article>}</For><Show when={!loading() && !rows().length}><p>{zh() ? "还没有已记录反馈。" : "No recorded feedback yet."}</p></Show><Show when={feedbackDetail()}>{(detail) => <article><h3>{zh() ? "反馈原文" : "Original feedback"}</h3><p>{sourceLabel(detail().source_type)} · {detail().status}</p><pre>{detail().feedback_text ?? "—"}</pre><Show when={detail().interpretation}><h3>{zh() ? "模型解释 · 不自动成为偏好" : "Model interpretation · not an active preference"}</h3><pre>{JSON.stringify(detail().interpretation, null, 2)}</pre></Show><details><summary>{zh() ? "执行来源" : "Execution provenance"}</summary><pre>{JSON.stringify(detail().semantic_call, null, 2)}</pre></details></article>}</Show></section>
          <section class="qf-story-section"><h2>{zh() ? "项目偏好候选" : "Project preference candidates"}</h2><CoreRequirementNotice operation="learning.preference.list" compact /><For each={studio.projectPreferences()}>{(preference) => <article><header><h3>{preference.statement}</h3><AuthorityLabel value={preference.state} /></header><p>{preference.mechanism}</p><p>project · v{preference.version}</p><button class="wui-button wui-button--ghost" type="button" disabled={busy() || !operations().includes("learning.preference.get")} onClick={() => void getPreference(preference.hypothesis_id)}>{zh() ? "查看证据与启停" : "Inspect evidence and activation"}</button><Show when={preference.active_for_future_production}><label class="qf-inline-actions"><input type="checkbox" checked={studio.selectedPreferenceIds().includes(preference.hypothesis_id)} onChange={(event) => studio.setSelectedPreferenceIds(event.currentTarget.checked ? [...studio.selectedPreferenceIds(), preference.hypothesis_id] : studio.selectedPreferenceIds().filter((id) => id !== preference.hypothesis_id))} />{zh() ? "下次注册写作任务时采用" : "Select for the next writing run"}</label></Show></article>}</For><Show when={!studio.preferenceLoading() && !studio.projectPreferences().length}><p>{zh() ? "还没有项目偏好候选。" : "No project preference candidates yet."}</p></Show>
            <Show when={preferenceDetail()}>{(preference) => <article><h3>{preference().statement}</h3><p>{preference().mechanism}</p><h4>{zh() ? "适用边界" : "Applicability"}</h4><pre>{JSON.stringify(preference().applicability, null, 2)}</pre><p>{zh() ? "证据" : "Evidence"}: {preference().evidence_ids.join(" · ") || "—"}</p><Show when={preference().contradiction_ids.length}><p>{zh() ? "反证" : "Contradictions"}: {preference().contradiction_ids.join(" · ")}</p></Show><Show when={preference().activation_review?.judgment}><h4>{zh() ? "启用评估" : "Activation review"}</h4><pre>{JSON.stringify(preference().activation_review?.judgment, null, 2)}</pre></Show>
              <Show when={!preference().active_for_future_production && preference().state !== "superseded"} fallback={<button class="wui-button wui-button--outline" type="button" disabled={busy() || !preference().active_for_future_production || !operations().includes("learning.preference.deactivate")} onClick={() => void changePreference(preference(), "deactivate")}>{zh() ? "停用这个项目偏好" : "Deactivate this project preference"}</button>}><button class="wui-button wui-button--outline" type="button" disabled={busy() || !operations().includes("learning.preference.review")} onClick={() => void reviewPreference(preference())}>{zh() ? "评估此版本能否启用" : "Review this version for activation"}</button><label class="qf-inline-actions"><input type="checkbox" checked={activationConsent()} disabled={busy()} onChange={(event) => setActivationConsent(event.currentTarget.checked)} />{zh() ? "我确认只在当前项目启用这条偏好" : "I explicitly authorize this preference for this project only"}</label><button class="wui-button wui-button--solid" type="button" disabled={busy() || !activationConsent() || !preference().activation_review?.judgment || !operations().includes("learning.preference.activate")} onClick={() => void changePreference(preference(), "activate")}>{zh() ? "作者确认启用" : "Activate with author confirmation"}</button></Show>
            </article>}</Show>
          </section>
        </div>
        <Show when={receipt()}>{(value) => <details><summary>{zh() ? "偏好状态变更收据" : "Preference state-change receipt"}</summary><pre class="qf-diff">{JSON.stringify(value(), null, 2)}</pre></details>}</Show>
        <p class="qf-inspector-boundary">{zh() ? "不训练模型权重，不自动提升为跨项目品味。未知模型调用不会被恢复操作自动重发。已启用 ≠ 本次已选中 ≠ 已进入冻结上下文。" : "No model weight training or automatic cross-project taste promotion. Resume does not replay an unknown model call. Active ≠ selected for this run ≠ loaded into frozen context."}</p>
      </Show>
    </section>
  );
}
