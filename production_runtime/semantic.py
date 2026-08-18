from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from agent_runtime import AgentBudget, AgentJob
from harness.context_runtime import canonical_json, fingerprint

from .contracts import ProductionRunError, assert_secret_free, parse_json_object
from .sources import AgentRuntimeLike

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_ROOT = ROOT / "harness" / "semantic_workers"
QUALITY_ROOT = ROOT / "quality"
for runtime_root in (SEMANTIC_ROOT, QUALITY_ROOT):
    if str(runtime_root) not in sys.path:
        sys.path.insert(0, str(runtime_root))

from peer_bridge_receipt import validate_receipt as validate_peer_bridge_receipt  # noqa: E402
from peer_chat_relay import build as build_peer_packet, validate_peer_result  # noqa: E402
from registered_contract_binding import validate_registered_job  # noqa: E402
from semantic_worker_router import make_contract_job, validate_result, worker_job_view  # noqa: E402

from quality.candidate_qualification import evaluate as evaluate_qualification  # noqa: E402
from quality.candidate_qualification import validate_qualification_receipt  # noqa: E402
from quality.production_readiness import evaluate as evaluate_production_readiness  # noqa: E402
from quality.production_release import aggregate as aggregate_production_release  # noqa: E402


class RegisteredSemanticExecutor:
    """Run non-independent registered semantic contracts through Model Service.

    This adapter never executes `quality.production_review`; that contract is
    deliberately reserved for the external independent handoff path below.
    """

    def __init__(self, agent_runtime: AgentRuntimeLike) -> None:
        self.agent_runtime = agent_runtime

    def execute(
        self,
        *,
        run: dict[str, Any],
        service_id: str,
        contract_id: str,
        subject_id: str,
        payload: dict[str, Any],
        model_preference: str | None,
        runtime_role: str,
        max_output_tokens: int = 4200,
    ) -> dict[str, Any]:
        if contract_id == "quality.production_review":
            raise ProductionRunError(
                "independent_review_external_required",
                "quality.production_review must be dispatched through the independent peer handoff, not the manager Model Service",
            )
        assert_secret_free(payload, label=f"registered semantic payload {contract_id}")
        try:
            semantic_job = make_contract_job(
                contract_id,
                subject_id,
                payload,
                source_session_id=str(run.get("session_id") or f"session:{run['run_id']}"),
                handoff_id=f"{run['run_id']}:{contract_id}",
            )
        except ValueError as exc:
            raise ProductionRunError("semantic_contract_invalid", str(exc)) from exc
        binding_errors = validate_registered_job(semantic_job)
        if binding_errors:
            raise ProductionRunError("semantic_contract_invalid", "; ".join(binding_errors))

        visible_job = worker_job_view(semantic_job)
        instruction = (
            "Execute exactly the registered Quillframe semantic contract supplied in context. "
            "Judge only its bounded payload and rubric. Return ONLY the judgment JSON object matching output_contract. "
            "Do not expose chain-of-thought, private reasoning, credentials, Canon writes, Framework writes, or user-taste writes."
        )
        agent_job = AgentJob(
            job_id=f"agent_{semantic_job['job_id']}",
            session_id=str(run.get("session_id") or f"session:{run['run_id']}"),
            run_id=str(run["run_id"]),
            task_mode=str(run["task_mode"]),
            runtime_role=runtime_role,
            service_id=service_id,
            instruction=instruction,
            context=[{"registered_semantic_job": visible_job}],
            tool_grants=set(),
            model_preference=model_preference,
            required_model_capabilities={"text"},
            authority={},
            budgets=AgentBudget(
                max_steps=3,
                max_model_requests=3,
                max_tool_calls=1,
                max_parallel_tool_calls=1,
                max_output_tokens_per_request=max_output_tokens,
                max_total_tokens=32_000,
                max_elapsed_ms=180_000,
            ),
            idempotency_key=f"{run['run_id']}:registered:{contract_id}:{semantic_job['input_fingerprint']}",
        )
        result = self.agent_runtime.run(agent_job)
        if result.status != "completed":
            raise ProductionRunError(
                "semantic_pending",
                f"registered semantic contract {contract_id} did not complete",
                detail={"agent_status": result.status, "errors": result.errors},
            )
        judgment = parse_json_object(result.final_text, label=contract_id)
        semantic_result = {
            "job_id": semantic_job["job_id"],
            "subject_id": semantic_job["subject_id"],
            "kind": semantic_job["kind"],
            "input_fingerprint": semantic_job["input_fingerprint"],
            "status": "completed",
            "worker": {
                "provider": "quillframe_model_service",
                "model_or_reviewer": result.model_id,
                "model_service_id": result.model_service_id,
                "protocol": result.protocol,
                "agent_job_id": agent_job.job_id,
                "agent_input_fingerprint": agent_job.input_fingerprint,
            },
            "judgment": judgment,
            "proposals": [],
            "errors": [],
            "execution": {
                "source_session_id": semantic_job.get("execution", {}).get("source_session_id"),
                "handoff_id": semantic_job.get("execution", {}).get("handoff_id"),
            },
        }
        result_errors = validate_result(semantic_job, semantic_result)
        if result_errors:
            raise ProductionRunError("semantic_output_invalid", "; ".join(result_errors))
        return {
            "contract_id": contract_id,
            "job": semantic_job,
            "result": semantic_result,
            "binding_fingerprint": fingerprint({"job": semantic_job, "result": semantic_result}),
            "authority": False,
        }


def semantic_status(binding: dict[str, Any]) -> str:
    result = binding.get("result") or {}
    judgment = result.get("judgment") if isinstance(result, dict) else None
    semantic_result = judgment.get("result") if isinstance(judgment, dict) else None
    if semantic_result == "insufficient_evidence":
        return "pending"
    if semantic_result in {"pass", "fail"}:
        return semantic_result
    raise ProductionRunError("semantic_output_invalid", "registered semantic judgment has no supported result")


def build_pre_independent_qualification(
    *,
    subject_id: str,
    candidate_fingerprint: str,
    self_audit_binding: dict[str, Any],
    reader_binding: dict[str, Any],
    continuity_receipt_fingerprint: str,
    repair_cycle: int = 0,
    repair_preservation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    self_status = semantic_status(self_audit_binding)
    reader_status = semantic_status(reader_binding)
    payload: dict[str, Any] = {
        "subject_id": subject_id,
        "candidate_fingerprint": candidate_fingerprint,
        "repair_cycle": repair_cycle,
        "self_audit": {"status": self_status, "semantic_binding": {"job": self_audit_binding["job"], "result": self_audit_binding["result"]}},
        "reader_engagement": {"status": reader_status, "semantic_binding": {"job": reader_binding["job"], "result": reader_binding["result"]}},
        "continuity": {
            "status": "pass",
            "candidate_fingerprint": candidate_fingerprint,
            "receipt_fingerprint": continuity_receipt_fingerprint,
            "evidence_refs": [f"continuity:{continuity_receipt_fingerprint}"],
        },
    }
    if repair_cycle > 0:
        payload["repair_preservation"] = repair_preservation or {"status": "pending"}
    try:
        receipt = evaluate_qualification(payload)
    except ValueError as exc:
        raise ProductionRunError("qualification_invalid", str(exc)) from exc
    errors = validate_qualification_receipt(
        receipt,
        candidate_fingerprint=candidate_fingerprint,
        subject_id=subject_id,
        require_qualified=False,
    )
    if errors:
        raise ProductionRunError("qualification_invalid", "; ".join(errors))
    return receipt


def prepare_independent_review(
    *,
    run: dict[str, Any],
    subject_id: str,
    candidate_fingerprint: str,
    candidate_text: str,
    reader_visible_context: list[dict[str, Any]],
    reader_grip: str,
    qualification_receipt: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_qualification_receipt(
        qualification_receipt,
        candidate_fingerprint=candidate_fingerprint,
        subject_id=subject_id,
        require_qualified=True,
    )
    if errors:
        raise ProductionRunError("not_qualified_for_independent", "; ".join(errors))
    required_provenance = {"project_id", "project_repo", "framework_repo", "framework_commit"}
    if not isinstance(provenance, dict) or not required_provenance.issubset(provenance):
        raise ProductionRunError(
            "independent_provenance_required",
            "independent review dispatch requires project_id/project_repo/framework_repo/framework_commit provenance",
        )
    payload = {
        "candidate_fingerprint": candidate_fingerprint,
        "candidate_text": candidate_text,
        "reader_visible_context": reader_visible_context,
        "reader_grip": reader_grip,
    }
    try:
        job = make_contract_job(
            "quality.production_review",
            subject_id,
            payload,
            source_session_id=str(run.get("session_id") or f"session:{run['run_id']}"),
            handoff_id=f"{run['run_id']}:quality.production_review",
            qualification_receipt=qualification_receipt,
        )
    except ValueError as exc:
        raise ProductionRunError("independent_job_invalid", str(exc)) from exc
    job["provenance"].update({key: provenance[key] for key in sorted(required_provenance)})
    try:
        packet = build_peer_packet(job)
    except ValueError as exc:
        raise ProductionRunError("independent_packet_invalid", str(exc)) from exc
    return {
        "schema": "quillframe_independent_review_handoff_v1",
        "subject_id": subject_id,
        "candidate_fingerprint": candidate_fingerprint,
        "qualification_receipt": qualification_receipt,
        "independent_job": job,
        "peer_packet": packet,
        "reader_grip": reader_grip,
        "reader_visible_context": reader_visible_context,
        "authority": False,
    }


def validate_independent_submission(
    *,
    handoff: dict[str, Any],
    peer_packet: dict[str, Any],
    result: dict[str, Any],
    bridge_receipt: dict[str, Any],
) -> dict[str, Any]:
    stored_packet = handoff.get("peer_packet")
    if not isinstance(stored_packet, dict) or canonical_json(stored_packet) != canonical_json(peer_packet):
        raise ProductionRunError("independent_packet_mismatch", "submitted peer packet does not match the frozen pending handoff")
    peer_errors = validate_peer_result(peer_packet, result)
    if peer_errors:
        raise ProductionRunError("independent_result_invalid", "; ".join(peer_errors))
    receipt_errors = validate_peer_bridge_receipt(bridge_receipt, peer_packet, result)
    if receipt_errors:
        raise ProductionRunError("independent_bridge_receipt_invalid", "; ".join(receipt_errors))
    stored_job = handoff.get("independent_job")
    packet_job = peer_packet.get("job")
    if not isinstance(stored_job, dict) or not isinstance(packet_job, dict):
        raise ProductionRunError("independent_job_invalid", "frozen independent job/packet job required")
    for key in ("job_id", "subject_id", "kind", "input_fingerprint"):
        if stored_job.get(key) != packet_job.get(key):
            raise ProductionRunError("independent_job_mismatch", f"peer packet changed independent job binding: {key}")
    return {
        "job": stored_job,
        "result": result,
        "peer_packet": peer_packet,
        "bridge_receipt": bridge_receipt,
    }


def final_readiness(
    *,
    candidate_fingerprint: str,
    qualification_receipt: dict[str, Any],
    reader_binding: dict[str, Any],
    continuity_receipt_fingerprint: str,
    independent_binding: dict[str, Any],
    reader_grip: str,
) -> dict[str, Any]:
    surface_status = qualification_receipt.get("surface_audit_status")
    if surface_status not in {"pass", "fail"}:
        surface_status = "pending"
    gates = [
        {"category": "surface", "candidate_fingerprint": candidate_fingerprint, "status": surface_status, "evidence_refs": [f"qualification:{qualification_receipt.get('receipt_fingerprint')}"]},
        {"category": "reader_engagement", "candidate_fingerprint": candidate_fingerprint, "status": semantic_status(reader_binding), "semantic_binding": {"job": reader_binding["job"], "result": reader_binding["result"]}},
        {"category": "continuity", "candidate_fingerprint": candidate_fingerprint, "status": "pass", "evidence_refs": [f"continuity:{continuity_receipt_fingerprint}"]},
        {"category": "semantic_independent", "candidate_fingerprint": candidate_fingerprint, "status": semantic_status({"result": independent_binding["result"]}), "semantic_binding": independent_binding},
    ]
    try:
        return evaluate_production_readiness({
            "candidate_fingerprint": candidate_fingerprint,
            "policy": {
                "reader_grip": reader_grip,
                "require_continuity": True,
                "require_semantic_rules": False,
                "require_independent_semantic": True,
            },
            "pre_independent_qualification": qualification_receipt,
            "gates": gates,
        })
    except ValueError as exc:
        raise ProductionRunError("production_readiness_invalid", str(exc)) from exc


def final_release(
    *,
    production_readiness: dict[str, Any],
    qualification_receipt: dict[str, Any],
    candidate_fingerprint: str,
    context_bundle_fingerprint: str,
    freeze_fingerprint: str,
    user_visible_gate_receipt_fingerprint: str,
) -> dict[str, Any]:
    """Aggregate semantic readiness with structural execution receipts.

    This is the only release object that can authorize manuscript visibility.
    A semantic PASS or user-visible stage receipt alone is insufficient.
    """
    structural_receipts = [
        {
            "kind": "context_assembly",
            "status": "pass",
            "candidate_fingerprint": candidate_fingerprint,
            "receipt_fingerprint": context_bundle_fingerprint,
            "evidence_refs": [f"context_bundle:{context_bundle_fingerprint}", f"freeze:{freeze_fingerprint}"],
        },
        {
            "kind": "user_visible_gate",
            "status": "pass",
            "candidate_fingerprint": candidate_fingerprint,
            "receipt_fingerprint": user_visible_gate_receipt_fingerprint,
            "evidence_refs": [f"user_visible_gate:{user_visible_gate_receipt_fingerprint}"],
        },
    ]
    try:
        return aggregate_production_release({
            "production_readiness": production_readiness,
            "pre_independent_qualification": qualification_receipt,
            "structural_policy": {"required_receipts": ["context_assembly", "user_visible_gate"]},
            "structural_receipts": structural_receipts,
        })
    except ValueError as exc:
        raise ProductionRunError("production_release_invalid", str(exc)) from exc
