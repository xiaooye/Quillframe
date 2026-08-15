#!/usr/bin/env python3
"""Deterministic conjunctive user-visible prose readiness gate.

Semantic systems produce the underlying Surface, Reader Engagement, continuity
and independent-review judgments. This module binds those receipts to one
candidate fingerprint and applies fail-closed release policy. It never averages
literary scores and never grants Canon authority.

A mandatory independent semantic gate is stronger than "some independent model
returned PASS". PASS/FAIL release evidence must be a validated result of a
registered model contract whose registry explicitly grants the corresponding
release role. Ad-hoc ``eval_judge`` jobs remain valid for blind eval suites but
cannot satisfy production release.
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

from peer_chat_relay import build as build_peer_packet, validate_peer_result  # noqa: E402
from semantic_worker_router import (  # noqa: E402
    load_contract_registry,
    make_contract_job,
    resolve_contract_registry,
    validate_result,
)
from quality_taxonomy import id_for_name, self_test as taxonomy_self_test  # noqa: E402
from repair_policy import self_test as repair_policy_self_test  # noqa: E402

SCHEMA = "novelforge_production_readiness_v1"
CATEGORIES = {"surface", "reader_engagement", "continuity", "semantic_independent"}
STATUSES = {"pass", "fail", "pending"}
READER_GRIP = {"low", "medium", "high", "very_high"}
SAFE_BUT_FLAT_ID = id_for_name("SAFE-BUT-FLAT")


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


def _validate_independence(
    binding: dict[str, Any],
    *,
    job: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Require either a validated peer-relay packet or a distinct worker session."""
    peer_packet = binding.get("peer_packet")
    if peer_packet is not None:
        if not isinstance(peer_packet, dict):
            raise ValueError("semantic_independent.peer_packet must be object")
        errors = validate_peer_result(peer_packet, result)
        if errors:
            raise ValueError("semantic_independent peer relay invalid: " + "; ".join(errors))
        packet_job = peer_packet.get("job") or {}
        for key in ("job_id", "subject_id", "kind", "input_fingerprint"):
            if packet_job.get(key) != job.get(key):
                raise ValueError(f"semantic_independent peer packet/job mismatch: {key}")
        worker = result.get("worker") or {}
        return {
            "mode": "peer_chat_relay",
            "relay_nonce": peer_packet.get("relay_nonce"),
            "run_reference": worker.get("run_reference") or (result.get("execution") or {}).get("run_reference"),
            "source_session_id": (job.get("execution") or {}).get("source_session_id"),
            "worker_session_id": (result.get("execution") or {}).get("worker_session_id"),
        }

    execution = job.get("execution") or {}
    result_execution = result.get("execution") or {}
    source_session = execution.get("source_session_id") if isinstance(execution, dict) else None
    worker_session = result_execution.get("worker_session_id") if isinstance(result_execution, dict) else None
    if not isinstance(source_session, str) or not source_session:
        raise ValueError("semantic_independent requires source_session_id or validated peer_packet")
    if not isinstance(worker_session, str) or not worker_session:
        raise ValueError("semantic_independent requires worker_session_id or validated peer_packet")
    if source_session == worker_session:
        raise ValueError("semantic_independent reviewer session must differ from manager/source session")
    return {
        "mode": "distinct_worker_session",
        "relay_nonce": None,
        "run_reference": result_execution.get("run_reference"),
        "source_session_id": source_session,
        "worker_session_id": worker_session,
    }


def _registered_semantic_gate(
    raw: dict[str, Any],
    *,
    category: str,
    candidate_fingerprint: str,
) -> dict[str, Any]:
    """Validate a release-bearing semantic job/result and derive its verdict.

    The caller is not allowed to convert a reviewer result into PASS by writing
    a different gate status. The semantic judgment is consumed directly after
    deterministic job/result validation and registry provenance checks.
    """
    binding = raw.get("semantic_binding")
    if not isinstance(binding, dict):
        raise ValueError(f"{category}.semantic_binding is required for pass/fail release evidence")
    job = binding.get("job")
    result = binding.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict):
        raise ValueError(f"{category}.semantic_binding requires job and result objects")

    errors = validate_result(job, result)
    if errors:
        raise ValueError(f"{category}.semantic_binding invalid: " + "; ".join(errors))
    if result.get("status") != "completed":
        raise ValueError(f"{category}.semantic result must be completed")

    input_obj = job.get("input")
    if not isinstance(input_obj, dict):
        raise ValueError(f"{category}.semantic job input required")
    contract_id = input_obj.get("model_contract_id")
    if not isinstance(contract_id, str) or not contract_id:
        raise ValueError(f"{category} requires registered model_contract_id")
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

    registry_path, pack_id = resolve_contract_registry(contract_id)
    registry = load_contract_registry(registry_path)
    contract = registry["contracts"].get(contract_id)
    if not isinstance(contract, dict):
        raise ValueError(f"{category}: registered contract unavailable: {contract_id}")
    roles = contract.get("release_roles", [])
    if not isinstance(roles, list) or category not in roles:
        raise ValueError(f"{category}: contract {contract_id} is not registered for release role {category}")
    if category == "semantic_independent" and contract.get("independent_gate") is not True:
        raise ValueError(f"{category}: contract {contract_id} is not an independent gate")

    expected_registry_path = str(registry_path.relative_to(SEM)) if registry_path.is_relative_to(SEM) else str(registry_path)
    expected = {
        "registry_schema": registry.get("schema"),
        "registry_version": registry.get("version"),
        "registry_path": expected_registry_path,
        "pack_id": pack_id,
        "model_contract_id": contract_id,
        "independent_gate": bool(contract.get("independent_gate", False)),
    }
    for key, value in expected.items():
        if provenance.get(key) != value:
            raise ValueError(f"{category}.semantic provenance mismatch: {key}")

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
    refs = _string_list(raw.get("evidence_refs", []), f"{category}.evidence_refs")
    worker = result.get("worker") if isinstance(result.get("worker"), dict) else {}
    return {
        "category": category,
        "status": derived_status,
        "candidate_fingerprint": candidate_fingerprint,
        "codes": codes,
        "evidence_refs": refs,
        "semantic_contract": {
            "model_contract_id": contract_id,
            "registry_schema": registry.get("schema"),
            "registry_version": registry.get("version"),
            "pack_id": pack_id,
            "release_role": category,
            "independent_gate": bool(contract.get("independent_gate", False)),
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
    codes = _string_list(raw.get("codes", []), f"{category}.codes")
    refs = _string_list(raw.get("evidence_refs", []), f"{category}.evidence_refs")
    if category == "reader_engagement" and SAFE_BUT_FLAT_ID in codes and status == "pass":
        raise ValueError(f"{SAFE_BUT_FLAT_ID} SAFE-BUT-FLAT cannot pass reader_engagement")
    return {
        "category": category,
        "status": status,
        "candidate_fingerprint": candidate_fingerprint,
        "codes": codes,
        "evidence_refs": refs,
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

        # Pending means no release claim has been made yet, so no completed
        # semantic binding is required. Any pass/fail independent claim must be
        # derived from a registered release contract.
        if category == "semantic_independent" and raw.get("status") != "pending":
            gate = _registered_semantic_gate(raw, category=category, candidate_fingerprint=candidate)
        elif category == "reader_engagement" and raw.get("semantic_binding") is not None and raw.get("status") != "pending":
            gate = _registered_semantic_gate(raw, category=category, candidate_fingerprint=candidate)
            if SAFE_BUT_FLAT_ID in gate["codes"] and gate["status"] == "pass":
                raise ValueError(f"{SAFE_BUT_FLAT_ID} SAFE-BUT-FLAT cannot pass reader_engagement")
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
        "registered_release_contract_required": require_semantic,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }


def _semantic_fixture(
    fp: str,
    semantic_result: str = "pass",
    *,
    same_session: bool = False,
    peer_relay: bool = False,
) -> dict[str, Any]:
    job = make_contract_job(
        "quality.production_review",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "A bounded production-review fixture."},
        source_session_id="SES-MANAGER",
    )
    packet = build_peer_packet(job) if peer_relay else None
    result: dict[str, Any] = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "chatgpt_peer_chat" if peer_relay else "self_test", "model_or_reviewer": "independent-fixture"},
        "judgment": {
            "confidence": 0.95,
            "result": semantic_result,
            "codes": [],
            "evidence": ["fixture evidence"],
            "summary": "fixture",
            "flatness_risk": "low" if semantic_result == "pass" else "blocking",
        },
        "proposals": [],
        "errors": [],
    }
    if peer_relay and packet is not None:
        result["worker"]["run_reference"] = packet["relay_nonce"]
    else:
        result["execution"] = {
            "source_session_id": "SES-MANAGER",
            "worker_session_id": "SES-MANAGER" if same_session else "SES-REVIEWER",
            "handoff_id": None,
            "attempt_id": "ATT-1",
        }
    binding: dict[str, Any] = {"job": job, "result": result}
    if packet is not None:
        binding["peer_packet"] = packet
    return binding


def self_test() -> int:
    fp = "sha256:" + "a" * 64

    def packet(
        surface: str = "pass",
        reader: str = "pass",
        continuity: str = "pass",
        semantic: str = "pass",
        reader_codes: list[str] | None = None,
        peer_relay: bool = True,
    ) -> dict[str, Any]:
        semantic_gate: dict[str, Any] = {
            "category": "semantic_independent",
            "status": semantic,
            "candidate_fingerprint": fp,
            "codes": [],
            "evidence_refs": ["semantic:self"],
        }
        if semantic in {"pass", "fail"}:
            semantic_gate["semantic_binding"] = _semantic_fixture(fp, semantic, peer_relay=peer_relay)
        return {
            "candidate_fingerprint": fp,
            "policy": {"reader_grip": "very_high", "require_continuity": True, "require_independent_semantic": True},
            "gates": [
                {"category": "surface", "status": surface, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["surface:a"]},
                {"category": "reader_engagement", "status": reader, "candidate_fingerprint": fp, "codes": reader_codes or [], "evidence_refs": ["reader:a"]},
                {"category": "continuity", "status": continuity, "candidate_fingerprint": fp, "codes": [], "evidence_refs": ["continuity:a"]},
                semantic_gate,
            ],
        }

    green = evaluate(packet())
    session_green = evaluate(packet(peer_relay=False))
    semantic_green_gate = next(g for g in green["gates"] if g["category"] == "semantic_independent")
    flat = evaluate(packet(reader="fail", reader_codes=[SAFE_BUT_FLAT_ID]))
    surface_fail = evaluate(packet(surface="fail"))
    semantic_fail = evaluate(packet(semantic="fail"))
    pending = evaluate(packet(semantic="pending"))

    mismatch_guard = False
    bad = packet()
    bad["gates"][0]["candidate_fingerprint"] = "sha256:" + "b" * 64
    try:
        evaluate(bad)
    except ValueError:
        mismatch_guard = True

    contradictory_flat_guard = False
    try:
        evaluate(packet(reader="pass", reader_codes=[SAFE_BUT_FLAT_ID]))
    except ValueError:
        contradictory_flat_guard = True

    adhoc_release_guard = False
    adhoc = packet()
    adhoc["gates"][-1].pop("semantic_binding", None)
    try:
        evaluate(adhoc)
    except ValueError as exc:
        adhoc_release_guard = "semantic_binding" in str(exc)

    same_session_guard = False
    same = packet(peer_relay=False)
    same["gates"][-1]["semantic_binding"] = _semantic_fixture(fp, "pass", same_session=True, peer_relay=False)
    try:
        evaluate(same)
    except ValueError as exc:
        same_session_guard = "must differ" in str(exc)

    candidate_contract_guard = False
    wrong_candidate = packet()
    wrong_candidate["gates"][-1]["semantic_binding"] = _semantic_fixture("sha256:" + "b" * 64, "pass", peer_relay=True)
    try:
        evaluate(wrong_candidate)
    except ValueError as exc:
        candidate_contract_guard = "contract candidate fingerprint mismatch" in str(exc)

    caller_status_override_guard = False
    override = packet()
    override["gates"][-1]["semantic_binding"] = _semantic_fixture(fp, "fail", peer_relay=True)
    override["gates"][-1]["status"] = "pass"
    try:
        evaluate(override)
    except ValueError as exc:
        caller_status_override_guard = "contradicts registered semantic result" in str(exc)

    missing_text_guard = False
    missing_text = packet(peer_relay=False)
    binding = missing_text["gates"][-1]["semantic_binding"]
    binding["job"]["input"]["payload"].pop("candidate_text", None)
    try:
        evaluate(missing_text)
    except ValueError:
        missing_text_guard = True

    taxonomy = taxonomy_self_test()
    taxonomy_ok = taxonomy.get("quality_taxonomy_contract") == "PASS"
    repair_policy = repair_policy_self_test()
    repair_policy_ok = repair_policy.get("repair_policy_contract") == "PASS"
    independence_mode = semantic_green_gate.get("semantic_contract", {}).get("independence", {}).get("mode")

    ok = all((
        green["ready_for_user_visible_review"] is True,
        session_green["ready_for_user_visible_review"] is True,
        flat["ready_for_user_visible_review"] is False and flat["blocking_gates"] == ["reader_engagement"],
        surface_fail["ready_for_user_visible_review"] is False and surface_fail["blocking_gates"] == ["surface"],
        semantic_fail["ready_for_user_visible_review"] is False and semantic_fail["blocking_gates"] == ["semantic_independent"],
        pending["ready_for_user_visible_review"] is False and pending["pending_gates"] == ["semantic_independent"],
        mismatch_guard,
        contradictory_flat_guard,
        adhoc_release_guard,
        same_session_guard,
        candidate_contract_guard,
        caller_status_override_guard,
        missing_text_guard,
        taxonomy_ok,
        repair_policy_ok,
        green["numeric_quality_aggregation"] is False,
        green["registered_release_contract_required"] is True,
        independence_mode == "peer_chat_relay",
    ))
    print(json.dumps({
        "production_readiness_contract": "PASS" if ok else "FAIL",
        "schema": SCHEMA,
        "surface_and_reader_are_conjunctive": True,
        "safe_but_flat_id": SAFE_BUT_FLAT_ID,
        "safe_but_flat_blocks": True,
        "candidate_fingerprint_bound": mismatch_guard,
        "semantic_contract_candidate_bound": candidate_contract_guard,
        "candidate_text_required": missing_text_guard,
        "pending_gate_blocks": True,
        "registered_release_contract_required": adhoc_release_guard,
        "caller_status_cannot_override_semantic_result": caller_status_override_guard,
        "peer_relay_independence_supported": independence_mode == "peer_chat_relay",
        "distinct_session_independence_supported": session_green["ready_for_user_visible_review"] is True,
        "same_session_rejected": same_session_guard,
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
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--input", required=True)
    evaluate_parser.add_argument("--output")
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
