from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from harness.context_runtime import canonical_json, fingerprint, stage_context
from persistence.quillframe_sqlite import ConflictError, now_iso

from .context import ProductionContextRuntime
from .contracts import MECHANISM_CONTEXT_STAGE, PRODUCTION_BUNDLE_SCHEMA, PRODUCTION_EXECUTION_SCHEMA, PRODUCTION_MECHANISMS, ProductionRunError, assert_secret_free, parse_json_object, public_stage_result
from .sources import _json


class ProductionRunExecutor(ProductionContextRuntime):
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
        materialized = {
            "mechanism": mechanism, "context_stage_id": context_stage_id,
            "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "loaded_object_ids": loaded_ids, "items": [deepcopy(payloads[object_id]) for object_id in loaded_ids],
            "selector": projection.get("selector"), "db_fetch_performed": False, "authority": False,
        }
        materialized["stage_context_fingerprint"] = fingerprint({key: materialized[key] for key in materialized if key != "authority"})
        return materialized

    @staticmethod
    def _stage_instruction(mechanism: str, user_instruction: str) -> str:
        common = "Return exactly one JSON object. Do not expose private reasoning or credentials. "
        if mechanism == "event_first_raw_draft":
            return common + "Produce the internal event-first raw draft for the user request. JSON: {\"status\":\"pass\"|\"fail\",\"text\":string,\"summary\":string,\"findings\":[]}. Raw draft is internal and will not be shown directly. Request: " + user_instruction
        if mechanism == "surface_realization":
            return common + "Realize the supplied internal draft into candidate prose without changing Canon authority. JSON: {\"status\":\"pass\"|\"fail\",\"text\":string,\"summary\":string,\"findings\":[]}. Request: " + user_instruction
        if mechanism in {"reader_engagement", "continuity", "independent_semantic_gate", "user_visible_gate", "story_canon_preflight"}:
            return common + f"Execute Quillframe mechanism {mechanism}. JSON: {{\"status\":\"pass\"|\"fail\",\"summary\":string,\"findings\":[string]}}. A fail is a real gate result; do not soften it. Request: " + user_instruction
        return common + f"Execute Quillframe mechanism {mechanism}. JSON: {{\"status\":\"pass\"|\"fail\",\"artifact\":object,\"summary\":string,\"findings\":[string]}}. Request: " + user_instruction

    def _run_stage(self, run: dict[str, Any], bundle: dict[str, Any], mechanism: str, *, service_id: str,
                   user_instruction: str, model_preference: str | None, artifacts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        frozen_stage = self.materialize_stage_context(bundle, mechanism)
        upstream: dict[str, Any] = {}
        if mechanism == "surface_realization":
            upstream["raw_draft"] = artifacts.get("event_first_raw_draft")
        elif mechanism in {"reader_engagement", "continuity", "independent_semantic_gate", "user_visible_gate"}:
            upstream["candidate"] = artifacts.get("surface_realization")
        if mechanism == "user_visible_gate":
            upstream["prior_gate_summaries"] = {key: value.get("summary") for key, value in artifacts.items() if isinstance(value, dict) and key in {"reader_engagement", "continuity", "independent_semantic_gate"}}
        context = [{"frozen_stage_context": frozen_stage, "upstream_artifacts": upstream}]
        job, result = self._agent_job(
            run=run, service_id=service_id, runtime_role=mechanism,
            instruction=self._stage_instruction(mechanism, user_instruction), context=context,
            model_preference=model_preference, suffix=mechanism,
            max_output_tokens=7000 if mechanism in {"event_first_raw_draft", "surface_realization"} else 3000,
        )
        if result.status != "completed":
            raise ProductionRunError("semantic_pending" if result.status in {"model_failed", "cancelled"} else "failed_gate", f"production mechanism {mechanism} did not complete", detail={"agent_status": result.status, "errors": result.errors})
        judgment = parse_json_object(result.final_text, label=mechanism)
        status = str(judgment.get("status") or "").strip().lower()
        if status not in {"pass", "fail"}:
            raise ProductionRunError("semantic_output_invalid", f"{mechanism}.status must be pass|fail")
        if mechanism in {"event_first_raw_draft", "surface_realization"}:
            text = judgment.get("text")
            if status == "pass" and (not isinstance(text, str) or not text.strip()):
                raise ProductionRunError("semantic_output_invalid", f"{mechanism} pass result requires non-empty text")
            if isinstance(text, str):
                judgment["artifact_fingerprint"] = fingerprint(text)
        elif "artifact" in judgment:
            judgment["artifact_fingerprint"] = fingerprint(judgment["artifact"])
        public = public_stage_result(
            mechanism=mechanism, context_stage_id=frozen_stage["context_stage_id"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"], freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            stage_context_fingerprint=frozen_stage["stage_context_fingerprint"], agent_input_fingerprint=job.input_fingerprint,
            model_service_id=result.model_service_id, model_id=result.model_id, protocol=result.protocol, judgment=judgment,
        )
        internal = deepcopy(judgment)
        if mechanism == "independent_semantic_gate":
            internal["reviewer_fingerprint"] = fingerprint({"job_input": job.input_fingerprint, "model_service_id": result.model_service_id, "model_id": result.model_id, "protocol": result.protocol, "result": judgment})
        return public, internal

    def _persist_stage_receipt(self, project_id: str, run_id: str, receipt: dict[str, Any]) -> None:
        assert_secret_free(receipt, label="production stage receipt")
        key = f"{run_id}:stage:{receipt['mechanism']}"
        with self.store.open_project(project_id) as conn:
            existing = conn.execute("SELECT payload_json FROM receipts WHERE idempotency_key=?", (key,)).fetchone()
            if existing:
                prior = _json(existing["payload_json"], {})
                if prior.get("stage_result_fingerprint") != receipt.get("stage_result_fingerprint"):
                    raise ProductionRunError("stage_replay_conflict", f"stage receipt changed for immutable idempotency key: {key}")
                return
            conn.execute("INSERT INTO receipts(receipt_id,run_id,receipt_kind,idempotency_key,payload_json,created_at) VALUES(?,?,?,?,?,?)", ("rcpt_" + uuid.uuid4().hex, run_id, "production_stage", key, canonical_json(receipt), now_iso()))
            conn.execute("INSERT INTO runtime_events(event_id,run_id,event_kind,payload_json,created_at) VALUES(?,?,?,?,?)", ("evt_" + uuid.uuid4().hex, run_id, "production_stage_completed", canonical_json({"mechanism": receipt["mechanism"], "stage_result_fingerprint": receipt["stage_result_fingerprint"], "context_bundle_fingerprint": receipt["context_bundle_fingerprint"]}), now_iso()))
            conn.commit()

    def _persist_candidate(self, project_id: str, run: dict[str, Any], bundle: dict[str, Any], document_id: str,
                           text: str, independent: dict[str, Any]) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            document = conn.execute("SELECT document_id FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if not document:
                raise ProductionRunError("target_document_required", f"production candidate target document does not exist: {document_id}")
            latest = self.store.latest_revision(conn, document_id)
            parent_id = latest["revision_id"] if latest else None
        try:
            revision = self.store.save_revision(
                project_id, document_id, text, expected_parent_revision_id=parent_id, source="production_runtime", authority_class="review",
                provenance={"run_id": run["run_id"], "context_bundle_fingerprint": bundle["bundle_fingerprint"], "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"], "authority": False},
            )
        except ConflictError as exc:
            raise ProductionRunError("revision_conflict", str(exc)) from exc
        candidate_id = "cand_" + uuid.uuid4().hex
        review_id = "review_" + uuid.uuid4().hex
        candidate_kind = "draft" if run["task_mode"] == "DRAFT" else "repair"
        stamp = now_iso()
        candidate_fp = revision["content_fingerprint"]
        review_public = {
            "verdict": independent.get("status"), "summary": independent.get("summary"), "findings": independent.get("findings", []),
            "reviewer_fingerprint": independent.get("reviewer_fingerprint"), "context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "private_reasoning_exposed": False,
        }
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,'review_draft',?,'PASS',?)",
                (candidate_id, document_id, revision["revision_id"], run["run_id"], run["task_mode"], candidate_kind, candidate_fp, stamp),
            )
            conn.execute(
                "INSERT INTO review_evidence(review_id,candidate_id,evidence_kind,result_json,candidate_fingerprint,reviewer_fingerprint,independent,stale,created_at) VALUES(?,?,?,?,?,?,1,0,?)",
                (review_id, candidate_id, "independent_semantic_gate", canonical_json(review_public), candidate_fp, independent.get("reviewer_fingerprint"), stamp),
            )
            conn.commit()
        return {"candidate_id": candidate_id, "revision_id": revision["revision_id"], "candidate_fingerprint": candidate_fp, "status": "review_draft", "user_visible_gate": "PASS", "authority": False}

    def _completed_projection(self, project_id: str, run: dict[str, Any], bundle: dict[str, Any] | None) -> dict[str, Any] | None:
        if run.get("status") != "completed":
            return None
        with self.store.open_project(project_id) as conn:
            candidate = conn.execute("SELECT candidate_id,revision_id,content_fingerprint,status,user_visible_gate FROM candidates WHERE run_id=? ORDER BY created_at DESC LIMIT 1", (run["run_id"],)).fetchone()
            receipts = [_json(row["payload_json"], {}) for row in conn.execute("SELECT payload_json FROM receipts WHERE run_id=? AND receipt_kind='production_stage' ORDER BY created_at,rowid", (run["run_id"],))]
        if not candidate:
            raise ProductionRunError("completed_run_missing_candidate", "completed production run has no persisted candidate")
        return {
            "schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run["run_id"], "status": "completed",
            "task_mode": run["task_mode"], "context_bundle_fingerprint": bundle.get("bundle_fingerprint") if bundle else None,
            "freeze_fingerprint": (bundle.get("freeze") or {}).get("freeze_fingerprint") if bundle else None,
            "stage_receipts": receipts, "candidate": {**dict(candidate), "candidate_fingerprint": candidate["content_fingerprint"], "authority": False},
            "candidate_visible": True, "raw_draft_visible": False, "accepted": candidate["status"] == "accepted", "settled": False,
            "replayed": True, "authority": False,
        }

    def execute(self, project_id: str, run_id: str, *, service_id: str, instruction: str,
                document_id: str | None = None, model_preference: str | None = None,
                stage_budgets: dict[str, int] | None = None) -> dict[str, Any]:
        if not isinstance(instruction, str) or not instruction.strip():
            raise ProductionRunError("invalid_args", "instruction is required")
        run = self._run_row(project_id, run_id)
        if run["task_mode"] not in {"DRAFT", "REVISE"}:
            raise ProductionRunError("production_mode_unsupported", "author.run.execute supports DRAFT/REVISE only")
        bundle = self._latest_bundle(project_id, run_id)
        completed = self._completed_projection(project_id, run, bundle)
        if completed is not None:
            return completed
        if run.get("status") == "failed_gate":
            raise ProductionRunError("failed_gate_requires_fresh_run", "a semantic gate rejected this run; create a fresh DRAFT/REVISE run instead of reviewer-shopping or replaying it")
        if run.get("status") == "semantic_running":
            raise ProductionRunError("run_in_progress", "production run is already executing")
        if not bundle:
            try:
                bundle = self.prepare_context(project_id, run_id, service_id=service_id, instruction=instruction, model_preference=model_preference, stage_budgets=stage_budgets)
            except ProductionRunError as exc:
                self._set_run(project_id, run_id, "semantic_pending" if exc.code == "semantic_pending" else "failed_gate")
                self._event(project_id, run_id, "production_context_failed", {"code": exc.code, "message": str(exc), "detail": exc.detail})
                raise
        self._set_run(project_id, run_id, "semantic_running")
        artifacts: dict[str, Any] = {}
        public_receipts: list[dict[str, Any]] = []
        writer_input_fingerprint: str | None = None
        reviewer_input_fingerprint: str | None = None
        for mechanism in PRODUCTION_MECHANISMS:
            validation = self._validate_bundle_current(project_id, bundle)
            self._event(project_id, run_id, "context_freeze_preflight", {"mechanism": mechanism, "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"], "context_bundle_fingerprint": bundle["bundle_fingerprint"], "validation_status": validation.get("status"), "tracked_db_fetch": True, "worker_db_fetch": False})
            if not validation.get("proceed"):
                self._set_run(project_id, run_id, "stale_conflict")
                result = {"schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id, "status": "stale_conflict", "context_bundle_fingerprint": bundle["bundle_fingerprint"], "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"], "validation": validation, "candidate_visible": False, "raw_draft_visible": False, "new_context_fingerprint_required": True, "authority": False}
                self._event(project_id, run_id, "production_stale_conflict", {"context_bundle_fingerprint": bundle["bundle_fingerprint"], "validation": validation})
                return result
            try:
                public, internal = self._run_stage(run, bundle, mechanism, service_id=service_id, user_instruction=instruction, model_preference=model_preference, artifacts=artifacts)
            except ProductionRunError as exc:
                status = "semantic_pending" if exc.code == "semantic_pending" else "failed_gate"
                self._set_run(project_id, run_id, status)
                self._event(project_id, run_id, "production_stage_failed", {"mechanism": mechanism, "code": exc.code, "message": str(exc), "detail": exc.detail})
                raise
            self._persist_stage_receipt(project_id, run_id, public)
            public_receipts.append(public)
            artifacts[mechanism] = internal
            if mechanism == "surface_realization": writer_input_fingerprint = public["agent_input_fingerprint"]
            if mechanism == "independent_semantic_gate": reviewer_input_fingerprint = public["agent_input_fingerprint"]
            if internal.get("status") == "fail":
                self._set_run(project_id, run_id, "failed_gate")
                self._event(project_id, run_id, "production_gate_rejected", {"mechanism": mechanism, "stage_result_fingerprint": public["stage_result_fingerprint"]})
                return {"schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id, "status": "failed_gate", "failed_mechanism": mechanism, "context_bundle_fingerprint": bundle["bundle_fingerprint"], "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"], "stage_receipts": public_receipts, "candidate_visible": False, "raw_draft_visible": False, "authority": False}
        if not writer_input_fingerprint or not reviewer_input_fingerprint or writer_input_fingerprint == reviewer_input_fingerprint:
            self._set_run(project_id, run_id, "failed_gate")
            raise ProductionRunError("independent_review_not_independent", "writer and independent reviewer must be distinct semantic invocations")
        candidate_text = str((artifacts.get("surface_realization") or {}).get("text") or "")
        target_document = document_id or run.get("target_ref")
        if not isinstance(target_document, str) or not target_document.strip():
            self._set_run(project_id, run_id, "failed_gate")
            raise ProductionRunError("target_document_required", "document_id or document target_ref is required before candidate persistence")
        candidate = self._persist_candidate(project_id, run, bundle, target_document, candidate_text, artifacts["independent_semantic_gate"])
        self._set_run(project_id, run_id, "completed", result_fingerprint=candidate["candidate_fingerprint"])
        result = {
            "schema": PRODUCTION_EXECUTION_SCHEMA, "project_id": project_id, "run_id": run_id, "status": "completed", "task_mode": run["task_mode"],
            "context_bundle_fingerprint": bundle["bundle_fingerprint"], "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "stage_receipts": public_receipts, "candidate": candidate, "candidate_visible": True, "raw_draft_visible": False,
            "accepted": False, "settled": False, "authority": False,
        }
        self._event(project_id, run_id, "production_candidate_ready", {"candidate_id": candidate["candidate_id"], "candidate_fingerprint": candidate["candidate_fingerprint"], "context_bundle_fingerprint": bundle["bundle_fingerprint"]})
        return result
