from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from typing import Any

from agent_runtime import AgentBudget, AgentJob, AgentResult
from agent_runtime.runner import CancellationToken
from harness.context_runtime import canonical_json, fingerprint, stage_context
from harness.semantic_workers.independent_invocation_receipt import (
    PROVIDERS as INDEPENDENT_PROVIDER_CONTRACTS,
    SCHEMA as INDEPENDENT_INVOCATION_RECEIPT_SCHEMA,
    build_receipt as build_independent_invocation_receipt,
    fingerprint as independent_fingerprint,
    validate_receipt as validate_independent_invocation_receipt,
)
from harness.semantic_workers.peer_chat_relay import validate_peer_result
from harness.semantic_workers.registered_contract_binding import (
    validate_recorded_registered_job,
    validate_registered_job,
)
from harness.semantic_workers.semantic_worker_router import validate_result as validate_semantic_result
from persistence.independent_review_repository import IndependentReviewError, IndependentReviewRepository
from persistence.production_stage_repository import ProductionStageError, ProductionStageRepository
from persistence.quillframe_sqlite import fingerprint_text, now_iso
from model_runtime.deadlines import DURABLE_REQUEST_TIMEOUT_MS
from quality.candidate_qualification import comparison_gate_status
from quality.author_objective_gate import validate_author_objectives
from quality.reader_expectation import ReaderExpectationError, record_observation, validate_observation_binding

from .context import ProductionContextRuntime
from .build_identity import framework_build_identity
from .confirmed_prefix import (
    PREFIX_ROLES as CONFIRMED_PREFIX_ROLES,
    REUSE_SCHEMA as CONFIRMED_PREFIX_REUSE_SCHEMA,
    build_reference as build_confirmed_prefix_reference,
    context_compatibility_fingerprint,
    load_confirmed_prefix,
)
from .craft_guidance import (
    freeze_craft_library, materialize_writer_craft, selection_input,
    validate_craft_snapshot, validate_mode,
)
from .contracts import (
    MECHANISM_CONTEXT_STAGE,
    PRODUCTION_BUNDLE_SCHEMA,
    PRODUCTION_EXECUTION_SCHEMA,
    PRODUCTION_MECHANISMS,
    ProductionRunError,
    assert_secret_free,
    parse_json_object,
    public_stage_result,
    validate_bundle_integrity,
)
from .semantic import (
    RegisteredSemanticExecutor,
    build_pre_independent_qualification,
    build_narrative_state_proposal,
    character_action_payloads,
    character_state_prepare_contract,
    final_readiness,
    final_release,
    narrative_existing_state,
    prepare_independent_review,
    prepared_character_action_payloads,
    semantic_status,
    validate_independent_submission,
    writer_safe_projection,
)
from .sources import _json
from .repair import (
    author_direction_evidence, author_objective_projection, candidate_lineage, comparison_payload, editor_payload, generation_instruction,
    materialize_author_objectives,
    generation_plan, objective_envelope, prior_lineage, writer_context,
)
from .writer_context import (
    WRITER_DIRECTIVE_VERSION,
    build_inventory as build_writer_inventory,
    materialize_writer_pack,
    model_inventory,
)
from .repair_source import freeze_repair_source, load_repair_source
from .reading_positioning import build_reading_positioning, reading_positioning_fields, READER_FIELDS
from learning.user_taste import (
    materialize_selection as materialize_user_taste_selection,
    selection_payload as user_taste_selection_payload,
    validate_snapshot as validate_user_taste_snapshot,
)

# Characters propose actions before the Scene resolver can resolve them. The
# public mechanism vocabulary remains shared with Context Runtime.
PRE_INDEPENDENT_MECHANISMS = (
    "story_canon_preflight", "character_simulation", "scene_simulation",
    "reader_pressure", "surface_realization",
    "reader_engagement", "continuity",
)
READER_GRIP_VALUES = {"low", "medium", "high", "very_high"}
WRITER_REALIZATION_GUIDANCE = (
    "Write the candidate directly from the Scene Realization Contract. Put judgment in action, pause, misunderstanding, "
    "avoidance and choice; show only what the POV would notice now. Let dialogue contest information, relationship, time, "
    "responsibility or resources. Let motive be inferred from behavior and cost, and stop explaining once the evidence is enough. "
    "End on a consequence or new constraint, not a theme summary. Use natural Chinese for ordinary narration and speech; "
    "use brief English only when this character and situation genuinely require it, with natural contextual understanding. "
)
_EXECUTION_SCOPE: ContextVar[dict[str, Any] | None] = ContextVar("quillframe_production_execution", default=None)
_READY_RUN_POOL = ThreadPoolExecutor(max_workers=64, thread_name_prefix="qf-production-resume")
_READY_RUN_LOCK = threading.RLock()
_READY_RUN_FUTURES: dict[tuple[str, str, str], Future[dict[str, Any] | None]] = {}


class ProductionRunExecutor(ProductionContextRuntime):
    def __init__(self, store, agent_runtime) -> None:  # noqa: ANN001
        super().__init__(store, agent_runtime)
        self.stage_repository = ProductionStageRepository(store)

    @staticmethod
    def _raise_stage_repository(exc: ProductionStageError) -> None:
        raise ProductionRunError(exc.code, str(exc), detail=exc.detail) from exc

    def _execution_scope(self, project_id: str | None = None, run_id: str | None = None) -> dict[str, Any] | None:
        scope = _EXECUTION_SCOPE.get()
        if scope is None or scope["store"] is not self.store:
            return None
        if project_id is not None and scope["project_id"] != project_id:
            return None
        if run_id is not None and scope["run_id"] != run_id:
            return None
        return scope

    def _guard_execution(self, conn, project_id: str, run_id: str) -> None:  # noqa: ANN001
        scope = self._execution_scope(project_id, run_id)
        try:
            self.stage_repository.guard_locked(conn, run_id, scope["owner"] if scope else None)
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)

    def _set_run(self, project_id: str, run_id: str, status: str, *, result_fingerprint: str | None = None) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            conn.execute(
                "UPDATE runs SET status=?,result_fingerprint=COALESCE(?,result_fingerprint),updated_at=? WHERE run_id=?",
                (status, result_fingerprint, now_iso(), run_id),
            )
            conn.commit()

    def _checkpoint_bundle(self, project_id: str, run_id: str, bundle: dict[str, Any]) -> None:
        self._checkpoint(project_id, run_id, "production_context_bundle", bundle, bundle["bundle_fingerprint"])

    def _event(self, project_id: str, run_id: str, kind: str, payload: dict[str, Any]) -> None:
        assert_secret_free(payload, label=f"runtime event {kind}")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            self.stage_repository._event_locked(conn, run_id, kind, payload)
            conn.commit()

    def _record_semantic_failure(self, project_id: str, run_id: str, error: ProductionRunError, *, mechanism: str | None = None) -> None:
        """Close the running state and record one safe failure per durable call."""
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            latest = conn.execute(
                "SELECT call_id,stage_key,runtime_role,result_fingerprint FROM production_stage_calls WHERE run_id=? ORDER BY rowid DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            call_id = latest["call_id"] if latest else None
            event_id = "evt_failure_" + fingerprint({"run_id": run_id, "call_id": call_id, "code": error.code})[7:]
            payload = {
                "mechanism": mechanism or (latest["runtime_role"] if latest else "semantic_execution"),
                "stage_key": latest["stage_key"] if latest else "semantic_execution",
                "code": error.code, "call_id": call_id,
                "result_fingerprint": latest["result_fingerprint"] if latest else None,
                "automatic_model_retry": False, "candidate_visible": False, "authority": False,
            }
            # Error messages/details can quote private input or model output.
            # Only deterministic journal metadata belongs in the public event.
            assert_secret_free(payload, label="runtime semantic failure event")
            conn.execute(
                "UPDATE runs SET status='semantic_pending',updated_at=? WHERE run_id=? AND status NOT IN ('failed_gate','completed','cancelled')",
                (now_iso(), run_id),
            )
            conn.execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,'production_stage_failed',?,?) ON CONFLICT(event_id) DO NOTHING",
                (event_id, run_id, canonical_json(payload), now_iso()),
            )
            conn.commit()

    def status(self, project_id: str, run_id: str) -> dict[str, Any]:
        result = super().status(project_id, run_id)
        journal = self.stage_repository.projection(project_id, run_id)
        if result["status"] == "semantic_running" and not journal["active_executor"]:
            result["status"] = "semantic_pending" if journal["unconfirmed_call_ids"] else "interrupted"
        result["execution_journal"] = journal
        if result["status"] == "failed_gate" and not journal["active_executor"] and not journal["unconfirmed_call_ids"]:
            with self.store.open_project(project_id) as conn:
                row = conn.execute(
                    "SELECT checkpoint_id,artifact_fingerprint FROM checkpoints WHERE run_id=? "
                    "AND checkpoint_kind='production_qualified_candidate' ORDER BY created_at DESC,rowid DESC LIMIT 1", (run_id,),
                ).fetchone()
                if row:
                    source_ref = {"source_run_id": run_id, "source_checkpoint_id": row["checkpoint_id"],
                                  "expected_candidate_fingerprint": row["artifact_fingerprint"]}
                    try:
                        source = freeze_repair_source(conn, source_ref=source_ref, target=self._run_row(project_id, run_id)["target_context"])
                        prior_lineage(source)
                    except ProductionRunError:
                        pass  # An invalid or incomplete source is never offered as repairable.
                    else:
                        result["repair_source"] = source_ref
        if (result["status"] == "semantic_pending" and not journal["active_executor"]
                and not journal["unconfirmed_call_ids"]):
            with self.store.open_project(project_id) as conn:
                try:
                    result["confirmed_prefix_source"] = build_confirmed_prefix_reference(conn, run_id)
                except ProductionRunError:
                    pass
        return result

    def _repair_source(self, project_id: str, run: dict[str, Any]) -> dict[str, Any] | None:
        requested = run["target_context"].get("payload", {}).get("repair_source")
        if run["task_mode"] != "REVISE":
            if requested is not None:
                raise ProductionRunError("repair_mode_required", "a failed candidate must be repaired through REVISE")
            return None
        if requested is None:
            raise ProductionRunError("repair_source_required", "REVISE requires a Core-frozen authorized repair source")
        with self.store.open_project(project_id) as conn:
            source = load_repair_source(conn, run["run_id"])
        source_author = source["source_target_context"].get("author_model", {})
        current_author = run["target_context"].get("author_model", {})
        if any(current_author.get(key) != source_author.get(key) for key in ("selected_hypothesis_ids", "active_preferences")):
            raise ProductionRunError("repair_objective_changed", "REVISE must preserve the source run's selected author preferences")
        prior_lineage(source)
        return source

    def _confirmed_prefix_source(
        self, project_id: str, run: dict[str, Any], source: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        requested = run["target_context"].get("payload", {}).get("confirmed_prefix_source")
        if requested is None:
            return None
        if run["task_mode"] != "REVISE" or source is None:
            raise ProductionRunError(
                "confirmed_prefix_invalid",
                "confirmed prefix recovery requires a Core-frozen REVISE source",
            )
        with self.store.open_project(project_id) as conn:
            frozen, private = load_confirmed_prefix(
                conn, run["run_id"], target=run["target_context"], repair_source=source,
            )
        return {"frozen": frozen, "private": private}

    def resume_execution(self, project_id: str, run_id: str) -> dict[str, Any]:
        """Continue only the immutable request; callers cannot revise its inputs."""
        try:
            request = self.stage_repository.load_request(project_id, run_id)
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)
        frozen_build = request.pop("framework_build", None)
        try:
            current_build = framework_build_identity()
        except ValueError as exc:
            raise ProductionRunError("framework_build_unavailable", str(exc)) from exc
        if frozen_build is None:
            raise ProductionRunError("fresh_run_required", "historical executions without a build fingerprint require a fresh run")
        if frozen_build != current_build:
            raise ProductionRunError(
                "framework_build_changed",
                "this execution is bound to a different immutable Framework build; resume through a new checkpoint-bound run",
                detail={
                    "frozen_build_fingerprint": frozen_build.get("build_fingerprint") if isinstance(frozen_build, dict) else None,
                    "current_build_fingerprint": current_build["build_fingerprint"],
                },
            )
        snapshot = request.pop("craft_guidance", None)
        if snapshot is None:
            raise ProductionRunError("fresh_run_required", "historical executions without a craft snapshot require a fresh run")
        validate_craft_snapshot(snapshot)
        request["craft_guidance_mode"] = snapshot["mode"]
        return self.execute(project_id, run_id, **request)

    def reconcile_billing(
        self,
        project_id: str,
        run_id: str,
        *,
        call_id: str,
        expected_result_fingerprint: str,
        cost_micros: int,
        evidence_ref: str,
        evidence_fingerprint: str,
    ) -> dict[str, Any]:
        try:
            return self.stage_repository.reconcile_billing_receipt(
                project_id,
                run_id,
                call_id=call_id,
                expected_result_fingerprint=expected_result_fingerprint,
                cost_micros=cost_micros,
                evidence_ref=evidence_ref,
                evidence_fingerprint=evidence_fingerprint,
            )
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)

    def framework_build_migration_preview(
        self, project_id: str, run_id: str
    ) -> dict[str, Any]:
        try:
            return self.stage_repository.build_migration_preview(
                project_id,
                run_id,
                new_framework_build=framework_build_identity(),
            )
        except (ProductionStageError, ValueError) as exc:
            if isinstance(exc, ProductionStageError):
                self._raise_stage_repository(exc)
            raise ProductionRunError("framework_build_unavailable", str(exc)) from exc

    def run_framework_build_migration_regression(
        self, project_id: str, run_id: str
    ) -> dict[str, Any]:
        """Run only the fixed offline suite; this never dispatches a model."""

        from .build_migration import run_and_record_build_regression

        try:
            return run_and_record_build_regression(
                self.stage_repository,
                project_id,
                run_id,
                new_framework_build=framework_build_identity(),
            )
        except (ProductionStageError, ValueError) as exc:
            if isinstance(exc, ProductionStageError):
                self._raise_stage_repository(exc)
            raise ProductionRunError("framework_build_unavailable", str(exc)) from exc

    def migrate_framework_build(
        self,
        project_id: str,
        run_id: str,
        *,
        expected_request_fingerprint: str,
        regression_receipt_id: str,
        authorization_ref: str,
    ) -> dict[str, Any]:
        try:
            return self.stage_repository.migrate_framework_build(
                project_id,
                run_id,
                expected_request_fingerprint=expected_request_fingerprint,
                new_framework_build=framework_build_identity(),
                regression_receipt_id=regression_receipt_id,
                authorization_ref=authorization_ref,
            )
        except (ProductionStageError, ValueError) as exc:
            if isinstance(exc, ProductionStageError):
                self._raise_stage_repository(exc)
            raise ProductionRunError("framework_build_unavailable", str(exc)) from exc

    def resume_ready_runs(self, project_id: str, *, limit: int = 32) -> dict[str, Any]:
        """Schedule durable wakes without waiting for unrelated model calls."""
        ready_runs = self.stage_repository.ready_runs(project_id, limit=limit)

        def resume_one(ready: dict[str, Any]) -> dict[str, Any] | None:
            run_id = ready["run_id"]
            wake_event_ids = ready["wake_event_ids"]
            try:
                result = self.resume_execution(project_id, run_id)
            except ProductionRunError as exc:
                if exc.code == "run_in_progress":
                    return None
                self.stage_repository.consume_wakes(
                    project_id, run_id, wake_event_ids=wake_event_ids
                )
                return {"run_id": run_id, "status": "stopped", "code": exc.code}
            self.stage_repository.consume_wakes(
                project_id, run_id, wake_event_ids=wake_event_ids
            )
            return {"run_id": run_id, "status": result.get("status", "unknown")}

        outcomes: list[dict[str, Any]] = []
        scheduled: list[str] = []
        store_key = str(self.store.root.resolve())
        with _READY_RUN_LOCK:
            # Reap prior completions without ever waiting for them. A failed
            # worker leaves its durable wake unconsumed for a later attempt.
            for key, future in list(_READY_RUN_FUTURES.items()):
                if key[0] != store_key or key[1] != project_id or not future.done():
                    continue
                del _READY_RUN_FUTURES[key]
                try:
                    outcome = future.result()
                except Exception as exc:
                    outcomes.append({
                        "run_id": key[2], "status": "stopped",
                        "code": "framework_exception:" + type(exc).__name__,
                    })
                else:
                    if outcome is not None:
                        outcomes.append(outcome)
            for ready in ready_runs:
                key = (store_key, project_id, ready["run_id"])
                active = _READY_RUN_FUTURES.get(key)
                if active is not None and not active.done():
                    continue
                if active is not None:
                    del _READY_RUN_FUTURES[key]
                _READY_RUN_FUTURES[key] = _READY_RUN_POOL.submit(resume_one, ready)
                scheduled.append(ready["run_id"])
        outcomes.sort(key=lambda item: item["run_id"])
        return {
            "schema": "quillframe_production_coordinator_tick_v1",
            "project_id": project_id,
            "outcomes": outcomes,
            "scheduled_run_ids": sorted(scheduled),
            "automatic_redispatch": False,
            "authority": False,
        }

    def _craft_snapshot(
        self, project_id: str, run_id: str, mode: str | None,
        source: dict[str, Any] | None, style_pack_root: str | Path | None = None,
        style_pack_manifest_fingerprint: str | None = None,
        confirmed_prefix: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resume frozen resources; a new repair inherits its source by default."""
        if style_pack_root is not None and not isinstance(style_pack_root, (str, Path)):
            raise ProductionRunError("invalid_args", "style_pack_root must be a filesystem path")
        if mode is not None:
            validate_mode(mode)
        run = self._run_row(project_id, run_id)
        target = run["target_context"]

        def expected_scope(manifest_fingerprint: str) -> dict[str, Any]:
            return {
                "schema": "quillframe_run_scoped_craft_binding_v1",
                "project_id": project_id, "run_id": run_id,
                "chapter_id": target["chapter_id"],
                "document_id": target["document_id"],
                "task_mode": run["task_mode"],
                "manifest_fingerprint": manifest_fingerprint,
                "one_off_opt_in": True, "authority": False,
            }

        def validate_actual_scope(snapshot: dict[str, Any]) -> None:
            if snapshot.get("mode") == "outline_plus_style_contract":
                manifest_fingerprint = snapshot.get("run_scope", {}).get("manifest_fingerprint")
                if snapshot.get("run_scope") != expected_scope(manifest_fingerprint):
                    raise ProductionRunError(
                        "craft_snapshot_invalid",
                        "combined craft snapshot is not bound to the actual native run",
                    )
        try:
            prior = self.stage_repository.load_request(project_id, run_id)
        except ProductionStageError as exc:
            if exc.code != "execution_request_missing":
                self._raise_stage_repository(exc)
        else:
            if style_pack_root is not None or style_pack_manifest_fingerprint is not None:
                raise ProductionRunError(
                    "execution_request_conflict",
                    "a resumed execution cannot replace its frozen style pack",
                )
            snapshot = prior.get("craft_guidance")
            if snapshot is None:
                raise ProductionRunError("fresh_run_required", "historical executions without a craft snapshot require a fresh run")
            validate_craft_snapshot(snapshot)
            validate_actual_scope(snapshot)
            if mode is not None and mode != snapshot["mode"]:
                raise ProductionRunError("execution_request_conflict", "craft mode cannot change within an immutable execution")
            return deepcopy(snapshot)
        if confirmed_prefix is not None:
            if style_pack_root is not None or style_pack_manifest_fingerprint is not None or mode not in {None, "baseline"}:
                raise ProductionRunError(
                    "confirmed_prefix_craft_conflict",
                    "a no-generation recovery cannot consume or replace a run-scoped Writer pack",
                )
            # The original generation pack remains frozen in predecessor
            # evidence.  This fresh run performs no Writer stage, so it uses a
            # neutral snapshot and cannot consume that one-run pack again.
            return freeze_craft_library("baseline")
        if source and source["source_request"].get("craft_guidance") is not None:
            snapshot = source["source_request"]["craft_guidance"]
            validate_craft_snapshot(snapshot)
            if snapshot.get("mode") == "outline_plus_style_contract":
                if (mode != "outline_plus_style_contract" or style_pack_root is None
                        or style_pack_manifest_fingerprint is None):
                    raise ProductionRunError(
                        "fresh_run_required",
                        "a run-scoped composite REVISE requires a new exact one-run pack",
                    )
                # Continue below and freeze the newly scoped pack. The parent
                # selector judgment may be reused only after the new catalog
                # and current planning evidence independently validate.
            elif mode is None or mode == snapshot["mode"]:
                if style_pack_root is not None:
                    raise ProductionRunError(
                        "execution_request_conflict",
                        "an inherited repair cannot replace its frozen style pack",
                    )
                return deepcopy(snapshot)
        selected_mode = mode or "baseline"
        if selected_mode == "style_contract":
            return freeze_craft_library(selected_mode, root=style_pack_root)
        if selected_mode == "outline_plus_style_contract":
            if not isinstance(style_pack_manifest_fingerprint, str):
                raise ProductionRunError(
                    "invalid_args", "combined craft requires its exact run-pack manifest fingerprint",
                )
            return freeze_craft_library(
                selected_mode, style_pack_root=style_pack_root,
                run_scope=expected_scope(style_pack_manifest_fingerprint),
            )
        if style_pack_root is not None or style_pack_manifest_fingerprint is not None:
            raise ProductionRunError(
                "invalid_args", "run-scoped style pack inputs require the combined mode",
            )
        return freeze_craft_library(selected_mode)

    def cancel_execution(self, project_id: str, run_id: str, *, user_authorized: bool) -> dict[str, Any]:
        if user_authorized is not True:
            raise ProductionRunError("authorization_required", "cancel requires explicit user action")
        try:
            with self.store.open_project(project_id) as conn:
                conn.execute("BEGIN IMMEDIATE")
                self.stage_repository.cancel_locked(conn, run_id)
                conn.commit()
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)
        return self.status(project_id, run_id)

    def refresh_context(self, project_id: str, run_id: str, **kwargs: Any) -> dict[str, Any]:
        raise ProductionRunError(
            "fresh_run_required",
            "context refresh requires a new author run; an immutable execution cannot spend unjournaled model calls",
        )

    def prepare_context(self, project_id: str, run_id: str, **kwargs: Any) -> dict[str, Any]:
        if self._execution_scope(project_id, run_id) is None:
            raise ProductionRunError(
                "execution_lease_required", "production context preparation must join the budgeted execution lease",
            )
        if "inherited_selection_bundle" in kwargs:
            raise ProductionRunError(
                "context_reuse_core_owned", "repair context reuse is derived only from the Core-frozen source",
            )
        run = self._run_row(project_id, run_id)
        source = self._repair_source(project_id, run)
        inherited = None
        if isinstance(source, dict) and source.get("source_kind") == "author_revision":
            inherited = self._latest_bundle(project_id, source["source_run_id"])
            if (not isinstance(inherited, dict)
                    or inherited.get("bundle_fingerprint") != source.get("source_context_bundle_fingerprint")):
                raise ProductionRunError("context_reuse_invalid", "author revision source context bundle changed")
        return super().prepare_context(
            project_id, run_id, inherited_selection_bundle=inherited, **kwargs,
        )

    @staticmethod
    def _stage_call_key(job: AgentJob) -> str:
        packet = job.context[0] if job.context else {}
        registered = packet.get("registered_semantic_job")
        if isinstance(registered, dict):
            return "registered:" + str(registered["input"]["model_contract_id"]) + ":" + str(registered["subject_id"])
        if job.runtime_role == "context_profile_deriver":
            return "context_profile:" + str(packet["source_object_id"])
        if job.runtime_role == "context_selector":
            return "context_selector:" + str(packet["stage_id"])
        return job.runtime_role

    def _confirm_agent_validation(
        self, job: AgentJob, *, validation_kind: str, validated_value: Any
    ) -> None:
        scope = self._execution_scope(run_id=job.run_id)
        if scope is None:
            raise ProductionRunError(
                "execution_lease_required", "node validation requires the frozen execution lease"
            )
        try:
            self.stage_repository.confirm_node_validation(
                scope["project_id"],
                job.run_id,
                scope["owner"],
                stage_key=self._stage_call_key(job),
                input_fingerprint=job.input_fingerprint,
                validation_kind=validation_kind,
                validation_fingerprint=fingerprint(validated_value),
            )
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)

    def _confirm_registered_validation(
        self, job: AgentJob, binding: dict[str, Any]
    ) -> None:
        self._confirm_agent_validation(
            job,
            validation_kind="registered_semantic_contract:" + str(binding["contract_id"]),
            validated_value=binding,
        )

    def _invoke_agent(self, job: AgentJob) -> AgentResult:
        scope = self._execution_scope(run_id=job.run_id)
        if scope is None:
            raise ProductionRunError(
                "execution_lease_required", "production model calls require a durable budgeted execution lease",
            )
        repository = self.stage_repository
        try:
            intent = repository.begin_call(
                scope["project_id"], job.run_id, scope["owner"],
                stage_key=self._stage_call_key(job), job=job.to_dict(),
            )
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)
        if intent["replayed"]:
            value = intent["result"]
            try:
                return AgentResult(**{field.name: value[field.name] for field in fields(AgentResult) if field.name in value})
            except (TypeError, ValueError) as exc:
                raise ProductionRunError("stage_result_corrupt", "confirmed AgentResult is invalid") from exc
        supports_durable = getattr(self.agent_runtime, "supports_durable_model_request", None)
        durable_request = bool(intent.get("pending")) or bool(
            not intent.get("pending")
            and job.idempotency_key
            and callable(supports_durable)
            and supports_durable(job.service_id, job.model_preference) is True
        )
        if durable_request and not intent.get("pending"):
            try:
                repository.mark_pollable(
                    scope["project_id"], job.run_id, scope["owner"], intent["call_id"],
                )
            except ProductionStageError as exc:
                self._raise_stage_repository(exc)
            intent["pending"] = True
        try:
            result = self.agent_runtime.run(job, cancellation=scope["cancellation"])
            if result.status == "model_pending":
                if not durable_request:
                    repository.mark_unconfirmed(
                        scope["project_id"], job.run_id, scope["owner"],
                        intent["call_id"], "non_durable_model_pending",
                    )
                    raise ProductionRunError(
                        "stage_result_unconfirmed",
                        "a non-durable provider returned pending; automatic reinvocation is forbidden",
                        detail={
                            "call_id": intent["call_id"],
                            "stage_key": self._stage_call_key(job),
                            "reconciliation_required": True,
                        },
                    )
                repository.mark_pending(
                    scope["project_id"], job.run_id, scope["owner"], intent["call_id"],
                )
                raise ProductionRunError(
                    "stage_result_pending", "the exact model worker is still running",
                    detail={"call_id": intent["call_id"], "stage_key": self._stage_call_key(job)},
                )
            ambiguous_poll_errors = {
                "dns_resolution_failed", "network_request_failed", "request_deadline_exceeded",
                "model_request_failed",
            }
            result_error_codes = {
                error.get("code") for error in result.errors if isinstance(error, dict)
            }
            if (
                intent.get("pending") and result.status == "model_failed"
                and result_error_codes.intersection(ambiguous_poll_errors)
            ):
                raise ProductionRunError(
                    "stage_result_pending", "the keyed model request has no terminal result yet",
                    detail={"call_id": intent["call_id"], "stage_key": self._stage_call_key(job)},
                )
            assert_secret_free(result.to_dict(), label="private stage result")
            repository.confirm_call(
                scope["project_id"], job.run_id, scope["owner"],
                call_id=intent["call_id"], result=result.to_dict(),
            )
            return result
        except ProductionStageError as exc:
            repository.mark_unconfirmed(scope["project_id"], job.run_id, scope["owner"], intent["call_id"], exc.code)
            self._raise_stage_repository(exc)
        except ProductionRunError as exc:
            if exc.code == "stage_result_pending":
                raise
            if intent.get("pending"):
                raise ProductionRunError(
                    "stage_result_pending", "polling the exact pending model request was interrupted",
                    detail={"call_id": intent["call_id"], "stage_key": self._stage_call_key(job)},
                ) from exc
            repository.mark_unconfirmed(
                scope["project_id"], job.run_id, scope["owner"], intent["call_id"],
                "external_call_interrupted",
            )
            raise
        except Exception as exc:
            if intent.get("pending"):
                raise ProductionRunError(
                    "stage_result_pending", "polling the exact pending model request was interrupted",
                    detail={"call_id": intent["call_id"], "stage_key": self._stage_call_key(job)},
                ) from exc
            repository.mark_unconfirmed(scope["project_id"], job.run_id, scope["owner"], intent["call_id"], "external_call_interrupted")
            if isinstance(exc, ProductionRunError):
                raise
            raise ProductionRunError(
                "stage_result_unconfirmed", "external stage call ended without an exact confirmed result",
                detail={"call_id": intent["call_id"], "stage_key": self._stage_call_key(job)},
            ) from exc

    def _agent_job(
        self, *, run: dict[str, Any], service_id: str, runtime_role: str, instruction: str,
        context: list[dict[str, Any]], model_preference: str | None, suffix: str,
        max_output_tokens: int = 4096,
        max_elapsed_ms: int = DURABLE_REQUEST_TIMEOUT_MS,
        max_model_request_ms: int | None = DURABLE_REQUEST_TIMEOUT_MS,
    ) -> tuple[AgentJob, AgentResult]:
        assert_secret_free(context, label=f"{runtime_role} context")
        stable_id = fingerprint({"run_id": run["run_id"], "role": runtime_role, "context": context, "instruction": instruction})[7:31]
        scope = self._execution_scope(run_id=str(run["run_id"]))
        if scope is None:
            raise ProductionRunError("execution_lease_required", "production AgentJob requires a frozen execution budget")
        try:
            remaining_cost = self.stage_repository.remaining_cost_budget(scope["project_id"], str(run["run_id"]))
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)
        if remaining_cost <= 0:
            raise ProductionRunError("run_cost_budget_exhausted", "frozen production cost budget is exhausted before dispatch")
        job = AgentJob(
            job_id=f"job_{run['run_id']}_{stable_id}",
            session_id=str(run.get("session_id") or f"session:{run['run_id']}"), run_id=str(run["run_id"]),
            task_mode=str(run["task_mode"]), runtime_role=runtime_role, service_id=service_id,
            instruction=instruction, context=context, model_preference=model_preference,
            required_model_capabilities=(
                {"text", "fiction_writing"} if runtime_role == "surface_realization" else {"text"}
            ), authority={},
            budgets=AgentBudget(max_steps=1, max_model_requests=1, max_tool_calls=1, max_parallel_tool_calls=1,
                                model_context_limit=200_000, max_output_tokens=max_output_tokens,
                                run_cost_budget=remaining_cost,
                                max_elapsed_ms=max_elapsed_ms, max_model_request_ms=max_model_request_ms),
            idempotency_key=f"{run['run_id']}:{suffix}:{stable_id}",
        )
        return job, self._invoke_agent(job)

    @staticmethod
    def materialize_stage_context(bundle: dict[str, Any], mechanism: str) -> dict[str, Any]:
        if bundle.get("schema") != PRODUCTION_BUNDLE_SCHEMA:
            raise ProductionRunError("context_bundle_invalid", "production context bundle schema mismatch")
        try:
            context_stage_id = MECHANISM_CONTEXT_STAGE[mechanism]
        except KeyError as exc:
            raise ProductionRunError("unknown_production_mechanism", mechanism) from exc
        projection = stage_context(bundle["freeze"], context_stage_id)
        loaded_ids = [str(row["object_id"]) for row in projection.get("selected", []) if isinstance(row, dict) and row.get("object_id")]
        payloads = bundle.get("source_payloads") or {}
        missing = [object_id for object_id in loaded_ids if object_id not in payloads]
        if missing:
            raise ProductionRunError("frozen_payload_missing", "Context Freeze selected payloads missing from immutable bundle", detail=missing)
        items = [deepcopy(payloads[object_id]) for object_id in loaded_ids]
        withheld: list[str] = []
        if mechanism in {"reader_pressure", "surface_realization"}:
            safe_items = []
            for item in items:
                kind = item.get("object_type")
                if kind == "character_knowledge":
                    withheld.append(str(item["object_id"]))
                    continue
                if kind in {"character", "relationship"}:
                    allowed = ("character_id", "name", "voice_notes") if kind == "character" else (
                        "relationship_id", "participant_a", "participant_b", "relationship_type"
                    )
                    view = item.get("model_view") or {}
                    item["model_view"] = {key: deepcopy(view[key]) for key in allowed if key in view}
                safe_items.append(item)
            items = safe_items
        materialized = {
            "mechanism": mechanism,
            "context_stage_id": context_stage_id,
            "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "loaded_object_ids": loaded_ids,
            "items": items,
            "withheld_private_object_ids": withheld,
            "selector": projection.get("selector"),
            "db_fetch_performed": False,
            "authority": False,
        }
        if mechanism in {"reader_pressure", "surface_realization"}:
            author_model = (bundle.get("target_context") or {}).get("author_model")
            if isinstance(author_model, dict):
                materialized["author_model"] = {key: deepcopy(author_model[key]) for key in (
                    "schema", "project_id", "priority_order", "explicit_intent", "selected_hypothesis_ids", "active_preferences",
                    "all_active_preferences_auto_included", "authority",
                ) if key in author_model}
        materialized["stage_context_fingerprint"] = fingerprint({key: materialized[key] for key in materialized if key != "authority"})
        return materialized

    @staticmethod
    def _stage_instruction(mechanism: str, user_instruction: str) -> str:
        common = (
            "Return exactly one JSON object for only the named production mechanism. "
            "The user request supplies task context; do not execute other stages, use tools, fetch missing records, "
            "write project state, accept a candidate, or settle a chapter. Do not expose private reasoning or credentials. "
            "Frozen source authority, canon_authority, project_write_authority and model_execution flags describe "
            "the source records and their permissions or provenance, not a denial of this dispatched semantic job. "
            "db_fetch_performed=false means the supplied projection was read from the frozen bundle without another fetch; "
            "it does not make its supplied contents unavailable or authorize a new lookup. "
            "Active plans and proposals may constrain proposed fiction without being accepted Canon. "
            "Respect their explicit hard bounds, but never promote planned events or proposed details into prior accepted facts. "
            "Returning an internal proposal or judgment grants no Canon, project-write, author-acceptance or settlement authority. "
        )
        if mechanism == "surface_realization":
            return (
                "Return exactly one JSON object. Do not use tools, expose private reasoning, write project state, "
                "accept or settle the candidate. " + WRITER_REALIZATION_GUIDANCE +
                "Treat writer_pack.author_objectives and writer_pack.director_note as the exact current task; "
                "For a fresh/direct realization return {\"status\":\"pass\"|\"fail\",\"text\":string,"
                "\"summary\":string,\"findings\":[]}. For bounded local repair return "
                "{\"status\":\"pass\"|\"fail\",\"edits\":[{\"target_id\":string,\"replacement_text\":string}],"
                "\"summary\":string,\"findings\":[]}. Follow the writer_pack mode. "
                "Directive version: " + WRITER_DIRECTIVE_VERSION
            )
        if mechanism == "story_canon_preflight":
            return common + (
                "Execute story_canon_preflight for the exact supplied target_context. Do not draft or require an already accepted chapter. "
                "Check the actual availability of materials explicitly required by the task, and whether proposed work conflicts "
                "with supplied accepted or locked facts, chronology, knowledge boundaries or explicit hard constraints. "
                "An original chapter may begin with no accepted Canon; creative choices may remain for later proposal stages. "
                "Do not fail solely because inputs are non-authoritative or the proposed events have not been accepted. "
                "Fail for a real blocking conflict or genuinely missing required material; do not invent or fetch it, assume a pass, "
                "or soften an actual failure. A pass permits only the next internal stage, subject to all later gates. "
                "JSON: {\"status\":\"pass\"|\"fail\",\"summary\":string,\"findings\":[string]}. Request: "
            ) + user_instruction
        if mechanism == "continuity":
            return common + (
                "Execute continuity for the exact supplied target_context and upstream candidate. Compare the candidate with "
                "the frozen established facts, story order, character knowledge boundaries and explicit hard constraints. "
                "Distinguish active-plan intentions from events already established in the story. Candidate prose is still a proposal; "
                "lack of author acceptance is not itself a continuity defect. Report actual contradictions or missing required evidence "
                "as fail; never repair the candidate or soften a real gate result. "
                "JSON: {\"status\":\"pass\"|\"fail\",\"summary\":string,\"findings\":[string]}. Request: "
            ) + user_instruction
        return common + f"Execute Quillframe mechanism {mechanism}. JSON: {{\"status\":\"pass\"|\"fail\",\"artifact\":object,\"summary\":string,\"findings\":[string]}}. Request: " + user_instruction

    def _run_stage(
        self,
        run: dict[str, Any],
        bundle: dict[str, Any],
        mechanism: str,
        *,
        service_id: str,
        user_instruction: str,
        model_preference: str | None,
        artifacts: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        repair = artifacts.get("repair")
        if repair and mechanism == "scene_simulation":
            user_instruction = generation_instruction(user_instruction, repair)
        if mechanism == "character_simulation":
            return self._run_character_stage(run, bundle, service_id=service_id, user_instruction=user_instruction, model_preference=model_preference)
        if mechanism == "scene_simulation":
            return self._run_scene_stage(run, bundle, service_id=service_id, user_instruction=user_instruction, model_preference=model_preference, artifacts=artifacts)
        if mechanism == "reader_pressure":
            return self._run_reader_pressure_stage(run, bundle, service_id=service_id, user_instruction=user_instruction, model_preference=model_preference, artifacts=artifacts)
        frozen_stage = self.materialize_stage_context(bundle, mechanism)
        upstream: dict[str, Any] = {}
        if mechanism == "reader_pressure":
            projection = (artifacts.get("scene_simulation") or {}).get("artifact")
            if not isinstance(projection, dict) or projection.get("projection_fingerprint") != fingerprint({
                key: value for key, value in projection.items() if key not in {"projection_fingerprint", "authority"}
            }):
                raise ProductionRunError("writer_projection_missing", "Writer requires an exact registered scene realization projection")
            upstream["writer_projection"] = deepcopy(projection)
        if mechanism == "continuity":
            candidate = artifacts.get("surface_realization") or {}
            upstream["candidate"] = {key: candidate.get(key) for key in ("text", "artifact_fingerprint")}
        context = [{"target_context": self._target_context(bundle)}]
        if mechanism != "surface_realization":
            context[0]["frozen_stage_context"] = frozen_stage
            context[0]["upstream_artifacts"] = upstream
        if mechanism == "surface_realization":
            scene = artifacts.get("scene_simulation") or {}
            binding = scene.get("projection_binding") or {}
            if binding.get("binding_fingerprint") != fingerprint({"job": binding.get("job"), "result": binding.get("result")}):
                raise ProductionRunError("craft_snapshot_invalid", "craft selection binding changed")
            guidance = materialize_writer_craft(
                artifacts.get("craft_snapshot"), binding["result"]["judgment"].get("craft_selection"),
                projection_input=scene.get("craft_projection_input") or binding["job"]["input"]["payload"],
                binding_fingerprint=binding["binding_fingerprint"],
            )
            if guidance != scene.get("craft_guidance"):
                raise ProductionRunError("craft_snapshot_invalid", "Writer craft projection differs from its confirmed selection")
            repair_projection = None
            if repair:
                repair_projection = writer_context(
                    artifacts["repair_source"], repair, frozen_stage,
                )
            projection = scene.get("artifact") or {}
            pack = materialize_writer_pack(
                scene.get("writer_context_inventory"),
                selected_context_ids=projection.get("selected_context_ids"),
                scene_contract=projection.get("scene_contract"),
                director_note=projection.get("director_note"),
                author_objectives=scene.get("author_objectives"),
                source_binding_fingerprint=binding["binding_fingerprint"],
                craft_guidance=guidance,
                repair_context=repair_projection,
            )
            context[0]["writer_pack"] = pack
        job, result = self._agent_job(
            run=run,
            service_id=service_id,
            runtime_role=mechanism,
            instruction=self._stage_instruction(mechanism, user_instruction),
            context=context,
            model_preference=model_preference,
            suffix=mechanism,
            max_output_tokens=7000 if mechanism == "surface_realization" else 3000,
            # Complete prose may need a longer response. This changes only the
            # frozen time budget, never the writing requirements or gate rules.
            max_elapsed_ms=DURABLE_REQUEST_TIMEOUT_MS,
            max_model_request_ms=DURABLE_REQUEST_TIMEOUT_MS,
        )
        if result.status != "completed":
            raise ProductionRunError(
                "semantic_pending" if result.status in {"model_failed", "cancelled"} else "failed_gate",
                f"production mechanism {mechanism} did not complete",
                detail={"agent_status": result.status, "errors": result.errors},
            )
        judgment = parse_json_object(result.final_text, label=mechanism)
        status = judgment.get("status")
        if not isinstance(status, str) or status not in {"pass", "fail"}:
            raise ProductionRunError("semantic_output_invalid", f"{mechanism}.status must be pass|fail")
        if mechanism == "surface_realization":
            local = bool(repair and repair["policy"]["generation_mode"] == "local_or_bounded_repair")
            if local and status == "pass":
                judgment["text"] = self._apply_bounded_writer_edits(
                    artifacts["repair_source"], repair, judgment.get("edits")
                )
            text = judgment.get("text")
            if status == "pass" and (not isinstance(text, str) or not text.strip()):
                raise ProductionRunError("semantic_output_invalid", "surface_realization pass result requires candidate prose")
            if isinstance(text, str):
                judgment["artifact_fingerprint"] = fingerprint_text(text)
        elif "artifact" in judgment:
            judgment["artifact_fingerprint"] = fingerprint(judgment["artifact"])
        if mechanism == "reader_pressure" and status == "pass" and not isinstance(judgment.get("artifact"), dict):
            raise ProductionRunError("semantic_output_invalid", "Reader Pressure pass requires a causal artifact for Writer")
        self._confirm_agent_validation(
            job,
            validation_kind="production_stage:" + mechanism,
            validated_value=judgment,
        )
        public = public_stage_result(
            mechanism=mechanism,
            context_stage_id=frozen_stage["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=frozen_stage["stage_context_fingerprint"],
            agent_input_fingerprint=job.input_fingerprint,
            model_service_id=result.model_service_id,
            model_id=result.model_id,
            protocol=result.protocol,
            judgment=judgment,
        )
        return public, deepcopy(judgment)

    @staticmethod
    def _target_context(bundle: dict[str, Any]) -> dict[str, Any]:
        target = bundle.get("target_context")
        if not isinstance(target, dict) or any(not isinstance(target.get(key), str) or not target[key] for key in ("chapter_id", "document_id")):
            raise ProductionRunError("target_context_missing", "production requires a frozen chapter/document target")
        for key in ("current_story_order", "current_reading_order"):
            order = target.get(key)
            if not isinstance(order, int) or isinstance(order, bool) or order < 0:
                raise ProductionRunError("target_context_missing", f"production requires a frozen {key} cutoff")
        return {key: target[key] for key in ("chapter_id", "document_id", "current_story_order", "current_reading_order")}

    @staticmethod
    def _apply_bounded_writer_edits(
        source: dict[str, Any], repair: dict[str, Any], edits: Any
    ) -> str:
        if not isinstance(edits, list):
            raise ProductionRunError("semantic_output_invalid", "bounded Writer must return edits")
        windows = {
            target["target_id"]: target["edit_window_quote"]
            for target in repair["policy"]["targets"]
            if target["route"] == "local_edit"
        }
        if (
            len(edits) != len(windows)
            or {item.get("target_id") for item in edits if isinstance(item, dict)} != set(windows)
        ):
            raise ProductionRunError(
                "semantic_output_invalid",
                "bounded Writer edits must match the exact target set",
            )
        replacements = {}
        for item in edits:
            replacement = item.get("replacement_text")
            if not isinstance(replacement, str):
                raise ProductionRunError(
                    "semantic_output_invalid",
                    "bounded Writer replacement_text must be a string",
                )
            replacements[item["target_id"]] = replacement
        text = source["candidate_text"]
        spans = []
        for target_id, window in windows.items():
            if text.count(window) != 1:
                raise ProductionRunError(
                    "repair_target_invalid",
                    "bounded edit window must occur exactly once in the source candidate",
                )
            start = text.index(window)
            spans.append((start, start + len(window), target_id))
        spans.sort()
        if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
            raise ProductionRunError("repair_target_invalid", "bounded edit windows overlap")
        for start, end, target_id in reversed(spans):
            text = text[:start] + replacements[target_id] + text[end:]
        return text

    def _causal_stage_receipt(
        self, *, bundle: dict[str, Any], mechanism: str, bindings: list[dict[str, Any]],
        internal: dict[str, Any], preparation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        frozen = self.materialize_stage_context(bundle, mechanism)
        identities = [{
            "contract_id": binding["contract_id"], "subject_id": binding["job"]["subject_id"],
            "input_fingerprint": binding["job"]["input_fingerprint"],
            "result_fingerprint": fingerprint(binding["result"]), "binding_fingerprint": binding["binding_fingerprint"],
        } for binding in bindings]
        worker = bindings[-1]["result"]["worker"] if bindings else (preparation or {})
        artifact_fp = fingerprint({"contracts": identities, "preparation": preparation, "artifact": internal.get("artifact")})
        internal["artifact_fingerprint"] = artifact_fp
        public = public_stage_result(
            mechanism=mechanism, context_stage_id=frozen["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"], freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=frozen["stage_context_fingerprint"],
            agent_input_fingerprint=fingerprint([binding["result"]["worker"]["agent_input_fingerprint"] for binding in bindings] or [preparation]),
            model_service_id=str(worker.get("model_service_id") or ""), model_id=str(worker.get("model_or_reviewer") or ""),
            protocol=str(worker.get("protocol") or ""),
            judgment={"status": internal["status"], "summary": "Bounded causal contracts completed; private simulation remains internal.",
                      "findings": [], "artifact_fingerprint": artifact_fp},
        )
        public["registered_contracts"] = identities
        public["stage_result_fingerprint"] = fingerprint({key: value for key, value in public.items() if key != "stage_result_fingerprint"})
        return public

    def _run_character_stage(
        self, run: dict[str, Any], bundle: dict[str, Any], *, service_id: str,
        user_instruction: str, model_preference: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        frozen = self.materialize_stage_context(bundle, "character_simulation")
        target = self._target_context(bundle)
        payloads = character_action_payloads(frozen, target)
        preparation = None
        if not payloads:
            # A new project has no accepted cast. Any initial cast is a model
            # proposal bound to the request, not code-authored Canon or a
            # fabricated existing character. Existing selected cast uses only
            # each actor's own frozen state above.
            instruction = (
                "Prepare the minimal proposed cast needed for this new chapter from the supplied request and frozen context. "
                "This is a proposal, never accepted Canon. Return only JSON matching the supplied output_contract. "
                "For original DRAFT/REVISE work, you may propose concrete starting circumstances, observable obstacles or resources, "
                "and personally acquired memory sources where the request and plans leave details open. "
                "These additions must remain compatible with every frozen hard bound and accepted fact; they do not replace existing Canon. "
                "Make the proposed starting situation causally usable by each actor, including how that actor could observe or learn the evidence. "
                "Missing creative detail is not by itself a missing external fact: supply a bounded proposal when the authorized fiction task allows it. "
                "Do not prescribe the next action, force a planned outcome, invent prior accepted events, or give actors knowledge of later events. "
                "Each character is one character.action_propose input with character_id, current_story_order (exact supplied cutoff), "
                "active_agenda (nonempty string), perceived_state (object), immediate_situation (object), perspective_memory (object). "
                "Use only character-visible information, never a planned outcome or another character's private knowledge. "
                "perceived_state may contain only a qualitative summary string; do not place evidence arrays or IDs there. "
                "Put every observation only in immediate_situation.observables, with observable_id, observation, source_ref and available_from_story_order. "
                "perspective_memory must contain exactly episodic_visible_events, visibility_tagged_facts and situation_patterns (empty arrays are valid). "
                "Every memory fact belongs in perspective_memory.visibility_tagged_facts and uses fact_id, claim, source_ref and available_from_story_order. "
                "Every episodic event uses event_id, source_ref and available_from_story_order; every situation pattern uses pattern_id, evidence_ref and available_from_story_order. "
                "Never use aliases such as perspective_memory.facts or perceived_state.observables. "
                "All evidence IDs must be unique within the character, and every availability order must be at or before the supplied cutoff. "
                "Do not serialize chain-of-thought. "
                "At most 12 characters. If this chapter needs no acting characters, an empty array is valid; explain briefly. "
                "Do not create prose or modify existing Canon."
            )
            job, result = self._agent_job(
                run=run, service_id=service_id, runtime_role="character_state_prepare", instruction=instruction,
                context=[{"request": user_instruction, "target_context": target, "frozen_stage_context": frozen,
                          "output_contract": character_state_prepare_contract()}],
                model_preference=model_preference, suffix="character-state-prepare", max_output_tokens=4800,
            )
            if result.status != "completed":
                raise ProductionRunError("semantic_pending", "character preparation has no confirmed completed output")
            judgment = parse_json_object(result.final_text, label="character_state_prepare")
            if judgment.get("status") != "pass":
                raise ProductionRunError("failed_gate" if judgment.get("status") == "fail" else "semantic_output_invalid", "character preparation did not pass")
            payloads = prepared_character_action_payloads(judgment, target)
            ids = [payload["character_id"] for payload in payloads]
            existing_ids = {row["model_view"].get("character_id") for row in bundle.get("source_payloads", {}).values() if row.get("object_type") == "character"}
            if existing_ids.intersection(ids):
                raise ProductionRunError("character_context_incomplete", "new cast proposal cannot replace an existing character absent from its frozen stage")
            self._confirm_agent_validation(
                job,
                validation_kind="production_stage:character_state_prepare",
                validated_value=judgment,
            )
            preparation = {
                "agent_job_id": job.job_id, "agent_input_fingerprint": job.input_fingerprint,
                "model_service_id": result.model_service_id, "model_or_reviewer": result.model_id,
                "protocol": result.protocol, "result_fingerprint": fingerprint(result.to_dict()),
            }
        registered = RegisteredSemanticExecutor(
            self.agent_runtime, invoke=self._invoke_agent,
            confirm_validation=self._confirm_registered_validation,
        )
        bindings = [registered.execute(
            run=run, service_id=service_id, contract_id="character.action_propose", subject_id=payload["character_id"],
            payload=payload, model_preference=model_preference, runtime_role="registered_character_action", max_output_tokens=2600,
        ) for payload in payloads]
        internal = {"status": "pass", "action_bindings": bindings, "artifact": {"character_count": len(bindings)}, "preparation": preparation}
        return self._causal_stage_receipt(bundle=bundle, mechanism="character_simulation", bindings=bindings, internal=internal, preparation=preparation), internal

    def _select_user_taste(
        self,
        run: dict[str, Any],
        bundle: dict[str, Any],
        *,
        service_id: str,
        user_instruction: str,
        model_preference: str | None,
        resolved: dict[str, Any],
        artifacts: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Freeze one semantic selection without exposing evidence to Writer.

        A repair inherits the source run's exact selection and snapshot. Normal
        resume reuses the current run checkpoint. The semantic result decides
        relevance only; the already-frozen standing policy owns eligibility.
        """
        scope = self._execution_scope(run_id=run["run_id"])
        if scope is None:
            raise ProductionRunError("execution_lease_required", "user_taste selection requires the production lease")
        project_id = scope["project_id"]
        checkpoint_kind = "production_user_taste_selection"

        def validate_selection_state(state: Any) -> None:
            if not isinstance(state, dict) or state.get("schema") != "quillframe_run_user_taste_selection_v1":
                raise ProductionRunError("user_taste_selection_invalid", "stored user_taste selection schema is invalid")
            expected_state = fingerprint({
                key: value for key, value in state.items() if key != "selection_fingerprint"
            })
            if state.get("selection_fingerprint") != expected_state:
                raise ProductionRunError("user_taste_selection_invalid", "stored user_taste selection changed")
            snapshot = state.get("snapshot")
            binding = state.get("binding")
            if not isinstance(snapshot, dict) or not isinstance(binding, dict):
                raise ProductionRunError("user_taste_selection_invalid", "stored user_taste selection is incomplete")
            try:
                validate_user_taste_snapshot(snapshot)
            except ValueError as exc:
                raise ProductionRunError("user_taste_selection_invalid", str(exc)) from exc
            if binding.get("binding_fingerprint") != fingerprint({"job": binding.get("job"), "result": binding.get("result")}):
                raise ProductionRunError("user_taste_selection_invalid", "stored user_taste semantic binding changed")
            job = binding.get("job")
            result = binding.get("result")
            errors = (
                validate_registered_job(job) + validate_semantic_result(job, result)
                if isinstance(job, dict) and isinstance(result, dict)
                else ["registered user_taste job/result required"]
            )
            input_obj = job.get("input") if isinstance(job, dict) else None
            payload = input_obj.get("payload") if isinstance(input_obj, dict) else None
            if not isinstance(payload, dict) or input_obj.get("model_contract_id") != "learning.preference_select":
                errors.append("learning.preference_select binding required")
            elif (
                payload.get("policy_fingerprint") != snapshot["policy"]["fingerprint"]
                or payload.get("candidate_fingerprint") != snapshot["candidate_fingerprint"]
                or payload.get("candidates") != snapshot["candidates"]
            ):
                errors.append("user_taste semantic input does not bind the frozen snapshot")
            if errors:
                raise ProductionRunError("user_taste_selection_invalid", "; ".join(errors))
            try:
                guidance = materialize_user_taste_selection(
                    snapshot, result["judgment"].get("selected"),
                    binding_fingerprint=binding["binding_fingerprint"],
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ProductionRunError("user_taste_selection_invalid", str(exc)) from exc
            if guidance != state.get("guidance"):
                raise ProductionRunError("user_taste_selection_invalid", "stored user_taste guidance changed")

        prior = self._latest_checkpoint(project_id, run["run_id"], checkpoint_kind)
        if prior is not None:
            validate_selection_state(prior)
            return prior

        repair_source = artifacts.get("repair_source")
        if isinstance(repair_source, dict):
            source_run_id = repair_source.get("source_run_id")
            inherited = self._latest_checkpoint(project_id, str(source_run_id), checkpoint_kind) if source_run_id else None
            if inherited is not None:
                validate_selection_state(inherited)
                inherited_state = deepcopy(inherited)
                inherited_state["inherited_from_run"] = source_run_id
                inherited_state["selection_fingerprint"] = fingerprint({
                    key: value for key, value in inherited_state.items() if key != "selection_fingerprint"
                })
                self._checkpoint(
                    project_id, run["run_id"], checkpoint_kind, inherited_state,
                    inherited_state["selection_fingerprint"],
                )
                return inherited_state

        author_model = (bundle.get("target_context") or {}).get("author_model")
        snapshot = author_model.get("user_taste_snapshot") if isinstance(author_model, dict) else None
        if snapshot is None:
            return None
        try:
            validate_user_taste_snapshot(snapshot)
        except ValueError as exc:
            raise ProductionRunError("user_taste_selection_invalid", str(exc)) from exc
        if isinstance(repair_source, dict) and snapshot.get("policy", {}).get("enabled") and snapshot.get("candidates"):
            raise ProductionRunError(
                "fresh_run_required",
                "repair source predates its exact user_taste selection; create a fresh run instead of changing the repair objective",
            )
        payload = user_taste_selection_payload(
            snapshot,
            request=user_instruction,
            scene_context={
                "scene_id": (bundle.get("target_context") or {}).get("chapter_id"),
                "resolved_trajectory": {
                    "input_fingerprint": resolved["job"]["input_fingerprint"],
                    "result_fingerprint": fingerprint(resolved["result"]),
                    "judgment": deepcopy(resolved["result"]["judgment"]),
                },
            },
        )
        if payload is None:
            return None
        binding = RegisteredSemanticExecutor(
            self.agent_runtime, invoke=self._invoke_agent,
            confirm_validation=self._confirm_registered_validation,
        ).execute(
            run=run, service_id=service_id, contract_id="learning.preference_select",
            subject_id=str((bundle.get("target_context") or {}).get("chapter_id") or run["run_id"]),
            payload=payload, model_preference=model_preference,
            runtime_role="registered_user_taste_selection", max_output_tokens=2400,
        )
        try:
            guidance = materialize_user_taste_selection(
                snapshot, binding["result"]["judgment"].get("selected"),
                binding_fingerprint=binding["binding_fingerprint"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProductionRunError("semantic_output_invalid", str(exc)) from exc
        state = {
            "schema": "quillframe_run_user_taste_selection_v1",
            "snapshot": deepcopy(snapshot),
            "binding": binding,
            "guidance": guidance,
            "inherited_from_run": None,
            "authority": False,
        }
        state["selection_fingerprint"] = fingerprint(state)
        self._checkpoint(project_id, run["run_id"], checkpoint_kind, state, state["selection_fingerprint"])
        return state

    def _run_scene_stage(
        self, run: dict[str, Any], bundle: dict[str, Any], *, service_id: str,
        user_instruction: str, model_preference: str | None, artifacts: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        target = self._target_context(bundle)
        character = artifacts.get("character_simulation") or {}
        actions = character.get("action_bindings")
        if not isinstance(actions, list):
            raise ProductionRunError("character_actions_missing", "Scene resolver requires confirmed character action bindings")
        # The resolver needs the actual evidence behind an action, not only its
        # cited IDs. Keep this private, fingerprint-bound input on the causal
        # side of the writer-safe realization boundary.
        evidence = [{
            "character_id": binding["job"]["subject_id"], "input_fingerprint": binding["job"]["input_fingerprint"],
            "bounded_input": deepcopy(binding["job"]["input"]["payload"]),
            "input_is_proposed_cast": character.get("preparation") is not None, "authority": False,
            "result_fingerprint": fingerprint(binding["result"]), "judgment": deepcopy(binding["result"]["judgment"]),
        } for binding in actions]
        registered = RegisteredSemanticExecutor(
            self.agent_runtime, invoke=self._invoke_agent,
            confirm_validation=self._confirm_registered_validation,
        )
        scene_id = target["chapter_id"]
        frozen_scene = self.materialize_stage_context(bundle, "scene_simulation")
        direction_evidence = author_direction_evidence(
            user_instruction, artifacts.get("repair")
        )
        writer_inventory = build_writer_inventory(
            frozen_scene,
            character_action_evidence=evidence,
            author_model=(bundle.get("target_context") or {}).get("author_model"),
        )
        resolved = registered.execute(
            run=run, service_id=service_id, contract_id="scene.resolve_actions", subject_id=scene_id,
            payload={"scene_id": scene_id, "current_story_order": target["current_story_order"],
                     "request": user_instruction, "character_action_evidence": evidence,
                     "frozen_scene_context": frozen_scene},
            model_preference=model_preference, runtime_role="registered_scene_resolution", max_output_tokens=3600,
        )
        if resolved["result"]["judgment"]["repair_routes"]:
            internal = {"status": "fail", "resolved_binding": resolved, "artifact": {"repair_routes": resolved["result"]["judgment"]["repair_routes"]}}
            return self._causal_stage_receipt(bundle=bundle, mechanism="scene_simulation", bindings=[resolved], internal=internal), internal
        projected = registered.execute(
            run=run, service_id=service_id, contract_id="scene.realization_project", subject_id=scene_id,
            payload={"scene_id": scene_id, "resolved_trajectory": {
                "judgment": resolved["result"]["judgment"], "input_fingerprint": resolved["job"]["input_fingerprint"],
                "result_fingerprint": fingerprint(resolved["result"]),
            }, "character_action_evidence": evidence,
                "pov_boundary": {**target, "private_state_may_not_be_serialized": True},
                "task_context": {"request": user_instruction},
                "author_direction_evidence": direction_evidence,
                "writer_context_inventory": model_inventory(writer_inventory),
                **selection_input(artifacts.get("craft_snapshot"), frozen_scene)},
            model_preference=model_preference, runtime_role="registered_scene_projection", max_output_tokens=3000,
        )
        internal = {"status": "pass", "artifact": writer_safe_projection(projected, scene_id=scene_id),
                    "resolved_binding": resolved, "projection_binding": projected,
                    "writer_context_inventory": writer_inventory,
                    "author_objectives": materialize_author_objectives(
                        direction_evidence,
                        projected["result"]["judgment"].get("author_objective_items"),
                    ),
                    "craft_guidance": materialize_writer_craft(
                        artifacts.get("craft_snapshot"), projected["result"]["judgment"].get("craft_selection"),
                        projection_input=projected["job"]["input"]["payload"],
                        binding_fingerprint=projected["binding_fingerprint"],
                    )}
        return self._causal_stage_receipt(bundle=bundle, mechanism="scene_simulation", bindings=[resolved, projected], internal=internal), internal

    def _run_reader_pressure_stage(
        self, run: dict[str, Any], bundle: dict[str, Any], *, service_id: str,
        user_instruction: str, model_preference: str | None, artifacts: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        frozen = self.materialize_stage_context(bundle, "reader_pressure")
        projection = (artifacts.get("scene_simulation") or {}).get("artifact")
        if not isinstance(projection, dict) or projection.get("projection_fingerprint") != fingerprint({
            key: value for key, value in projection.items() if key not in {"projection_fingerprint", "authority"}
        }):
            raise ProductionRunError("writer_projection_missing", "Reader Pressure requires an exact registered writer-safe scene projection")
        sources = [{"source_ref": "scene-projection:" + projection["projection_fingerprint"], "content": projection}]
        # Reader Pressure predicts from the writer-safe current scene, exact
        # settled reading history and the existing reader-expectation ledger.
        # Raw plans, character state, research and world inventories belong on
        # the causal side of the scene projection. Passing them through here
        # would reveal future/private planning and let a pre-draft reader model
        # mistake author intent for something the reader has observed.
        reader_source_types = {"accepted_manuscript"}
        for row in frozen["items"]:
            reader_ledger = (
                row.get("object_type") == "runtime_state"
                and row.get("domain") == "reader_pressure"
            )
            if row.get("object_type") not in reader_source_types and not reader_ledger:
                continue
            sources.append({
                "source_ref": row["object_id"],
                "source_fingerprint": row["source_fingerprint"],
                "authority": row["authority"],
                "content": row["model_view"],
            })
        payload = {"chapter_id": bundle["target_context"]["chapter_id"],
                   "current_reading_order": bundle["target_context"]["current_reading_order"],
                   "author_request": user_instruction, "sources": sources}
        payload.update(reading_positioning_fields(
            artifacts.get("reading_positioning"), target_context=bundle["target_context"],
            reader_grip=(self._execution_scope(run_id=run["run_id"]) or {}).get("reader_grip"),
            execution_request_fingerprint=(self._execution_scope(run_id=run["run_id"]) or {}).get("request_fingerprint"),
        ))
        if isinstance(frozen.get("author_model"), dict):
            payload["author_model"] = frozen["author_model"]
        binding = RegisteredSemanticExecutor(
            self.agent_runtime, invoke=self._invoke_agent,
            confirm_validation=self._confirm_registered_validation,
        ).execute(
            run=run, service_id=service_id, contract_id="reader.pressure", subject_id=bundle["target_context"]["chapter_id"],
            payload=payload, model_preference=model_preference, runtime_role="registered_reader_pressure", max_output_tokens=3000,
        )
        judgment = binding["result"]["judgment"]
        allowed = {source["source_ref"] for source in sources}
        if any(ref not in allowed for point in judgment["pressure_points"] for ref in point["evidence_refs"]):
            raise ProductionRunError("semantic_output_invalid", "Reader Pressure cites an unknown source identity")
        artifact = deepcopy(judgment)
        artifact_fp = fingerprint(artifact)
        worker = binding["result"]["worker"]
        public = public_stage_result(
            mechanism="reader_pressure", context_stage_id=frozen["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"], freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=frozen["stage_context_fingerprint"], agent_input_fingerprint=worker["agent_input_fingerprint"],
            model_service_id=worker["model_service_id"], model_id=worker["model_or_reviewer"], protocol=worker["protocol"],
            judgment={"status": judgment["status"], "summary": judgment["summary"], "artifact_fingerprint": artifact_fp},
        )
        public["model_contract_id"] = "reader.pressure"
        public["registered_contract_binding_fingerprint"] = binding["binding_fingerprint"]
        public["stage_result_fingerprint"] = fingerprint({key: value for key, value in public.items() if key != "stage_result_fingerprint"})
        return public, {"status": judgment["status"], "artifact": artifact, "artifact_fingerprint": artifact_fp}

    def _reader_history(self, bundle: dict[str, Any]) -> list[dict[str, Any]]:
        frozen = self.materialize_stage_context(bundle, "reader_engagement")
        return [{"source_ref": "chapter:" + row["model_view"]["story_node_id"],
                 "chapter_id": row["model_view"]["story_node_id"], "revision_id": row["model_view"]["revision_id"],
                 "content_fingerprint": row["model_view"]["content_fingerprint"],
                 "reading_order": row["model_view"]["reading_order"], "content": row["model_view"]["content"]}
                for row in frozen["items"] if row["object_type"] == "accepted_manuscript"]

    def _registered_stage_receipt(
        self,
        *,
        bundle: dict[str, Any],
        mechanism: str,
        binding: dict[str, Any],
        candidate_fingerprint: str,
    ) -> dict[str, Any]:
        frozen_stage = self.materialize_stage_context(bundle, mechanism)
        semantic_result = binding["result"]
        judgment = semantic_result["judgment"]
        worker = semantic_result.get("worker") or {}
        public_judgment = {
            "status": semantic_status(binding),
            "summary": judgment.get("report"),
            "findings": judgment.get("evidence_refs", []),
            "artifact_fingerprint": candidate_fingerprint,
        }
        receipt = public_stage_result(
            mechanism=mechanism,
            context_stage_id=frozen_stage["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=frozen_stage["stage_context_fingerprint"],
            agent_input_fingerprint=binding["job"]["input_fingerprint"],
            model_service_id=str(worker.get("model_service_id") or worker.get("provider") or "registered_semantic_worker"),
            model_id=str(worker.get("model_or_reviewer") or "registered-reviewer"),
            protocol=str(worker.get("protocol") or "registered_model_contract"),
            judgment=public_judgment,
        )
        receipt["model_contract_id"] = binding["job"]["input"]["model_contract_id"]
        receipt["registered_contract_binding_fingerprint"] = binding.get("binding_fingerprint") or fingerprint({"job": binding["job"], "result": semantic_result})
        receipt["stage_result_fingerprint"] = fingerprint({key: value for key, value in receipt.items() if key != "stage_result_fingerprint"})
        return receipt

    def _persist_stage_receipt(
        self,
        project_id: str,
        run_id: str,
        receipt: dict[str, Any],
        *,
        effect_guard: Callable[[Any], None] | None = None,
    ) -> None:
        assert_secret_free(receipt, label="production stage receipt")
        key = f"{run_id}:stage:{receipt['mechanism']}"
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            if effect_guard is not None:
                effect_guard(conn)
            existing = conn.execute("SELECT payload_json FROM receipts WHERE idempotency_key=?", (key,)).fetchone()
            if existing:
                prior = _json(existing["payload_json"], {})
                if prior.get("stage_result_fingerprint") != receipt.get("stage_result_fingerprint"):
                    raise ProductionRunError("stage_replay_conflict", f"stage receipt changed for immutable idempotency key: {key}")
                conn.commit()
                return
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, run_id, "production_stage", key, canonical_json(receipt), now_iso()),
            )
            conn.execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                (
                    "evt_" + uuid.uuid4().hex,
                    run_id,
                    "production_stage_completed",
                    canonical_json({
                        "mechanism": receipt["mechanism"],
                        "stage_result_fingerprint": receipt["stage_result_fingerprint"],
                        "context_bundle_fingerprint": receipt["context_bundle_fingerprint"],
                    }),
                    now_iso(),
                ),
            )
            conn.commit()

    def _checkpoint(self, project_id: str, run_id: str, kind: str, state: dict[str, Any], artifact_fingerprint: str) -> None:
        assert_secret_free(state, label=kind)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            conn.execute(
                "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,?,?,?,?)",
                ("ckpt_" + uuid.uuid4().hex, run_id, kind, canonical_json(state), artifact_fingerprint, now_iso()),
            )
            conn.commit()

    def _checkpoint_once(
        self, project_id: str, run_id: str, *, checkpoint_id: str, kind: str,
        state: dict[str, Any], artifact_fingerprint: str,
    ) -> None:
        """Persist one deterministic recovery checkpoint or exact-replay it."""
        assert_secret_free(state, label=kind)
        encoded = canonical_json(state)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            rows = conn.execute(
                "SELECT checkpoint_id,state_json,artifact_fingerprint FROM checkpoints "
                "WHERE run_id=? AND checkpoint_kind=? ORDER BY rowid",
                (run_id, kind),
            ).fetchall()
            if rows:
                if (len(rows) != 1 or rows[0]["checkpoint_id"] != checkpoint_id
                        or rows[0]["state_json"] != encoded
                        or rows[0]["artifact_fingerprint"] != artifact_fingerprint):
                    raise ProductionRunError(
                        "confirmed_prefix_replay_conflict",
                        f"immutable recovery checkpoint changed: {kind}",
                    )
                conn.commit()
                return
            conn.execute(
                "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (checkpoint_id, run_id, kind, encoded, artifact_fingerprint, now_iso()),
            )
            conn.commit()

    def _persist_independent_evidence(
        self, project_id: str, run_id: str, *, handoff: dict[str, Any], result: dict[str, Any],
        independence_receipt: dict[str, Any], submission_evidence_fingerprint: str,
        effect_guard: Callable[[Any], None],
    ) -> None:
        """Keep the exact validated response, including FAIL, under its owner."""
        from .recorded_independent import EVIDENCE_KIND, _snapshot
        evidence = _snapshot(
            run_id=run_id, handoff=handoff, result=result, receipt=independence_receipt,
            submission_fingerprint=submission_evidence_fingerprint,
        )
        encoded = canonical_json(evidence)
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            effect_guard(conn)
            rows = conn.execute(
                "SELECT state_json,artifact_fingerprint FROM checkpoints WHERE run_id=? AND checkpoint_kind=?",
                (run_id, EVIDENCE_KIND),
            ).fetchall()
            if rows:
                if len(rows) != 1 or rows[0]["state_json"] != encoded or rows[0]["artifact_fingerprint"] != evidence["evidence_fingerprint"]:
                    raise ProductionRunError("independent_evidence_replay_conflict", "original independent result changed for immutable run")
            else:
                conn.execute(
                    "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,?,?,?,?)",
                    ("independent-evidence:" + run_id, run_id, EVIDENCE_KIND, encoded, evidence["evidence_fingerprint"], now_iso()),
                )
            conn.commit()

    def _latest_checkpoint(self, project_id: str, run_id: str, kind: str) -> dict[str, Any] | None:
        with self.store.open_project(project_id) as conn:
            row = conn.execute(
                "SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind=? ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (run_id, kind),
            ).fetchone()
        return _json(row["state_json"], {}) if row else None

    def _recorded_registered_binding(
        self, project_id: str, source: dict[str, Any], *, runtime_role: str, contract_id: str,
        _seen: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        """Rebuild one exact verified parent binding without dispatching a model."""
        source_run_id = source.get("source_run_id")
        if not isinstance(source_run_id, str) or not source_run_id or source_run_id in _seen:
            raise ProductionRunError(
                "repair_checkpoint_invalid", "source causal checkpoint ancestry is invalid",
            )
        with self.store.open_project(project_id) as conn:
            rows = conn.execute(
                "SELECT * FROM production_stage_calls WHERE run_id=? AND runtime_role=? ORDER BY rowid",
                (source_run_id, runtime_role),
            ).fetchall()
            if not rows and source.get("source_task_mode") == "REVISE":
                parent = load_repair_source(
                    conn, source_run_id, _seen=_seen | {source_run_id}, _recorded=True,
                )
            else:
                parent = None
        if parent is not None:
            return self._recorded_registered_binding(
                project_id, parent, runtime_role=runtime_role, contract_id=contract_id,
                _seen=_seen | {source_run_id},
            )
        if len(rows) != 1 or rows[0]["state"] != "confirmed":
            raise ProductionRunError("repair_checkpoint_missing", f"source requires one confirmed {runtime_role} call")
        row = rows[0]
        agent_job = _json(row["job_json"], None)
        agent_result = _json(row["result_json"], None)
        if (not isinstance(agent_job, dict) or not isinstance(agent_result, dict)
                or canonical_json(agent_job) != row["job_json"] or canonical_json(agent_result) != row["result_json"]
                or agent_job.get("run_id") != source_run_id
                or agent_job.get("runtime_role") != runtime_role
                or agent_job.get("input_fingerprint") != row["input_fingerprint"]
                or agent_result.get("status") != "completed"
                or fingerprint(agent_result) != row["result_fingerprint"]):
            raise ProductionRunError("repair_checkpoint_invalid", f"source {runtime_role} call changed")
        context = agent_job.get("context")
        semantic_job = context[0].get("registered_semantic_job") if isinstance(context, list) and len(context) == 1 and isinstance(context[0], dict) else None
        if (not isinstance(semantic_job, dict) or validate_recorded_registered_job(semantic_job)
                or semantic_job.get("input", {}).get("model_contract_id") != contract_id):
            raise ProductionRunError("repair_checkpoint_invalid", f"source {contract_id} job changed")
        judgment = parse_json_object(agent_result.get("final_text"), label=f"source {contract_id}")
        semantic_result = {
            "job_id": semantic_job["job_id"], "subject_id": semantic_job["subject_id"],
            "kind": semantic_job["kind"], "input_fingerprint": semantic_job["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": "quillframe_model_service", "model_or_reviewer": agent_result.get("model_id"),
                "model_service_id": agent_result.get("model_service_id"), "protocol": agent_result.get("protocol"),
                "agent_job_id": agent_job.get("job_id"), "agent_input_fingerprint": agent_job.get("input_fingerprint"),
            },
            "judgment": judgment, "proposals": [], "errors": [],
            "execution": {
                "source_session_id": semantic_job.get("execution", {}).get("source_session_id"),
                "handoff_id": semantic_job.get("execution", {}).get("handoff_id"),
            },
        }
        errors = validate_semantic_result(semantic_job, semantic_result)
        if errors:
            raise ProductionRunError("repair_checkpoint_invalid", "; ".join(errors))
        binding = {
            "contract_id": contract_id, "job": semantic_job, "result": semantic_result,
            "binding_fingerprint": fingerprint({"job": semantic_job, "result": semantic_result}),
            "authority": False,
        }
        return binding

    def _seed_local_author_revision(
        self, project_id: str, run: dict[str, Any], bundle: dict[str, Any],
        source: dict[str, Any], artifacts: dict[str, Any], repair: dict[str, Any],
    ) -> dict[str, Any]:
        """Reuse only frozen causal/style evidence for a bounded prose repair."""
        if source.get("source_kind") != "author_revision" or repair["policy"]["generation_mode"] != "local_or_bounded_repair":
            raise ProductionRunError("local_revision_reuse_invalid", "bounded checkpoint reuse requires a local author revision")
        if not self._local_revision_context_reusable(bundle, source):
            raise ProductionRunError(
                "local_revision_reuse_stale",
                "bounded causal-checkpoint reuse requires an exact parent context universe",
            )
        scene_binding = self._recorded_registered_binding(
            project_id, source, runtime_role="registered_scene_projection", contract_id="scene.realization_project",
        )
        pressure_binding = self._recorded_registered_binding(
            project_id, source, runtime_role="registered_reader_pressure", contract_id="reader.pressure",
        )
        scene_id = bundle["target_context"]["chapter_id"]
        projection = writer_safe_projection(scene_binding, scene_id=scene_id)
        current_scene = self.materialize_stage_context(bundle, "scene_simulation")
        source_action_evidence = (
            scene_binding.get("job", {}).get("input", {}).get("payload", {}).get(
                "character_action_evidence"
            )
        )
        if not isinstance(source_action_evidence, list):
            raise ProductionRunError(
                "repair_checkpoint_invalid",
                "source scene projection lacks character action evidence",
            )
        writer_inventory = build_writer_inventory(
            current_scene,
            character_action_evidence=source_action_evidence,
            author_model=(bundle.get("target_context") or {}).get("author_model"),
        )
        author_objectives = author_objective_projection(
            source["source_request"]["instruction"], repair
        )
        guidance = materialize_writer_craft(
            artifacts.get("craft_snapshot"), scene_binding["result"]["judgment"].get("craft_selection"),
            projection_input=selection_input(artifacts.get("craft_snapshot"), current_scene),
            binding_fingerprint=scene_binding["binding_fingerprint"],
        )
        pressure = deepcopy(pressure_binding["result"]["judgment"])
        if pressure.get("status") != "pass":
            raise ProductionRunError("repair_checkpoint_invalid", "source Reader Pressure did not pass")
        pressure_fp = fingerprint(pressure)
        scene_state = {
            "status": "pass", "artifact": projection, "projection_binding": scene_binding,
            "craft_projection_input": selection_input(artifacts.get("craft_snapshot"), current_scene),
            "craft_guidance": guidance,
            "writer_context_inventory": writer_inventory,
            "author_objectives": author_objectives,
        }
        artifacts.update({
            "scene_simulation": scene_state,
            "reader_pressure": {"status": "pass", "artifact": pressure, "artifact_fingerprint": pressure_fp},
        })
        state = {
            "schema": "quillframe_local_author_revision_reuse_v1",
            "run_id": run["run_id"], "source_run_id": source["source_run_id"],
            "source_candidate_fingerprint": source["candidate_fingerprint"],
            "source_context_bundle_fingerprint": source["source_context_bundle_fingerprint"],
            "current_context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "generation_mode": "local_or_bounded_repair",
            "source_context_exact": True,
            "reused_mechanisms": [
                "context_selection", "story_canon_preflight", "character_simulation",
                "scene_simulation", "reader_pressure",
            ],
            "scene_projection_binding_fingerprint": scene_binding["binding_fingerprint"],
            "reader_pressure_binding_fingerprint": pressure_binding["binding_fingerprint"],
            "craft_guidance_fingerprint": guidance.get("guidance_fingerprint") if isinstance(guidance, dict) else None,
            "model_calls_reused": 0, "authority": False,
        }
        state["reuse_fingerprint"] = fingerprint({key: value for key, value in state.items() if key != "reuse_fingerprint"})
        self._checkpoint(project_id, run["run_id"], "production_local_revision_reuse", state, state["reuse_fingerprint"])
        self._event(project_id, run["run_id"], "production_local_revision_reused", {
            "source_run_id": source["source_run_id"],
            "source_candidate_fingerprint": source["candidate_fingerprint"],
            "reuse_fingerprint": state["reuse_fingerprint"], "authority": False,
        })
        return state

    @staticmethod
    def _local_revision_context_reusable(bundle: dict[str, Any], source: dict[str, Any]) -> bool:
        selectors = {
            stage_id: greenlight.get("selector", {})
            for stage_id, greenlight in bundle.get("freeze", {}).get("stage_greenlights", {}).items()
        }
        return bool(selectors) and all(
            selector.get("kind") == "author_revision_checkpoint_reuse"
            and selector.get("source_run_id") == source.get("source_run_id")
            and selector.get("source_bundle_fingerprint") == source.get("source_context_bundle_fingerprint")
            for selector in selectors.values()
        )

    def _seed_local_author_revision_text(
        self, project_id: str, run: dict[str, Any], bundle: dict[str, Any],
        source: dict[str, Any], artifacts: dict[str, Any],
    ) -> dict[str, Any]:
        """Keep the requested source prose while rebuilding changed causal context."""
        state = {
            "schema": "quillframe_local_author_revision_reuse_v1",
            "run_id": run["run_id"], "source_run_id": source["source_run_id"],
            "source_candidate_fingerprint": source["candidate_fingerprint"],
            "source_context_bundle_fingerprint": source["source_context_bundle_fingerprint"],
            "current_context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "generation_mode": "local_or_bounded_repair",
            "source_context_exact": False,
            "reused_mechanisms": [],
            "model_calls_reused": 0, "authority": False,
        }
        state["reuse_fingerprint"] = fingerprint({
            key: value for key, value in state.items() if key != "reuse_fingerprint"
        })
        self._checkpoint(
            project_id, run["run_id"], "production_local_revision_reuse",
            state, state["reuse_fingerprint"],
        )
        self._event(project_id, run["run_id"], "production_local_revision_source_seeded", {
            "source_run_id": source["source_run_id"],
            "source_candidate_fingerprint": source["candidate_fingerprint"],
            "reuse_fingerprint": state["reuse_fingerprint"], "authority": False,
        })
        return state

    def _seed_confirmed_prefix(
        self,
        project_id: str,
        run: dict[str, Any],
        bundle: dict[str, Any],
        source: dict[str, Any],
        confirmed_prefix: dict[str, Any],
        artifacts: dict[str, Any],
        *,
        reading_positioning: dict[str, Any],
        reader_visible_context: list[dict[str, Any]],
        reader_grip: str,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Materialize predecessor evidence without copying or charging calls."""
        frozen = confirmed_prefix["frozen"]
        private = confirmed_prefix["private"]
        if (context_compatibility_fingerprint(bundle)
                != frozen["source_context"]["compatibility_fingerprint"]):
            raise ProductionRunError(
                "confirmed_prefix_context_changed",
                "current Context differs from the terminal prefix Context",
            )
        if source.get("source_fingerprint") != frozen["source_repair_source_fingerprint"]:
            raise ProductionRunError(
                "confirmed_prefix_source_changed",
                "current repair source differs from the terminal prefix",
            )
        plan_state = deepcopy(private["repair_plan_state"])
        repair = plan_state.get("generation_plan")
        if (not isinstance(repair, dict)
                or repair.get("policy", {}).get("generation_mode") != "local_or_bounded_repair"):
            raise ProductionRunError(
                "confirmed_prefix_repair_invalid",
                "confirmed prefix recovery requires the exact bounded repair plan",
            )
        candidate_text = private["surface_text"]
        candidate_fingerprint = fingerprint_text(candidate_text)
        if candidate_fingerprint != frozen["candidate_fingerprint"]:
            raise ProductionRunError(
                "confirmed_prefix_candidate_changed",
                "confirmed prefix candidate bytes changed",
            )
        author_objectives = deepcopy(private.get("author_objectives"))
        try:
            validated_author_objectives = validate_author_objectives(author_objectives)
        except ValueError as exc:
            raise ProductionRunError(
                "confirmed_prefix_objectives_invalid",
                "confirmed prefix author objectives are invalid",
            ) from exc
        if (
            validated_author_objectives["objectives_fingerprint"]
            != frozen.get("source_author_objectives_fingerprint")
        ):
            raise ProductionRunError(
                "confirmed_prefix_objectives_changed",
                "confirmed prefix author-objective binding changed",
            )
        reader_binding = deepcopy(private["reader_binding"])
        reader_payload = reader_binding["job"]["input"]["payload"]
        scope = self._execution_scope(project_id, run["run_id"])
        if scope is None:
            raise ProductionRunError(
                "execution_lease_required",
                "confirmed prefix materialization requires the production lease",
            )
        current_reader_fields = reading_positioning_fields(
            reading_positioning,
            target_context=bundle["target_context"],
            reader_grip=reader_grip,
            execution_request_fingerprint=scope["request_fingerprint"],
        )
        if (any(reader_payload.get(key) != value for key, value in current_reader_fields.items())
                or reader_payload.get("reader_visible_context") != reader_visible_context):
            raise ProductionRunError(
                "confirmed_prefix_reader_context_changed",
                "current Reader-visible positioning or history differs from the confirmed Reader input",
            )

        plan_artifact_fingerprint = fingerprint(repair)
        self._checkpoint_once(
            project_id,
            run["run_id"],
            checkpoint_id="confirmed-prefix-plan:" + run["run_id"],
            kind="production_repair_plan",
            state=plan_state,
            artifact_fingerprint=plan_artifact_fingerprint,
        )

        calls = private["calls"]
        source_receipts = private["stage_receipts"]
        call_indexes = {
            "surface_realization": 1,
            "reader_engagement": 2,
            "continuity": 3,
        }
        public_receipts: list[dict[str, Any]] = []
        for mechanism in ("surface_realization", "reader_engagement", "continuity"):
            call = calls[call_indexes[mechanism]]
            row, agent_job, agent_result = call
            current_stage = self.materialize_stage_context(bundle, mechanism)
            receipt = public_stage_result(
                mechanism=mechanism,
                context_stage_id=current_stage["context_stage_id"],
                context_bundle_fingerprint=bundle["bundle_fingerprint"],
                freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
                stage_context_fingerprint=current_stage["stage_context_fingerprint"],
                agent_input_fingerprint=(
                    reader_binding["job"]["input_fingerprint"]
                    if mechanism == "reader_engagement"
                    else agent_job["input_fingerprint"]
                ),
                model_service_id=str(agent_result.get("model_service_id") or ""),
                model_id=str(agent_result.get("model_id") or ""),
                protocol=str(agent_result.get("protocol") or ""),
                judgment={
                    "status": "pass",
                    "summary": "Exact predecessor evidence revalidated by Core.",
                    "findings": [],
                    "artifact_fingerprint": candidate_fingerprint,
                },
            )
            receipt.update({
                "evidence_kind": "confirmed_prefix_reuse",
                "confirmed_prefix_fingerprint": frozen["prefix_fingerprint"],
                "source_run_id": frozen["source_run_id"],
                "source_call_id": row["call_id"],
                "source_result_fingerprint": row["result_fingerprint"],
                "source_stage_result_fingerprint": source_receipts[mechanism]["stage_result_fingerprint"],
                "current_run_model_invoked": False,
                "source_model_invocation_referenced": True,
            })
            receipt["stage_result_fingerprint"] = fingerprint({
                key: value for key, value in receipt.items() if key != "stage_result_fingerprint"
            })
            self._persist_stage_receipt(project_id, run["run_id"], receipt)
            public_receipts.append(receipt)

        reuse_state = {
            "schema": CONFIRMED_PREFIX_REUSE_SCHEMA,
            "run_id": run["run_id"],
            "source_run_id": frozen["source_run_id"],
            "source_prefix_fingerprint": frozen["prefix_fingerprint"],
            "current_execution_request_fingerprint": scope["request_fingerprint"],
            "current_context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "current_freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "current_repair_source_fingerprint": source["source_fingerprint"],
            "repair_plan_fingerprint": plan_artifact_fingerprint,
            "candidate_fingerprint": candidate_fingerprint,
            "reused_mechanisms": list(CONFIRMED_PREFIX_ROLES),
            "referenced_model_calls": 4,
            "current_run_model_calls_charged": 0,
            "compatibility_fingerprint": context_compatibility_fingerprint(bundle),
            "stage_reuse_receipt_fingerprints": [
                receipt["stage_result_fingerprint"] for receipt in public_receipts
            ],
            "authority": False,
        }
        reuse_state["reuse_fingerprint"] = fingerprint(reuse_state)
        self._checkpoint_once(
            project_id,
            run["run_id"],
            checkpoint_id="confirmed-prefix-reuse:" + run["run_id"],
            kind="production_confirmed_prefix_reuse",
            state=reuse_state,
            artifact_fingerprint=reuse_state["reuse_fingerprint"],
        )
        self._event(project_id, run["run_id"], "production_confirmed_prefix_reused", {
            "source_run_id": frozen["source_run_id"],
            "source_prefix_fingerprint": frozen["prefix_fingerprint"],
            "candidate_fingerprint": candidate_fingerprint,
            "reuse_fingerprint": reuse_state["reuse_fingerprint"],
            "referenced_model_calls": 4,
            "current_run_model_calls_charged": 0,
            "authority": False,
        })
        artifacts.update({
            "repair": repair,
            "repair_source": source,
            "scene_simulation": {
                "status": "pass",
                "author_objectives": validated_author_objectives,
            },
            "surface_realization": {
                "status": "pass",
                "text": candidate_text,
                "artifact_fingerprint": candidate_fingerprint,
            },
            "continuity": {"status": "pass", "artifact_fingerprint": candidate_fingerprint},
        })
        return repair, reader_binding, public_receipts

    def _latest_independent_handoff(self, project_id: str, run_id: str) -> dict[str, Any] | None:
        """Load one native 1.0 frozen handoff without upgrading stored state."""
        with self.store.open_project(project_id) as conn:
            row = conn.execute(
                """SELECT state_json FROM checkpoints
                WHERE run_id=? AND checkpoint_kind='production_independent_handoff'
                ORDER BY created_at DESC,rowid DESC LIMIT 1""",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            handoff = _json(row["state_json"], {})
            packet = handoff.get("peer_packet")
            exact_bytes = canonical_json(packet)
            stored_bytes = handoff.get("peer_packet_bytes")
            if not isinstance(packet, dict) or not isinstance(stored_bytes, str) or stored_bytes != exact_bytes:
                raise ProductionRunError(
                    "independent_handoff_invalid",
                    "1.0 handoff requires exact frozen peer_packet and peer_packet_bytes",
                )
            return handoff

    def _persist_release_receipt(
        self,
        project_id: str,
        run_id: str,
        release: dict[str, Any],
        *,
        effect_guard: Callable[[Any], None] | None = None,
    ) -> None:
        assert_secret_free(release, label="production release")
        key = f"{run_id}:production_release"
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            if effect_guard is not None:
                effect_guard(conn)
            existing = conn.execute(
                "SELECT payload_json FROM receipts WHERE receipt_kind='production_release' AND idempotency_key=?",
                (key,),
            ).fetchone()
            if existing:
                prior = _json(existing["payload_json"], {})
                if prior.get("release_fingerprint") != release.get("release_fingerprint"):
                    raise ProductionRunError("production_release_replay_conflict", "production release changed for immutable run")
                conn.commit()
                return
            conn.execute(
                "INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                ("rcpt_" + uuid.uuid4().hex, run_id, "production_release", key, canonical_json(release), now_iso()),
            )
            conn.commit()

    def _persist_candidate(
        self,
        project_id: str,
        run: dict[str, Any],
        bundle: dict[str, Any],
        document_id: str,
        text: str,
        candidate_fingerprint: str,
        independent_binding: dict[str, Any],
        readiness: dict[str, Any],
        release: dict[str, Any],
        *,
        effect_guard: Callable[[Any], None],
    ) -> dict[str, Any]:
        independence_receipt = independent_binding["independence_receipt"]
        independent_result = independent_binding["result"]
        review_public = {
            "model_contract_id": "quality.production_review",
            "judgment": independent_result.get("judgment"),
            "worker": independent_result.get("worker"),
            "job_id": independent_result.get("job_id"),
            "input_fingerprint": independent_result.get("input_fingerprint"),
            "independence_receipt": independence_receipt,
            "production_readiness": readiness,
            "submission_evidence_fingerprint": independent_binding["submission_evidence_fingerprint"],
            "private_reasoning_exposed": False,
            "authority": False,
        }
        qualified = self._latest_checkpoint(project_id, run["run_id"], "production_qualified_candidate")
        reader_binding = (qualified or {}).get("reader_binding")
        reader_observation = (qualified or {}).get("reader_expectation_binding")
        if not isinstance(reader_binding, dict) or not isinstance(reader_observation, dict):
            raise ProductionRunError("reader_evidence_missing", "released candidate requires its exact reader evidence")
        reader_payload = reader_binding["job"]["input"]["payload"]
        if reader_payload.get("candidate_fingerprint") != candidate_fingerprint:
            raise ProductionRunError("reader_evidence_mismatch", "reader evidence changed its candidate binding")
        reader_judgment = reader_binding["result"]["judgment"]
        review_public["reader_engagement"] = {
            "candidate_fingerprint": candidate_fingerprint, "source_type": "model_proxy",
            **{key: deepcopy(reader_judgment.get(key)) for key in ("result", "report", "strongest_positive", "strongest_problem", "evidence_refs")},
        }
        assert_secret_free(review_public, label="independent review evidence")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run["run_id"])
            effect_guard(conn)
            existing = conn.execute(
                "SELECT candidate_id,revision_id,status,content_fingerprint,user_visible_gate FROM candidates WHERE run_id=? ORDER BY created_at,rowid",
                (run["run_id"],),
            ).fetchall()
            if existing:
                if len(existing) != 1 or existing[0]["content_fingerprint"] != candidate_fingerprint:
                    raise ProductionRunError(
                        "candidate_replay_conflict",
                        "production run already persisted a different or ambiguous candidate",
                    )
                evidence = conn.execute(
                    "SELECT candidate_fingerprint,result_json FROM review_evidence WHERE candidate_id=? AND independent=1",
                    (existing[0]["candidate_id"],),
                ).fetchall()
                prior_evidence = _json(evidence[0]["result_json"], {}) if len(evidence) == 1 else {}
                if (
                    len(evidence) != 1
                    or evidence[0]["candidate_fingerprint"] != candidate_fingerprint
                    or prior_evidence.get("submission_evidence_fingerprint")
                    != independent_binding.get("submission_evidence_fingerprint")
                ):
                    raise ProductionRunError(
                        "candidate_replay_conflict",
                        "persisted production candidate lacks exact independent review evidence",
                    )
                conn.commit()
                return {
                    "candidate_id": existing[0]["candidate_id"],
                    "revision_id": existing[0]["revision_id"],
                    "candidate_fingerprint": candidate_fingerprint,
                    "status": existing[0]["status"],
                    "user_visible_gate": existing[0]["user_visible_gate"],
                    "production_release_fingerprint": release.get("release_fingerprint"),
                    "authority": False,
                }
            document = conn.execute("SELECT document_id FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if not document:
                raise ProductionRunError("target_document_required", f"production candidate target document does not exist: {document_id}")
            latest = self.store.latest_revision(conn, document_id)
            parent_id = latest["revision_id"] if latest else None
            content_fingerprint = fingerprint_text(text)
            if content_fingerprint != candidate_fingerprint:
                raise ProductionRunError("candidate_fingerprint_mismatch", "diagnostic candidate changed before Review Draft persistence")
            revision = conn.execute(
                "SELECT revision_id FROM document_revisions WHERE document_id=? AND content_fingerprint=?",
                (document_id, content_fingerprint),
            ).fetchone()
            revision_id = revision["revision_id"] if revision else "rev_" + uuid.uuid4().hex
            if not revision:
                conn.execute(
                    """INSERT INTO document_revisions(
                    revision_id,document_id,parent_revision_id,content,content_fingerprint,created_at,source,authority_class,provenance_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        revision_id,
                        document_id,
                        parent_id,
                        text,
                        content_fingerprint,
                        now_iso(),
                        "production_runtime",
                        "review",
                        canonical_json({
                            "run_id": run["run_id"],
                            "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                            "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                            "production_readiness_schema": readiness.get("schema"),
                            "production_release_fingerprint": release.get("release_fingerprint"),
                            "authority": False,
                        }),
                    ),
                )
                title = conn.execute("SELECT title FROM documents WHERE document_id=?", (document_id,)).fetchone()["title"]
                self.store.index_search(conn, "document", document_id, title, text, commit=False)
            candidate_id = "cand_" + uuid.uuid4().hex
            review_id = "review_" + uuid.uuid4().hex
            candidate_kind = "draft" if run["task_mode"] == "DRAFT" else "repair"
            stamp = now_iso()
            conn.execute(
                "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,'review_draft',?,'PASS',?)",
                (candidate_id, document_id, revision_id, run["run_id"], run["task_mode"], candidate_kind, candidate_fingerprint, stamp),
            )
            conn.execute(
                "INSERT INTO review_evidence(review_id,candidate_id,evidence_kind,result_json,candidate_fingerprint,reviewer_fingerprint,independent,stale,created_at) VALUES(?,?,?,?,?,?,1,0,?)",
                (
                    review_id,
                    candidate_id,
                    "quality.production_review",
                    canonical_json(review_public),
                    candidate_fingerprint,
                    independence_receipt.get("result_fingerprint"),
                    stamp,
                ),
            )
            try:
                record_observation(conn, run_id=run["run_id"], candidate_id=candidate_id, binding=reader_observation)
            except ReaderExpectationError as exc:
                raise ProductionRunError(exc.code, str(exc)) from exc
            conn.commit()
        return {
            "candidate_id": candidate_id,
            "revision_id": revision_id,
            "candidate_fingerprint": candidate_fingerprint,
            "status": "review_draft",
            "user_visible_gate": "PASS",
            "production_release_fingerprint": release.get("release_fingerprint"),
            "authority": False,
        }

    def _persist_candidate_ready_event(
        self,
        project_id: str,
        run_id: str,
        *,
        candidate_id: str,
        candidate_fingerprint: str,
        context_bundle_fingerprint: str,
        independent_result_fingerprint: str | None,
        effect_guard: Callable[[Any], None],
    ) -> None:
        payload = {
            "candidate_id": candidate_id,
            "candidate_fingerprint": candidate_fingerprint,
            "context_bundle_fingerprint": context_bundle_fingerprint,
            "independent_result_fingerprint": independent_result_fingerprint,
        }
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            effect_guard(conn)
            existing = conn.execute(
                "SELECT payload_json FROM runtime_events WHERE run_id=? AND event_kind='production_candidate_ready' ORDER BY created_at,rowid",
                (run_id,),
            ).fetchall()
            if existing:
                if len(existing) != 1 or existing[0]["payload_json"] != canonical_json(payload):
                    raise ProductionRunError(
                        "candidate_ready_event_conflict",
                        "production candidate-ready event changed for immutable run",
                    )
                conn.commit()
                return
            conn.execute(
                "INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)",
                ("evt_" + uuid.uuid4().hex, run_id, "production_candidate_ready", canonical_json(payload), now_iso()),
            )
            conn.commit()

    def _set_independent_run(
        self,
        project_id: str,
        run_id: str,
        status: str,
        *,
        effect_guard: Callable[[Any], None],
        result_fingerprint: str | None = None,
    ) -> None:
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._guard_execution(conn, project_id, run_id)
            effect_guard(conn)
            conn.execute(
                "UPDATE runs SET status=?,result_fingerprint=COALESCE(?,result_fingerprint),updated_at=? WHERE run_id=?",
                (status, result_fingerprint, now_iso(), run_id),
            )
            conn.commit()

    @staticmethod
    def _lifecycle_receipt_event(event: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_id": event["event_id"],
            "event_kind": event["event_kind"],
            "event_fingerprint": event["event_fingerprint"],
        }

    @staticmethod
    def _raise_independent_repository(exc: IndependentReviewError) -> None:
        raise ProductionRunError(exc.code, str(exc), detail=exc.detail) from exc

    def _assert_independent_project_identity(self, project_id: str) -> None:
        try:
            IndependentReviewRepository(self.store).assert_project_identity(project_id)
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)

    def prepare_independent_dispatch(
        self,
        project_id: str,
        run_id: str,
        *,
        provider: str,
        parent_session_id: str,
    ) -> dict[str, Any]:
        self._assert_independent_project_identity(project_id)
        handoff = self._latest_independent_handoff(project_id, run_id)
        if not handoff:
            raise ProductionRunError("independent_handoff_missing", "frozen independent handoff is required before native dispatch")
        try:
            return IndependentReviewRepository(self.store).prepare(
                project_id,
                run_id,
                candidate_fingerprint=handoff["candidate_fingerprint"],
                packet_bytes=handoff["peer_packet_bytes"],
                job_id=handoff["independent_job"]["job_id"],
                input_fingerprint=handoff["independent_job"]["input_fingerprint"],
                relay_nonce=handoff["peer_packet"]["relay_nonce"],
                provider=provider,
                parent_session_id=parent_session_id,
            )
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)

    def claim_independent_dispatch(
        self,
        project_id: str,
        *,
        provider: str,
        parent_session_id: str,
        agent_type: str,
        host_agent_id: str,
        host_invocation_id: str,
    ) -> dict[str, Any]:
        self._assert_independent_project_identity(project_id)
        try:
            return IndependentReviewRepository(self.store).claim(
                project_id,
                provider=provider,
                parent_session_id=parent_session_id,
                agent_type=agent_type,
                host_agent_id=host_agent_id,
                host_invocation_id=host_invocation_id,
            )
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)

    def fail_independent_dispatch(
        self,
        project_id: str,
        *,
        lease_id: str,
        reviewer_session_id: str,
        host_agent_id: str,
        host_invocation_id: str,
        error: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(error, dict) or not error:
            raise ProductionRunError("invalid_args", "non-empty infrastructure error object is required")
        self._assert_independent_project_identity(project_id)
        try:
            return IndependentReviewRepository(self.store).fail(
                project_id,
                lease_id=lease_id,
                reviewer_session_id=reviewer_session_id,
                host_agent_id=host_agent_id,
                host_invocation_id=host_invocation_id,
                error=error,
            )
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)

    def _validate_native_lifecycle_receipt(
        self,
        project_id: str,
        run_id: str,
        handoff: dict[str, Any],
        peer_packet: dict[str, Any],
        result: dict[str, Any],
        receipt: dict[str, Any],
        *,
        native_lease_id: str | None = None,
        completion_event: dict[str, Any] | None = None,
    ) -> None:
        errors = validate_independent_invocation_receipt(receipt, peer_packet, result)
        if errors:
            raise ProductionRunError("independent_invocation_receipt_invalid", "; ".join(errors))
        repository = IndependentReviewRepository(self.store)
        try:
            lease = repository.lease(project_id, str(receipt.get("lease_id") or ""))
            durable_events = repository.lifecycle_events(project_id, lease["lease_id"])
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)
        expected = {
            "project_id": project_id,
            "run_id": run_id,
            "candidate_fingerprint": handoff["candidate_fingerprint"],
            "job_id": handoff["independent_job"]["job_id"],
            "input_fingerprint": handoff["independent_job"]["input_fingerprint"],
            "packet_fingerprint": independent_fingerprint(peer_packet),
            "result_fingerprint": independent_fingerprint(result),
            "relay_nonce": peer_packet["relay_nonce"],
            "provider": lease["provider"],
            "transport": lease["transport"],
            "parent_session_id": lease["parent_session_id"],
            "reviewer_session_id": lease["reviewer_session_id"],
            "host_agent_id": lease["host_agent_id"],
            "host_invocation_id": lease["host_invocation_id"],
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                raise ProductionRunError("independent_invocation_receipt_invalid", f"durable native lifecycle mismatch: {key}")
        if lease["packet_bytes"] != handoff["peer_packet_bytes"]:
            raise ProductionRunError("independent_packet_mismatch", "native lease packet bytes changed")
        if lease["status"] == "completed":
            if canonical_json(receipt) != lease.get("receipt_json"):
                raise ProductionRunError("independent_invocation_receipt_invalid", "native receipt differs from durable completed lease")
            expected_events = [self._lifecycle_receipt_event(event) for event in durable_events]
        elif (
            lease["status"] == "claimed"
            and native_lease_id == lease["lease_id"]
            and isinstance(completion_event, dict)
        ):
            if lease.get("completion_event_json") != canonical_json(completion_event):
                raise ProductionRunError(
                    "independent_invocation_receipt_invalid",
                    "native receipt completion event differs from the durable completion plan",
                )
            expected_events = [
                *[self._lifecycle_receipt_event(event) for event in durable_events],
                self._lifecycle_receipt_event(completion_event),
            ]
        else:
            raise ProductionRunError("independent_invocation_receipt_invalid", "native receipt does not match completed or completing durable lifecycle")
        if receipt.get("lifecycle_events") != expected_events:
            raise ProductionRunError("independent_invocation_receipt_invalid", "native receipt lifecycle event binding mismatch")

    def complete_independent_dispatch(
        self,
        project_id: str,
        *,
        lease_id: str,
        reviewer_session_id: str,
        host_agent_id: str,
        host_invocation_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        self._assert_independent_project_identity(project_id)
        repository = IndependentReviewRepository(self.store)
        try:
            lease = repository.lease(project_id, lease_id)
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)
        if (
            lease["reviewer_session_id"] != reviewer_session_id
            or lease["host_agent_id"] != host_agent_id
            or lease["host_invocation_id"] != host_invocation_id
        ):
            raise ProductionRunError("independent_lifecycle_mismatch", "native completion identity mismatch")
        peer_packet = json.loads(lease["packet_bytes"])
        result_errors = validate_peer_result(peer_packet, result)
        provider_contract = INDEPENDENT_PROVIDER_CONTRACTS[lease["provider"]]
        if (result.get("worker") or {}).get("provider") != provider_contract["worker_provider"]:
            result_errors.append("native result worker.provider does not match lease provider")
        if result_errors:
            raise ProductionRunError("independent_result_invalid", "; ".join(result_errors))
        result_fingerprint = independent_fingerprint(result)
        if lease["status"] == "completed":
            if lease["result_fingerprint"] != result_fingerprint:
                raise ProductionRunError("independent_attempt_consumed", "different native result cannot replay completed lease")
            receipt = json.loads(lease["receipt_json"])
            return self.submit_independent(
                project_id,
                lease["run_id"],
                peer_packet=peer_packet,
                result=result,
                independence_receipt=receipt,
            )
        if lease["status"] != "claimed":
            raise ProductionRunError("independent_lease_not_claimed", "native completion requires a claimed lease")
        try:
            completion_event = repository.planned_completion_event(project_id, lease_id, result_fingerprint)
            durable_events = repository.lifecycle_events(project_id, lease_id)
            receipt = build_independent_invocation_receipt(
                peer_packet,
                result,
                lease_id=lease_id,
                project_id=project_id,
                run_id=lease["run_id"],
                provider=lease["provider"],
                parent_session_id=lease["parent_session_id"],
                reviewer_session_id=reviewer_session_id,
                host_agent_id=host_agent_id,
                host_invocation_id=host_invocation_id,
                lifecycle_events=[
                    *[self._lifecycle_receipt_event(event) for event in durable_events],
                    self._lifecycle_receipt_event(completion_event),
                ],
            )
        except (IndependentReviewError, ValueError) as exc:
            if isinstance(exc, IndependentReviewError):
                self._raise_independent_repository(exc)
            raise ProductionRunError("independent_result_invalid", str(exc)) from exc
        return self.submit_independent(
            project_id,
            lease["run_id"],
            peer_packet=peer_packet,
            result=result,
            independence_receipt=receipt,
            _native_lease_id=lease_id,
            _native_completion_event=completion_event,
        )

    def complete_independent_judgment(
        self,
        project_id: str,
        *,
        lease_id: str,
        reviewer_session_id: str,
        host_agent_id: str,
        host_invocation_id: str,
        judgment: dict[str, Any],
    ) -> dict[str, Any]:
        """Complete a native review without persisting its frozen packet in host state."""
        if not isinstance(judgment, dict):
            raise ProductionRunError("invalid_args", "native reviewer judgment must be an object")
        self._assert_independent_project_identity(project_id)
        repository = IndependentReviewRepository(self.store)
        try:
            lease = repository.lease(project_id, lease_id)
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)
        if (
            lease["reviewer_session_id"] != reviewer_session_id
            or lease["host_agent_id"] != host_agent_id
            or lease["host_invocation_id"] != host_invocation_id
        ):
            raise ProductionRunError("independent_lifecycle_mismatch", "native completion identity mismatch")
        packet = json.loads(lease["packet_bytes"])
        job = packet.get("job") or {}
        nonce = packet.get("relay_nonce")
        result = {
            "schema": "quillframe_peer_review_result_v1",
            "job_id": job.get("job_id"),
            "subject_id": job.get("subject_id"),
            "kind": job.get("kind"),
            "input_fingerprint": job.get("input_fingerprint"),
            "status": "completed",
            "judgment": deepcopy(judgment),
            "worker": {
                "provider": INDEPENDENT_PROVIDER_CONTRACTS[lease["provider"]]["worker_provider"],
                "model_or_reviewer": lease.get("agent_type") or "quillframe-independent-reviewer",
                "session_id": reviewer_session_id,
                "run_reference": nonce,
            },
            "proposals": [],
            "errors": [],
            "execution": {"run_reference": nonce},
        }
        return self.complete_independent_dispatch(
            project_id,
            lease_id=lease_id,
            reviewer_session_id=reviewer_session_id,
            host_agent_id=host_agent_id,
            host_invocation_id=host_invocation_id,
            result=result,
        )

    def submit_independent(
        self,
        project_id: str,
        run_id: str,
        *,
        peer_packet: dict[str, Any],
        result: dict[str, Any],
        independence_receipt: dict[str, Any],
        _native_lease_id: str | None = None,
        _native_completion_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._assert_independent_project_identity(project_id)
        if not isinstance(independence_receipt, dict):
            raise ProductionRunError(
                "independence_receipt_invalid",
                "submit requires one 1.0 independence_receipt",
            )
        receipt = independence_receipt
        handoff = self._latest_independent_handoff(project_id, run_id)
        if not handoff:
            raise ProductionRunError("independent_handoff_missing", "frozen independent handoff is required")
        if receipt.get("schema") == INDEPENDENT_INVOCATION_RECEIPT_SCHEMA:
            self._validate_native_lifecycle_receipt(
                project_id,
                run_id,
                handoff,
                peer_packet,
                result,
                receipt,
                native_lease_id=_native_lease_id,
                completion_event=_native_completion_event,
            )
            transport = str(receipt.get("transport"))
        else:
            transport = "github_actions"
        # Reject malformed evidence before it can acquire the processing owner.
        validate_independent_submission(
            handoff=handoff,
            peer_packet=peer_packet,
            result=result,
            independence_receipt=receipt,
        )
        packet_project_id = ((handoff.get("independent_job") or {}).get("provenance") or {}).get("project_id")
        if packet_project_id != project_id or receipt.get("project_id") != project_id:
            raise ProductionRunError("independent_project_mismatch", "packet and receipt must bind the actual runtime Project")
        evidence_fingerprint = fingerprint(
            {
                "packet_bytes": handoff["peer_packet_bytes"],
                "result": result,
                "independence_receipt": receipt,
            }
        )
        repository = IndependentReviewRepository(self.store)
        try:
            ownership = repository.begin_attempt(
                project_id,
                run_id,
                handoff["candidate_fingerprint"],
                evidence_fingerprint=evidence_fingerprint,
                transport=transport,
                native_lease_id=_native_lease_id,
            )
        except IndependentReviewError as exc:
            self._raise_independent_repository(exc)
        if not ownership["owner"]:
            return ownership["response"]
        token = ownership["processing_token"]
        epoch = ownership["processing_epoch"]
        try:
            response = self._process_independent_submission(
                project_id,
                run_id,
                peer_packet=peer_packet,
                result=result,
                independence_receipt=receipt,
                submission_evidence_fingerprint=evidence_fingerprint,
                processing_repository=repository,
                processing_candidate_fingerprint=handoff["candidate_fingerprint"],
                processing_token=token,
                processing_epoch=epoch,
            )
            if response.get("status") == "stale_conflict":
                repository.release_attempt(project_id, run_id, handoff["candidate_fingerprint"], token, epoch)
                return response
            try:
                if _native_lease_id is not None and _native_completion_event is not None:
                    repository.finalize_native(
                        project_id,
                        lease_id=_native_lease_id,
                        completion_event=_native_completion_event,
                        receipt=receipt,
                        result_fingerprint=independent_fingerprint(result),
                        processing_token=token,
                        processing_epoch=epoch,
                        evidence_fingerprint=evidence_fingerprint,
                        response=response,
                    )
                else:
                    repository.terminalize_attempt(
                        project_id,
                        run_id,
                        handoff["candidate_fingerprint"],
                        processing_token=token,
                        processing_epoch=epoch,
                        evidence_fingerprint=evidence_fingerprint,
                        response=response,
                    )
            except IndependentReviewError as exc:
                self._raise_independent_repository(exc)
            return response
        except Exception:
            repository.abandon_attempt(project_id, run_id, handoff["candidate_fingerprint"], token, epoch)
            raise

    def _completed_projection(
        self,
        project_id: str,
        run: dict[str, Any],
        bundle: dict[str, Any] | None,
        *,
        expected_submission_evidence_fingerprint: str | None = None,
    ) -> dict[str, Any] | None:
        if run.get("status") != "completed":
            return None
        with self.store.open_project(project_id) as conn:
            candidate_rows = conn.execute(
                "SELECT candidate_id,revision_id,content_fingerprint,status,user_visible_gate FROM candidates WHERE run_id=? ORDER BY created_at,rowid",
                (run["run_id"],),
            ).fetchall()
            candidate = candidate_rows[0] if len(candidate_rows) == 1 else None
            receipts = [
                _json(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY created_at,rowid",
                    (run["run_id"],),
                )
            ]
            release_row = conn.execute(
                "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_release' ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (run["run_id"],),
            ).fetchone()
            review_rows = conn.execute(
                "SELECT result_json FROM review_evidence WHERE candidate_id=? AND independent=1 ORDER BY created_at,rowid",
                (candidate["candidate_id"],),
            ).fetchall() if candidate else []
        if len(candidate_rows) > 1:
            raise ProductionRunError(
                "completed_run_candidate_ambiguous",
                "completed production run has multiple persisted candidates",
            )
        if not candidate:
            raise ProductionRunError("completed_run_missing_candidate", "completed production run has no persisted candidate")
        release = _json(release_row["payload_json"], {}) if release_row else {}
        if (
            release.get("schema") != "quillframe_production_release_v1"
            or release.get("candidate_fingerprint") != candidate["content_fingerprint"]
            or release.get("ready_for_user_visible_review") is not True
        ):
            raise ProductionRunError("production_release_missing", "completed production candidate lacks a valid exact-fingerprint production release")
        if expected_submission_evidence_fingerprint is not None:
            persisted_review = _json(review_rows[0]["result_json"], {}) if len(review_rows) == 1 else {}
            if persisted_review.get("submission_evidence_fingerprint") != expected_submission_evidence_fingerprint:
                raise ProductionRunError(
                    "independent_recovery_evidence_mismatch",
                    "completed production side effects do not bind the submitted independent evidence",
                )
        return {
            "schema": PRODUCTION_EXECUTION_SCHEMA,
            "project_id": project_id,
            "run_id": run["run_id"],
            "status": "completed",
            "task_mode": run["task_mode"],
            "context_bundle_fingerprint": bundle.get("bundle_fingerprint") if bundle else None,
            "freeze_fingerprint": (bundle.get("freeze") or {}).get("freeze_fingerprint") if bundle else None,
            "stage_receipts": receipts,
            "candidate": {**dict(candidate), "candidate_fingerprint": candidate["content_fingerprint"], "authority": False},
            "candidate_visible": True,
            "production_release": release,
            "raw_draft_visible": False,
            "accepted": candidate["status"] == "accepted",
            "settled": False,
            "replayed": True,
            "authority": False,
        }

    def _awaiting_external_projection(self, project_id: str, run: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any] | None:
        if run.get("status") != "awaiting_external":
            return None
        handoff = self._latest_independent_handoff(project_id, run["run_id"])
        qualified = self._latest_checkpoint(project_id, run["run_id"], "production_qualified_candidate")
        if handoff:
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run["run_id"],
                "status": "awaiting_external",
                "awaiting": "independent_semantic_review",
                "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                "candidate_fingerprint": handoff["candidate_fingerprint"],
                "qualification_receipt_fingerprint": handoff["qualification_receipt"]["receipt_fingerprint"],
                "independent_review_request": {
                    "schema": handoff["schema"],
                    "subject_id": handoff["subject_id"],
                    "candidate_fingerprint": handoff["candidate_fingerprint"],
                    "job_id": handoff["independent_job"]["job_id"],
                    "input_fingerprint": handoff["independent_job"]["input_fingerprint"],
                    "packet_fingerprint": fingerprint(handoff["peer_packet"]),
                    "qualification_receipt_fingerprint": handoff["qualification_receipt"]["receipt_fingerprint"],
                    "native_dispatch_ready": True,
                },
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }
        if qualified:
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run["run_id"],
                "status": "awaiting_external",
                "awaiting": "independent_provenance",
                "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                "candidate_fingerprint": qualified["candidate_fingerprint"],
                "required_input": ["project_id", "project_repo", "framework_repo", "framework_commit"],
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }
        return None

    def _build_handoff_from_qualified(
        self,
        project_id: str,
        run: dict[str, Any],
        bundle: dict[str, Any],
        qualified: dict[str, Any],
        independent_provenance: dict[str, Any],
    ) -> dict[str, Any]:
        self._assert_independent_project_identity(project_id)
        if independent_provenance.get("project_id") != project_id:
            raise ProductionRunError(
                "independent_project_mismatch",
                "independent packet provenance project_id must equal the actual runtime Project",
            )
        positioning = qualified.get("reading_positioning")
        reader_payload = qualified["reader_binding"]["job"]["input"]["payload"]
        if positioning is not None:
            fields = reading_positioning_fields(
                positioning, target_context=bundle["target_context"], reader_grip=qualified["reader_grip"],
                execution_request_fingerprint=(self._execution_scope(project_id, run["run_id"]) or {}).get("request_fingerprint"),
            )
            if {key: reader_payload[key] for key in READER_FIELDS if key in reader_payload} != fields:
                raise ProductionRunError("reader_positioning_mismatch", "independent positioning must equal the completed Reader's frozen input")
        elif any(key in reader_payload for key in READER_FIELDS if key != "reader_grip"):
            raise ProductionRunError("reader_positioning_missing", "the completed Reader's positioning source cannot be dropped before independent review")
        handoff = prepare_independent_review(
            run=run,
            subject_id=qualified["subject_id"],
            candidate_fingerprint=qualified["candidate_fingerprint"],
            candidate_text=qualified["candidate_text"],
            author_objectives=qualified["author_objectives"],
            reader_visible_context=qualified["reader_visible_context"],
            reader_grip=qualified["reader_grip"],
            qualification_receipt=qualified["qualification_receipt"],
            provenance=independent_provenance,
            reading_positioning=positioning,
        )
        handoff["context_bundle_fingerprint"] = bundle["bundle_fingerprint"]
        handoff["freeze_fingerprint"] = bundle["freeze"]["freeze_fingerprint"]
        handoff["document_id"] = qualified["document_id"]
        handoff["reader_binding"] = qualified["reader_binding"]
        handoff["continuity_receipt_fingerprint"] = qualified["continuity_receipt_fingerprint"]
        self._checkpoint(project_id, run["run_id"], "production_independent_handoff", handoff, handoff["candidate_fingerprint"])
        IndependentReviewRepository(self.store).ensure_attempt(project_id, run["run_id"], handoff["candidate_fingerprint"])
        self._set_run(project_id, run["run_id"], "awaiting_external")
        self._event(
            project_id,
            run["run_id"],
            "production_independent_requested",
            {
                "candidate_fingerprint": handoff["candidate_fingerprint"],
                "qualification_receipt_fingerprint": handoff["qualification_receipt"]["receipt_fingerprint"],
                "independent_job_fingerprint": handoff["independent_job"]["input_fingerprint"],
                "peer_packet_fingerprint": fingerprint(handoff["peer_packet"]),
                "authority": False,
            },
        )
        return self._awaiting_external_projection(project_id, {**run, "status": "awaiting_external"}, bundle) or {}

    def execute(
        self, project_id: str, run_id: str, *, service_id: str, instruction: str | None = None,
        document_id: str | None = None, model_preference: str | None = None,
        stage_budgets: dict[str, int] | None = None, reader_grip: str | None = None,
        rule_material: list[dict[str, Any]] | None = None, reader_visible_context: list[dict[str, Any]] | None = None,
        independent_provenance: dict[str, Any] | None = None, repair_preservation: dict[str, Any] | None = None,
        max_model_calls: int = 64, run_cost_budget: int = 10_000_000,
        inherit_repair_request: bool = False,
        craft_guidance_mode: str | None = None,
        style_pack_root: str | Path | None = None,
        style_pack_manifest_fingerprint: str | None = None,
        confirmed_prefix_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(inherit_repair_request, bool):
            raise ProductionRunError("invalid_args", "inherit_repair_request must be boolean")
        if repair_preservation is not None:
            raise ProductionRunError("repair_preservation_core_owned", "repair comparison evidence must be executed and bound by Core")
        run = self._run_row(project_id, run_id)
        source = self._repair_source(project_id, run)
        confirmed_prefix = self._confirmed_prefix_source(project_id, run, source)
        frozen_prefix_fingerprint = (
            confirmed_prefix["frozen"]["prefix_fingerprint"] if confirmed_prefix else None
        )
        if confirmed_prefix_fingerprint not in {None, frozen_prefix_fingerprint}:
            raise ProductionRunError(
                "confirmed_prefix_changed",
                "execution cannot replace its Core-frozen confirmed prefix",
            )
        if confirmed_prefix_fingerprint is not None and confirmed_prefix is None:
            raise ProductionRunError(
                "confirmed_prefix_missing",
                "execution supplied a confirmed prefix for an ordinary run",
            )
        if inherit_repair_request:
            if source is None:
                raise ProductionRunError("repair_source_required", "only a frozen REVISE source can supply the original request")
            if any(value is not None for value in (instruction, reader_grip, rule_material, reader_visible_context)):
                raise ProductionRunError("repair_request_conflict", "inherited repair inputs cannot be replaced by caller inputs")
            original = source["source_request"]
            instruction, reader_grip = original["instruction"], original["reader_grip"]
            rule_material = deepcopy(original["rule_material"])
            reader_visible_context = deepcopy(original.get("reader_visible_context") or [])
        if source and any(value != source["source_request"].get(key) for key, value in (
                ("instruction", instruction), ("reader_grip", reader_grip), ("rule_material", rule_material))):
            raise ProductionRunError("repair_objective_changed", "this repair must retain the exact original request, reader grip and rule material")
        if source and (reader_visible_context or []) != (source["source_request"].get("reader_visible_context") or []):
            raise ProductionRunError("repair_objective_changed", "this repair must retain the original reader-visible context")
        if not isinstance(instruction, str) or not instruction.strip() or not isinstance(service_id, str) or not service_id.strip():
            raise ProductionRunError("invalid_args", "instruction and service_id are required")
        if reader_grip not in READER_GRIP_VALUES:
            raise ProductionRunError("invalid_args", "reader_grip must be low|medium|high|very_high")
        if not isinstance(rule_material, list) or not rule_material or any(not isinstance(item, dict) for item in rule_material):
            raise ProductionRunError("quality_rule_material_required", "non-empty authoritative rule_material is required")
        if reader_visible_context is not None and (
            not isinstance(reader_visible_context, list) or any(not isinstance(item, dict) for item in reader_visible_context)
        ):
            raise ProductionRunError("invalid_args", "reader_visible_context must be an object array")
        target = run["target_context"]
        if document_id is not None and document_id != target["document_id"]:
            raise ProductionRunError("target_document_mismatch", "execution cannot replace the Core-frozen target document")
        craft_snapshot = self._craft_snapshot(
            project_id, run_id, craft_guidance_mode, source, style_pack_root,
            style_pack_manifest_fingerprint, confirmed_prefix,
        )
        request = {
            "service_id": service_id, "instruction": instruction,
            "document_id": target["document_id"], "model_preference": model_preference,
            "stage_budgets": stage_budgets or {}, "reader_grip": reader_grip,
            "rule_material": rule_material, "reader_visible_context": reader_visible_context or [],
            "repair_preservation": repair_preservation,
            "max_model_calls": max_model_calls,
            "run_cost_budget": run_cost_budget,
            "craft_guidance": craft_snapshot,
            "framework_build": framework_build_identity(),
        }
        if frozen_prefix_fingerprint is not None:
            request["confirmed_prefix_fingerprint"] = frozen_prefix_fingerprint
        assert_secret_free(request, label="frozen production request")
        # Public labels are explicit task inputs, not metadata mined from a
        # plan or author preference. Reject malformed declarations before any
        # profile/selector/model call, then derive them again from the bundle.
        request_fingerprint = fingerprint(request)
        build_reading_positioning(
            target_context=target, reader_grip=reader_grip,
            execution_request_fingerprint=request_fingerprint,
        )
        # Provenance may be supplied after qualification. It cannot alter any
        # generation input or replace an already-frozen independent packet.
        try:
            owner = self.stage_repository.acquire(project_id, run_id, request)
        except ProductionStageError as exc:
            self._raise_stage_repository(exc)
        cancellation = CancellationToken()
        scope = {"store": self.store, "project_id": project_id, "run_id": run_id, "owner": owner, "cancellation": cancellation,
                 "request_fingerprint": request_fingerprint, "reader_grip": reader_grip,
                 "framework_build_fingerprint": request["framework_build"]["build_fingerprint"]}
        token = _EXECUTION_SCOPE.set(scope)
        stop = threading.Event()

        def keep_alive() -> None:
            while not stop.wait(self.stage_repository.lease_seconds / 3):
                try:
                    self.stage_repository.renew(project_id, run_id, owner)
                except Exception:
                    cancellation.cancel()
                    return

        heartbeat = threading.Thread(target=keep_alive, name=f"qf-production-{run_id}", daemon=True)
        heartbeat.start()
        try:
            journal = self.stage_repository.projection(project_id, run_id)
            if (
                journal.get("hard_unconfirmed_call_ids", journal["unconfirmed_call_ids"])
                or journal.get("billing_reconciliation_call_ids")
            ):
                self._set_run(project_id, run_id, "semantic_pending")
                return self._unconfirmed_projection(project_id, run_id)
            return self._execute_frozen(project_id, run_id, **request, independent_provenance=independent_provenance)
        except ProductionRunError as exc:
            if self.status(project_id, run_id)["status"] == "cancelled":
                return {"schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id,
                        "status": "cancelled", "candidate_visible": False, "raw_draft_visible": False, "authority": False}
            if exc.code in {"model_call_budget_exhausted", "run_cost_budget_exhausted"}:
                self._set_run(project_id, run_id, "budget_exhausted")
                return {"schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id,
                        "status": "budget_exhausted", "execution_journal": self.stage_repository.projection(project_id, run_id),
                        "candidate_visible": False, "raw_draft_visible": False, "authority": False}
            if exc.code in {"selected_preference_stale", "settled_source_stale", "settled_source_invalid", "target_context_invalid"}:
                self._set_run(project_id, run_id, "stale_conflict")
                return {"schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id,
                        "status": "stale_conflict", "validation": {"status": "stale_conflict", "proceed": False, "code": exc.code},
                        "new_context_fingerprint_required": True, "candidate_visible": False, "raw_draft_visible": False, "authority": False}
            if exc.code in {
                "stage_result_unconfirmed", "stage_deadline_exceeded",
                "stage_result_pending", "billing_reconciliation_required",
            }:
                self._set_run(project_id, run_id, "semantic_pending")
                return self._unconfirmed_projection(project_id, run_id)
            if exc.code == "run_cancelled":
                return {
                    "schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id,
                    "status": "cancelled", "candidate_visible": False, "raw_draft_visible": False, "authority": False,
                }
            if exc.code in {"semantic_pending", "semantic_output_invalid"}:
                self._record_semantic_failure(project_id, run_id, exc)
            raise
        except Exception as exc:
            # Unexpected internal faults are the only path that may create a
            # build-migration source. Persist a type-only fingerprint so
            # private prompt/result text is never copied into bug metadata.
            error_fingerprint = fingerprint({
                "schema": "quillframe_framework_bug_evidence_v1",
                "error_type": type(exc).__name__,
                "request_fingerprint": request_fingerprint,
                "framework_build_fingerprint": request["framework_build"]["build_fingerprint"],
            })
            try:
                self.stage_repository.mark_framework_bug_blocked(
                    project_id, run_id, owner,
                    error_type=type(exc).__name__,
                    error_fingerprint=error_fingerprint,
                )
            except Exception:
                # Never replace the original Framework exception. If a stage
                # is unconfirmed or accounting is incomplete, migration stays
                # unavailable and the ordinary recovery evidence remains.
                pass
            raise
        finally:
            stop.set()
            heartbeat.join(timeout=1)
            try:
                self.stage_repository.release(project_id, run_id, owner)
            finally:
                _EXECUTION_SCOPE.reset(token)

    def _unconfirmed_projection(self, project_id: str, run_id: str) -> dict[str, Any]:
        journal = self.stage_repository.projection(project_id, run_id)
        pollable = bool(journal.get("pending_call_ids") and not journal.get("hard_unconfirmed_call_ids"))
        billing_required = bool(journal.get("billing_reconciliation_call_ids"))
        return {
            "schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id,
            "status": "semantic_pending",
            "awaiting": (
                "billing_reconciliation" if billing_required
                else "same_model_request" if pollable
                else "stage_result_confirmation"
            ),
            "execution_journal": journal,
            "automatic_model_retry": False, "same_request_poll_only": pollable,
            "candidate_visible": False, "raw_draft_visible": False, "authority": False,
        }

    def _execute_frozen(
        self,
        project_id: str,
        run_id: str,
        *,
        service_id: str,
        instruction: str,
        document_id: str | None = None,
        model_preference: str | None = None,
        stage_budgets: dict[str, int] | None = None,
        reader_grip: str,
        rule_material: list[dict[str, Any]],
        reader_visible_context: list[dict[str, Any]] | None = None,
        independent_provenance: dict[str, Any] | None = None,
        repair_preservation: dict[str, Any] | None = None,
        max_model_calls: int = 64,
        run_cost_budget: int = 10_000_000,
        craft_guidance: dict[str, Any],
        framework_build: dict[str, Any],
        confirmed_prefix_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(instruction, str) or not instruction.strip():
            raise ProductionRunError("invalid_args", "instruction is required")
        if reader_grip not in READER_GRIP_VALUES:
            raise ProductionRunError("invalid_args", "reader_grip must be low|medium|high|very_high")
        if not isinstance(rule_material, list) or not rule_material or any(not isinstance(item, dict) for item in rule_material):
            raise ProductionRunError("quality_rule_material_required", "non-empty authoritative rule_material is required for registered candidate self-audit")
        reader_visible_context = reader_visible_context or []
        if not isinstance(reader_visible_context, list) or any(not isinstance(item, dict) for item in reader_visible_context):
            raise ProductionRunError("invalid_args", "reader_visible_context must be an object array")
        assert_secret_free(rule_material, label="quality rule material")
        assert_secret_free(reader_visible_context, label="reader-visible context")
        scope = self._execution_scope(project_id, run_id)
        if (
            not isinstance(framework_build, dict)
            or scope is None
            or framework_build.get("build_fingerprint") != scope.get("framework_build_fingerprint")
        ):
            raise ProductionRunError("framework_build_changed", "production graph changed its frozen Framework build binding")

        run = self._run_row(project_id, run_id)
        if run["task_mode"] not in {"DRAFT", "REVISE"}:
            raise ProductionRunError("production_mode_unsupported", "author.run.execute supports DRAFT/REVISE only")
        bundle = self._latest_bundle(project_id, run_id)
        completed = self._completed_projection(project_id, run, bundle)
        if completed is not None:
            return completed
        self._validate_selected_preferences(project_id, run["target_context"])
        if run.get("status") == "failed_gate":
            raise ProductionRunError("failed_gate_requires_fresh_run", "a semantic gate rejected this run; create a fresh DRAFT/REVISE run instead of reviewer-shopping or replaying it")
        source = self._repair_source(project_id, run)
        confirmed_prefix = self._confirmed_prefix_source(project_id, run, source)
        actual_prefix_fingerprint = (
            confirmed_prefix["frozen"]["prefix_fingerprint"] if confirmed_prefix else None
        )
        if actual_prefix_fingerprint != confirmed_prefix_fingerprint:
            raise ProductionRunError(
                "confirmed_prefix_changed",
                "frozen execution request does not bind the current confirmed prefix",
            )
        if source:
            source_bundle = self._latest_bundle(project_id, source["source_run_id"])
            if not source_bundle or source_bundle.get("bundle_fingerprint") != source["source_context_bundle_fingerprint"]:
                raise ProductionRunError("repair_source_stale", "the source context bundle changed")
            validate_bundle_integrity(source_bundle)
            if source.get("source_kind") != "author_revision":
                validation = self._validate_bundle_current(project_id, source_bundle)
                if not validation.get("proceed"):
                    raise ProductionRunError("repair_source_stale", "the failed source context is no longer current")
            # An author-requested revision retains exact historical source
            # evidence, but its new context is frozen and checked below. It
            # does not relabel the old context as current authority.
        if bundle and self._latest_independent_handoff(project_id, run_id):
            # Recover a process that committed the frozen packet before the
            # awaiting_external status/event. Never mint a replacement nonce.
            self._set_run(project_id, run_id, "awaiting_external")
            run = {**run, "status": "awaiting_external"}
        if bundle:
            waiting = self._awaiting_external_projection(project_id, run, bundle)
            if waiting:
                if waiting.get("awaiting") == "independent_provenance" and independent_provenance:
                    qualified = self._latest_checkpoint(project_id, run_id, "production_qualified_candidate")
                    if not qualified:
                        raise ProductionRunError("qualified_candidate_missing", "awaiting independent provenance but qualification checkpoint is missing")
                    validation = self._validate_bundle_current(project_id, bundle)
                    if not validation.get("proceed"):
                        self._set_run(project_id, run_id, "stale_conflict")
                        return {
                            "schema": PRODUCTION_EXECUTION_SCHEMA,
                            "project_id": project_id,
                            "run_id": run_id,
                            "status": "stale_conflict",
                            "validation": validation,
                            "new_context_fingerprint_required": True,
                            "candidate_visible": False,
                            "raw_draft_visible": False,
                            "authority": False,
                        }
                    return self._build_handoff_from_qualified(project_id, run, bundle, qualified, independent_provenance)
                return waiting

        if not bundle:
            try:
                bundle = self.prepare_context(
                    project_id,
                    run_id,
                    service_id=service_id,
                    instruction=instruction,
                    model_preference=model_preference,
                    stage_budgets=stage_budgets,
                )
            except ProductionRunError as exc:
                if exc.code == "stage_result_pending":
                    self._set_run(project_id, run_id, "semantic_pending")
                    raise
                self._set_run(project_id, run_id, "semantic_pending" if exc.code == "semantic_pending" else "failed_gate")
                self._event(project_id, run_id, "production_context_failed", {"code": exc.code, "message": str(exc), "detail": exc.detail})
                raise

        self._set_run(project_id, run_id, "semantic_running")
        history = self._reader_history(bundle)
        if reader_visible_context and reader_visible_context != history:
            raise ProductionRunError("reader_context_untrusted", "Blind Reader history must equal the Core-frozen accepted source projection")
        reader_visible_context = history
        reading_positioning = build_reading_positioning(
            target_context=bundle["target_context"], reader_grip=reader_grip,
            execution_request_fingerprint=(self._execution_scope(project_id, run_id) or {}).get("request_fingerprint"),
        )
        reader_fields = reading_positioning_fields(
            reading_positioning, target_context=bundle["target_context"], reader_grip=reader_grip,
        )
        validate_craft_snapshot(craft_guidance)
        artifacts: dict[str, Any] = {"reading_positioning": reading_positioning, "craft_snapshot": deepcopy(craft_guidance)}
        public_receipts: list[dict[str, Any]] = []
        reader_binding: dict[str, Any] | None = None
        registered = RegisteredSemanticExecutor(
            self.agent_runtime, invoke=self._invoke_agent,
            confirm_validation=self._confirm_registered_validation,
        )
        repair: dict[str, Any] | None = None
        mechanisms = PRE_INDEPENDENT_MECHANISMS
        if confirmed_prefix:
            if source is None:
                raise ProductionRunError(
                    "confirmed_prefix_invalid",
                    "confirmed prefix recovery lost its repair source",
                )
            validation = self._validate_bundle_current(project_id, bundle)
            if not validation.get("proceed"):
                raise ProductionRunError(
                    "confirmed_prefix_context_changed",
                    "current Project state changed before prefix materialization",
                    detail=validation,
                )
            repair, reader_binding, public_receipts = self._seed_confirmed_prefix(
                project_id,
                run,
                bundle,
                source,
                confirmed_prefix,
                artifacts,
                reading_positioning=reading_positioning,
                reader_visible_context=reader_visible_context,
                reader_grip=reader_grip,
            )
            mechanisms = ()
        elif source:
            frozen_story = self.materialize_stage_context(bundle, "story_canon_preflight")
            envelope = objective_envelope(source, frozen_story, reading_positioning=reading_positioning)
            editor = registered.execute(
                run=run, service_id=service_id, contract_id="editor.repair_spec", subject_id=document_id or source["source_target_context"]["document_id"],
                payload=editor_payload(source, envelope, frozen_story), model_preference=model_preference,
                runtime_role="registered_repair_editor", max_output_tokens=4200,
            )
            repair = generation_plan(editor, envelope, source_kind=source.get("source_kind"))
            if repair["policy"]["repair_owner"] in {"runtime", "human", "research", "context"}:
                self._set_run(project_id, run_id, "failed_gate")
                self._event(project_id, run_id, "production_repair_requires_external_action", {
                    "repair_owner": repair["policy"]["repair_owner"], "editor_binding_fingerprint": editor["binding_fingerprint"], "authority": False,
                })
                raise ProductionRunError("repair_owner_requires_external_action", "the Editor selected a repair requiring a separate authorized action")
            self._checkpoint(project_id, run_id, "production_repair_plan", {"editor_binding": editor, "generation_plan": repair}, fingerprint(repair))
            artifacts.update({"repair": repair, "repair_source": source})
            self._event(project_id, run_id, "production_repair_planned", {
                "source_run_id": source["source_run_id"], "source_candidate_fingerprint": source["candidate_fingerprint"],
                "generation_mode": repair["policy"]["generation_mode"], "repair_owner": repair["policy"]["repair_owner"],
                "editor_binding_fingerprint": editor["binding_fingerprint"], "authority": False,
            })

        if (source and source.get("source_kind") == "author_revision" and repair
                and repair["policy"]["generation_mode"] == "local_or_bounded_repair"
                and confirmed_prefix is None):
            if self._local_revision_context_reusable(bundle, source):
                self._seed_local_author_revision(project_id, run, bundle, source, artifacts, repair)
                mechanisms = ("surface_realization", "reader_engagement", "continuity")
            else:
                # The prose remains the authorized repair source, but changed
                # context must rebuild every causal checkpoint before editing.
                self._seed_local_author_revision_text(project_id, run, bundle, source, artifacts)
                mechanisms = PRE_INDEPENDENT_MECHANISMS

        for mechanism in mechanisms:
            validation = self._validate_bundle_current(project_id, bundle)
            self._event(
                project_id,
                run_id,
                "context_freeze_preflight",
                {
                    "mechanism": mechanism,
                    "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                    "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                    "validation_status": validation.get("status"),
                    "tracked_db_fetch": True,
                    "worker_db_fetch": False,
                },
            )
            if not validation.get("proceed"):
                self._set_run(project_id, run_id, "stale_conflict")
                result = {
                    "schema": PRODUCTION_EXECUTION_SCHEMA,
                    "project_id": project_id,
                    "run_id": run_id,
                    "status": "stale_conflict",
                    "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                    "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                    "validation": validation,
                    "candidate_visible": False,
                    "raw_draft_visible": False,
                    "new_context_fingerprint_required": True,
                    "authority": False,
                }
                self._event(project_id, run_id, "production_stale_conflict", {"context_bundle_fingerprint": bundle["bundle_fingerprint"], "validation": validation})
                return result

            try:
                if mechanism == "reader_engagement":
                    candidate_text = str((artifacts.get("surface_realization") or {}).get("text") or "")
                    candidate_fingerprint = fingerprint_text(candidate_text)
                    reader_binding = registered.execute(
                        run=run,
                        service_id=service_id,
                        contract_id="reader.engagement_audit",
                        subject_id=str(document_id or run.get("target_ref") or run_id),
                        payload={
                            "candidate_fingerprint": candidate_fingerprint,
                            "candidate_text": candidate_text,
                            "reader_visible_context": reader_visible_context,
                            **reader_fields,
                        },
                        model_preference=model_preference,
                        runtime_role="registered_reader_engagement",
                    )
                    public = self._registered_stage_receipt(
                        bundle=bundle,
                        mechanism=mechanism,
                        binding=reader_binding,
                        candidate_fingerprint=candidate_fingerprint,
                    )
                    internal = {
                        "status": semantic_status(reader_binding),
                        "summary": reader_binding["result"]["judgment"].get("report"),
                        "findings": reader_binding["result"]["judgment"].get("evidence_refs", []),
                    }
                else:
                    public, internal = self._run_stage(
                        run,
                        bundle,
                        mechanism,
                        service_id=service_id,
                        user_instruction=instruction,
                        model_preference=model_preference,
                        artifacts=artifacts,
                    )
            except ProductionRunError as exc:
                if exc.code == "stage_result_pending":
                    raise
                if exc.code in {"semantic_pending", "semantic_output_invalid"}:
                    self._record_semantic_failure(project_id, run_id, exc, mechanism=mechanism)
                else:
                    self._set_run(project_id, run_id, "failed_gate")
                    self._event(project_id, run_id, "production_stage_failed", {"mechanism": mechanism, "code": exc.code, "message": str(exc), "detail": exc.detail})
                raise

            self._persist_stage_receipt(project_id, run_id, public)
            public_receipts.append(public)
            artifacts[mechanism] = internal
            if internal.get("status") == "pending":
                self._set_run(project_id, run_id, "semantic_pending")
                return {
                    "schema": PRODUCTION_EXECUTION_SCHEMA,
                    "project_id": project_id,
                    "run_id": run_id,
                    "status": "semantic_pending",
                    "pending_mechanism": mechanism,
                    "candidate_visible": False,
                    "raw_draft_visible": False,
                    "authority": False,
                }
            # A confirmed Reader rejection still needs continuity/self-audit
            # evidence for a repair source. Keep its FAIL binding unchanged;
            # pre-independent qualification below will block release.
            if internal.get("status") == "fail" and mechanism != "reader_engagement":
                self._set_run(project_id, run_id, "failed_gate")
                self._event(project_id, run_id, "production_gate_rejected", {"mechanism": mechanism, "stage_result_fingerprint": public["stage_result_fingerprint"]})
                return {
                    "schema": PRODUCTION_EXECUTION_SCHEMA,
                    "project_id": project_id,
                    "run_id": run_id,
                    "status": "failed_gate",
                    "failed_mechanism": mechanism,
                    "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                    "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                    "stage_receipts": public_receipts,
                    "candidate_visible": False,
                    "raw_draft_visible": False,
                    "authority": False,
                }

        if reader_binding is None:
            raise ProductionRunError("reader_binding_missing", "registered reader engagement result missing")
        candidate_text = str((artifacts.get("surface_realization") or {}).get("text") or "")
        candidate_fingerprint = fingerprint_text(candidate_text)
        target_document = document_id or run.get("target_ref")
        if not isinstance(target_document, str) or not target_document.strip():
            self._set_run(project_id, run_id, "failed_gate")
            raise ProductionRunError("target_document_required", "document_id or document target_ref is required before candidate qualification")
        continuity_receipt = next((receipt for receipt in public_receipts if receipt["mechanism"] == "continuity"), None)
        if not continuity_receipt:
            raise ProductionRunError("continuity_receipt_missing", "continuity stage receipt missing before qualification")
        author_objectives = (artifacts.get("scene_simulation") or {}).get("author_objectives")
        if not isinstance(author_objectives, dict):
            raise ProductionRunError("author_objectives_missing", "the exact objectives shown to the Writer are required for review")

        try:
            self_audit = registered.execute(
                run=run,
                service_id=service_id,
                contract_id="quality.candidate_self_audit",
                subject_id=target_document,
                payload={
                    "candidate_fingerprint": candidate_fingerprint,
                    "candidate_text": candidate_text,
                    "rule_material": rule_material,
                    "reader_grip": reader_grip,
                    "author_objectives": author_objectives,
                },
                model_preference=model_preference,
                runtime_role="registered_candidate_self_audit",
                max_output_tokens=5200,
            )
            repair_cycle = 0
            lineage = None
            if source and repair:
                lineage = candidate_lineage(source, run, candidate_text, repair)
                repair_cycle = len(lineage["nodes"]) - 1
                comparison = registered.execute(
                    run=run, service_id=service_id, contract_id="quality.compare", subject_id="repair:" + run_id,
                    payload=comparison_payload(source, run, candidate_text, repair, lineage), model_preference=model_preference,
                    runtime_role="registered_repair_comparison", max_output_tokens=4200,
                )
                repair_preservation = {"status": comparison_gate_status(comparison["result"]["judgment"]), "semantic_binding": comparison}
            qualification = build_pre_independent_qualification(
                subject_id=target_document,
                candidate_fingerprint=candidate_fingerprint,
                self_audit_binding=self_audit,
                reader_binding=reader_binding,
                continuity_receipt_fingerprint=continuity_receipt["stage_result_fingerprint"],
                repair_cycle=repair_cycle,
                repair_preservation=repair_preservation,
            )
        except ProductionRunError as exc:
            self._set_run(project_id, run_id, "semantic_pending" if exc.code in {
                "semantic_pending", "semantic_output_invalid", "stage_result_pending",
            } else "failed_gate")
            raise

        qualified_state = {
            "schema": "quillframe_qualified_diagnostic_candidate_v1",
            "run_id": run_id,
            "subject_id": target_document,
            "document_id": target_document,
            "candidate_fingerprint": candidate_fingerprint,
            "candidate_text": candidate_text,
            "context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "reader_grip": reader_grip,
            "reading_positioning": reading_positioning,
            "reader_visible_context": reader_visible_context,
            "reader_binding": reader_binding,
            "self_audit_binding": self_audit,
            "author_objectives": author_objectives,
            "continuity_receipt_fingerprint": continuity_receipt["stage_result_fingerprint"],
            "qualification_receipt": qualification,
            "authority": False,
        }
        if lineage:
            qualified_state["repair_lineage"] = lineage
            qualified_state["repair_preservation"] = repair_preservation
        if confirmed_prefix:
            qualified_state["confirmed_prefix_fingerprint"] = confirmed_prefix["frozen"]["prefix_fingerprint"]
            qualified_state["confirmed_prefix_reuse_fingerprint"] = (
                self._latest_checkpoint(project_id, run_id, "production_confirmed_prefix_reuse") or {}
            ).get("reuse_fingerprint")
        if qualification["qualification_status"] == "qualified_for_independent":
            observation = registered.execute(
                run=run, service_id=service_id, contract_id="reader.expectations", subject_id=target_document,
                payload={"chapter_id": bundle["target_context"]["chapter_id"], "document_id": target_document,
                         "candidate_fingerprint": candidate_fingerprint, "candidate_text": candidate_text,
                         "current_reading_order": bundle["target_context"]["current_reading_order"],
                         "reader_visible_context": reader_visible_context, "existing_expectations": bundle["reader_expectations"]},
                model_preference=model_preference, runtime_role="registered_reader_expectations", max_output_tokens=3600,
            )
            try:
                validate_observation_binding(observation)
            except ReaderExpectationError as exc:
                raise ProductionRunError("semantic_output_invalid", str(exc)) from exc
            qualified_state["reader_expectation_binding"] = observation
            narrative_payload = {
                "chapter_id": bundle["target_context"]["chapter_id"],
                "document_id": target_document,
                "candidate_fingerprint": candidate_fingerprint,
                "candidate_text": candidate_text,
                "current_story_order": bundle["target_context"]["current_story_order"],
                "existing_state": narrative_existing_state(bundle),
            }
            try:
                narrative = registered.execute(
                    run=run, service_id=service_id, contract_id="narrative.world",
                    subject_id=target_document, payload=narrative_payload,
                    model_preference=model_preference,
                    runtime_role="registered_narrative_state", max_output_tokens=5200,
                )
            except ProductionRunError as exc:
                if (exc.code != "semantic_output_invalid"
                        or "did not return one JSON object" not in str(exc)):
                    raise
                # Never repair JSON locally or reuse malformed bytes. Dispatch
                # one fresh, separately journaled reconstruction against the
                # exact same frozen contract and candidate.
                narrative = registered.execute(
                    run=run, service_id=service_id, contract_id="narrative.world",
                    subject_id=target_document + ":format-repair-1",
                    payload=narrative_payload, model_preference=model_preference,
                    runtime_role="registered_narrative_state_format_repair",
                    max_output_tokens=5200,
                )
            try:
                proposal = build_narrative_state_proposal(narrative, bundle)
            except ProductionRunError as exc:
                if exc.code != "narrative_evidence_mismatch":
                    raise
                try:
                    narrative = registered.execute(
                        run=run, service_id=service_id, contract_id="narrative.world",
                        subject_id=target_document + ":evidence-repair-1",
                        payload=narrative_payload, model_preference=model_preference,
                        runtime_role="registered_narrative_state_evidence_repair",
                        max_output_tokens=5200,
                    )
                except ProductionRunError as repair_dispatch_exc:
                    if repair_dispatch_exc.code != "model_call_budget_exhausted":
                        raise
                    proposal = None
                    self._event(project_id, run_id, "production_narrative_proposal_omitted", {
                        "reason": "unsupported_exact_candidate_quote_at_model_budget_boundary",
                        "registered_binding_fingerprint": narrative["binding_fingerprint"],
                        "repair_model_call_dispatched": False,
                        "authority": False,
                    })
                else:
                    try:
                        proposal = build_narrative_state_proposal(narrative, bundle)
                    except ProductionRunError as repair_exc:
                        if repair_exc.code != "narrative_evidence_mismatch":
                            raise
                        proposal = None
                        self._event(project_id, run_id, "production_narrative_proposal_omitted", {
                            "reason": "unsupported_exact_candidate_quote_after_fresh_reconstruction",
                            "registered_binding_fingerprint": narrative["binding_fingerprint"],
                            "repair_model_call_dispatched": True,
                            "authority": False,
                        })
            if proposal is not None:
                self._checkpoint(project_id, run_id, "production_narrative_proposal", {
                    "proposal": proposal, "registered_binding": narrative,
                }, proposal["proposal_fingerprint"])
        self._checkpoint(project_id, run_id, "production_qualified_candidate", qualified_state, candidate_fingerprint)
        self._event(
            project_id,
            run_id,
            "production_candidate_qualified",
            {
                "candidate_fingerprint": candidate_fingerprint,
                "qualification_status": qualification["qualification_status"],
                "qualification_receipt_fingerprint": qualification["receipt_fingerprint"],
                "authority": False,
            },
        )

        if qualification["qualification_status"] == "awaiting_semantic":
            self._set_run(project_id, run_id, "semantic_pending")
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run_id,
                "status": "semantic_pending",
                "pending": qualification["pending_gates"],
                "candidate_fingerprint": candidate_fingerprint,
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }
        if qualification["qualification_status"] != "qualified_for_independent":
            self._set_run(project_id, run_id, "failed_gate")
            self._event(project_id, run_id, "production_gate_rejected", {
                "mechanism": "pre_independent_qualification", "stage_result_fingerprint": qualification["receipt_fingerprint"],
            })
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run_id,
                "status": "failed_gate",
                "failed_mechanism": "pre_independent_qualification",
                "qualification": {
                    "status": qualification["qualification_status"],
                    "failed_gates": qualification["failed_gates"],
                    "blocking_finding_count": len(qualification["blocking_findings"]),
                    "receipt_fingerprint": qualification["receipt_fingerprint"],
                },
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }

        self._set_run(project_id, run_id, "awaiting_external")
        if not independent_provenance:
            return self._awaiting_external_projection(project_id, {**run, "status": "awaiting_external"}, bundle) or {}
        return self._build_handoff_from_qualified(project_id, run, bundle, qualified_state, independent_provenance)

    def _process_independent_submission(
        self,
        project_id: str,
        run_id: str,
        *,
        peer_packet: dict[str, Any],
        result: dict[str, Any],
        independence_receipt: dict[str, Any],
        submission_evidence_fingerprint: str,
        processing_repository: IndependentReviewRepository,
        processing_candidate_fingerprint: str,
        processing_token: str,
        processing_epoch: int,
    ) -> dict[str, Any]:
        def effect_guard(conn) -> None:  # noqa: ANN001
            try:
                processing_repository.assert_and_renew_attempt_owner(
                    conn,
                    project_id,
                    run_id,
                    processing_candidate_fingerprint,
                    processing_token,
                    processing_epoch,
                )
            except IndependentReviewError as exc:
                self._raise_independent_repository(exc)

        def mark_effects_started() -> None:
            try:
                processing_repository.mark_attempt_effects_started(
                    project_id,
                    run_id,
                    processing_candidate_fingerprint,
                    processing_token,
                    processing_epoch,
                )
            except IndependentReviewError as exc:
                self._raise_independent_repository(exc)

        run = self._run_row(project_id, run_id)
        if run.get("status") == "completed":
            bundle = self._latest_bundle(project_id, run_id)
            mark_effects_started()
            replay = self._completed_projection(
                project_id,
                run,
                bundle,
                expected_submission_evidence_fingerprint=submission_evidence_fingerprint,
            )
            if replay is None:
                raise ProductionRunError("completed_run_missing_candidate", "completed production run has no candidate")
            self._persist_candidate_ready_event(
                project_id,
                run_id,
                candidate_id=replay["candidate"]["candidate_id"],
                candidate_fingerprint=replay["candidate"]["candidate_fingerprint"],
                context_bundle_fingerprint=str(replay.get("context_bundle_fingerprint") or ""),
                independent_result_fingerprint=independence_receipt.get("result_fingerprint"),
                effect_guard=effect_guard,
            )
            return replay
        if run.get("status") not in {"awaiting_external", "failed_gate", "semantic_pending"}:
            raise ProductionRunError("independent_submission_not_expected", f"run status is {run.get('status')}, not awaiting_external")
        bundle = self._latest_bundle(project_id, run_id)
        handoff = self._latest_independent_handoff(project_id, run_id)
        if not bundle or not handoff:
            raise ProductionRunError("independent_handoff_missing", "frozen Context bundle and independent handoff are required")
        validation = self._validate_bundle_current(project_id, bundle)
        if not validation.get("proceed"):
            self._set_independent_run(project_id, run_id, "stale_conflict", effect_guard=effect_guard)
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run_id,
                "status": "stale_conflict",
                "validation": validation,
                "new_context_fingerprint_required": True,
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }

        independent_binding = validate_independent_submission(
            handoff=handoff,
            peer_packet=peer_packet,
            result=result,
            independence_receipt=independence_receipt,
        )
        independent_binding["submission_evidence_fingerprint"] = submission_evidence_fingerprint
        packet_project_id = ((handoff.get("independent_job") or {}).get("provenance") or {}).get("project_id")
        if packet_project_id != project_id or independence_receipt.get("project_id") != project_id:
            raise ProductionRunError("independent_project_mismatch", "packet and receipt must bind the actual runtime Project")
        readiness = final_readiness(
            candidate_fingerprint=handoff["candidate_fingerprint"],
            qualification_receipt=handoff["qualification_receipt"],
            reader_binding=handoff["reader_binding"],
            continuity_receipt_fingerprint=handoff["continuity_receipt_fingerprint"],
            independent_binding=independent_binding,
            reader_grip=handoff["reader_grip"],
        )

        independent_stage = self.materialize_stage_context(bundle, "independent_semantic_gate")
        independent_judgment = result.get("judgment") or {}
        independent_receipt = public_stage_result(
            mechanism="independent_semantic_gate",
            context_stage_id=independent_stage["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=independent_stage["stage_context_fingerprint"],
            agent_input_fingerprint=handoff["independent_job"]["input_fingerprint"],
            model_service_id=str((result.get("worker") or {}).get("provider") or "peer_review"),
            model_id=str((result.get("worker") or {}).get("model_or_reviewer") or "independent-reviewer"),
            protocol=str(independence_receipt.get("transport") or "project_owned_peer_bridge"),
            judgment={
                "status": independent_judgment.get("result"),
                "summary": independent_judgment.get("report"),
                "findings": independent_judgment.get("evidence_refs", []),
                "artifact_fingerprint": handoff["candidate_fingerprint"],
            },
        )
        independent_receipt["model_contract_id"] = "quality.production_review"
        independent_receipt["independence_result_fingerprint"] = independence_receipt.get("result_fingerprint")
        independent_receipt["independence_provider"] = (
            independence_receipt.get("provider") or independence_receipt.get("worker_provider")
        )
        independent_receipt["independence_transport"] = (
            independence_receipt.get("transport") or "github_actions"
        )
        independent_receipt["independence_assurance_class"] = (
            independence_receipt.get("assurance_class") or "project_owned_automation_receipt"
        )
        independent_receipt["stage_result_fingerprint"] = fingerprint({key: value for key, value in independent_receipt.items() if key != "stage_result_fingerprint"})
        mark_effects_started()
        self._persist_independent_evidence(
            project_id, run_id, handoff=handoff, result=result, independence_receipt=independence_receipt,
            submission_evidence_fingerprint=submission_evidence_fingerprint, effect_guard=effect_guard,
        )
        self._persist_stage_receipt(project_id, run_id, independent_receipt, effect_guard=effect_guard)

        if not readiness.get("ready_for_user_visible_review"):
            self._set_independent_run(
                project_id,
                run_id,
                "failed_gate" if readiness.get("blocking_gates") else "semantic_pending",
                effect_guard=effect_guard,
            )
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run_id,
                "status": "failed_gate" if readiness.get("blocking_gates") else "semantic_pending",
                "failed_mechanism": "independent_semantic_gate" if readiness.get("blocking_gates") else None,
                "production_readiness": readiness,
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }

        visible_stage = self.materialize_stage_context(bundle, "user_visible_gate")
        visible_receipt = public_stage_result(
            mechanism="user_visible_gate",
            context_stage_id=visible_stage["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=visible_stage["stage_context_fingerprint"],
            agent_input_fingerprint=fingerprint(readiness),
            model_service_id="deterministic_quality_gate",
            model_id="quality.production_readiness",
            protocol="deterministic_conjunctive_gate",
            judgment={
                "status": "pass",
                "summary": "Registered qualification, continuity and independent peer evidence passed the conjunctive user-visible gate.",
                "findings": [],
                "artifact_fingerprint": handoff["candidate_fingerprint"],
            },
        )
        visible_receipt["production_readiness_schema"] = readiness.get("schema")
        visible_receipt["stage_result_fingerprint"] = fingerprint({key: value for key, value in visible_receipt.items() if key != "stage_result_fingerprint"})
        self._persist_stage_receipt(project_id, run_id, visible_receipt, effect_guard=effect_guard)

        release = final_release(
            production_readiness=readiness,
            qualification_receipt=handoff["qualification_receipt"],
            candidate_fingerprint=handoff["candidate_fingerprint"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            user_visible_gate_receipt_fingerprint=visible_receipt["stage_result_fingerprint"],
        )
        if release.get("ready_for_user_visible_review") is not True:
            self._set_independent_run(
                project_id,
                run_id,
                "failed_gate" if release.get("blocking_structural_receipts") else "semantic_pending",
                effect_guard=effect_guard,
            )
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run_id,
                "status": "failed_gate" if release.get("blocking_structural_receipts") else "semantic_pending",
                "failed_mechanism": "production_release",
                "production_readiness": readiness,
                "production_release": release,
                "candidate_visible": False,
                "raw_draft_visible": False,
                "authority": False,
            }
        self._persist_release_receipt(project_id, run_id, release, effect_guard=effect_guard)

        candidate = self._persist_candidate(
            project_id,
            run,
            bundle,
            handoff["document_id"],
            handoff["independent_job"]["input"]["payload"]["candidate_text"],
            handoff["candidate_fingerprint"],
            independent_binding,
            readiness,
            release,
            effect_guard=effect_guard,
        )
        self._set_independent_run(
            project_id,
            run_id,
            "completed",
            result_fingerprint=candidate["candidate_fingerprint"],
            effect_guard=effect_guard,
        )
        self._persist_candidate_ready_event(
            project_id,
            run_id,
            candidate_id=candidate["candidate_id"],
            candidate_fingerprint=candidate["candidate_fingerprint"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            independent_result_fingerprint=independence_receipt.get("result_fingerprint"),
            effect_guard=effect_guard,
        )
        with self.store.open_project(project_id) as conn:
            receipts = [
                _json(row["payload_json"], {})
                for row in conn.execute(
                    "SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY created_at,rowid",
                    (run_id,),
                )
            ]
        return {
            "schema": PRODUCTION_EXECUTION_SCHEMA,
            "project_id": project_id,
            "run_id": run_id,
            "status": "completed",
            "task_mode": run["task_mode"],
            "context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "stage_receipts": receipts,
            "candidate": candidate,
            "candidate_visible": True,
            "raw_draft_visible": False,
            "accepted": False,
            "settled": False,
            "production_readiness": readiness,
            "production_release": release,
            "authority": False,
        }
