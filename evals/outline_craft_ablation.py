"""Prepare a six-pair direct-realization ablation; never dispatch or judge.

One registered scene/context projection is shared by both arms of each case.
Each arm then makes exactly one direct Surface Writer call with identical
settings and causal constraints.  The only treatment is selected positive
craft guidance inside the Writer pack.  No Raw Draft or post-hoc humanizer is
created. Live execution requires a separately authorized, budgeted host.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from agent_runtime import AgentBudget, AgentJob, AgentResult
from harness.context_runtime import fingerprint
from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import make_contract_job, validate_result
from model_runtime.structured_output import validate_structured_text
from production_runtime.craft_guidance import (
    freeze_craft_library, materialize_writer_craft, selection_input, validate_craft_snapshot,
)
from production_runtime.repair import author_direction_evidence, materialize_author_objectives
from production_runtime.runtime import ProductionRunExecutor
from production_runtime.semantic import writer_safe_projection
from production_runtime.writer_context import (
    build_inventory as build_writer_inventory,
    materialize_writer_pack,
    model_inventory,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = Path(__file__).with_name("fixtures") / "outline_craft_ablation.json"
SCHEMA = "quillframe_outline_craft_evaluation_v2"
ARMS = ("baseline", "outline_driven")
STAGES = ("surface_realization",)
READER_FIELDS = {"genre_profile", "platform_profile", "chapter_position", "reader_grip"}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["status", "text", "summary", "findings"],
    "properties": {"status": {"type": "string", "enum": ["pass", "fail"]}, "text": {"type": "string"},
                   "summary": {"type": "string"}, "findings": {"type": "array", "items": {"type": "string"}}},
    "additionalProperties": False,
}
DISCLAIMER = "Synthetic held-out tasks; no gold labels, production release, Canon, taste activation or General Craft promotion."


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = fingerprint({key: item for key, item in value.items() if key != field})
    return value


def _check(value: dict[str, Any], field: str) -> None:
    _require(value.get(field) == fingerprint({key: item for key, item in value.items() if key != field}), field + " changed")


def load_suite(path: Path = DEFAULT_SUITE) -> dict[str, Any]:
    suite = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(suite.get("schema") == "quillframe_outline_craft_suite_v1", "invalid held-out suite")
    provenance = suite.get("provenance", {})
    _require(provenance.get("authorship") == "original_synthetic_assistant_authored" and all(
        provenance.get(key) is False for key in ("derived_from_consumer", "derived_from_external_prose",
                                                "human_quality_validated", "market_evidence")), "invalid provenance")
    _require(_nonempty(suite.get("generation_request")), "generation request missing")
    cases = suite.get("cases")
    _require(isinstance(cases, list) and len(cases) == 6, "six held-out cases required")
    seen: set[str] = set()
    for case in cases:
        identity = case.get("case_id")
        _require(_nonempty(identity) and identity not in seen, "duplicate or missing case")
        seen.add(identity)
        _require(set(case.get("reader_context", {})) == READER_FIELDS, "only explicit reader fields are allowed")
        _require(all(_nonempty(value) for value in case["reader_context"].values()), "empty reader declaration")
        _require(set(case.get("planning", {})) == {"overall_outline", "chapter_outline", "scene_details"}
                 and all(_nonempty(value) for value in case["planning"].values()), "three current planning levels required")
        _require(isinstance(case.get("writer_safe_facts"), list) and bool(case["writer_safe_facts"])
                 and all(_nonempty(value) for value in case["writer_safe_facts"]), "writer-safe facts required")
        _require(isinstance(case.get("pov_boundary"), dict), "explicit POV boundary required")
    return suite


def prepare_evaluation(*, run_id: str, order_seed: str, service_id: str, model_id: str,
                       reasoning_effort: str, suite_path: Path = DEFAULT_SUITE,
                       created_at: str | None = None) -> dict[str, Any]:
    """Freeze six selection jobs and all positive resources. Zero model calls."""
    _require(all(_nonempty(value) for value in (run_id, order_seed, service_id, model_id, reasoning_effort)),
             "explicit run, ordering seed and host model settings required")
    suite = load_suite(suite_path)
    snapshot = freeze_craft_library("outline_driven")
    when = created_at or datetime.now(timezone.utc).isoformat()
    cases = []
    for original in suite["cases"]:
        case = deepcopy(original)
        alias = "SCENE-" + fingerprint([run_id, case["case_id"]])[7:23]
        planning_items = []
        for level, content in case["planning"].items():
            view = {"level": level, "text": content}
            planning_items.append({"object_id": alias + ":" + level, "object_type": "plan", "authority": "active_plan",
                                   "lifecycle": "active_plan", "source_fingerprint": fingerprint(view), "model_view": view})
        writer_items = []
        for index, fact in enumerate(case["writer_safe_facts"]):
            view = {"fact_id": f"{alias}:fact:{index + 1}", "fact": fact}
            writer_items.append({
                "object_id": view["fact_id"],
                "object_type": "world_fact",
                "authority": "accepted",
                "source_fingerprint": fingerprint(view),
                "model_view": view,
            })
        writer_inventory = build_writer_inventory(
            {"items": writer_items},
            character_action_evidence=[],
            author_model=None,
        )
        direction_evidence = author_direction_evidence(suite["generation_request"])
        payload = {"scene_id": alias, "resolved_trajectory": {"origin": "fixed_synthetic_task_constraints",
                   "interaction_trace": case["planning"]["scene_details"], "facts": case["writer_safe_facts"]},
                   "character_action_evidence": [], "pov_boundary": case["pov_boundary"],
                   "task_context": {"request": suite["generation_request"]},
                   "author_direction_evidence": direction_evidence,
                   "writer_context_inventory": model_inventory(writer_inventory),
                   **selection_input(snapshot, {"mechanism": "scene_simulation", "items": planning_items})}
        job = make_contract_job("scene.realization_project", alias, payload,
                                source_session_id="EVAL-" + run_id, handoff_id=run_id + ":" + alias)
        job["created_at"] = when
        case.update(
            alias=alias,
            selection_job=job,
            writer_context_inventory=writer_inventory,
            author_direction_evidence=direction_evidence,
        )
        cases.append(case)
    bindings = {}
    for path in (Path(__file__), ROOT / "production_runtime/runtime.py", ROOT / "production_runtime/craft_guidance.py",
                 ROOT / "production_runtime/repair.py", ROOT / "production_runtime/writer_context.py",
                 ROOT / "harness/semantic_workers/contracts/production-loop.json", Path(suite_path)):
        bindings[path.name] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    prepared = {"schema": SCHEMA, "run_id": run_id, "created_at": when, "order_seed": order_seed,
                "suite_fingerprint": fingerprint(suite), "source_file_fingerprints": bindings,
                "settings": {"service_id": service_id, "model_id": model_id, "reasoning_effort": reasoning_effort,
                             "sampling_binding": "provider_defaults_unpinned"},
                "planned_model_calls": 18, "craft_snapshot": snapshot, "cases": cases,
                "writer_instructions": {stage: ProductionRunExecutor._stage_instruction(stage, suite["generation_request"])
                                        for stage in STAGES},
                "status": "prepared_not_executed", "authority": False, "disclaimer": DISCLAIMER}
    return _seal(prepared, "plan_fingerprint")


def validate_prepared(prepared: dict[str, Any]) -> None:
    _require(prepared.get("schema") == SCHEMA and prepared.get("authority") is False, "invalid prepared evaluation")
    _check(prepared, "plan_fingerprint")
    validate_craft_snapshot(prepared["craft_snapshot"])
    _require(len(prepared["cases"]) == 6 and prepared["planned_model_calls"] == 18, "incomplete experiment")
    for case in prepared["cases"]:
        _require(not validate_registered_job(case["selection_job"]), "selection contract is no longer dispatchable")


def _case(prepared: dict[str, Any], case_id: str) -> dict[str, Any]:
    validate_prepared(prepared)
    found = [case for case in prepared["cases"] if case["case_id"] == case_id]
    _require(len(found) == 1, "unknown or duplicate case")
    return found[0]


def selector_job(prepared: dict[str, Any], case_id: str) -> dict[str, Any]:
    """Send only this registered job through the existing semantic executor."""
    return deepcopy(_case(prepared, case_id)["selection_job"])


def _validate_selection(prepared: dict[str, Any], case: dict[str, Any], binding: dict[str, Any]) -> None:
    _require(binding.get("job") == case["selection_job"], "selection belongs to another frozen job")
    result = binding.get("result", {})
    _require(result.get("status") == "completed" and not validate_result(binding["job"], result), "invalid selection result")
    _require(binding.get("binding_fingerprint") == fingerprint({"job": binding["job"], "result": result}), "selection binding changed")
    worker = result.get("worker", {})
    _require(worker.get("model_or_reviewer") == prepared["settings"]["model_id"]
             and worker.get("model_service_id") == prepared["settings"]["service_id"], "selection model or service differs")
    materialize_writer_craft(prepared["craft_snapshot"], result["judgment"]["craft_selection"],
                             projection_input=binding["job"]["input"]["payload"], binding_fingerprint=binding["binding_fingerprint"])


def _result_text(job: AgentJob, result: AgentResult) -> str:
    _require(result.job_id == job.job_id and result.session_id == job.session_id and result.run_id == job.run_id
             and result.input_fingerprint == job.input_fingerprint, "generation result is not bound to this job")
    _require(result.model_id == job.model_preference and result.model_service_id == job.service_id,
             "generation model or service differs")
    _require(result.status == "completed" and result.model_requests == 1 and result.tool_calls == 0, "generation did not complete one tool-free call")
    value = validate_structured_text(result.final_text, OUTPUT_SCHEMA)
    _require(value["status"] == "pass" and _nonempty(value["text"]), "failed or empty generation is not a blind sample")
    return value["text"]


def writer_job(prepared: dict[str, Any], case_id: str, arm: str, stage: str,
               projection_binding: dict[str, Any]) -> AgentJob:
    case = _case(prepared, case_id)
    _require(arm in ARMS and stage in STAGES, "unknown arm or stage")
    _validate_selection(prepared, case, projection_binding)
    projection = writer_safe_projection(projection_binding, scene_id=case["alias"])
    guidance = None
    if arm == "outline_driven":
        guidance = materialize_writer_craft(
            prepared["craft_snapshot"], projection_binding["result"]["judgment"]["craft_selection"],
            projection_input=projection_binding["job"]["input"]["payload"],
            binding_fingerprint=projection_binding["binding_fingerprint"])
    objectives = materialize_author_objectives(
        case["author_direction_evidence"],
        projection_binding["result"]["judgment"]["author_objective_items"],
    )
    pack = materialize_writer_pack(
        case["writer_context_inventory"],
        selected_context_ids=projection["selected_context_ids"],
        scene_contract=projection["scene_contract"],
        director_note=projection["director_note"],
        author_objectives=objectives,
        source_binding_fingerprint=projection_binding["binding_fingerprint"],
        craft_guidance=guidance,
    )
    context = [{
        "target_context": {
            "chapter_id": case["alias"],
            "document_id": case["alias"] + "-DOC",
            "current_story_order": 1,
            "current_reading_order": 1,
        },
        "writer_pack": pack,
    }]
    # Opaque IDs do not tell the Writer which experimental arm it received.
    identity = fingerprint([prepared["run_id"], case_id, arm, stage])[7:31]
    return AgentJob(job_id="craft-" + identity, session_id="EVAL-WRITER-" + identity,
                    run_id=prepared["run_id"], task_mode="DRAFT", runtime_role=stage,
                    service_id=prepared["settings"]["service_id"], model_preference=prepared["settings"]["model_id"],
                    instruction=prepared["writer_instructions"][stage], context=context, authority={},
                    required_model_capabilities={"text", "fiction_writing"},
                    budgets=AgentBudget(max_steps=1, max_model_requests=1, max_tool_calls=1, max_parallel_tool_calls=1,
                                        model_context_limit=200000, max_output_tokens=7000,
                                        run_cost_budget=10_000_000,
                                        max_elapsed_ms=600000, max_model_request_ms=600000),
                    idempotency_key="craft:" + identity)


def record_generation(prepared: dict[str, Any], *, case_id: str, arm: str, stage: str,
                      projection_binding: dict[str, Any], result: AgentResult,
                      host_receipt: dict[str, Any]) -> dict[str, Any]:
    """Keep exact host outputs/identity; a typed receipt is not proof of isolation."""
    job = writer_job(prepared, case_id, arm, stage, projection_binding)
    _result_text(job, result)
    _require(set(host_receipt) == {"host_run_ref", "request_ref", "evidence_class", "packet_only_context", "reasoning_effort"},
             "bounded host receipt required")
    _require(all(_nonempty(host_receipt[key]) for key in ("host_run_ref", "request_ref"))
             and host_receipt["evidence_class"] in ("live_model", "synthetic_test")
             and host_receipt["packet_only_context"] is True
             and host_receipt["reasoning_effort"] == prepared["settings"]["reasoning_effort"], "host settings or context attestation missing")
    record = {"case_id": case_id, "arm": arm, "stage": stage, "plan_fingerprint": prepared["plan_fingerprint"],
              "projection_binding_fingerprint": projection_binding["binding_fingerprint"],
              "job": job.to_dict(), "result": result.to_dict(), "host_receipt": deepcopy(host_receipt),
              "host_isolation_independently_verified": False, "production_release_eligible": False}
    return _seal(record, "record_fingerprint")


def _agent_result(value: dict[str, Any]) -> AgentResult:
    return AgentResult(**{key: value[key] for key in AgentResult.__dataclass_fields__ if key in value})


def blind_batches(prepared: dict[str, Any], *, selection_bindings: dict[str, dict[str, Any]],
                  records: list[dict[str, Any]], allow_synthetic: bool = False) -> list[dict[str, Any]]:
    """Export prose/profile only, two pairs at a time; never export the mapping."""
    validate_prepared(prepared)
    _require(len(records) == 12, "complete six-pair direct-Writer records required")
    indexed = {}
    seen_requests: set[tuple[str, str]] = set()
    for record in records:
        _check(record, "record_fingerprint")
        identity = (record["case_id"], record["arm"], record["stage"])
        _require(identity not in indexed, "duplicate generation record")
        indexed[identity] = record
        host = record["host_receipt"]
        request_ref = (host["host_run_ref"], host["request_ref"])
        _require(request_ref not in seen_requests, "host request reused for different samples")
        seen_requests.add(request_ref)
        _require(allow_synthetic or host["evidence_class"] == "live_model", "synthetic outputs cannot become live blind evidence")
    cases = sorted(prepared["cases"], key=lambda case: fingerprint([prepared["order_seed"], case["case_id"], "presentation"]))
    orientations = sorted(cases, key=lambda case: fingerprint([prepared["order_seed"], case["case_id"], "orientation"]))
    baseline_first = {case["case_id"] for case in orientations[:3]}
    pairs = []
    for case in cases:
        cid = case["case_id"]
        _require(cid in selection_bindings, "missing exact selection binding")
        texts = {}
        for arm in ARMS:
            for stage in STAGES:
                _require((cid, arm, stage) in indexed, "missing generation stage")
                record = indexed[(cid, arm, stage)]
                result = _agent_result(record["result"])
                expected = record_generation(prepared, case_id=cid, arm=arm, stage=stage,
                                             projection_binding=selection_bindings[cid], result=result,
                                             host_receipt=record["host_receipt"])
                _require(record == expected, "generation record changed or belongs to another plan")
                texts[arm] = json.loads(result.final_text)["text"]
        # Balance presentation order, while the salted permutation hides it.
        order = ARMS if cid in baseline_first else tuple(reversed(ARMS))
        pair_id = fingerprint([prepared["order_seed"], case["alias"], "blind"])[7:23]
        pairs.append({"pair_id": pair_id, "reader_context": deepcopy(case["reader_context"]),
                      "A": texts[order[0]], "B": texts[order[1]]})
    return [{"schema": "quillframe_craft_blind_batch_v1", "batch_id": f"batch-{i // 2 + 1}",
             "synthetic_test_only": allow_synthetic,
             "instructions": "逐组阅读 A、B。可选 A、B、平手、两版都不满意或证据不足；请说明具体读感并引用片段。这里只评价给出的正文，不猜测生成方法。",
             "pairs": pairs[i:i + 2]} for i in range(0, 6, 2)]


def human_observation(batch: dict[str, Any], *, pair_id: str, choice: str, reason: str,
                      reviewer_ref: str, prior_exposure: bool = False) -> dict[str, Any]:
    _require(batch.get("schema") == "quillframe_craft_blind_batch_v1", "invalid blind batch")
    _require(choice in ("A", "B", "tie", "both_bad", "insufficient_evidence"), "invalid human choice")
    _require(_nonempty(reason) and _nonempty(reviewer_ref) and isinstance(prior_exposure, bool), "attributed human explanation required")
    matches = [pair for pair in batch["pairs"] if pair["pair_id"] == pair_id]
    _require(len(matches) == 1, "unknown blind pair")
    pair = matches[0]
    observation = {"schema": "quillframe_craft_human_observation_v1", "batch_fingerprint": fingerprint(batch),
                   "pair_id": pair_id, "choice": choice, "reason": reason, "reviewer_ref": reviewer_ref,
                   "presented_text_fingerprints": {key: fingerprint(pair[key]) for key in ("A", "B")},
                   "prior_exposure": prior_exposure, "blind_eligible": not prior_exposure and not batch["synthetic_test_only"],
                   "created_at": datetime.now(timezone.utc).isoformat(), "authority": False,
                   "taste_activation": False, "framework_promotion": False}
    return _seal(observation, "observation_fingerprint")


def save_new(path: Path, value: dict[str, Any]) -> None:
    """Append-only artifact creation; never replace old evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare"])
    for name in ("output", "run-id", "order-seed", "service-id", "model-id", "reasoning-effort"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    prepared = prepare_evaluation(run_id=args.run_id, order_seed=args.order_seed, service_id=args.service_id,
                                  model_id=args.model_id, reasoning_effort=args.reasoning_effort)
    save_new(Path(args.output), prepared)
    print(json.dumps({"status": prepared["status"], "planned_model_calls": prepared["planned_model_calls"], "model_execution": False,
                      "plan_fingerprint": prepared["plan_fingerprint"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
