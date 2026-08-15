#!/usr/bin/env python3
"""Deterministic conjunctive user-visible prose readiness gate.

Semantic systems own literary judgments. This module binds their receipts to one
candidate fingerprint and applies fail-closed release policy. It never averages
literary scores and never grants Canon authority.

Production Reader Engagement and mandatory independent review are release roles,
not free-form status fields. A pass/fail claim for either role must be derived
from a validated registered model contract. Mandatory independent review must
also carry a Project-owned peer-validation receipt bound to the exact result;
self-declared session ids are not independence proof.
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

from peer_bridge_receipt import (  # noqa: E402
    build_receipt as build_peer_bridge_receipt,
    validate_receipt as validate_peer_bridge_receipt,
)
from peer_chat_relay import build as build_peer_packet, validate_peer_result  # noqa: E402
from registered_contract_binding import (  # noqa: E402
    self_test as registered_binding_self_test,
    validate_registered_job,
)
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402
from quality_taxonomy import id_for_name, self_test as taxonomy_self_test  # noqa: E402
from repair_policy import self_test as repair_policy_self_test  # noqa: E402

SCHEMA = "novelforge_production_readiness_v1"
CATEGORIES = {"surface", "reader_engagement", "continuity", "semantic_independent"}
STATUSES = {"pass", "fail", "pending"}
READER_GRIP = {"low", "medium", "high", "very_high"}
REGISTERED_RELEASE_CATEGORIES = {"reader_engagement", "semantic_independent"}
SAFE_BUT_FLAT_ID = id_for_name("SAFE-BUT-FLAT")
CHECKLIST_CAUSALITY_ID = id_for_name("CHECKLIST-CAUSALITY")


def _fp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
        raise ValueError(f"{name} must be string list")
    return list(value)


def _validate_independence(binding: dict[str, Any], *, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Require Project-owned peer bridge proof; self-declared sessions never qualify."""
    peer_packet = binding.get("peer_packet")
    bridge_receipt = binding.get("bridge_receipt")
    if not isinstance(peer_packet, dict):
        raise ValueError("semantic_independent requires validated peer_packet")
    if not isinstance(bridge_receipt, dict):
        raise ValueError("semantic_independent requires project bridge_receipt")

    relay_errors = validate_peer_result(peer_packet, result)
    if relay_errors:
        raise ValueError("semantic_independent peer relay invalid: " + "; ".join(relay_errors))
    packet_job = peer_packet.get("job")
    if not isinstance(packet_job, dict):
        raise ValueError("semantic_independent peer packet job required")
    for key in ("job_id", "subject_id", "kind", "input_fingerprint"):
        if packet_job.get(key) != job.get(key):
            raise ValueError(f"semantic_independent peer packet/job mismatch: {key}")

    receipt_errors = validate_peer_bridge_receipt(bridge_receipt, peer_packet, result)
    if receipt_errors:
        raise ValueError("semantic_independent project bridge receipt invalid: " + "; ".join(receipt_errors))
    return {
        "mode": "project_owned_peer_bridge",
        "project_id": bridge_receipt.get("project_id"),
        "project_repo": bridge_receipt.get("project_repo"),
        "framework_repo": bridge_receipt.get("framework_repo"),
        "framework_commit": bridge_receipt.get("framework_commit"),
        "issue_number": bridge_receipt.get("issue_number"),
        "result_fingerprint": bridge_receipt.get("result_fingerprint"),
        "relay_nonce_fingerprint": bridge_receipt.get("relay_nonce_fingerprint"),
    }


def _registered_semantic_gate(
    raw: dict[str, Any],
    *,
    category: str,
    candidate_fingerprint: str,
    reader_grip: str,
) -> dict[str, Any]:
    """Validate one registered release-role job/result and derive its verdict."""
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
    payload = input_obj.get("payload")
    if not isinstance(contract_id, str) or not contract_id:
        raise ValueError(f"{category} requires registered model_contract_id")
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
    if category == "reader_engagement" and contract_id != "reader.engagement_audit":
        raise ValueError("reader_engagement requires reader.engagement_audit")
    if category == "semantic_independent" and contract_id != "quality.production_review":
        raise ValueError("semantic_independent requires quality.production_review")
    if category == "semantic_independent" and provenance.get("independent_gate") is not True:
        raise ValueError("semantic_independent contract must declare independent_gate=true")

    independence: dict[str, Any] | None = None
    if category == "semantic_independent":
        independence = _validate_independence(binding, job=job, result=result)

    judgment = result.get("judgment")
    if not isinstance(judgment, dict):
        raise ValueError(f"{category}.semantic judgment required")
    derived_status = judgment.get("result")
    if derived_status not in {"pass", "fail"}:
        raise ValueError(f"{category}.semantic judgment.result must be pass|fail")
    declared = raw.get("status")
    if declared is not None and declared != derived_status:
        raise ValueError(f"{category}.status contradicts registered semantic result")

    codes = _string_list(judgment.get("codes", []), f"{category}.semantic judgment.codes")
    flatness_risk = judgment.get("flatness_risk")
    if derived_status == "pass":
        if SAFE_BUT_FLAT_ID in codes:
            raise ValueError(f"{category}: {SAFE_BUT_FLAT_ID} SAFE-BUT-FLAT cannot coexist with pass")
        if category == "semantic_independent" and CHECKLIST_CAUSALITY_ID in codes:
            raise ValueError(f"{category}: {CHECKLIST_CAUSALITY_ID} CHECKLIST CAUSALITY cannot coexist with pass")
        if flatness_risk in {"high", "blocking"}:
            raise ValueError(f"{category}: high/blocking flatness_risk cannot coexist with pass")
        if category == "reader_engagement" and reader_grip == "very_high" and flatness_risk != "low":
            raise ValueError("reader_engagement: very_high reader_grip requires flatness_risk=low for pass")

    refs = _string_list(raw.get("evidence_refs", []), f"{category}.evidence_refs")
    worker = result.get("worker") if isinstance(result.get("worker"), dict) else {}
    return {
        "category": category,
        "status": derived_status,
        "candidate_fingerprint": candidate_fingerprint,
        "codes": codes,
        "evidence_refs": refs,
        "flatness_risk": flatness_risk,
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
    }


def _plain_gate(raw: dict[str, Any], *, category: str, candidate_fingerprint: str) -> dict[str, Any]:
    status = raw.get("status")
    if status not in STATUSES:
        raise ValueError(f"invalid gate status: {category}")
    if category in REGISTERED_RELEASE_CATEGORIES and status != "pending":
        raise ValueError(f"{category}.semantic_binding is required for pass/fail release evidence")
    return {
        "category": category,
        "status": status,
        "candidate_fingerprint": candidate_fingerprint,
        "codes": _string_list(raw.get("codes", []), f"{category}.codes"),
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
    require_semantic = policy.get("require_independent_semantic", False)
    if not isinstance(require_continuity, bool) or not isinstance(require_semantic, bool):
        raise ValueError("policy requirement flags must be boolean")

    required = ["surface", "reader_engagement"]
    if require_continuity:
        required.append("continuity")
    if require_semantic:
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

        status = raw.get("status")
        if category in REGISTERED_RELEASE_CATEGORIES and status != "pending":
            gate = _registered_semantic_gate(raw, category=category, candidate_fingerprint=candidate, reader_grip=grip)
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
            "require_independent_semantic": require_semantic,
        },
        "required_gates": required,
        "gates": [gates[k] for k in sorted(gates)],
        "blocking_gates": blocking,
        "pending_gates": pending,
        "ready_for_user_visible_review": ready,
        "conjunctive_gate": True,
        "numeric_quality_aggregation": False,
        "registered_reader_engagement_required": True,
        "registered_independent_release_contract_required": require_semantic,
        "project_bridge_receipt_required_for_independence": require_semantic,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def _reader_binding(
    fp: str,
    result_value: str = "pass",
    *,
    codes: list[str] | None = None,
    flatness_risk: str | None = None,
) -> dict[str, Any]:
    risk = flatness_risk or ("low" if result_value == "pass" else "blocking")
    job = make_contract_job(
        "reader.engagement_audit",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "A bounded reader-engagement fixture.", "reader_grip": "very_high"},
        source_session_id="SES-MANAGER",
    )
    judgment = {
        "confidence": 0.95,
        "result": result_value,
        "active_reader_question": "Will the immediate pressure force a meaningful choice?",
        "question_evolution": "The fixture changes the available choice and consequence.",
        "pressure_ladder": "Pressure increases through consequence, not countdown repetition.",
        "reader_rewards": "The reader receives a concrete state change.",
        "character_energy": "The character owns the choice.",
        "tonal_contrast": "The register changes with consequence.",
        "information_value": "New information changes the next action.",
        "causal_momentum": "Each beat changes available options.",
        "relationship_movement": "The interaction changes leverage.",
        "procedure_compression": "Routine procedure is compressed.",
        "ending_forward_pull": "The ending opens a concrete next-state question.",
        "flatness_risk": risk,
        "codes": list(codes or []),
        "evidence": ["fixture evidence"],
    }
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "cold-reader-fixture"},
        "judgment": judgment,
        "proposals": [],
        "errors": [],
    }
    return {"job": job, "result": result}


def _production_binding(
    fp: str,
    result_value: str = "pass",
    *,
    codes: list[str] | None = None,
    flatness_risk: str | None = None,
) -> dict[str, Any]:
    risk = flatness_risk or ("low" if result_value == "pass" else "blocking")
    job = make_contract_job(
        "quality.production_review",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "A bounded production-review fixture.", "reader_grip": "very_high"},
        source_session_id="SES-MANAGER",
    )
    job["provenance"].update({
        "project_id": "PROJECT-SELF",
        "project_repo": "owner/project",
        "framework_repo": "owner/framework",
        "framework_commit": "f" * 40,
    })
    packet = build_peer_packet(job)
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "chatgpt_peer_chat", "model_or_reviewer": "independent-fixture", "run_reference": packet["relay_nonce"]},
        "judgment": {
            "confidence": 0.95,
            "result": result_value,
            "codes": list(codes or []),
            "evidence": ["fixture evidence"],
            "summary": "fixture",
            "flatness_risk": risk,
        },
        "proposals": [],
        "errors": [],
    }
    receipt = build_peer_bridge_receipt(
        packet,
        result,
        project_id="PROJECT-SELF",
        project_repo="owner/project",
        framework_repo="owner/framework",
        framework_commit="f" * 40,
        issue_number=7,
        runtime_trace={
            "github_run_id": 1,
            "github_run_attempt": 1,
            "github_event_name": "issue_comment",
            "result_comment_id": 1,
            "workflow_name": "self-test",
            "framework_action_ref": "f" * 40,
        },
    )
    return {"job": job, "result": result, "peer_packet": packet, "bridge_receipt": receipt}


def self_test() -> int:
    fp = "sha256:" + "a" * 64

    def packet(
        *,
        surface: str = "pass",
        reader: str = "pass",
        continuity: str = "pass",
        semantic: str = "pass",
    ) -> dict[str, Any]:
        reader_gate: dict[str, Any] = {
            "category": "reader_engagement",
            "status": reader,
            "candidate_fingerprint": fp,
            "codes": [],
            "evidence_refs": ["reader:self"],
        }
        if reader in {"pass", "fail"}:
            reader_gate["semantic_binding"] = _reader_binding(fp, reader)
        semantic_gate: dict[str, Any] = {
            "category": "semantic_independent",
            "status": semantic,
            "candidate_fingerprint": fp,
            "codes": [],
            "evidence_refs": ["semantic:self"],
        }
        if semantic in {"pass", "fail"}:
            semantic_gate["semantic_binding"] = _production_binding(fp, semantic)
        return {
            "candidate_fingerprint": fp,
            "policy": {"reader_grip": "very_high", "require_continuity": True, "require_independent_semantic": True},
            "gates": [
                {"category": "surface", "status": surface, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["surface:self"]},
                reader_gate,
                {"category": "continuity", "status": continuity, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["continuity:self"]},
                semantic_gate,
            ],
        }

    green = evaluate(packet())
    reader_fail = evaluate(packet(reader="fail"))
    surface_fail = evaluate(packet(surface="fail"))
    semantic_fail = evaluate(packet(semantic="fail"))
    semantic_pending = evaluate(packet(semantic="pending"))
    reader_pending = evaluate(packet(reader="pending"))

    outer_mismatch_guard = False
    bad = packet()
    bad["gates"][0]["candidate_fingerprint"] = "sha256:" + "b" * 64
    try:
        evaluate(bad)
    except ValueError:
        outer_mismatch_guard = True

    adhoc_reader_guard = False
    adhoc_reader = packet()
    adhoc_reader["gates"][1].pop("semantic_binding", None)
    try:
        evaluate(adhoc_reader)
    except ValueError as exc:
        adhoc_reader_guard = "semantic_binding" in str(exc)

    adhoc_semantic_guard = False
    adhoc_semantic = packet()
    adhoc_semantic["gates"][-1].pop("semantic_binding", None)
    try:
        evaluate(adhoc_semantic)
    except ValueError as exc:
        adhoc_semantic_guard = "semantic_binding" in str(exc)

    bridge_receipt_guard = False
    no_receipt = packet()
    no_receipt["gates"][-1]["semantic_binding"].pop("bridge_receipt", None)
    try:
        evaluate(no_receipt)
    except ValueError as exc:
        bridge_receipt_guard = "bridge_receipt" in str(exc)

    bare_session_guard = False
    bare_session = packet()
    binding = bare_session["gates"][-1]["semantic_binding"]
    binding.pop("peer_packet", None)
    binding.pop("bridge_receipt", None)
    binding["result"]["execution"] = {"source_session_id": "SES-MANAGER", "worker_session_id": "SES-B"}
    try:
        evaluate(bare_session)
    except ValueError as exc:
        bare_session_guard = "peer_packet" in str(exc) or "bridge_receipt" in str(exc)

    candidate_contract_guard = False
    wrong_candidate = packet()
    wrong_candidate["gates"][-1]["semantic_binding"] = _production_binding("sha256:" + "b" * 64, "pass")
    try:
        evaluate(wrong_candidate)
    except ValueError as exc:
        candidate_contract_guard = "candidate fingerprint mismatch" in str(exc)

    caller_status_override_guard = False
    override = packet()
    override["gates"][-1]["semantic_binding"] = _production_binding(fp, "fail")
    override["gates"][-1]["status"] = "pass"
    try:
        evaluate(override)
    except ValueError as exc:
        caller_status_override_guard = "contradicts registered semantic result" in str(exc)

    reader_flat_pass_guard = False
    reader_flat = packet()
    reader_flat["gates"][1]["semantic_binding"] = _reader_binding(fp, "pass", codes=[SAFE_BUT_FLAT_ID])
    try:
        evaluate(reader_flat)
    except ValueError as exc:
        reader_flat_pass_guard = SAFE_BUT_FLAT_ID in str(exc)

    reader_medium_flatness_guard = False
    reader_medium = packet()
    reader_medium["gates"][1]["semantic_binding"] = _reader_binding(fp, "pass", flatness_risk="medium")
    try:
        evaluate(reader_medium)
    except ValueError as exc:
        reader_medium_flatness_guard = "very_high reader_grip" in str(exc)

    production_checklist_pass_guard = False
    checklist = packet()
    checklist["gates"][-1]["semantic_binding"] = _production_binding(fp, "pass", codes=[CHECKLIST_CAUSALITY_ID])
    try:
        evaluate(checklist)
    except ValueError as exc:
        production_checklist_pass_guard = CHECKLIST_CAUSALITY_ID in str(exc)

    production_flatness_pass_guard = False
    blocked = packet()
    blocked["gates"][-1]["semantic_binding"] = _production_binding(fp, "pass", flatness_risk="blocking")
    try:
        evaluate(blocked)
    except ValueError as exc:
        production_flatness_pass_guard = "flatness_risk" in str(exc)

    receipt_tamper_guard = False
    tampered = packet()
    tampered["gates"][-1]["semantic_binding"]["bridge_receipt"]["result_fingerprint"] = "sha256:" + "0" * 64
    try:
        evaluate(tampered)
    except ValueError as exc:
        receipt_tamper_guard = "result_fingerprint" in str(exc)

    taxonomy_ok = taxonomy_self_test().get("quality_taxonomy_contract") == "PASS"
    repair_policy_ok = repair_policy_self_test().get("repair_policy_contract") == "PASS"
    binding_test = registered_binding_self_test()
    registered_binding_ok = binding_test.get("registered_contract_binding_contract") == "PASS"
    semantic_green_gate = next(g for g in green["gates"] if g["category"] == "semantic_independent")
    independence_mode = semantic_green_gate.get("semantic_contract", {}).get("independence", {}).get("mode")

    ok = all((
        green["ready_for_user_visible_review"] is True,
        reader_fail["blocking_gates"] == ["reader_engagement"],
        surface_fail["blocking_gates"] == ["surface"],
        semantic_fail["blocking_gates"] == ["semantic_independent"],
        semantic_pending["pending_gates"] == ["semantic_independent"],
        reader_pending["pending_gates"] == ["reader_engagement"],
        outer_mismatch_guard,
        adhoc_reader_guard,
        adhoc_semantic_guard,
        bridge_receipt_guard,
        bare_session_guard,
        candidate_contract_guard,
        caller_status_override_guard,
        reader_flat_pass_guard,
        reader_medium_flatness_guard,
        production_checklist_pass_guard,
        production_flatness_pass_guard,
        receipt_tamper_guard,
        taxonomy_ok,
        repair_policy_ok,
        registered_binding_ok,
        green["registered_reader_engagement_required"] is True,
        green["registered_independent_release_contract_required"] is True,
        green["project_bridge_receipt_required_for_independence"] is True,
        green["numeric_quality_aggregation"] is False,
        independence_mode == "project_owned_peer_bridge",
    ))
    print(json.dumps({
        "production_readiness_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "surface_and_reader_are_conjunctive": True,
        "safe_but_flat_id": SAFE_BUT_FLAT_ID,
        "checklist_causality_id": CHECKLIST_CAUSALITY_ID,
        "candidate_fingerprint_bound": outer_mismatch_guard,
        "semantic_contract_candidate_bound": candidate_contract_guard,
        "registered_reader_engagement_required": adhoc_reader_guard,
        "registered_independent_release_contract_required": adhoc_semantic_guard,
        "registered_contract_definition_bound": registered_binding_ok,
        "project_bridge_receipt_required": bridge_receipt_guard,
        "bare_distinct_session_not_independence": bare_session_guard,
        "caller_status_cannot_override_semantic_result": caller_status_override_guard,
        "blocking_reader_code_cannot_pass": reader_flat_pass_guard,
        "very_high_reader_grip_flatness_guard": reader_medium_flatness_guard,
        "blocking_production_code_cannot_pass": production_checklist_pass_guard,
        "blocking_flatness_cannot_pass": production_flatness_pass_guard,
        "peer_receipt_result_tamper_rejected": receipt_tamper_guard,
        "project_owned_peer_bridge_independence": independence_mode == "project_owned_peer_bridge",
        "quality_taxonomy_contract": taxonomy_ok,
        "repair_policy_contract": repair_policy_ok,
        "numeric_quality_aggregation": False,
        "authority": False,
        "model_execution": False,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge production-readiness gate")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--input", required=True)
    ev.add_argument("--output")
    args = parser.parse_args()
    if args.command == "self-test":
        return self_test()
    value = evaluate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())