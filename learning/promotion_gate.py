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
from pathlib import Path
import re
from typing import Any

from harness.semantic_workers.registered_contract_binding import validate_registered_job
from harness.semantic_workers.semantic_worker_router import make_contract_job, validate_result

SCHEMA = "quillframe_learning_promotion_candidate_v1"
SCOPES = {"one_off", "project", "user_taste", "general_craft"}
PASS_STATES = {"pass", "passed", "success", "green"}
PROMOTION_REVIEW_CONTRACT = "learning.promotion_review"
INDEPENDENT_EVAL_CONTRACT = "learning.evaluate"
ARTIFACT_BINDING_FIELDS = (
    "candidate_artifact_fingerprint",
    "craft_pack_fingerprint",
)
_FINGERPRINT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _valid_fingerprint(value: Any) -> bool:
    return isinstance(value, str) and _FINGERPRINT_RE.fullmatch(value) is not None


def _artifact_pair(value: Any, expected: dict[str, Any] | None = None) -> dict[str, Any]:
    container = value if isinstance(value, dict) else {}
    raw = {key: container.get(key) for key in ARTIFACT_BINDING_FIELDS}
    valid = all(_valid_fingerprint(raw[key]) for key in ARTIFACT_BINDING_FIELDS)
    expected_valid = expected is not None and expected.get("valid") is True
    matches_expected = (
        None
        if expected is None
        else valid
        and expected_valid
        and all(raw[key] == expected.get(key) for key in ARTIFACT_BINDING_FIELDS)
    )
    return {
        key: raw[key] if _valid_fingerprint(raw[key]) else None
        for key in ARTIFACT_BINDING_FIELDS
    } | {
        "valid": valid,
        "matches_expected": matches_expected,
    }


def _binding_payload(binding: Any) -> dict[str, Any]:
    if not isinstance(binding, dict):
        return {}
    job = binding.get("job")
    input_obj = job.get("input") if isinstance(job, dict) else None
    payload = input_obj.get("payload") if isinstance(input_obj, dict) else None
    return payload if isinstance(payload, dict) else {}


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
    expected_artifacts = _artifact_pair(candidate)
    observed_artifacts = _artifact_pair(
        _binding_payload(candidate.get("semantic_review_binding")),
        expected_artifacts,
    )
    try:
        job, payload, judgment = _binding_result(candidate.get("semantic_review_binding"), PROMOTION_REVIEW_CONTRACT, label="semantic_review")
    except ValueError as exc:
        return {
            "valid": False,
            "ready": False,
            "status": "invalid",
            "blockers": [str(exc)],
            "artifact_binding": observed_artifacts,
        }

    binding_errors: list[str] = []
    expected = {
        "candidate_id": candidate.get("candidate_id"),
        "scope": candidate.get("scope"),
        "mechanism": str(candidate.get("mechanism") or "").strip(),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            binding_errors.append(f"semantic review payload mismatch: {key}")
    if candidate.get("scope") == "general_craft":
        for key in ARTIFACT_BINDING_FIELDS:
            if payload.get(key) != candidate.get(key):
                binding_errors.append(f"semantic review payload mismatch: {key}")
    if nonempty_refs(payload.get("evidence_refs")) != evidence_refs:
        binding_errors.append("semantic review payload mismatch: evidence_refs")

    result = judgment.get("result")
    supported_scope = judgment.get("supported_scope")
    unresolved = nonempty_refs(judgment.get("unresolved_contradictions"))
    if result not in {"pass", "fail", "insufficient_evidence"}:
        binding_errors.append("semantic review judgment.result invalid")
    ready = (
        result == "pass" and supported_scope == candidate.get("scope")
        and not unresolved and not binding_errors
    )
    blockers = list(binding_errors)
    if result == "fail":
        blockers.append("semantic review rejected proposed scope/mechanism")
    elif result == "insufficient_evidence":
        blockers.append("semantic review found insufficient evidence")
    elif result == "pass" and supported_scope != candidate.get("scope"):
        blockers.append("semantic review does not support the proposed scope")
    if unresolved:
        blockers.append("semantic review has unresolved contradictions")
    return {
        "valid": not binding_errors,
        "ready": ready,
        "status": result if result in {"pass", "fail", "insufficient_evidence"} else "invalid",
        "supported_scope": supported_scope,
        "unresolved_contradictions": unresolved,
        "job_fingerprint": job.get("input_fingerprint"),
        "artifact_binding": observed_artifacts,
        "blockers": blockers,
        "semantic_evidence_count_threshold_used": False,
        "authority": False,
    }


def _independent_eval(candidate: dict[str, Any]) -> dict[str, Any]:
    expected_artifacts = _artifact_pair(candidate)
    observed_artifacts = _artifact_pair(
        _binding_payload(candidate.get("independent_eval_binding")),
        expected_artifacts,
    )
    try:
        job, payload, judgment = _binding_result(candidate.get("independent_eval_binding"), INDEPENDENT_EVAL_CONTRACT, label="independent_eval")
    except ValueError as exc:
        return {
            "valid": False,
            "ready": False,
            "blockers": [str(exc)],
            "artifact_binding": observed_artifacts,
        }
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
    if candidate.get("scope") == "general_craft":
        for key in ARTIFACT_BINDING_FIELDS:
            if payload.get(key) != candidate.get(key):
                errors.append(f"independent eval payload mismatch: {key}")
    if judgment.get("result") != "pass":
        errors.append("independent semantic evaluation must pass")
    return {
        "valid": not errors,
        "ready": not errors,
        "job_fingerprint": job.get("input_fingerprint"),
        "artifact_binding": observed_artifacts,
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
    candidate_artifacts = _artifact_pair(candidate)
    mechanism = str(candidate.get("mechanism") or "").strip()
    if not mechanism:
        blockers.append("mechanism required")
    evidence = candidate.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
        blockers.append("evidence must be object")
    evidence_refs = nonempty_refs(evidence.get("evidence_refs"))

    semantic_review = {
        "valid": False,
        "ready": False,
        "status": "not_applicable",
        "blockers": [],
        "artifact_binding": _artifact_pair({}, candidate_artifacts),
    }
    if scope in {"project", "user_taste", "general_craft"} and mechanism:
        if not evidence_refs:
            blockers.append(f"{scope} promotion requires traceable evidence_refs")
        else:
            semantic_review = _promotion_semantic_review(candidate, evidence_refs)
            blockers.extend(semantic_review["blockers"])

    independent_eval = {
        "valid": False, "ready": False, "blockers": [],
        "required": scope in {"user_taste", "general_craft"},
        "artifact_binding": _artifact_pair({}, candidate_artifacts),
    }
    framework_ci_artifacts = _artifact_pair({}, candidate_artifacts) | {
        "commit": None,
        "binding_valid": False,
    }
    rollback_artifacts = _artifact_pair({}, candidate_artifacts) | {
        "rollback_ref": None,
        "binding_valid": False,
    }
    framework_ci_binding_valid = False
    rollback_binding_valid = False
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
        # standing-policy/write path. This gate proves bound semantics,
        # personalized evaluation and contradiction reconciliation only.
        independent_eval = _independent_eval(candidate)
        blockers.extend(independent_eval["blockers"])
        contradiction_review = evidence.get("contradiction_review")
        if not passed(contradiction_review):
            blockers.append("user_taste requires a passed contradiction review")
        if not blockers and semantic_review.get("ready") and independent_eval.get("ready"):
            status = "ready_for_activation"
    elif scope == "general_craft":
        independent_eval = _independent_eval(candidate)
        blockers.extend(independent_eval["blockers"])
        version_target = str(evidence.get("version_target") or "").strip()
        for key in ARTIFACT_BINDING_FIELDS:
            if not _valid_fingerprint(candidate.get(key)):
                blockers.append(f"general_craft requires valid {key}")
        if not version_target:
            blockers.append("general_craft requires version_target")
        ci = evidence.get("framework_ci")
        framework_ci_artifacts = _artifact_pair(ci, candidate_artifacts)
        if not passed(ci):
            blockers.append("general_craft requires green framework CI evidence")
        if isinstance(ci, dict):
            commit = str(ci.get("commit") or "").strip()
            commit_valid = len(commit) == 40 and all(
                c in "0123456789abcdefABCDEF" for c in commit
            )
            if not commit_valid:
                blockers.append("framework CI evidence must bind an exact 40-hex commit")
        else:
            commit_valid = False
        if not framework_ci_artifacts["valid"]:
            blockers.append("framework CI must bind both general_craft artifact fingerprints")
        elif framework_ci_artifacts["matches_expected"] is not True:
            blockers.append("framework CI artifact fingerprint binding mismatch")
        framework_ci_binding_valid = (
            passed(ci)
            and commit_valid
            and framework_ci_artifacts["matches_expected"] is True
        )
        framework_ci_artifacts.update({
            "commit": commit if commit_valid else None,
            "binding_valid": framework_ci_binding_valid,
        })
        rollback_binding = evidence.get("rollback_binding")
        rollback_artifacts = _artifact_pair(rollback_binding, candidate_artifacts)
        rollback_ref = (
            str(rollback_binding.get("rollback_ref") or "").strip()
            if isinstance(rollback_binding, dict)
            else ""
        )
        if not rollback_ref:
            blockers.append("general_craft requires rollback_binding.rollback_ref")
        if not rollback_artifacts["valid"]:
            blockers.append("rollback binding must bind both general_craft artifact fingerprints")
        elif rollback_artifacts["matches_expected"] is not True:
            blockers.append("rollback artifact fingerprint binding mismatch")
        rollback_binding_valid = (
            bool(rollback_ref) and rollback_artifacts["matches_expected"] is True
        )
        rollback_artifacts.update({
            "rollback_ref": rollback_ref or None,
            "binding_valid": rollback_binding_valid,
        })
        if not nonempty_refs(evidence.get("provenance_refs")):
            blockers.append("general_craft requires provenance_refs")
        logical_works = nonempty_refs(evidence.get("logical_work_refs"))
        if len(logical_works) < 2:
            blockers.append("general_craft requires multiple distinct logical_work_refs")
        if not nonempty_refs(evidence.get("counterexample_refs")):
            blockers.append("general_craft requires counterexample_refs")
        profile_boundary = evidence.get("profile_boundary")
        if not isinstance(profile_boundary, dict) or not profile_boundary:
            blockers.append("general_craft requires a non-empty profile_boundary")
        public_corpus_version = str(evidence.get("public_corpus_version") or "").strip()
        if not public_corpus_version:
            blockers.append("general_craft requires public_corpus_version")
        if not blockers and semantic_review.get("ready") and independent_eval.get("ready"):
            status = "promotable"

    artifact_binding = {
        "required": scope == "general_craft",
        **candidate_artifacts,
        "semantic_review": semantic_review.get("artifact_binding"),
        "independent_eval": independent_eval.get("artifact_binding"),
        "framework_ci": framework_ci_artifacts,
        "rollback": rollback_artifacts,
        "all_bound": (
            candidate_artifacts["valid"]
            and semantic_review.get("valid") is True
            and semantic_review.get("artifact_binding", {}).get("matches_expected") is True
            and independent_eval.get("valid") is True
            and independent_eval.get("artifact_binding", {}).get("matches_expected") is True
            and framework_ci_binding_valid
            and rollback_binding_valid
            if scope == "general_craft"
            else None
        ),
    }

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
        "artifact_binding": artifact_binding,
        "semantic_evidence_count_threshold_used": False,
        "behavior_write_authority": False,
        "canon_write_authority": False,
        "durable_user_taste_write_authority": False,
        "next_action": (
            "authorized_manager_or_human_review" if status in {"promotable", "ready_for_activation"}
            else "repair_evidence_or_narrow_scope"
        ),
    }


def _semantic_binding(
    candidate_id: str,
    scope: str,
    mechanism: str,
    refs: list[str],
    *,
    result: str = "pass",
    supported_scope: str | None = None,
    candidate_artifact_fingerprint: str | None = None,
    craft_pack_fingerprint: str | None = None,
) -> dict[str, Any]:
    payload = {"candidate_id": candidate_id, "scope": scope, "mechanism": mechanism, "evidence_refs": refs}
    if candidate_artifact_fingerprint is not None:
        payload["candidate_artifact_fingerprint"] = candidate_artifact_fingerprint
    if craft_pack_fingerprint is not None:
        payload["craft_pack_fingerprint"] = craft_pack_fingerprint
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


def _eval_binding(
    candidate_id: str,
    scope: str,
    mechanism: str,
    *,
    result: str = "pass",
    candidate_artifact_fingerprint: str | None = None,
    craft_pack_fingerprint: str | None = None,
) -> dict[str, Any]:
    payload = {
        "candidate_id": candidate_id,
        "scope": scope,
        "mechanism": mechanism,
        "fixture": "bounded regression evidence",
    }
    if candidate_artifact_fingerprint is not None:
        payload["candidate_artifact_fingerprint"] = candidate_artifact_fingerprint
    if craft_pack_fingerprint is not None:
        payload["craft_pack_fingerprint"] = craft_pack_fingerprint
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
        "evidence": {"evidence_refs": refs, "contradiction_review": {"status": "pass"}},
    }
    reviewed_candidate["semantic_review_binding"] = _semantic_binding("UT-GOOD", "user_taste", "low narrator commentary", refs)
    reviewed_candidate["independent_eval_binding"] = _eval_binding("UT-GOOD", "user_taste", "low narrator commentary")
    reviewed = evaluate(reviewed_candidate)

    narrow = {
        "schema": SCHEMA, "candidate_id": "UT-NARROW", "scope": "user_taste", "mechanism": "low narrator commentary",
        "evidence": {"evidence_refs": refs, "contradiction_review": {"status": "pass"}},
        "semantic_review_binding": _semantic_binding("UT-NARROW", "user_taste", "low narrator commentary", refs, supported_scope="project"),
        "independent_eval_binding": _eval_binding("UT-NARROW", "user_taste", "low narrator commentary"),
    }
    narrowed = evaluate(narrow)

    caller_override = json.loads(json.dumps(reviewed_candidate))
    caller_override["semantic_review_binding"]["result"]["judgment"]["result"] = "fail"
    caller_override_result = evaluate(caller_override)

    gc_refs = ["SRC-A"]
    candidate_artifact_fingerprint = "sha256:" + "a" * 64
    craft_pack_fingerprint = "sha256:" + "b" * 64
    gc = {
        "schema": SCHEMA, "candidate_id": "GC-GOOD", "scope": "general_craft", "mechanism": "causal scene pressure",
        "candidate_artifact_fingerprint": candidate_artifact_fingerprint,
        "craft_pack_fingerprint": craft_pack_fingerprint,
        "evidence": {
            "evidence_refs": gc_refs,
            "version_target": "1.0.0-dev.0",
            "rollback_binding": {
                "rollback_ref": "git:baseline",
                "candidate_artifact_fingerprint": candidate_artifact_fingerprint,
                "craft_pack_fingerprint": craft_pack_fingerprint,
            },
            "framework_ci": {
                "conclusion": "success",
                "commit": "0123456789abcdef0123456789abcdef01234567",
                "candidate_artifact_fingerprint": candidate_artifact_fingerprint,
                "craft_pack_fingerprint": craft_pack_fingerprint,
            },
            "provenance_refs": ["SRC-A"],
            "logical_work_refs": ["WORK-A", "WORK-B"],
            "counterexample_refs": ["WORK-C"],
            "profile_boundary": {"profiles": ["serial"]},
            "public_corpus_version": "1.0.0",
        },
        "semantic_review_binding": _semantic_binding(
            "GC-GOOD", "general_craft", "causal scene pressure", gc_refs,
            candidate_artifact_fingerprint=candidate_artifact_fingerprint,
            craft_pack_fingerprint=craft_pack_fingerprint,
        ),
        "independent_eval_binding": _eval_binding(
            "GC-GOOD", "general_craft", "causal scene pressure",
            candidate_artifact_fingerprint=candidate_artifact_fingerprint,
            craft_pack_fingerprint=craft_pack_fingerprint,
        ),
    }
    general = evaluate(gc)
    gc_no_rollback = json.loads(json.dumps(gc)); gc_no_rollback["evidence"].pop("rollback_binding")
    general_no_rollback = evaluate(gc_no_rollback)

    ok = all([
        unreviewed["status"] == "blocked",
        reviewed["status"] == "ready_for_activation",
        narrowed["status"] == "blocked",
        caller_override_result["status"] == "blocked",
        general["status"] == "promotable",
        general["artifact_binding"]["all_bound"] is True,
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
        "general_craft_artifact_binding_required": general["artifact_binding"]["all_bound"] is True,
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
