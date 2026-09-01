import { For, Show, createSignal, onCleanup } from "solid-js";
import { PageIntro } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";
import { AuthorityLabel, CoreRequirementNotice } from "../authoring/AuthoringUI";
import { connectedModelService, type ModelServiceListProjection } from "../authoring/contracts";
import { collectionId as projectionCollectionId, corpusEligibilityCounts, corpusMetadataView, corpusProgress,
  parseCorpusRecord, parseCorpusSelection, type CorpusEligibilityCounts, type CorpusProfile, type CorpusRecord,
  type CorpusSelectionProjection } from "../research/corpusContracts";

type SearchRow = { entity_type: string; entity_id: string; title: string; snippet: string; rank: number };
const STYLE_LEARNING_PROTOCOL = "quillframe_corpus_style_learning_v1";
const isRecord = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);

export default function Research() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const operations = () => studio.bridgeCapabilities()?.operations ?? [];
  const localCorpusAvailable = () => studio.surface() === "local_app" && operations().includes("corpus.collection.scan");
  const [query, setQuery] = createSignal("");
  const [rows, setRows] = createSignal<SearchRow[]>([]);
  const [collectionPath, setCollectionPath] = createSignal("");
  const [rightsClass, setRightsClass] = createSignal<"analysis_only" | "redistributable" | "unknown">("analysis_only");
  const [rightsBasis, setRightsBasis] = createSignal("");
  const [collectionId, setCollectionId] = createSignal("");
  const [existingStudyId, setExistingStudyId] = createSignal("");
  const [studyProfile, setStudyProfile] = createSignal<CorpusProfile>("general");
  const [scanResult, setScanResult] = createSignal<CorpusRecord>();
  const [scanEligibility, setScanEligibility] = createSignal<CorpusEligibilityCounts>({});
  const [selection, setSelection] = createSignal<CorpusSelectionProjection>();
  const [selectedWorkIds, setSelectedWorkIds] = createSignal<string[]>([]);
  const [rightsScopeAcknowledged, setRightsScopeAcknowledged] = createSignal(false);
  const [studyResult, setStudyResult] = createSignal<CorpusRecord>();
  const [packPreview, setPackPreview] = createSignal<CorpusRecord>();
  const [activationResult, setActivationResult] = createSignal<CorpusRecord>();
  const [error, setError] = createSignal<string>();
  const [busy, setBusy] = createSignal<string>();
  let generation = 0;
  let disposed = false;
  const message = (cause: unknown) => cause instanceof Error ? cause.message : String(cause);
  const currentStudyId = () => selection()?.study_id ?? (typeof studyResult()?.study_id === "string" ? studyResult()!.study_id as string : "");
  const progress = () => studyResult() ? corpusProgress(studyResult()) : undefined;
  const styleRunner = () => {
    const value = studyResult()?.runner;
    return isRecord(value) ? value : undefined;
  };
  const selected = (workId: string) => selectedWorkIds().includes(workId);
  const selectionConfirmed = () => selection()?.status === "confirmed";
  const countLabel = (value: number | undefined) => value === undefined ? (zh() ? "未报告" : "not reported") : String(value);
  const toggleWork = (workId: string, enabled: boolean) => {
    setRightsScopeAcknowledged(false);
    setSelectedWorkIds((current) => enabled
      ? [...new Set([...current, workId])]
      : current.filter((item) => item !== workId));
  };

  const run = async (operation: string, args: Record<string, unknown>, accept: (data: unknown) => void) => {
    if (busy() || !operations().includes(operation)) return;
    const request = ++generation;
    setBusy(operation); setError(undefined);
    try {
      const result = await invokeBridge(operation, args);
      if (disposed || request !== generation) return;
      if (result.status !== "ok" || result.data === null) throw new Error(operationError(result));
      accept(result.data);
    } catch (cause) { if (!disposed && request === generation) setError(message(cause)); }
    finally { if (!disposed && request === generation) setBusy(undefined); }
  };

  const search = async () => {
    if (!studio.projectId() || !query().trim()) return;
    await run("project.search", { project_id: studio.projectId(), query: query().trim(), limit: 30 }, (data) => {
      const projection = data as { results?: SearchRow[] };
      if (!projection || !Array.isArray(projection.results)) throw new Error("project_search_projection_invalid");
      setRows(projection.results);
    });
  };

  const scanCollection = async () => {
    if (!localCorpusAvailable() || !collectionPath().trim() || !rightsBasis().trim()) return;
    await run("corpus.collection.scan", {
      collection_path: collectionPath().trim(),
      rights: { rights_class: rightsClass(), rights_basis: rightsBasis().trim() },
    }, (data) => {
      const projection = parseCorpusRecord(data);
      const eligibility = corpusEligibilityCounts(projection);
      setScanResult(projection);
      setScanEligibility(eligibility);
      const identity = projectionCollectionId(projection);
      if (identity) setCollectionId(identity);
      setSelection(undefined); setSelectedWorkIds([]); setRightsScopeAcknowledged(false); setStudyResult(undefined);
    });
  };

  const acceptSelection = (data: unknown, expected: { profile: CorpusProfile; collection_id?: string; study_id?: string }) => {
    const proposal = parseCorpusSelection(data, { allowPrivateLabels: studio.surface() === "local_app" });
    if (expected.collection_id && proposal.collection_id !== expected.collection_id) throw new Error("corpus_selection_collection_mismatch");
    if (expected.study_id && proposal.study_id !== expected.study_id) throw new Error("corpus_selection_study_mismatch");
    if (proposal.profile !== expected.profile) throw new Error("corpus_selection_profile_mismatch");
    setSelection(proposal); setExistingStudyId(proposal.study_id);
    setSelectedWorkIds(proposal.items.filter((item) => item.selected).map((item) => item.work_id));
    setRightsScopeAcknowledged(false);
    setStudyResult(undefined); setPackPreview(undefined); setActivationResult(undefined);
  };

  const proposeSelection = async () => {
    if (!collectionId().trim()) return;
    const requestedProfile = studyProfile();
    await run("corpus.selection.propose", { collection_id: collectionId().trim(), profile: requestedProfile, limit: 24 }, (data) => {
      acceptSelection(data, { collection_id: collectionId().trim(), profile: requestedProfile });
    });
  };

  const loadExistingSelection = async () => {
    if (studio.surface() !== "local_app" || !existingStudyId().trim()) return;
    const requestedStudyId = existingStudyId().trim();
    const requestedProfile = studyProfile();
    await run("corpus.selection.propose", { study_id: requestedStudyId, profile: requestedProfile, limit: 24 }, (data) => {
      acceptSelection(data, { study_id: requestedStudyId, profile: requestedProfile });
    });
  };

  const refreshSelection = async () => {
    const proposal = selection();
    if (!proposal || proposal.status !== "proposed") return;
    await run("corpus.selection.refresh", {
      study_id: proposal.study_id,
      profile: proposal.profile,
      expected_proposal_hash: proposal.proposal_fingerprint,
    }, (data) => {
      acceptSelection(data, { study_id: proposal.study_id, profile: proposal.profile });
    });
  };

  const confirmSelection = async () => {
    const proposal = selection();
    if (!proposal || !rightsScopeAcknowledged() || proposal.status !== "proposed" || selectedWorkIds().length < 1) return;
    const confirmedIds = proposal.items.filter((item) => selected(item.work_id)).map((item) => item.work_id);
    if (confirmedIds.length < 1) return;
    await run("corpus.selection.confirm", {
      study_id: proposal.study_id, work_ids: confirmedIds, proposal_fingerprint: proposal.proposal_fingerprint, profile: proposal.profile,
      user_authorized: true,
    }, (data) => {
      const confirmed = parseCorpusRecord(data);
      if (confirmed.study_id !== proposal.study_id) throw new Error("corpus_selection_study_mismatch");
      if (confirmed.profile !== proposal.profile) throw new Error("corpus_selection_profile_mismatch");
      setSelection({ ...proposal, status: typeof confirmed.status === "string" ? confirmed.status : "confirmed" });
      setStudyResult(confirmed);
    });
  };

  const connectedService = async () => {
    const result = await invokeBridge<ModelServiceListProjection>("model.service.list");
    if (result.status !== "ok" || !result.data) throw new Error(operationError(result));
    const service = connectedModelService(result.data.items);
    if (!service?.service_id) throw new Error(zh() ? "请先在 AI 与模型连接可用服务。" : "Connect an available service in AI & Models first.");
    return service.service_id;
  };

  const studyOperation = async (action: "start" | "status" | "resume" | "cancel") => {
    const studyId = currentStudyId();
    if (!studyId || (action === "start" && !selectionConfirmed())) return;
    const args: Record<string, unknown> = { study_id: studyId, analysis_protocol_id: STYLE_LEARNING_PROTOCOL, user_authorized: true };
    if (action === "start" || action === "resume") {
      if (!operations().includes("model.service.list")) return;
      try {
        args.service_id = await connectedService();
        args.execute_semantic = true;
        // One click advances a bounded semantic research cycle. This is an
        // execution budget, not a claim that every pool member must be read.
        args.max_jobs = 8;
      } catch (cause) {
        setError(message(cause));
        return;
      }
    }
    await run(`corpus.study.${action}`, args, (data) => { setStudyResult(parseCorpusRecord(data)); });
  };

  const previewPack = async () => {
    const studyId = currentStudyId();
    if (!studyId) return;
    await run("corpus.pack.preview", { study_id: studyId }, (data) => {
      setPackPreview(parseCorpusRecord(data));
      setActivationResult(undefined);
    });
  };

  const activatePack = async () => {
    const studyId = currentStudyId();
    const projectId = studio.projectId();
    if (!studyId || !projectId || !packPreview()) return;
    await run("corpus.pack.activate", {
      project_id: projectId,
      study_id: studyId,
      applicability: { scope: "project", profile: studyProfile() },
      expected_version: 0,
      idempotency_key: `activate:${projectId}:${studyId}`,
      user_authorized: true,
    }, (data) => setActivationResult(parseCorpusRecord(data)));
  };

  onCleanup(() => { disposed = true; generation += 1; });

  return (
    <section class="nf-page qf-research-page">
      <PageIntro eyebrow="RESEARCH & CORPUS" title={zh() ? "研究是证据，不是 Canon。" : "Research is evidence, not Canon."} body={zh() ? "从用户有权使用的本地副本建立精确来源池。Core 提出动态的最小充分 cohort；先完成黄金三章预览并暂停，确认后才继续全量拆解。Studio 不展示小说全文，Writer 只接收 source-free 机制投影。" : "Build an exact source pool from local copies you may use. Core proposes a dynamic minimal sufficient cohort, pauses after the Golden Three preview, and continues only after confirmation. Studio never displays novel prose; Writer receives only source-free mechanism projections."} />
      <Show when={error()}>{(value) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><span class="wui-alert__description">{value()}</span></div></div>}</Show>

      <section class="qf-editorial-sheet" aria-labelledby="local-corpus-title">
        <div class="qf-section-head"><div><h2 id="local-corpus-title">{zh() ? "1 · 扫描本地语料副本" : "1 · Scan local corpus copies"}</h2><p>{zh() ? "扫描只在本地宿主执行。先声明权利依据；analysis_only 不会获得公开发布全文的权限。" : "Scanning runs only on a local host. Declare the rights basis first; analysis_only never grants permission to publish full text."}</p></div><AuthorityLabel value={localCorpusAvailable() ? "local_only" : "local_host_required"} /></div>
        <CoreRequirementNotice operation="corpus.collection.scan" compact />
        <Show when={studio.surface() === "hosted_web"}><aside class="qf-awaiting-core" role="status"><div><strong>local_path_forbidden</strong><code>corpus.collection.scan</code></div><p>{zh() ? "Web Studio 不接收、保存或转发电脑路径。请在桌面 Studio 扫描，再在 Web 中使用 Core 返回的 collection_id。" : "Web Studio never accepts, stores or forwards workstation paths. Scan in desktop Studio, then use the Core-issued collection_id on the web."}</p></aside></Show>
        <label class="nf-field-label"><span>{zh() ? "本地文件夹路径" : "Local folder path"}</span><input class="wui-input" value={collectionPath()} disabled={!localCorpusAvailable() || !!busy()} onInput={(event) => setCollectionPath(event.currentTarget.value)} placeholder="C:\\Users\\…\\范文" /></label>
        <div class="qf-intent-fields"><label class="nf-field-label"><span>{zh() ? "权利类别" : "Rights class"}</span><select class="wui-input" value={rightsClass()} disabled={!localCorpusAvailable() || !!busy()} onChange={(event) => setRightsClass(event.currentTarget.value as "analysis_only" | "redistributable" | "unknown")}><option value="analysis_only">analysis_only</option><option value="redistributable">redistributable</option><option value="unknown">unknown</option></select></label><label class="nf-field-label"><span>{zh() ? "权利依据（必填）" : "Rights basis (required)"}</span><input class="wui-input" value={rightsBasis()} disabled={!localCorpusAvailable() || !!busy()} onInput={(event) => setRightsBasis(event.currentTarget.value)} placeholder={zh() ? "例如：本人购买并获授权作内部分析；不得再分发全文" : "Example: licensed for private analysis; full-text redistribution prohibited"} /></label></div>
        <button class="wui-button wui-button--solid" type="button" disabled={!localCorpusAvailable() || !!busy() || !collectionPath().trim() || !rightsBasis().trim()} onClick={() => void scanCollection()}>{zh() ? "扫描元数据，不公开全文" : "Scan metadata without publishing text"}</button>
        <Show when={scanResult()}>{(result) => <p role="status"><strong>{zh() ? "扫描结果" : "Scan result"}</strong> · {projectionCollectionId(result()) ?? "collection_id pending"} · {typeof (result().logical_works ?? result().work_count) === "number" ? `${String(result().logical_works ?? result().work_count)} works` : String(result().status ?? "ready")} · excluded: {countLabel(scanEligibility().excluded)} · quarantined: {countLabel(scanEligibility().quarantined)}</p>}</Show>
      </section>

      <section class="qf-editorial-sheet" aria-labelledby="selection-title">
        <div class="qf-section-head"><div><h2 id="selection-title">{zh() ? "2 · 生成并确认动态来源池" : "2 · Propose and confirm a dynamic source pool"}</h2><p>{zh() ? "Core 默认提出最多 24 部的最小 cohort；你可以缩小选择。确认会绑定研究 profile、成员清单和 exact proposal fingerprint。" : "Core proposes a minimal cohort of up to 24 works by default, and you may narrow it. Confirmation binds the study profile, membership and exact proposal fingerprint."}</p></div><AuthorityLabel value={selection() ? "review" : "proposal"} /></div>
        <label class="nf-field-label"><span>{zh() ? "研究内容分级 profile" : "Study content profile"}</span><select class="wui-input" value={studyProfile()} disabled={!!busy()} onChange={(event) => { setStudyProfile(event.currentTarget.value as CorpusProfile); setSelection(undefined); setSelectedWorkIds([]); setRightsScopeAcknowledged(false); setStudyResult(undefined); }}><option value="general">general</option><option value="adult_explicit">adult_explicit</option></select></label>
        <label class="nf-field-label"><span>{zh() ? "新建清单的 collection_id" : "collection_id for a new list"}</span><input class="wui-input" value={collectionId()} disabled={!!busy()} onInput={(event) => setCollectionId(event.currentTarget.value)} /></label>
        <button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !collectionId().trim() || !operations().includes("corpus.selection.propose")} onClick={() => void proposeSelection()}>{zh() ? "生成最小充分研究清单" : "Propose a minimal sufficient cohort"}</button>
        <Show when={studio.surface() === "local_app"}><div><label class="nf-field-label"><span>{zh() ? "加载既有 proposal 的 study_id" : "study_id of an existing proposal"}</span><input class="wui-input" value={existingStudyId()} disabled={!!busy()} onInput={(event) => setExistingStudyId(event.currentTarget.value)} /></label><button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !existingStudyId().trim() || !operations().includes("corpus.selection.propose")} onClick={() => void loadExistingSelection()}>{zh() ? "加载既有动态清单（不确认）" : "Load an existing dynamic cohort (no confirmation)"}</button><p>{zh() ? "加载会以 study_id + profile 幂等重放现有 proposal。本地宿主只把书名与作者临时合并进确认清单；relative locator 不会渲染或写入浏览器持久状态。" : "Loading idempotently replays the existing proposal with study_id + profile. The local host merges only labels and creators into this temporary checklist; relative locators are neither rendered nor persisted by the browser."}</p></div></Show>
        <Show when={studio.surface() === "hosted_web"}><p>{zh() ? "Web 端只显示匿名 public_work_id，不请求本地书名、作者或 locator。" : "The web view uses anonymous public_work_id values and never requests local labels, creators or locators."}</p></Show>
        <Show when={selection()}>{(proposal) => <>
          <p class="nf-mono">{proposal().study_id} · status: {proposal().status ?? "unknown"} · profile: {proposal().profile} · {selectedWorkIds().length}/{proposal().items.length} in pool · {proposal().proposal_fingerprint}</p>
          <p>{zh() ? "资格聚合" : "Eligibility aggregates"} · excluded: {countLabel(proposal().eligibility_counts.excluded)} · quarantined: {countLabel(proposal().eligibility_counts.quarantined)}</p>
          <p>{zh() ? "成员勾选只表示纳入可用来源池，不表示该作品已经完成文学审查，也不要求 AI 最终使用每一部。" : "Membership checks include works in the available source pool. They do not mean a literary review is complete, and AI is not required to use every work."}</p>
          <Show when={proposal().status === "proposed"}>
            <button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !operations().includes("corpus.selection.refresh")} onClick={() => void refreshSelection()}>{zh() ? "按当前规则原位刷新此 V5 proposal" : "Refresh this V5 proposal under current rules"}</button>
            <p>{zh() ? "刷新要求绑定上方旧 hash，只替换尚未确认的成员与 hash；study_id、public_study_id、profile 和 seed 保持不变。" : "Refresh binds the old hash and replaces only unconfirmed membership and its hash; study_id, public_study_id, profile and seed stay unchanged."}</p>
          </Show>
          <div class="qf-learning-list" aria-label={zh() ? "语料研究可用来源池" : "Corpus research available source pool"}><For each={proposal().items}>{(item, index) => <article><label class="qf-inline-actions"><input type="checkbox" checked={selected(item.work_id)} disabled={!!busy() || proposal().status !== "proposed"} onChange={(event) => toggleWork(item.work_id, event.currentTarget.checked)} /><span><strong>{index() + 1}. {item.title}</strong><small class="nf-mono">{item.creator ?? "—"} · {item.rights_class ?? "rights recorded by Core"} · {item.work_id}</small></span></label></article>}</For></div>
          <Show when={proposal().status === "proposed"}><label class="qf-inline-actions"><input type="checkbox" checked={rightsScopeAcknowledged()} disabled={!!busy()} onChange={(event) => setRightsScopeAcknowledged(event.currentTarget.checked)} /><span>{zh() ? "我确认上方 exact 来源池适用已声明的分析权利与研究 profile；完整原文继续留在本地，不进入 Git 或公开制品。" : "I confirm that the declared analysis rights and study profile apply to the exact source pool above; complete source text remains local and never enters Git or a public artifact."}</span></label></Show>
          <button class="wui-button wui-button--solid" type="button" disabled={!!busy() || !rightsScopeAcknowledged() || proposal().status !== "proposed" || selectedWorkIds().length < 1 || !operations().includes("corpus.selection.confirm")} onClick={() => void confirmSelection()}>{zh() ? `确认已选 ${selectedWorkIds().length} 部并绑定上方 hash` : `Confirm ${selectedWorkIds().length} selected works and bind the hash above`}</button>
          <Show when={proposal().status !== "proposed"}><p role="status">{zh() ? "该 study 已不处于 proposed 状态；来源池仅供查看，不能再次确认。" : "This study is no longer proposed. The source pool is view-only and cannot be confirmed again."}</p></Show>
        </>}</Show>
      </section>

      <section class="qf-editorial-sheet" aria-labelledby="study-title">
        <div class="qf-section-head"><div><h2 id="study-title">{zh() ? "3 · AI 文风研究" : "3 · AI prose-style research"}</h2><p>{zh() ? "目标：自适应。AI-native 设计让 AI 判断场景功能与文风维度、发现证据缺口、请求下一批最小充分作品／场景功能证据，并判断跨作品结论是否收敛；动态作品调度只有在 Core 回执明确报告后才算已实现。确定性运行时只把场景功能当检索提示，负责绑定来源身份、物化有界片段、拒绝污染窗口并记录回执，不作文学判断。语言、完整性和拼接信号只缩窄证据范围。普通身材与外貌描写继续属于 general craft。" : "Target: adaptive. The AI-native design assigns scene/style classification, evidence gaps, requests for the next minimum-sufficient work/scene-function evidence, and cross-work convergence to AI; dynamic work scheduling is implemented only when the Core receipt explicitly reports it. The deterministic runtime treats scene functions only as retrieval hints while binding source identity, materializing bounded passages, rejecting contaminated windows and recording receipts; it makes no literary judgment. Language, completeness and concatenation signals narrow evidence scope rather than fail the pool, while ordinary body and appearance description remains general craft."}</p></div><AuthorityLabel value={progress()?.status ?? "not_started"} /></div>
        <CoreRequirementNotice operation="corpus.study.status" compact />
        <Show when={progress()}>{(value) => <div><p><strong>{zh() ? "AI 研究状态" : "AI research state"}</strong> · {value().status} · {zh() ? "兼容作品计数" : "compatibility work count"}: {value().compatibility_work_count} · {zh() ? "可用池" : "available pool"}: {countLabel(value().available_pool_count ?? selection()?.items.length)} · {zh() ? "已激活" : "activated"}: {countLabel(value().activated_count)} · {zh() ? "已分析" : "analysed"}: {countLabel(value().analysed_count)} · {zh() ? "语义调用" : "semantic attempts"}: {countLabel(value().semantic_attempts)}</p><p>{zh() ? "兼容作品计数只用于恢复与审计；它不是证据覆盖率或文学质量分数。" : "The compatibility work count supports recovery and audit only; it is not an evidence-coverage or literary-quality score."}</p></div>}</Show>
        <Show when={styleRunner()}>{(runner) => <details open><summary>{zh() ? "AI 研究回执状态（不含原文）" : "AI research receipt state (no source prose)"}</summary><pre>{JSON.stringify(corpusMetadataView({
          analysis_protocol_id: runner().analysis_protocol_id,
          phase: runner().phase,
          result_state: runner().result_state,
          work_count: runner().work_count,
          work_states: runner().work_states,
          cohort_cycle: runner().cohort_cycle,
          cohort_states: runner().cohort_states ?? (zh() ? "Core 未报告" : "not reported by Core"),
          sample_states: runner().sample_states,
          axis_states: runner().axis_states,
          claim_states: runner().claim_states,
          semantic_attempts: runner().semantic_attempts,
          axis_reconciliation: runner().axis_reconciliation ?? (zh() ? "Core 未报告" : "not reported by Core"),
          axis_reconciliation_execution: runner().axis_reconciliation_execution ?? (zh() ? "Core 未报告" : "not reported by Core"),
          missing_gates: isRecord(runner().candidate_bundle) ? (runner().candidate_bundle as Record<string, unknown>).missing_gates : undefined,
        }), null, 2)}</pre></details>}</Show>
        <p>{zh() ? "每次开始或继续会推进一轮有界语义研究；预算暂停不等于失败。以充分证据停止是目标，而不是把遍历全池当作质量门。只有 Core 回执中的 dynamic_work_cohort_implemented 明确为 true 时，Studio 才会显示这项动态能力已经实现；字段缺失则如实显示“Core 未报告”。" : "Each start or continue action advances one bounded semantic research cycle; a budget pause is not failure. Stopping on sufficient evidence is the target, rather than treating full-pool traversal as a quality gate. Studio shows dynamic cohort scheduling as implemented only when the Core receipt explicitly reports dynamic_work_cohort_implemented as true; a missing field is shown as not reported."}</p>
        <div class="qf-inline-actions"><button class="wui-button wui-button--solid" type="button" disabled={!!busy() || !selectionConfirmed() || !operations().includes("corpus.study.start") || !operations().includes("model.service.list")} onClick={() => void studyOperation("start")}>{zh() ? "开始 AI 文风研究" : "Start AI prose-style research"}</button><button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !currentStudyId() || !operations().includes("corpus.study.status")} onClick={() => void studyOperation("status")}>{zh() ? "刷新证据状态" : "Refresh evidence state"}</button><button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !currentStudyId() || !operations().includes("corpus.study.resume") || !operations().includes("model.service.list")} onClick={() => void studyOperation("resume")}>{zh() ? "继续 AI 文风研究" : "Continue AI prose-style research"}</button><button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !currentStudyId() || !operations().includes("corpus.study.cancel")} onClick={() => void studyOperation("cancel")}>{zh() ? "只取消本次分析" : "Cancel this analysis only"}</button></div>
      </section>

      <section class="qf-editorial-sheet" aria-labelledby="source-free-pack-title">
        <div class="qf-section-head"><div><h2 id="source-free-pack-title">{zh() ? "4 · 预览并激活 source-free Writer Pack" : "4 · Preview and activate a source-free Writer Pack"}</h2><p>{zh() ? "完整研究只会生成抽象的读者需求、情绪链、戏剧功能、可替换槽位、禁抄元素与节奏指导。Writer 看不到来源作品身份、路径、引文或可复刻片段。" : "A completed study yields only abstract reader needs, emotion chains, dramatic functions, replaceable slots, forbidden-copy elements, and rhythm guidance. Writer sees no source identity, path, quotation, or imitation-ready passage."}</p></div><AuthorityLabel value={activationResult() ? "active" : packPreview() ? "preview_only" : "not_prepared"} /></div>
        <div class="qf-inline-actions"><button class="wui-button wui-button--outline" type="button" disabled={!!busy() || !currentStudyId() || !operations().includes("corpus.pack.preview")} onClick={() => void previewPack()}>{zh() ? "预览无来源 Writer Pack" : "Preview source-free Writer Pack"}</button><button class="wui-button wui-button--solid" type="button" disabled={!!busy() || !packPreview() || !studio.projectId() || !operations().includes("corpus.pack.activate")} onClick={() => void activatePack()}>{zh() ? "确认激活到当前 Project" : "Confirm activation for this Project"}</button></div>
        <Show when={packPreview()}>{(value) => <details open><summary>{zh() ? "Writer 可见投影" : "Writer-visible projection"}</summary><pre>{JSON.stringify(corpusMetadataView(value()), null, 2)}</pre></details>}</Show>
        <Show when={activationResult()}>{(value) => <p role="status"><strong>{zh() ? "已激活" : "Activated"}</strong> · {String(value().pack_fingerprint ?? "source-free pack")} · version {String(value().version ?? "—")}</p>}</Show>
      </section>

      <section class="qf-editorial-sheet">
        <h2>{zh() ? "Project 内证据搜索" : "Search evidence inside the Project"}</h2>
        <form class="qf-search-line" onSubmit={(event) => { event.preventDefault(); void search(); }}><label class="nf-field-label"><span>{zh() ? "搜索 Project evidence" : "Search Project evidence"}</span><input class="wui-input" value={query()} onInput={(event) => setQuery(event.currentTarget.value)} /></label><button class="wui-button wui-button--solid" disabled={!!busy() || !query().trim() || !studio.projectId()}>{busy() === "project.search" ? (zh() ? "搜索中…" : "Searching…") : (zh() ? "搜索" : "Search")}</button></form>
        <div class="qf-search-results" aria-live="polite"><For each={rows()}>{(row) => <article><div><strong>{row.title}</strong><span class="qf-authority-label">evidence</span></div><small class="nf-mono">{row.entity_type} · {row.entity_id}</small><p>{row.snippet}</p></article>}</For><Show when={!rows().length && query()}><p>{zh() ? "没有返回结果。" : "No results returned."}</p></Show></div>
      </section>
    </section>
  );
}
