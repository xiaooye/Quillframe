from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from harness.context_runtime import canonical_json, fingerprint, stage_context
from persistence.quillframe_sqlite import ConflictError, fingerprint_text, now_iso

from .context import ProductionContextRuntime
from .contracts import (
    MECHANISM_CONTEXT_STAGE,
    PRODUCTION_BUNDLE_SCHEMA,
    PRODUCTION_EXECUTION_SCHEMA,
    PRODUCTION_MECHANISMS,
    ProductionRunError,
    assert_secret_free,
    parse_json_object,
    public_stage_result,
)
from .semantic import (
    RegisteredSemanticExecutor,
    build_pre_independent_qualification,
    final_readiness,
    final_release,
    prepare_independent_review,
    semantic_status,
    validate_independent_submission,
)
from .sources import _json

PRE_INDEPENDENT_MECHANISMS = tuple(
    mechanism for mechanism in PRODUCTION_MECHANISMS
    if mechanism not in {"independent_semantic_gate", "user_visible_gate"}
)
READER_GRIP_VALUES = {"low", "medium", "high", "very_high"}


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
            "mechanism": mechanism,
            "context_stage_id": context_stage_id,
            "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
            "context_bundle_fingerprint": bundle["bundle_fingerprint"],
            "loaded_object_ids": loaded_ids,
            "items": [deepcopy(payloads[object_id]) for object_id in loaded_ids],
            "selector": projection.get("selector"),
            "db_fetch_performed": False,
            "authority": False,
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
        if mechanism in {"continuity", "story_canon_preflight"}:
            return common + f"Execute Quillframe mechanism {mechanism}. JSON: {{\"status\":\"pass\"|\"fail\",\"summary\":string,\"findings\":[string]}}. A fail is a real gate result; do not soften it. Request: " + user_instruction
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
        frozen_stage = self.materialize_stage_context(bundle, mechanism)
        upstream: dict[str, Any] = {}
        if mechanism == "surface_realization":
            upstream["raw_draft"] = artifacts.get("event_first_raw_draft")
        elif mechanism == "continuity":
            upstream["candidate"] = artifacts.get("surface_realization")
        context = [{"frozen_stage_context": frozen_stage, "upstream_artifacts": upstream}]
        job, result = self._agent_job(
            run=run,
            service_id=service_id,
            runtime_role=mechanism,
            instruction=self._stage_instruction(mechanism, user_instruction),
            context=context,
            model_preference=model_preference,
            suffix=mechanism,
            max_output_tokens=7000 if mechanism in {"event_first_raw_draft", "surface_realization"} else 3000,
        )
        if result.status != "completed":
            raise ProductionRunError(
                "semantic_pending" if result.status in {"model_failed", "cancelled"} else "failed_gate",
                f"production mechanism {mechanism} did not complete",
                detail={"agent_status": result.status, "errors": result.errors},
            )
        judgment = parse_json_object(result.final_text, label=mechanism)
        status = str(judgment.get("status") or "").strip().lower()
        if status not in {"pass", "fail"}:
            raise ProductionRunError("semantic_output_invalid", f"{mechanism}.status must be pass|fail")
        if mechanism in {"event_first_raw_draft", "surface_realization"}:
            text = judgment.get("text")
            if status == "pass" and (not isinstance(text, str) or not text.strip()):
                raise ProductionRunError("semantic_output_invalid", f"{mechanism} pass result requires non-empty text")
            if isinstance(text, str):
                judgment["artifact_fingerprint"] = fingerprint_text(text)
        elif "artifact" in judgment:
            judgment["artifact_fingerprint"] = fingerprint(judgment["artifact"])
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
            conn.execute(
                "INSERT INTO checkpoints(checkpoint_id,run_id,checkpoint_kind,state_json,artifact_fingerprint,created_at) VALUES(?,?,?,?,?,?)",
                ("ckpt_" + uuid.uuid4().hex, run_id, kind, canonical_json(state), artifact_fingerprint, now_iso()),
            )
            conn.commit()

    def _latest_checkpoint(self, project_id: str, run_id: str, kind: str) -> dict[str, Any] | None:
        with self.store.open_project(project_id) as conn:
            row = conn.execute(
                "SELECT state_json FROM checkpoints WHERE run_id=? AND checkpoint_kind=? ORDER BY created_at DESC,rowid DESC LIMIT 1",
                (run_id, kind),
            ).fetchone()
        return _json(row["state_json"], {}) if row else None

    def _persist_release_receipt(self, project_id: str, run_id: str, release: dict[str, Any]) -> None:
        assert_secret_free(release, label="production release")
        key = f"{run_id}:production_release"
        with self.store.open_project(project_id) as conn:
            existing = conn.execute(
                "SELECT payload_json FROM receipts WHERE receipt_kind='production_release' AND idempotency_key=?",
                (key,),
            ).fetchone()
            if existing:
                prior = _json(existing["payload_json"], {})
                if prior.get("release_fingerprint") != release.get("release_fingerprint"):
                    raise ProductionRunError("production_release_replay_conflict", "production release changed for immutable run")
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
    ) -> dict[str, Any]:
        with self.store.open_project(project_id) as conn:
            document = conn.execute("SELECT document_id FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if not document:
                raise ProductionRunError("target_document_required", f"production candidate target document does not exist: {document_id}")
            latest = self.store.latest_revision(conn, document_id)
            parent_id = latest["revision_id"] if latest else None
        try:
            revision = self.store.save_revision(
                project_id,
                document_id,
                text,
                expected_parent_revision_id=parent_id,
                source="production_runtime",
                authority_class="review",
                provenance={
                    "run_id": run["run_id"],
                    "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                    "freeze_fingerprint": bundle["freeze"]["freeze_fingerprint"],
                    "production_readiness_schema": readiness.get("schema"),
                    "production_release_fingerprint": release.get("release_fingerprint"),
                    "authority": False,
                },
            )
        except ConflictError as exc:
            raise ProductionRunError("revision_conflict", str(exc)) from exc
        if revision["content_fingerprint"] != candidate_fingerprint:
            raise ProductionRunError("candidate_fingerprint_mismatch", "diagnostic candidate changed before Review Draft persistence")

        candidate_id = "cand_" + uuid.uuid4().hex
        review_id = "review_" + uuid.uuid4().hex
        candidate_kind = "draft" if run["task_mode"] == "DRAFT" else "repair"
        stamp = now_iso()
        bridge_receipt = independent_binding["bridge_receipt"]
        independent_result = independent_binding["result"]
        review_public = {
            "model_contract_id": "quality.production_review",
            "judgment": independent_result.get("judgment"),
            "worker": independent_result.get("worker"),
            "job_id": independent_result.get("job_id"),
            "input_fingerprint": independent_result.get("input_fingerprint"),
            "bridge_receipt": bridge_receipt,
            "production_readiness": readiness,
            "private_reasoning_exposed": False,
            "authority": False,
        }
        assert_secret_free(review_public, label="independent review evidence")
        with self.store.open_project(project_id) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO candidates(candidate_id,document_id,revision_id,run_id,task_mode,candidate_kind,status,content_fingerprint,user_visible_gate,created_at) VALUES(?,?,?,?,?,?,'review_draft',?,'PASS',?)",
                (candidate_id, document_id, revision["revision_id"], run["run_id"], run["task_mode"], candidate_kind, candidate_fingerprint, stamp),
            )
            conn.execute(
                "INSERT INTO review_evidence(review_id,candidate_id,evidence_kind,result_json,candidate_fingerprint,reviewer_fingerprint,independent,stale,created_at) VALUES(?,?,?,?,?,?,1,0,?)",
                (
                    review_id,
                    candidate_id,
                    "quality.production_review",
                    canonical_json(review_public),
                    candidate_fingerprint,
                    bridge_receipt.get("result_fingerprint"),
                    stamp,
                ),
            )
            conn.commit()
        return {
            "candidate_id": candidate_id,
            "revision_id": revision["revision_id"],
            "candidate_fingerprint": candidate_fingerprint,
            "status": "review_draft",
            "user_visible_gate": "PASS",
            "production_release_fingerprint": release.get("release_fingerprint"),
            "authority": False,
        }

    def _completed_projection(self, project_id: str, run: dict[str, Any], bundle: dict[str, Any] | None) -> dict[str, Any] | None:
        if run.get("status") != "completed":
            return None
        with self.store.open_project(project_id) as conn:
            candidate = conn.execute(
                "SELECT candidate_id,revision_id,content_fingerprint,status,user_visible_gate FROM candidates WHERE run_id=? ORDER BY created_at DESC LIMIT 1",
                (run["run_id"],),
            ).fetchone()
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
        if not candidate:
            raise ProductionRunError("completed_run_missing_candidate", "completed production run has no persisted candidate")
        release = _json(release_row["payload_json"], {}) if release_row else {}
        if (
            release.get("schema") != "quillframe_production_release_v1"
            or release.get("candidate_fingerprint") != candidate["content_fingerprint"]
            or release.get("ready_for_user_visible_review") is not True
        ):
            raise ProductionRunError("production_release_missing", "completed production candidate lacks a valid exact-fingerprint production release")
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
        handoff = self._latest_checkpoint(project_id, run["run_id"], "production_independent_handoff")
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
                    "peer_packet": handoff["peer_packet"],
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
        handoff = prepare_independent_review(
            run=run,
            subject_id=qualified["subject_id"],
            candidate_fingerprint=qualified["candidate_fingerprint"],
            candidate_text=qualified["candidate_text"],
            reader_visible_context=qualified["reader_visible_context"],
            reader_grip=qualified["reader_grip"],
            qualification_receipt=qualified["qualification_receipt"],
            provenance=independent_provenance,
        )
        handoff["context_bundle_fingerprint"] = bundle["bundle_fingerprint"]
        handoff["freeze_fingerprint"] = bundle["freeze"]["freeze_fingerprint"]
        handoff["document_id"] = qualified["document_id"]
        handoff["reader_binding"] = qualified["reader_binding"]
        handoff["continuity_receipt_fingerprint"] = qualified["continuity_receipt_fingerprint"]
        self._checkpoint(project_id, run["run_id"], "production_independent_handoff", handoff, handoff["candidate_fingerprint"])
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
                self._set_run(project_id, run_id, "semantic_pending" if exc.code == "semantic_pending" else "failed_gate")
                self._event(project_id, run_id, "production_context_failed", {"code": exc.code, "message": str(exc), "detail": exc.detail})
                raise

        self._set_run(project_id, run_id, "semantic_running")
        artifacts: dict[str, Any] = {}
        public_receipts: list[dict[str, Any]] = []
        reader_binding: dict[str, Any] | None = None
        registered = RegisteredSemanticExecutor(self.agent_runtime)

        for mechanism in PRE_INDEPENDENT_MECHANISMS:
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
                            "reader_grip": reader_grip,
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
                status = "semantic_pending" if exc.code in {"semantic_pending", "semantic_output_invalid"} else "failed_gate"
                self._set_run(project_id, run_id, status)
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
            if internal.get("status") == "fail":
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
                },
                model_preference=model_preference,
                runtime_role="registered_candidate_self_audit",
                max_output_tokens=5200,
            )
            repair_cycle = 1 if run["task_mode"] == "REVISE" else 0
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
            self._set_run(project_id, run_id, "semantic_pending" if exc.code in {"semantic_pending", "semantic_output_invalid"} else "failed_gate")
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
            "reader_visible_context": reader_visible_context,
            "reader_binding": reader_binding,
            "self_audit_binding": self_audit,
            "continuity_receipt_fingerprint": continuity_receipt["stage_result_fingerprint"],
            "qualification_receipt": qualification,
            "authority": False,
        }
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
            return {
                "schema": PRODUCTION_EXECUTION_SCHEMA,
                "project_id": project_id,
                "run_id": run_id,
                "status": "failed_gate",
                "failed_mechanism": "pre_independent_qualification",
                "qualification": {
                    "status": qualification["qualification_status"],
                    "failed_gates": qualification["failed_gates"],
                    "blocking_findings": qualification["blocking_findings"],
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

    def submit_independent(
        self,
        project_id: str,
        run_id: str,
        *,
        peer_packet: dict[str, Any],
        result: dict[str, Any],
        bridge_receipt: dict[str, Any],
    ) -> dict[str, Any]:
        run = self._run_row(project_id, run_id)
        if run.get("status") == "completed":
            bundle = self._latest_bundle(project_id, run_id)
            replay = self._completed_projection(project_id, run, bundle)
            if replay is None:
                raise ProductionRunError("completed_run_missing_candidate", "completed production run has no candidate")
            return replay
        if run.get("status") != "awaiting_external":
            raise ProductionRunError("independent_submission_not_expected", f"run status is {run.get('status')}, not awaiting_external")
        bundle = self._latest_bundle(project_id, run_id)
        handoff = self._latest_checkpoint(project_id, run_id, "production_independent_handoff")
        if not bundle or not handoff:
            raise ProductionRunError("independent_handoff_missing", "frozen Context bundle and independent handoff are required")
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

        independent_binding = validate_independent_submission(
            handoff=handoff,
            peer_packet=peer_packet,
            result=result,
            bridge_receipt=bridge_receipt,
        )
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
            protocol="project_owned_peer_bridge",
            judgment={
                "status": independent_judgment.get("result"),
                "summary": independent_judgment.get("report"),
                "findings": independent_judgment.get("evidence_refs", []),
                "artifact_fingerprint": handoff["candidate_fingerprint"],
            },
        )
        independent_receipt["model_contract_id"] = "quality.production_review"
        independent_receipt["bridge_receipt_result_fingerprint"] = bridge_receipt.get("result_fingerprint")
        independent_receipt["stage_result_fingerprint"] = fingerprint({key: value for key, value in independent_receipt.items() if key != "stage_result_fingerprint"})
        self._persist_stage_receipt(project_id, run_id, independent_receipt)

        if not readiness.get("ready_for_user_visible_review"):
            self._set_run(project_id, run_id, "failed_gate" if readiness.get("blocking_gates") else "semantic_pending")
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
        self._persist_stage_receipt(project_id, run_id, visible_receipt)

        release = final_release(
            production_readiness=readiness,
            qualification_receipt=handoff["qualification_receipt"],
            candidate_fingerprint=handoff["candidate_fingerprint"],
            context_bundle_fingerprint=bundle["bundle_fingerprint"],
            freeze_fingerprint=bundle["freeze"]["freeze_fingerprint"],
            user_visible_gate_receipt_fingerprint=visible_receipt["stage_result_fingerprint"],
        )
        if release.get("ready_for_user_visible_review") is not True:
            self._set_run(project_id, run_id, "failed_gate" if release.get("blocking_structural_receipts") else "semantic_pending")
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
        self._persist_release_receipt(project_id, run_id, release)

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
        )
        self._set_run(project_id, run_id, "completed", result_fingerprint=candidate["candidate_fingerprint"])
        self._event(
            project_id,
            run_id,
            "production_candidate_ready",
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_fingerprint": candidate["candidate_fingerprint"],
                "context_bundle_fingerprint": bundle["bundle_fingerprint"],
                "independent_result_fingerprint": bridge_receipt.get("result_fingerprint"),
            },
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
