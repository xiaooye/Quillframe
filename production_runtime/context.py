from __future__ import annotations

import json
import uuid
from copy import deepcopy
from typing import Any

from agent_runtime import AgentBudget, AgentJob, AgentResult
from harness.context_runtime import STAGES, build_candidate_pool, canonical_json, derive_semantic_profile, fingerprint, freeze_context, pack_budget, validate_context_decision, validate_freeze
from persistence.context_repository import ContextRepository
from persistence.quillframe_sqlite import QuillframeStore, now_iso

from .contracts import MECHANISM_CONTEXT_STAGE, PRODUCTION_BUNDLE_SCHEMA, PRODUCTION_STATUS_SCHEMA, ProductionRunError, assert_secret_free, parse_json_object, validate_bundle_integrity
from .sources import AgentRuntimeLike, CONTEXT_STAGE_IDS, ProjectContextSourceLoader, _json

DEFAULT_STAGE_BUDGET = 12_000
MAX_PROFILE_JOBS = 96


class ProductionContextRuntime:
    """Fingerprint-bound Context orchestration for one production run."""

    def __init__(self, store: QuillframeStore, agent_runtime: AgentRuntimeLike) -> None:
        self.store = store
        self.agent_runtime = agent_runtime
        self.context_repository = ContextRepository(store)
        self.loader = ProjectContextSourceLoader(store, self.context_repository)

    def status(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            run = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not run:
                raise ProductionRunError("run_not_found", run_id)
            events = [dict(row) for row in conn.execute("SELECT event_kind,payload_json,created_at FROM runtime_events WHERE run_id=? ORDER BY created_at,rowid", (run_id,))]
            candidate = conn.execute("SELECT candidate_id,content_fingerprint,user_visible_gate,status FROM candidates WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run_id,)).fetchone()
        return {
            "schema": PRODUCTION_STATUS_SCHEMA, "project_id": project_id, "run_id": run_id,
            "task_mode": run["task_mode"], "target_ref": run["target_ref"], "status": run["status"],
            "result_fingerprint": run["result_fingerprint"],
            "events": [{**row, "payload": _json(row.pop("payload_json"), {})} for row in events],
            "candidate": dict(candidate) if candidate else None, "authority": False,
        }

    def _run_row(self, project_id: str, run_id: str) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            request = conn.execute(
                "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? "
                "AND checkpoint_kind='author_run_request' ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if not row:
            raise ProductionRunError("run_not_found", run_id)
        run = dict(row)
        if run["task_mode"] in {"DRAFT", "REVISE"}:
            target = _json(request["state_json"], None) if request else None
            if not isinstance(target, dict) or target.get("schema") != "quillframe_author_run_request_v1":
                raise ProductionRunError("target_context_missing", "Core author_run_request checkpoint is required")
            if request["artifact_fingerprint"] != fingerprint(target):
                raise ProductionRunError("target_context_invalid", "author request checkpoint fingerprint does not match")
            if any(not isinstance(target.get(key), str) or not target[key].strip() for key in ("chapter_id", "document_id")):
                raise ProductionRunError("target_context_invalid", "author request has no exact chapter/document target")
            for key in ("current_story_order", "current_reading_order"):
                value = target.get(key)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ProductionRunError("target_context_invalid", f"author request requires explicit {key}")
            if target.get("task_mode") != run["task_mode"] or target.get("target_ref") != run["target_ref"]:
                raise ProductionRunError("target_context_invalid", "author request changed its run binding")
            if not isinstance(target.get("payload"), dict):
                raise ProductionRunError("target_context_invalid", "author request payload must be an object")
            run["target_context"] = target
        return run

    def _load_sources(self, project_id: str, target: dict[str, Any]) -> list[dict[str, Any]]:
        self._validate_selected_preferences(project_id, target)
        return self.loader.load(
            project_id, chapter_id=target["chapter_id"], document_id=target["document_id"],
            current_story_order=target["current_story_order"], current_reading_order=target["current_reading_order"],
        )

    def _validate_selected_preferences(self, project_id: str, target: dict[str, Any]) -> None:
        selected = target.get("payload", {}).get("selected_preference_ids", [])
        if not selected:
            return
        frozen = target.get("author_model")
        if not isinstance(frozen, dict) or frozen.get("selected_hypothesis_ids") != selected or frozen.get("project_id") != project_id:
            raise ProductionRunError("selected_preference_stale", "selected author preferences do not match the frozen request")
        from core_operations import CoreOperations
        try:
            current = CoreOperations(self.store).project_learning().project_context(project_id=project_id, selected_hypothesis_ids=selected)
        except ValueError as exc:
            raise ProductionRunError("selected_preference_stale", "a selected preference is no longer active for this Project") from exc
        keys = ("selected_hypothesis_ids", "active_preferences")
        if fingerprint({key: frozen.get(key) for key in keys}) != fingerprint({key: current.get(key) for key in keys}):
            raise ProductionRunError("selected_preference_stale", "selected author preference version or content changed")

    def _event(self, project_id: str, run_id: str, kind: str, payload: dict[str, Any]) -> None:
        assert_secret_free(payload, label=f"runtime event {kind}")
        with self.store.open_project(project_id) as conn:
            conn.execute("INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)", ("evt_" + uuid.uuid4().hex, run_id, kind, canonical_json(payload), now_iso()))
            conn.commit()

    def _set_run(self, project_id: str, run_id: str, status: str, *, result_fingerprint: str | None = None) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("UPDATE runs SET status=?,result_fingerprint=COALESCE(?,result_fingerprint),updated_at=? WHERE run_id=?", (status, result_fingerprint, now_iso(), run_id))
            conn.commit()

    def _checkpoint_bundle(self, project_id: str, run_id: str, bundle: dict[str, Any]) -> None:
        assert_secret_free(bundle, label="production context bundle")
        with self.store.open_project(project_id) as conn:
            conn.execute(
                "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,?,?,?,?)",
                ("ckpt_" + uuid.uuid4().hex, run_id, "production_context_bundle", canonical_json(bundle), bundle["bundle_fingerprint"], now_iso()),
            )
            conn.commit()

    def _latest_bundle(self, project_id: str, run_id: str) -> dict[str, Any] | None:
        with self.store.open_project(project_id) as conn:
            row = conn.execute("SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind='production_context_bundle' ORDER BY created_at DESC,rowid DESC LIMIT 1", (run_id,)).fetchone()
        return _json(row["state_json"], {}) if row else None

    def _agent_job(self, *, run: dict[str, Any], service_id: str, runtime_role: str, instruction: str,
                   context: list[dict[str, Any]], model_preference: str | None, suffix: str,
                   max_output_tokens: int = 4096) -> tuple[AgentJob, AgentResult]:
        assert_secret_free(context, label=f"{runtime_role} context")
        job = AgentJob(
            job_id=f"job_{run['run_id']}_{suffix}_{uuid.uuid4().hex[:10]}",
            session_id=str(run.get("session_id") or f"session:{run['run_id']}"), run_id=str(run["run_id"]),
            task_mode=str(run["task_mode"]), runtime_role=runtime_role, service_id=service_id,
            instruction=instruction, context=context, model_preference=model_preference,
            required_model_capabilities={"text"}, authority={},
            budgets=AgentBudget(max_steps=4, max_model_requests=4, max_tool_calls=1, max_parallel_tool_calls=1,
                                max_output_tokens_per_request=max_output_tokens, max_total_tokens=64_000, max_elapsed_ms=180_000),
            idempotency_key=f"{run['run_id']}:{suffix}",
        )
        return job, self.agent_runtime.run(job)

    def _ensure_profiles(self, run: dict[str, Any], project_id: str, items: list[dict[str, Any]], *, service_id: str, model_preference: str | None) -> None:
        pending = [item for item in items if not isinstance(item.get("profile"), dict) or item["profile"].get("source_fingerprint") != item["source_fingerprint"] or item["profile"].get("status") != "current"]
        if len(pending) > MAX_PROFILE_JOBS:
            raise ProductionRunError("semantic_profile_batch_too_large", f"{len(pending)} semantic profiles require derivation; bounded maximum is {MAX_PROFILE_JOBS}")
        allowed_stages = sorted(STAGES)
        for index, item in enumerate(pending):
            instruction = (
                "Derive one Quillframe Semantic Context Profile. Return only JSON with fields: description (string), "
                "trigger_when (string), estimated_tokens (non-negative integer), semantic_tags (string array), "
                "stage_affinities (array using only allowed_stage_ids). This is derived retrieval metadata only; "
                "do not assign authority, Canon status, lifecycle, acceptance, or settlement."
            )
            packet = {"source_object_id": item["object_id"], "source_object_type": item["object_type"], "source_fingerprint": item["source_fingerprint"], "model_view": item["model_view"], "allowed_stage_ids": allowed_stages}
            job, result = self._agent_job(run=run, service_id=service_id, runtime_role="context_profile_deriver", instruction=instruction, context=[packet], model_preference=model_preference, suffix=f"profile-{index}", max_output_tokens=1200)
            if result.status != "completed":
                raise ProductionRunError("semantic_pending", "semantic profile derivation did not complete", detail={"object_id": item["object_id"], "agent_status": result.status, "errors": result.errors})
            metadata = parse_json_object(result.final_text, label="context profile derivation")
            profile = derive_semantic_profile(
                {"object_id": item["object_id"], "object_type": item["object_type"], "source_fingerprint": item["source_fingerprint"], "model_text": canonical_json(item["model_view"])},
                metadata,
                generator_provenance={"kind": "agent_runtime", "job_id": job.job_id, "job_fingerprint": job.input_fingerprint, "model_service_id": result.model_service_id, "model_id": result.model_id, "protocol": result.protocol},
                manual_override=self.context_repository.get_override(project_id, item["object_id"]),
            )
            self.context_repository.save_profile(project_id, profile)
            item["profile"] = profile

    def prepare_context(self, project_id: str, run_id: str, *, service_id: str, instruction: str,
                        model_preference: str | None = None, stage_budgets: dict[str, int] | None = None,
                        refresh_reason: str | None = None) -> dict[str, Any]:
        run = self._run_row(project_id, run_id)
        if run["task_mode"] not in {"DRAFT", "REVISE"}:
            raise ProductionRunError("production_mode_unsupported", "author.run.execute currently owns the DRAFT/REVISE production graph; other task modes remain separate semantic contracts")
        stage_budgets = dict(stage_budgets or {})
        previous = self._latest_bundle(project_id, run_id)
        target = run["target_context"]
        items = self._load_sources(project_id, target)
        self._ensure_profiles(run, project_id, items, service_id=service_id, model_preference=model_preference)
        source_fps, source_states, source_universe_fp = self.loader.state_projection(items)
        pools: list[dict[str, Any]] = []
        pinned_greenlights: dict[str, dict[str, Any]] = {}
        greenlights: list[dict[str, Any]] = []
        # Resolve task-input eligibility and resource limits before spending a
        # selector call. These receipts do not claim a model selected the pins.
        for stage_id in CONTEXT_STAGE_IDS:
            pool = build_candidate_pool(run_id=run_id, stage_id=stage_id, items=items)
            hard_budget = stage_budgets.get(stage_id, DEFAULT_STAGE_BUDGET)
            if isinstance(hard_budget, bool) or not isinstance(hard_budget, int) or hard_budget < 0:
                raise ProductionRunError("invalid_stage_budget", f"invalid hard budget for {stage_id}")
            pinned_decision = validate_context_decision(pool, {"selections": []}, selector={"kind": "task_binding", "model_invoked": False})
            if not pinned_decision["proceed"]:
                raise ProductionRunError("required_context_unavailable", "required task input is not eligible", detail={"stage_id": stage_id, "errors": pinned_decision["errors"]})
            pinned_greenlight = pack_budget(pinned_decision, hard_budget=hard_budget)
            if pinned_greenlight["grounding_incomplete_due_budget"]:
                raise ProductionRunError("grounding_incomplete_due_budget", f"required task inputs could not fit stage budget for {stage_id}")
            pools.append(pool)
            pinned_greenlights[stage_id] = pinned_greenlight
        for index, pool in enumerate(pools):
            stage_id = pool["stage_id"]
            pinned_greenlight = pinned_greenlights[stage_id]
            hard_budget = pinned_greenlight["hard_budget"]
            pinned_ids = set(pinned_greenlight["pinned_profile_ids"])
            optional = [row for row in pool["eligible"] if row["profile_id"] not in pinned_ids]
            if optional:
                selector_packet = {"run_id": run_id, "stage_id": stage_id, "candidate_universe_fingerprint": pool["candidate_universe_fingerprint"],
                                   "eligible": optional, "required_inputs": pinned_greenlight["pinned_inputs"],
                                   "hard_budget": hard_budget, "remaining_budget": hard_budget - pinned_greenlight["estimated_tokens"], "instruction": instruction}
                selector_instruction = (
                    "Select optional Quillframe Context for exactly one stage from the supplied eligible candidates. "
                    "Core has separately bound required_inputs to this exact task; these inputs are already reserved "
                    "within the hard budget and are not semantic selections. Choose optional inputs within remaining_budget. "
                    "Return only JSON: {\"selections\":[{\"profile_id\":string,\"stage_id\":string,\"priority\":number,"
                    "\"reason_code\":short_string,\"reason\":short_string,\"required_for_grounding\":boolean}]}. "
                    "Never invent IDs, never return excluded objects, never grant authority, and never expose chain-of-thought."
                )
                job, result = self._agent_job(run=run, service_id=service_id, runtime_role="context_selector", instruction=selector_instruction, context=[selector_packet], model_preference=model_preference, suffix=f"selector-{index}", max_output_tokens=2400)
                if result.status != "completed":
                    raise ProductionRunError("semantic_pending", "Context Decision Agent did not complete", detail={"stage_id": stage_id, "agent_status": result.status, "errors": result.errors})
                decision_payload = parse_json_object(result.final_text, label=f"context selector {stage_id}")
                selector = {"kind": "agent_runtime", "job_id": job.job_id, "input_fingerprint": job.input_fingerprint, "model_service_id": result.model_service_id, "model_id": result.model_id, "protocol": result.protocol}
            else:
                decision_payload = {"selections": []}
                selector = {"kind": "deterministic_no_optional_candidates", "model_invoked": False}
            decision = validate_context_decision(pool, decision_payload, selector=selector)
            if not decision["proceed"]:
                raise ProductionRunError("semantic_invalid", "Context Decision returned invalid candidate identities", detail={"stage_id": stage_id, "errors": decision["errors"]})
            greenlight = pack_budget(decision, hard_budget=hard_budget)
            if greenlight.get("grounding_incomplete_due_budget") is True:
                raise ProductionRunError("grounding_incomplete_due_budget", f"required grounding could not fit stage budget for {stage_id}")
            self.context_repository.save_stage_selection(project_id, pool, greenlight)
            greenlights.append(greenlight)

        frozen = freeze_context(run_id=run_id, task_mode=run["task_mode"], pools=pools, greenlights=greenlights)
        self.context_repository.save_freeze(project_id, frozen)
        loaded_ids = sorted({object_id for green in greenlights for object_id in green.get("loaded_object_ids", [])})
        by_id = {item["object_id"]: item for item in items}
        reader_expectations = deepcopy(by_id["reader-expectations:" + project_id]["model_view"]["expectations"])
        payloads = {
            object_id: {"object_id": object_id, "object_type": by_id[object_id]["object_type"], "authority": by_id[object_id]["authority"],
                        "lifecycle": by_id[object_id]["lifecycle"], "domain": by_id[object_id]["domain"],
                        "source_fingerprint": by_id[object_id]["source_fingerprint"], "model_view": deepcopy(by_id[object_id]["model_view"])}
            for object_id in loaded_ids
        }
        binding = {"run_id": run_id, "task_mode": run["task_mode"], "target_context": deepcopy(target), "reader_expectations": reader_expectations, "freeze_fingerprint": frozen["freeze_fingerprint"],
                   "source_universe_fingerprint": source_universe_fp, "source_payloads": payloads,
                   "stage_bindings": MECHANISM_CONTEXT_STAGE,
                   "supersedes_bundle_fingerprint": previous.get("bundle_fingerprint") if previous else None,
                   "refresh_reason": refresh_reason}
        bundle = {"schema": PRODUCTION_BUNDLE_SCHEMA, **binding, "freeze": frozen, "source_fingerprints": source_fps,
                  "source_states": source_states, "created_at": now_iso(), "authority": False}
        bundle["bundle_fingerprint"] = fingerprint(binding)
        self._checkpoint_bundle(project_id, run_id, bundle)
        self._set_run(project_id, run_id, "context_frozen")
        self._event(project_id, run_id, "production_context_frozen", {"bundle_fingerprint": bundle["bundle_fingerprint"], "freeze_fingerprint": frozen["freeze_fingerprint"], "source_universe_fingerprint": source_universe_fp, "supersedes_bundle_fingerprint": binding["supersedes_bundle_fingerprint"], "refresh_reason": refresh_reason})
        return bundle

    def refresh_context(self, project_id: str, run_id: str, *, service_id: str, instruction: str,
                        model_preference: str | None = None, stage_budgets: dict[str, int] | None = None,
                        reason: str = "explicit_refresh") -> dict[str, Any]:
        return self.prepare_context(project_id, run_id, service_id=service_id, instruction=instruction, model_preference=model_preference, stage_budgets=stage_budgets, refresh_reason=reason)

    def _validate_bundle_current(self, project_id: str, bundle: dict[str, Any]) -> dict[str, Any]:
        validate_bundle_integrity(bundle)
        target = self._run_row(project_id, bundle["run_id"])["target_context"]
        if target != bundle["target_context"]:
            return {"status": "stale_conflict", "proceed": False, "target_context_changed": True,
                    "new_context_fingerprint_required": True}
        current = self._load_sources(project_id, target)
        current_fps, current_states, universe = self.loader.state_projection(current)
        validation = validate_freeze(bundle["freeze"], current_fps, current_states)
        if universe != bundle["source_universe_fingerprint"]:
            validation = {**validation, "status": "stale_conflict", "proceed": False, "new_context_fingerprint_required": True, "source_universe_changed": True, "current_source_universe_fingerprint": universe}
        return validation
