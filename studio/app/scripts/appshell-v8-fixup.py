from pathlib import Path

p = Path('studio/app/src/AppShell.tsx')
text = p.read_text(encoding='utf-8')

text = text.replace(
'''  type AuthorRunStartResult,
  type AuthoringIntent,
  type ContextRuntimeProjection,
  type InspectorListProjection,
''',
'''  type AuthorRunStartResult,
  type AuthorRunStatusProjection,
  type AuthoringIntent,
  type ContextRuntimeProjection,
  type ModelServiceListProjection,
  type ProductionExecutionProjection,
''')

text = text.replace(
'''  "project.create": "/start",
  "project.inspect": "/",
  "document.create": "/manuscript",
  "document.revision.save": "/manuscript",
  "document.revision.compare": "/manuscript",
  "author.run.start": "/manuscript",
  "inspector.context.runtime": "/context",
  "inspector.runs.list": "/runtime",
  "inspector.candidates.list": "/review",
  "candidate.accept": "/review",
  "settlement.apply": "/review",
  "publication.preview": "/publication",
  "publication.build": "/publication",
''',
'''  "project.create": "/start",
  "project.list": "/start",
  "project.inspect": "/",
  "document.create": "/manuscript",
  "document.list": "/manuscript",
  "document.open": "/manuscript",
  "document.revision.save": "/manuscript",
  "document.revision.compare": "/manuscript",
  "author.run.start": "/manuscript",
  "author.run.status": "/runtime",
  "author.run.execute": "/manuscript",
  "inspector.context.runtime": "/context",
  "inspector.runs.list": "/runtime",
  "inspector.candidates.list": "/review",
  "candidate.review.get": "/review",
  "candidate.accept": "/review",
  "candidate.reject": "/review",
  "candidate.revision.request": "/review",
  "settlement.preflight": "/review",
  "settlement.apply": "/review",
  "model.service.add": "/settings?section=models",
  "model.service.list": "/settings?section=models",
  "publication.preview": "/publication",
  "publication.build": "/publication",
''')

text = text.replace(
'''  const [run, setRun] = createSignal<AuthorRunStartResult>();
  const [runStatus, setRunStatus] = createSignal("");
  const [contextProjection, setContextProjection] = createSignal<ContextRuntimeProjection>();
''',
'''  const [run, setRun] = createSignal<AuthorRunStartResult>();
  const [runStatus, setRunStatus] = createSignal("");
  const [productionStatus, setProductionStatus] = createSignal<string>();
  const [readerGrip, setReaderGrip] = createSignal<"low" | "medium" | "high" | "very_high">("high");
  const [contextProjection, setContextProjection] = createSignal<ContextRuntimeProjection>();
''')

text = text.replace(
'''  const currentDocument = () => new URLSearchParams(location.search).get("document")?.trim() || undefined;
''',
'''  const currentDocument = () => {
    const fromUrl = new URLSearchParams(location.search).get("document")?.trim();
    if (fromUrl) return fromUrl;
    const projectId = currentProject();
    if (!projectId || typeof localStorage === "undefined") return undefined;
    return localStorage.getItem(`quillframe.ui.lastDocumentId:${projectId}`)?.trim() || undefined;
  };
''')

marker = '''  const refreshRunEvidence = async () => {
'''
execute = '''  const executeRun = async () => {
    const projectId = currentProject();
    const activeRun = run();
    const runId = activeRun?.run_id || studio.lastRunId();
    if (!projectId || !runId || !instruction().trim()) return;
    if (activeRun && !["DRAFT", "REVISE"].includes(activeRun.task_mode)) {
      setAiError(zh() ? "当前 production executor 只拥有 DRAFT / REVISE；AUDIT / RESEARCH 必须使用各自 Core contract。" : "The production executor owns DRAFT / REVISE only; AUDIT / RESEARCH require their own Core contracts.");
      return;
    }
    setAiBusy(true);
    setAiError(undefined);
    try {
      const services = await invokeBridge<ModelServiceListProjection>("model.service.list");
      if (services.status !== "ok" || !services.data) throw new Error(operationError(services));
      const service = services.data.items.find((item) => item.credential_present && item.service_id);
      if (!service?.service_id) throw new Error(zh() ? "没有带可用 credential 的 Model Service。请先到 AI 与模型连接 Endpoint + Access Token。" : "No Model Service with a usable credential is connected. Add Endpoint + Access Token in AI & Models first.");
      const response = await invokeBridge<ProductionExecutionProjection>("author.run.execute", {
        project_id: projectId,
        run_id: runId,
        service_id: service.service_id,
        instruction: instruction().trim(),
        document_id: currentDocument(),
        reader_grip: readerGrip(),
        rule_material: [{
          id: "studio-current-request",
          authority: "current_request",
          statement: instruction().trim(),
        }],
      });
      if (response.status !== "ok" || !response.data) throw new Error(operationError(response));
      setProductionStatus(response.data.status);
      setRunStatus(response.data.status);
      await refreshRunEvidence();
    } catch (error) {
      setAiError(error instanceof Error ? error.message : String(error));
    } finally {
      setAiBusy(false);
    }
  };

'''
if execute.strip() not in text:
    text = text.replace(marker, execute + marker, 1)

old_refresh = '''      if (supported().includes("inspector.runs.list")) {
        const response = await invokeBridge<InspectorListProjection<{ run_id: string; status?: string }>>("inspector.runs.list", { project_id: projectId });
        if (response.status === "ok" && response.data) {
          const persisted = response.data.items.find((item) => item.run_id === runId);
          if (persisted?.status) setRunStatus(persisted.status);
        }
      }
'''
new_refresh = '''      if (supported().includes("author.run.status")) {
        const response = await invokeBridge<AuthorRunStatusProjection>("author.run.status", { project_id: projectId, run_id: runId });
        if (response.status === "ok" && response.data) setRunStatus(response.data.status);
      }
'''
text = text.replace(old_refresh, new_refresh)

old_ui = '''          <button class="wui-button wui-button--solid" type="button" disabled={aiBusy() || !currentProject() || !instruction().trim() || !supported().includes("author.run.start")} onClick={() => void startRun()}>{aiBusy() ? (zh() ? "处理中…" : "Working…") : (zh() ? "启动 Core Run" : "Start Core run")}</button>
          <CoreRequirementNotice operation="author.run.start" compact />
'''
new_ui = '''          <div class="qf-inline-actions">
            <button class="wui-button wui-button--solid" type="button" disabled={aiBusy() || !currentProject() || !instruction().trim() || !supported().includes("author.run.start")} onClick={() => void startRun()}>{aiBusy() ? (zh() ? "处理中…" : "Working…") : (zh() ? "注册 Core Run" : "Register Core run")}</button>
            <button class="wui-button wui-button--outline" type="button" disabled={aiBusy() || !(run()?.run_id || studio.lastRunId()) || !instruction().trim() || !supported().includes("author.run.execute") || !supported().includes("model.service.list")} onClick={() => void executeRun()}>{zh() ? "Execute production" : "Execute production"}</button>
          </div>
          <label class="nf-field-label"><span>{zh() ? "Reader grip（本次请求）" : "Reader grip (this request)"}</span><select class="wui-input" value={readerGrip()} onChange={(event) => setReaderGrip(event.currentTarget.value as "low" | "medium" | "high" | "very_high")}><option value="medium">medium</option><option value="high">high</option><option value="very_high">very_high</option><option value="low">low</option></select></label>
          <CoreRequirementNotice operation="author.run.start" compact />
          <CoreRequirementNotice operation="author.run.execute" compact />
'''
text = text.replace(old_ui, new_ui)

text = text.replace(
'''              <CoreRequirementNotice operation="run.events.list" compact />
''',
'''              <CoreRequirementNotice operation="author.run.status" compact />
              <Show when={productionStatus() === "awaiting_external"}><p class="qf-success-note">{zh() ? "已到真实 independent handoff boundary；Studio 不会用同一 runtime 自审替代外部独立审查。" : "Reached the real independent handoff boundary; Studio will not substitute same-runtime self-review for external independent review."}</p></Show>
''')

p.write_text(text, encoding='utf-8')
