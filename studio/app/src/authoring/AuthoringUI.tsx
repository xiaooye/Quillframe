import { For, Show } from "solid-js";
import { CORE_CONSUMER_REQUIREMENTS, RUN_PROGRESS_STAGES, type ContextRuntimeProjection, type RunProgressStageId } from "./contracts";
import { useStudio } from "../studio";

export function AuthorityLabel(props: { value: string; detail?: string }) {
  return (
    <span class="qf-authority-label" data-authority={props.value} title={props.detail}>
      <span aria-hidden="true">✦</span>
      <span>{props.value}</span>
    </span>
  );
}

export function CoreRequirementNotice(props: { operation: string; compact?: boolean }) {
  const studio = useStudio();
  const requirement = CORE_CONSUMER_REQUIREMENTS.find((item) => item.operation === props.operation);
  const supported = () => studio.bridgeCapabilities()?.operations.includes(props.operation) ?? false;
  return (
    <Show when={!supported()}>
      <aside class="qf-awaiting-core" data-compact={props.compact ? "true" : undefined} role="status">
        <div>
          <strong>{studio.bridgeAvailable() ? "awaiting_external" : "Core unbound"}</strong>
          <code>{props.operation}</code>
        </div>
        <Show when={requirement}>
          {(item) => (
            <p>{item().whyUiCannotImplement}</p>
          )}
        </Show>
      </aside>
    </Show>
  );
}

export function RunProgress(props: { completed?: RunProgressStageId[]; current?: RunProgressStageId | null; waiting?: boolean; zh?: boolean }) {
  const completed = () => new Set(props.completed ?? []);
  return (
    <ol class="qf-run-progress" aria-label={props.zh ? "Agent Run 进度" : "Agent run progress"}>
      <For each={RUN_PROGRESS_STAGES}>
        {(stage) => {
          const state = () => completed().has(stage.id) ? "complete" : props.current === stage.id ? "current" : "pending";
          return (
            <li data-state={state()}>
              <span class="qf-run-progress__mark" aria-hidden="true">{state() === "complete" ? "✓" : state() === "current" ? "•" : "○"}</span>
              <span>{props.zh ? stage.zh : stage.en}</span>
              <span class="sr-only">{state()}</span>
            </li>
          );
        }}
      </For>
      <Show when={props.waiting}>
        <li class="qf-run-progress__waiting" data-state="waiting">{props.zh ? "等待 Core runtime evidence；不会根据时间推断步骤已完成。" : "Waiting for Core runtime evidence; Studio never infers completed stages from elapsed time."}</li>
      </Show>
    </ol>
  );
}

function displayObjectId(value: string): string {
  const parts = value.split(/[/:]/).filter(Boolean);
  return parts.at(-1) || value;
}

export function WriterContextStrip(props: { projection?: ContextRuntimeProjection; zh?: boolean }) {
  const loaded = () => props.projection?.items.filter((item) => item.state === "loaded") ?? [];
  const considered = () => props.projection?.items.filter((item) => ["eligible", "considered", "selected", "dropped_due_budget"].includes(item.state)) ?? [];
  return (
    <section class="qf-writer-context" aria-label={props.zh ? "当前 Context" : "Current Context"}>
      <div class="qf-writer-context__head">
        <strong>Context</strong>
        <span>{props.zh ? `${loaded().length} 项实际加载` : `${loaded().length} actually loaded`}</span>
      </div>
      <div class="qf-writer-context__chips">
        <For each={loaded().slice(0, 6)}>
          {(item) => <span class="qf-context-chip" data-state="loaded">{displayObjectId(item.source_object_id)} <small>Loaded</small></span>}
        </For>
        <Show when={!loaded().length}><span class="qf-context-empty">{props.zh ? "尚无 Core freeze evidence" : "No Core freeze evidence yet"}</span></Show>
      </div>
      <details>
        <summary>{props.zh ? "为什么使用这些？" : "Why these?"}</summary>
        <p>{props.zh ? "只有 state=loaded 的对象才表示实际进入该阶段。Considered/Selected 不是 Loaded。" : "Only state=loaded means the object actually entered this stage. Considered/Selected is not Loaded."}</p>
        <Show when={considered().length}>
          <div class="qf-context-considered">
            <strong>{props.zh ? "MODEL CONSIDERED RELEVANT / 未必加载" : "MODEL CONSIDERED RELEVANT / NOT NECESSARILY LOADED"}</strong>
            <For each={considered().slice(0, 8)}>{(item) => <span>{displayObjectId(item.source_object_id)} · {item.state}</span>}</For>
          </div>
        </Show>
      </details>
    </section>
  );
}
