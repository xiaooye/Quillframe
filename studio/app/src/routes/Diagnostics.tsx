import { Show, createSignal, onMount } from "solid-js";
import { PageIntro, CoreHostBoundary, JsonBlock } from "../components";
import { useI18n } from "../i18n";
import { useStudio } from "../studio";
import { invokeBridge, operationError } from "../bridge";

type DoctorResult = {
  schema?: string;
  ok?: boolean;
  fix?: boolean;
  data_root?: string;
  checks?: Array<{ check?: string; status?: string; detail?: unknown; error?: string }>;
  errors?: string[];
};

export default function Diagnostics() {
  const { locale } = useI18n();
  const studio = useStudio();
  const zh = () => locale() === "zh-CN";
  const [result, setResult] = createSignal<DoctorResult>();
  const [error, setError] = createSignal<string>();
  const [loading, setLoading] = createSignal(false);

  const runDoctor = async () => {
    if (!studio.bridgeAvailable() || !studio.bridgeCapabilities()?.operations.includes("database.doctor")) return;
    setLoading(true); setError(undefined);
    try {
      const response = await invokeBridge<DoctorResult>("database.doctor", studio.projectId() ? { project_id: studio.projectId(), fix: false } : { fix: false });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setResult(response.data);
    } catch (cause) { setResult(undefined); setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { setLoading(false); }
  };

  onMount(() => { if (studio.bridgeAvailable()) void runDoctor(); });

  return (
    <section class="nf-page qf-diagnostics-page">
      <PageIntro eyebrow="INSPECTOR · DIAGNOSTICS" title={zh() ? "诊断读取 Core，不修写作语义。" : "Diagnostics read Core state; they do not repair story semantics."} body={zh() ? "当前可见诊断只调用 typed database.doctor(fix=false)。Studio 不直接读 SQLite，也不会把 doctor 结果解释成 literary quality、Canon readiness 或 production readiness。" : "The visible diagnostic surface calls typed database.doctor(fix=false) only. Studio never reads SQLite directly or interprets doctor output as literary quality, Canon readiness or production readiness."} actions={studio.bridgeAvailable() ? <button class="wui-button wui-button--outline" type="button" disabled={loading()} onClick={() => void runDoctor()}>{loading() ? (zh() ? "检查中…" : "Checking…") : (zh() ? "重新检查" : "Run doctor")}</button> : undefined} />
      <Show when={studio.bridgeAvailable()} fallback={<CoreHostBoundary />}>
        <Show when={error()}>{(message) => <div class="wui-alert" role="alert"><div class="wui-alert__body"><strong class="wui-alert__title">database.doctor</strong><span class="wui-alert__description">{message()}</span></div></div>}</Show>
        <Show when={result()} fallback={<div class="qf-empty-workspace"><strong>{zh() ? "尚无 Doctor evidence" : "No doctor evidence yet"}</strong></div>}>
          {(doctor) => <section class="qf-editorial-sheet"><div class="qf-section-head"><div><span class="nf-eyebrow">CORE EVIDENCE</span><h2>{doctor().ok ? (zh() ? "数据库检查通过" : "Database checks passed") : (zh() ? "存在诊断问题" : "Diagnostic issues present")}</h2></div><span class="qf-authority-label">authority=false</span></div><div class="qf-runtime-columns"><section><header><span>CHECKS</span><strong>{doctor().checks?.length ?? 0}</strong></header>{doctor().checks?.map((check) => <article><strong>{check.check ?? "check"}</strong><span>{check.status ?? "unknown"}</span><small>{check.error ?? ""}</small></article>)}</section><section><header><span>ERRORS</span><strong>{doctor().errors?.length ?? 0}</strong></header>{doctor().errors?.map((item) => <article><span>{item}</span></article>)}</section></div><details class="qf-context-fingerprints"><summary>{zh() ? "原始 typed evidence" : "Raw typed evidence"}</summary><JsonBlock value={doctor()} label={doctor().schema ?? "database.doctor"} /></details></section>}
        </Show>
      </Show>
    </section>
  );
}
