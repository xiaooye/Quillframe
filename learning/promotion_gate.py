#!/usr/bin/env python3
"""Deterministic authority gate for Quillframe learning promotion.

Models judge whether evidence semantically supports a preference/craft hypothesis
at a proposed scope. This module verifies that judgment is an exact registered
contract result bound to the same candidate/evidence, then enforces objective
authority requirements such as explicit activation authority, independent eval,
version/rollback/CI provenance and write separation.

No result from this module edits Framework behavior, Canon, or durable user
preference state. No semantic result grants its own write authority.
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

from registered_contract_binding import validate_registered_job  # noqa: E402
from semantic_worker_router import make_contract_job, validate_result  # noqa: E402

SCHEMA = "quillframe_learning_promotion_candidate_v1"
SCOPES = {"one_off", "project", "user_taste", "general_craft"}
PASS_STATES = {"pass", "passed", "success", "green"}
PROMOTION_REVIEW_CONTRACT = "learning.promotion_review"
INDEPENDENT_EVAL_CONTRACT = "learning.evaluate"


def passed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in PASS_STATES
    if isinstance(value, dict):
        for key in ("status", "result", "conclusion"):
            if key in value:
                return passed(value[key])
    return False


def nonempty_refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(x).strip() for x in value if str(x).strip()))


def _binding_result(binding: Any, contract_id: str, *, label: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(binding, dict):
        raise ValueError(f"{label} registered semantic binding required")
    job = binding.get("job")
    result = binding.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict):
        raise ValueError(f"{label} requires job and result objects")
    errors = validate_registered_job(job)
    if errors:
        raise ValueError(f"{label} registered contract invalid: " + "; ".join(errors))
    result_errors = validate_result(job, result)
    if result_errors:
        raise ValueError(f"{label} semantic result invalid: " + "; ".join(result_errors))
    if result.get("status") != "completed":
        raise ValueError(f"{label} semantic result must be completed")
    input_obj = job.get("input")
    if not isinstance(input_obj, dict) or input_obj.get("model_contract_id") != contract_id:
        raise ValueError(f"{label} requires {contract_id}")
    payload = input_obj.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(f"{label} contract payload required")
    judgment = result.get("judgment")
    if not isinstance(judgment, dict):
        raise ValueError(f"{label} judgment required")
    return job, payload, judgment


def _promotion_semantic_review(candidate: dict[str, Any], evidence_refs: list[str]) -> dict[str, Any]:
    try:
        job, payload, judgment = _binding_result(candidate.get("semantic_review_binding"), PROMOTION_REVIEW_CONTRACT, label="semantic_review")
    except ValueError as exc:
        return {"valid": False, "ready": False, "status": "invalid", "blockers": [str(exc)]}

    binding_errors: list[str] = []
    expected = {
        "candidate_id": candidate.get("candidate_id"),
        "scope": candidate.get("scope"),
        "mechanism": str(candidate.get("mechanism") or "").strip(),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            binding_errors.append(f"semantic review payload mismatch: {key}")
    if nonempty_refs(payload.get("evidence_refs")) != evidence_refs:
        binding_errors.append("semantic review payload mismatch: evidence_refs")

    result = judgment.get("result")
    supported_scope = judgment.get("supported_scope")
    if result not in {"pass", "fail", "insufficient_evidence"}:
        binding_errors.append("semantic review judgment.result invalid")
    ready = result == "pass" and supported_scope == candidate.get("scope") and not binding_errors
    blockers = list(binding_errors)
    if result == "fail":
        blockers.append("semantic review rejected proposed scope/mechanism")
    elif result == "insufficient_evidence":
        blockers.append("semantic review found insufficient evidence")
    elif result == "pass" and supported_scope != candidate.get("scope"):
        blockers.append("semantic review does not support the proposed scope")
    return {
        "valid": not binding_errors,
        "ready": ready,
        "status": result if result in {"pass", "fail", "insufficient_evidence"} else "invalid",
        "supported_scope": supported_scope,
        "job_fingerprint": job.get("input_fingerprint"),
        "blockers": blockers,
        "semantic_evidence_count_threshold_used": False,
        "authority": False,
    }


def _independent_eval(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        job, payload, judgment = _binding_result(candidate.get("independent_eval_binding"), INDEPENDENT_EVAL_CONTRACT, label="independent_eval")
    except ValueError as exc:
        return {"valid": False, "ready": False, "blockers": [str(exc)]}
    provenance = job.get("provenance") if isinstance(job.get("provenance"), dict) else {}
    errors: list[str] = []
    if provenance.get("independent_gate") is not True:
        errors.append("independent eval contract must declare independent_gate=true")
    for key, expected in {
        "candidate_id": candidate.get("candidate_id"),
        "scope": candidate.get("scope"),
        "mechanism": str(candidate.get("mechanism") or "").strip(),
    }.items():
        if payload.get(key) != expected:
            errors.append(f"independent eval payload mismatch: {key}")
    if judgment.get("result") != "pass":
        errors.append("independent semantic evaluation must pass")
    return {
        "valid": not errors,
        "ready": not errors,
        "job_fingerprint": job.get("input_fingerprint"),
        "blockers": errors,
        "authority": False,
    }


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if candidate.get("schema") != SCHEMA:
        blockers.append(f"schema must be {SCHEMA}")
    scope = candidate.get("scope")
    if scope not in SCOPES:
        blockers.append("invalid scope")
    mechanism = str(candidate.get("mechanism") or "").strip()
    if not mechanism:
        blockers.append("mechanism required")
    evidence = candidate.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
        blockers.append("evidence must be object")
    evidence_refs = nonempty_refs(evidence.get("evidence_refs"))

    semantic_review = {"valid": False, "ready": False, "status": "not_applicable", "blockers": []}
    if scope in {"project", "user_taste", "general_craft"} and mechanism:
        if not evidence_refs:
            blockers.append(f"{scope} promotion requires traceable evidence_refs")
        else:
            semantic_review = _promotion_semantic_review(candidate, evidence_refs)
            blockers.extend(semantic_review["blockers"])

    independent_eval = {"valid": False, "ready": False, "blockers": [], "required": scope == "general_craft"}
    status = "blocked"
    if scope == "one_off":
        blockers.append("one_off scope is intentionally non-durable")
    elif scope == "project":
        if not evidence.get("explicit_project_authority", False):
            blockers.append("project activation requires explicit project authority")
        if not blockers and semantic_review.get("ready"):
            status = "ready_for_activation"
    elif scope == "user_taste":
        # Durable user-taste write permission is deliberately checked by the
        # Author Model/write path. This gate proves semantic scope/evidence only.
        if not blockers and semantic_review.get("ready"):
            status = "ready_for_activation"
    elif scope == "general_craft":
        independent_eval = _independent_eval(candidate)
        blockers.extend(independent_eval["blockers"])
        version_target = str(evidence.get("version_target") or "").strip()
        rollback_ref = str(evidence.get("rollback_ref") or "").strip()
        if not version_target:
            blockers.append("general_craft requires version_target")
        if not rollback_ref:
            blockers.append("general_craft requires rollback_ref")
        ci = evidence.get("framework_ci")
        if not passed(ci):
            blockers.append("general_craft requires green framework CI evidence")
        if isinstance(ci, dict):
            commit = str(ci.get("commit") or "").strip()
            if len(commit) != 40 or any(c not in "0123456789abcdefABCDEF" for c in commit):
                blockers.append("framework CI evidence must bind an exact 40-hex commit")
        if not nonempty_refs(evidence.get("provenance_refs")):
            blockers.append("general_craft requires provenance_refs")
        if not blockers and semantic_review.get("ready") and independent_eval.get("ready"):
            status = "promotable"

    return {
        "schema": "quillframe_learning_promotion_gate_v2",
        "candidate_id": candidate.get("candidate_id"),
        "scope": scope,
        "mechanism": mechanism or None,
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "semantic_review": semantic_review,
        "independent_eval": independent_eval,
        "semantic_evidence_count_threshold_used": False,
        "behavior_write_authority": False,
        "canon_write_authority": False,
        "durable_user_taste_write_authority": False,
        "next_action": (
            "authorized_manager_or_human_review" if status in {"promotable", "ready_for_activation"}
            else "repair_evidence_or_narrow_scope"
        ),
    }


def _semantic_binding(candidate_id: str, scope: str, mechanism: str, refs: list[str], *, result: str = "pass", supported_scope: str | None = None) -> dict[str, Any]:
    payload = {"candidate_id": candidate_id, "scope": scope, "mechanism": mechanism, "evidence_refs": refs}
    job = make_contract_job(PROMOTION_REVIEW_CONTRACT, candidate_id, payload, source_session_id="SES-SELF")
    judgment = {
        "confidence": 0.9,
        "result": result,
        "supported_scope": supported_scope or scope,
        "report": "Bound semantic promotion-review fixture.",
        "evidence_refs": refs,
        "unresolved_contradictions": [],
        "recommended_boundary": {},
    }
    semantic_result = {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "semantic-fixture"},
        "judgment": judgment, "proposals": [], "errors": [],
    }
    return {"job": job, "result": semantic_result}


def _eval_binding(candidate_id: str, scope: str, mechanism: str, *, result: str = "pass") -> dict[str, Any]:
    payload = {"candidate_id": candidate_id, "scope": scope, "mechanism": mechanism, "fixture": "bounded regression evidence"}
    job = make_contract_job(INDEPENDENT_EVAL_CONTRACT, candidate_id, payload, source_session_id="SES-INDEPENDENT")
    semantic_result = {
        "job_id": job["job_id"], "subject_id": job["subject_id"], "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"], "status": "completed",
        "worker": {"provider": "self_test_independent", "model_or_reviewer": "independent-fixture"},
        "judgment": {"confidence": 0.9, "result": result, "codes": [], "evidence": ["fixture"]},
        "proposals": [], "errors": [],
    }
    return {"job": job, "result": semantic_result}


def self_test() -> dict[str, Any]:
    refs = ["review:explicit"]
    unreviewed = evaluate({
        "schema": SCHEMA, "candidate_id": "UT-UNREVIEWED", "scope": "user_taste", "mechanism": "low narrator commentary",
        "evidence": {"evidence_refs": refs, "explicit_user_evidence": 999, "independent_consistent_corrections": 999},
    })
    reviewed_candidate = {
        "schema": SCHEMA, "candidate_id": "UT-GOOD", "scope": "user_taste", "mechanism": "low narrator commentary",
        "evidence": {"evidence_refs": refs},
    }
    reviewed_candidate["semantic_review_binding"] = _semantic_binding("UT-GOOD", "user_taste", "low narrator commentary", refs)
    reviewed = evaluate(reviewed_candidate)

    narrow = {
        "schema": SCHEMA, "candidate_id": "UT-NARROW", "scope": "user_taste", "mechanism": "low narrator commentary",
        "evidence": {"evidence_refs": refs},
        "semantic_review_binding": _semantic_binding("UT-NARROW", "user_taste", "low narrator commentary", refs, supported_scope="project"),
    }
    narrowed = evaluate(narrow)

    caller_override = json.loads(json.dumps(reviewed_candidate))
    caller_override["semantic_review_binding"]["result"]["judgment"]["result"] = "fail"
    caller_override_result = evaluate(caller_override)

    gc_refs = ["SRC-A"]
    gc = {
        "schema": SCHEMA, "candidate_id": "GC-GOOD", "scope": "general_craft", "mechanism": "causal scene pressure",
        "evidence": {
            "evidence_refs": gc_refs,
            "version_target": "0.9.1",
            "rollback_ref": "git:baseline",
            "framework_ci": {"conclusion": "success", "commit": "0123456789abcdef0123456789abcdef01234567"},
            "provenance_refs": ["SRC-A"],
        },
        "semantic_review_binding": _semantic_binding("GC-GOOD", "general_craft", "causal scene pressure", gc_refs),
        "independent_eval_binding": _eval_binding("GC-GOOD", "general_craft", "causal scene pressure"),
    }
    general = evaluate(gc)
    gc_no_rollback = json.loads(json.dumps(gc)); gc_no_rollback["evidence"].pop("rollback_ref")
    general_no_rollback = evaluate(gc_no_rollback)

    ok = all([
        unreviewed["status"] == "blocked",
        reviewed["status"] == "ready_for_activation",
        narrowed["status"] == "blocked",
        caller_override_result["status"] == "blocked",
        general["status"] == "promotable",
        general_no_rollback["status"] == "blocked",
        reviewed["semantic_evidence_count_threshold_used"] is False,
        reviewed["durable_user_taste_write_authority"] is False,
    ])
    return {
        "promotion_gate_contract": "PASS" if ok else "FAIL",
        "unreviewed_user_taste_blocked": unreviewed["status"] == "blocked",
        "semantic_scope_review_required": reviewed["status"] == "ready_for_activation" and narrowed["status"] == "blocked",
        "caller_cannot_override_bound_semantic_result": caller_override_result["status"] == "blocked",
        "semantic_evidence_count_threshold_used": False,
        "general_craft_independent_eval_required": general["status"] == "promotable",
        "general_craft_objective_rollback_required": general_no_rollback["status"] == "blocked",
        "auto_behavior_write": False,
        "auto_canon_write": False,
        "auto_durable_user_taste_write": False,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Quillframe learning promotion authority gate")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate"); e.add_argument("--candidate", required=True); e.add_argument("--output")
    sub.add_parser("self-test")
    args = p.parse_args()
    if args.cmd == "self-test":
        result = self_test(); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result["promotion_gate_contract"] == "PASS" else 1
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8")); result = evaluate(candidate)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output: Path(args.output).write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
