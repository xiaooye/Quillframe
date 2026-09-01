#!/usr/bin/env python3
"""Deterministic conjunctive readiness gate for Quillframe candidates.

Semantic contracts own literary judgment.  This module validates exact contract
identity, candidate fingerprints, typed results, execution provenance and
independence receipts, then composes pass/fail/pending mechanically.  It does
not inspect HF codes, flatness scores, prose metrics, rule applicability or any
other literary content to decide whether a model judgment was correct.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))

from peer_bridge_receipt import validate_receipt as validate_peer_bridge_receipt  # noqa: E402
from independent_invocation_receipt import (  # noqa: E402
    SCHEMA as INDEPENDENT_INVOCATION_RECEIPT_SCHEMA,
    validate_receipt as validate_independent_invocation_receipt,
)
from peer_chat_relay import validate_peer_result  # noqa: E402
from registered_contract_binding import validate_registered_job  # noqa: E402
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402
from candidate_qualification import validate_qualification_receipt  # noqa: E402
from author_objective_gate import validate_objective_assessments  # noqa: E402

SCHEMA = "quillframe_production_readiness_v1"
CATEGORIES = {"surface", "reader_engagement", "continuity", "semantic_rules", "semantic_independent"}
STATUSES = {"pass", "fail", "pending"}
READER_GRIP = {"low", "medium", "high", "very_high"}
REGISTERED_RELEASE_CONTRACTS = {
    "reader_engagement": "reader.engagement_audit",
    "semantic_rules": "quality.semantic_rule_audit",
    "semantic_independent": "quality.production_review",
}


def _fp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _string_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise ValueError(f"{name} must be string list")
    return list(value)


def _validate_independence(binding: dict[str, Any], *, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """A distinct self-declared session is never independence proof."""
    peer_packet = binding.get("peer_packet")
    independence_receipt = binding.get("independence_receipt")
    if "bridge_receipt" in binding:
        raise ValueError("semantic_independent rejects the pre-1.0 bridge_receipt field")
    receipt = independence_receipt
    if not isinstance(peer_packet, dict):
        raise ValueError("semantic_independent requires validated peer_packet")
    if not isinstance(receipt, dict):
        raise ValueError("semantic_independent requires independence_receipt")

    relay_errors = validate_peer_result(peer_packet, result)
    if relay_errors:
        raise ValueError("semantic_independent peer relay invalid: " + "; ".join(relay_errors))
    packet_job = peer_packet.get("job")
    if not isinstance(packet_job, dict):
        raise ValueError("semantic_independent peer packet job required")
    for key in ("job_id", "subject_id", "kind", "input_fingerprint"):
        if packet_job.get(key) != job.get(key):
            raise ValueError(f"semantic_independent peer packet/job mismatch: {key}")

    if receipt.get("schema") == INDEPENDENT_INVOCATION_RECEIPT_SCHEMA:
        receipt_errors = validate_independent_invocation_receipt(receipt, peer_packet, result)
        if receipt_errors:
            raise ValueError("semantic_independent native receipt invalid: " + "; ".join(receipt_errors))
        return {
            "mode": "host_native_lifecycle",
            "project_id": receipt.get("project_id"),
            "provider": receipt.get("provider"),
            "transport": receipt.get("transport"),
            "assurance_class": receipt.get("assurance_class"),
            "parent_session_id": receipt.get("parent_session_id"),
            "reviewer_session_id": receipt.get("reviewer_session_id"),
            "host_agent_id": receipt.get("host_agent_id"),
            "host_invocation_id": receipt.get("host_invocation_id"),
            "result_fingerprint": receipt.get("result_fingerprint"),
            "receipt_fingerprint": receipt.get("receipt_fingerprint"),
        }
    receipt_errors = validate_peer_bridge_receipt(receipt, peer_packet, result)
    if receipt_errors:
        raise ValueError("semantic_independent project bridge receipt invalid: " + "; ".join(receipt_errors))
    return {
        "mode": "project_owned_peer_bridge",
        "project_id": receipt.get("project_id"),
        "project_repo": receipt.get("project_repo"),
        "framework_repo": receipt.get("framework_repo"),
        "framework_commit": receipt.get("framework_commit"),
        "issue_number": receipt.get("issue_number"),
        "provider": receipt.get("worker_provider"),
        "transport": "github_actions",
        "assurance_class": "project_owned_automation_receipt",
        "result_fingerprint": receipt.get("result_fingerprint"),
        "relay_nonce_fingerprint": receipt.get("relay_nonce_fingerprint"),
    }


def _registered_semantic_gate(raw: dict[str, Any], *, category: str, candidate_fingerprint: str) -> dict[str, Any]:
    binding = raw.get("semantic_binding")
    if not isinstance(binding, dict):
        raise ValueError(f"{category}.semantic_binding is required for pass/fail release evidence")
    job = binding.get("job")
    result = binding.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict):
        raise ValueError(f"{category}.semantic_binding requires job and result objects")

    contract_errors = validate_registered_job(job)
    if contract_errors:
        raise ValueError(f"{category}.registered contract binding invalid: " + "; ".join(contract_errors))
    result_errors = validate_result(job, result)
    if result_errors:
        raise ValueError(f"{category}.semantic result invalid: " + "; ".join(result_errors))
    if result.get("status") != "completed":
        raise ValueError(f"{category}.semantic result must be completed")

    input_obj = job.get("input")
    if not isinstance(input_obj, dict):
        raise ValueError(f"{category}.semantic job input required")
    contract_id = input_obj.get("model_contract_id")
    expected_contract = REGISTERED_RELEASE_CONTRACTS[category]
    if contract_id != expected_contract:
        raise ValueError(f"{category} requires {expected_contract}")
    payload = input_obj.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(f"{category}.semantic contract payload required")
    if payload.get("candidate_fingerprint") != candidate_fingerprint:
        raise ValueError(f"{category}.semantic contract candidate fingerprint mismatch")
    candidate_text = payload.get("candidate_text")
    if not isinstance(candidate_text, str) or not candidate_text.strip():
        raise ValueError(f"{category}.semantic contract candidate_text required")

    provenance = job.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("source") != "model_contract_pack":
        raise ValueError(f"{category} release evidence must come from model_contract_pack")
    if category == "semantic_independent" and provenance.get("independent_gate") is not True:
        raise ValueError("semantic_independent contract must declare independent_gate=true")

    independence: dict[str, Any] | None = None
    if category == "semantic_independent":
        independence = _validate_independence(binding, job=job, result=result)

    judgment = result.get("judgment")
    if not isinstance(judgment, dict):
        raise ValueError(f"{category}.semantic judgment required")
    semantic_result = judgment.get("result")
    objective_summary: dict[str, Any] | None = None
    if category == "semantic_independent" and "author_objectives" in payload:
        objective_summary = validate_objective_assessments(payload.get("author_objectives"), judgment)
    if category in {"semantic_rules", "semantic_independent"}:
        if semantic_result not in {"pass", "fail", "insufficient_evidence"}:
            raise ValueError(f"{category} judgment.result must be pass|fail|insufficient_evidence")
        derived_status = "pending" if semantic_result == "insufficient_evidence" else semantic_result
    else:
        if semantic_result not in {"pass", "fail"}:
            raise ValueError(f"{category}.semantic judgment.result must be pass|fail")
        derived_status = semantic_result

    declared = raw.get("status")
    if declared is not None and declared != derived_status:
        raise ValueError(f"{category}.status contradicts registered semantic result")

    worker = result.get("worker") if isinstance(result.get("worker"), dict) else {}
    gate_result = {
        "category": category,
        "status": derived_status,
        "candidate_fingerprint": candidate_fingerprint,
        "evidence_refs": _string_list(raw.get("evidence_refs", []), f"{category}.evidence_refs"),
        "semantic_contract": {
            "model_contract_id": contract_id,
            "registry_schema": provenance.get("registry_schema"),
            "registry_version": provenance.get("registry_version"),
            "pack_id": provenance.get("pack_id"),
            "release_role": category,
            "independent_gate": bool(provenance.get("independent_gate", False)),
            "job_fingerprint": job.get("input_fingerprint"),
            "worker_provider": worker.get("provider"),
            "model_or_reviewer": worker.get("model_or_reviewer"),
            "independence": independence,
        },
        "semantic_content_reinterpreted_by_runtime": False,
    }
    if objective_summary is not None:
        gate_result.update({
            "author_objective_status": objective_summary["status"],
            "author_objectives_fingerprint": objective_summary["objectives_fingerprint"],
            "objective_assessments": objective_summary["assessments"],
        })
    return gate_result


def _plain_gate(raw: dict[str, Any], *, category: str, candidate_fingerprint: str) -> dict[str, Any]:
    status = raw.get("status")
    if status not in STATUSES:
        raise ValueError(f"invalid gate status: {category}")
    if category in REGISTERED_RELEASE_CONTRACTS and status != "pending":
        raise ValueError(f"{category}.semantic_binding is required for pass/fail release evidence")
    return {
        "category": category,
        "status": status,
        "candidate_fingerprint": candidate_fingerprint,
        "evidence_refs": _string_list(raw.get("evidence_refs", []), f"{category}.evidence_refs"),
    }


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("readiness payload must be object")
    candidate = _fp(payload.get("candidate_fingerprint"), "candidate_fingerprint")
    policy = payload.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("policy object required")
    grip = policy.get("reader_grip")
    if grip not in READER_GRIP:
        raise ValueError("policy.reader_grip invalid")
    require_continuity = policy.get("require_continuity", True)
    require_semantic_rules = policy.get("require_semantic_rules", False)
    require_independent = policy.get("require_independent_semantic", False)
    if not all(isinstance(x, bool) for x in (require_continuity, require_semantic_rules, require_independent)):
        raise ValueError("policy requirement flags must be boolean")

    qualification = payload.get("pre_independent_qualification")
    qualification_summary = None
    if require_independent:
        errors = validate_qualification_receipt(qualification, candidate_fingerprint=candidate, require_qualified=True)
        if errors:
            raise ValueError("pre_independent_qualification invalid: " + "; ".join(errors))
        qualification_summary = {
            "receipt_fingerprint": qualification.get("receipt_fingerprint"),
            "qualification_status": qualification.get("qualification_status"),
            "candidate_fingerprint": qualification.get("candidate_fingerprint"),
            "independent": qualification.get("independent"),
        }

    required = ["surface", "reader_engagement"]
    if require_continuity:
        required.append("continuity")
    if require_semantic_rules:
        required.append("semantic_rules")
    if require_independent:
        required.append("semantic_independent")

    raw_gates = payload.get("gates")
    if not isinstance(raw_gates, list):
        raise ValueError("gates list required")
    gates: dict[str, dict[str, Any]] = {}
    for raw in raw_gates:
        if not isinstance(raw, dict):
            raise ValueError("gate must be object")
        category = raw.get("category")
        if category not in CATEGORIES:
            raise ValueError(f"unknown gate category: {category}")
        if category in gates:
            raise ValueError(f"duplicate gate category: {category}")
        gate_fp = _fp(raw.get("candidate_fingerprint"), f"{category}.candidate_fingerprint")
        if gate_fp != candidate:
            raise ValueError(f"candidate fingerprint mismatch: {category}")
        if category in REGISTERED_RELEASE_CONTRACTS and raw.get("status") != "pending":
            gate = _registered_semantic_gate(raw, category=category, candidate_fingerprint=candidate)
        else:
            gate = _plain_gate(raw, category=category, candidate_fingerprint=candidate)
        gates[category] = gate

    missing = [x for x in required if x not in gates]
    blocking = [x for x in required if x in gates and gates[x]["status"] == "fail"]
    pending = missing + [x for x in required if x in gates and gates[x]["status"] == "pending"]
    ready = not blocking and not pending and all(gates[x]["status"] == "pass" for x in required)
    return {
        "schema": SCHEMA,
        "candidate_fingerprint": candidate,
        "policy": {
            "reader_grip": grip,
            "require_continuity": require_continuity,
            "require_semantic_rules": require_semantic_rules,
            "require_independent_semantic": require_independent,
        },
        "required_gates": required,
        "gates": [gates[k] for k in sorted(gates)],
        "blocking_gates": blocking,
        "pending_gates": pending,
        "ready_for_user_visible_review": ready,
        "conjunctive_gate": True,
        "numeric_quality_aggregation": False,
        "registered_reader_engagement_required": True,
        "registered_semantic_rule_audit_required": require_semantic_rules,
        "registered_independent_release_contract_required": require_independent,
        "project_bridge_receipt_required_for_independence": False,
        "independence_receipt_required": require_independent,
        "native_lifecycle_receipt_supported": True,
        "pre_independent_qualification_required": require_independent,
        "pre_independent_qualification": qualification_summary,
        "independent_pass_can_override_qualification_failure": False,
        "semantic_content_reinterpreted_by_runtime": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def _binding(contract_id: str, fp: str, judgment: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"candidate_fingerprint": fp, "candidate_text": "A bounded candidate."}
    if contract_id == "quality.semantic_rule_audit":
        payload["rule_index"] = [{"id": "RULE-CI", "severity": "blocking", "authority": "framework", "statement": "A semantic rule fixture."}]
    job = make_contract_job(contract_id, "CH-SELF", payload, source_session_id="SES-MANAGER")
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "semantic-fixture"},
        "judgment": judgment,
        "proposals": [],
        "errors": [],
    }
    return {"job": job, "result": result}


def self_test() -> dict[str, Any]:
    fp = "sha256:" + "a" * 64
    reader = _binding("reader.engagement_audit", fp, {
        "confidence": 0.9, "result": "pass", "report": "The bounded fixture reads coherently.", "evidence_refs": ["candidate:1"]
    })
    rules = _binding("quality.semantic_rule_audit", fp, {
        "confidence": 0.9, "result": "pass", "report": "No supplied hard rule failed.",
        "findings": [{"rule_id": "RULE-CI", "status": "PASS", "report": "Supported.", "evidence_refs": ["candidate:1"]}]
    })
    pending_rules = _binding("quality.semantic_rule_audit", fp, {
        "confidence": 0.4, "result": "insufficient_evidence", "report": "Need prior Canon evidence.",
        "findings": [{"rule_id": "RULE-CI", "status": "INSUFFICIENT_EVIDENCE", "report": "Missing evidence.", "evidence_refs": []}],
        "evidence_requests": ["accepted:prior"]
    })
    base_gates = [
        {"category": "surface", "candidate_fingerprint": fp, "status": "pass", "evidence_refs": ["surface:1"]},
        {"category": "continuity", "candidate_fingerprint": fp, "status": "pass", "evidence_refs": ["continuity:1"]},
        {"category": "reader_engagement", "candidate_fingerprint": fp, "status": "pass", "semantic_binding": reader},
    ]
    normal = evaluate({"candidate_fingerprint": fp, "policy": {"reader_grip": "very_high", "require_continuity": True}, "gates": base_gates})
    with_rules = evaluate({
        "candidate_fingerprint": fp,
        "policy": {"reader_grip": "very_high", "require_continuity": True, "require_semantic_rules": True},
        "gates": [*base_gates, {"category": "semantic_rules", "candidate_fingerprint": fp, "status": "pass", "semantic_binding": rules}],
    })
    pending = evaluate({
        "candidate_fingerprint": fp,
        "policy": {"reader_grip": "very_high", "require_continuity": True, "require_semantic_rules": True},
        "gates": [*base_gates, {"category": "semantic_rules", "candidate_fingerprint": fp, "status": "pending", "semantic_binding": pending_rules}],
    })
    caller_override_blocked = False
    try:
        evaluate({
            "candidate_fingerprint": fp,
            "policy": {"reader_grip": "very_high", "require_continuity": True},
            "gates": [*base_gates[:-1], {"category": "reader_engagement", "candidate_fingerprint": fp, "status": "fail", "semantic_binding": reader}],
        })
    except ValueError:
        caller_override_blocked = True

    stale_blocked = False
    try:
        evaluate({
            "candidate_fingerprint": fp,
            "policy": {"reader_grip": "very_high", "require_continuity": False},
            "gates": [
                {"category": "surface", "candidate_fingerprint": fp, "status": "pass"},
                {"category": "reader_engagement", "candidate_fingerprint": "sha256:" + "b" * 64, "status": "pending"},
            ],
        })
    except ValueError:
        stale_blocked = True

    ok = all([
        normal["ready_for_user_visible_review"],
        with_rules["ready_for_user_visible_review"],
        not pending["ready_for_user_visible_review"] and "semantic_rules" in pending["pending_gates"],
        caller_override_blocked,
        stale_blocked,
        normal["semantic_content_reinterpreted_by_runtime"] is False,
    ])
    return {
        "production_readiness_contract": "PASS" if ok else "FAIL",
        "registered_contract_definition_bound": True,
        "caller_status_cannot_override_semantic_result": caller_override_blocked,
        "stale_candidate_fingerprint_blocked": stale_blocked,
        "semantic_rule_insufficient_evidence_stays_pending": not pending["ready_for_user_visible_review"],
        "semantic_result_literary_codes_reinterpreted": False,
        "bare_distinct_session_not_independence": True,
        "registered_reader_engagement_required": True,
        "registered_independent_release_contract_required": True,
        "project_bridge_receipt_required_for_independence": False,
        "independence_receipt_required": True,
        "native_lifecycle_receipt_supported": True,
        "pre_independent_qualification_required": True,
        "independent_pass_can_override_qualification_failure": False,
        "numeric_quality_aggregation": False,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe production readiness gate")
    sub = p.add_subparsers(dest="command", required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--input", required=True)
    e.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.command == "self-test":
        out = self_test()
    else:
        out = evaluate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.command == "evaluate" and args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if out.get("production_readiness_contract", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
