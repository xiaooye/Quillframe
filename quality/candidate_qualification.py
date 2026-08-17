#!/usr/bin/env python3
"""Deterministic pre-independent qualification for NovelForge production candidates.

Literary judgment is supplied by registered semantic contracts. This module only
validates exact candidate/subject bindings, semantic result provenance, required
stage status, blocking finding state and the resulting fingerprint-bound receipt.
It is explicitly non-independent and cannot satisfy the mandatory production
review gate by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "harness" / "semantic_workers"

SCHEMA = "novelforge_candidate_qualification_v1"
STATUSES = {"awaiting_semantic", "repair_required", "qualified_for_independent"}
GATE_STATUSES = {"pass", "fail", "pending"}
REGISTERED_GATES = {
    "self_audit": "quality.candidate_self_audit",
    "reader_engagement": "reader.engagement_audit",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _string_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f"{name} must be string array")
    return list(value)


def _result_fingerprint(result: dict[str, Any]) -> str:
    return _fp(result)


def _load_semantic_runtime() -> tuple[Any, Any]:
    # Local import avoids a module-import cycle: semantic_worker_router may use
    # validate_qualification_receipt as its production-review dispatch guard.
    if str(SEM) not in sys.path:
        sys.path.insert(0, str(SEM))
    from registered_contract_binding import validate_registered_job  # type: ignore
    from semantic_worker_router import validate_result  # type: ignore
    return validate_registered_job, validate_result


def _semantic_gate(raw: Any, *, gate: str, candidate: str, subject_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{gate} gate object required")
    declared = raw.get("status")
    if declared not in GATE_STATUSES:
        raise ValueError(f"{gate}.status must be pass|fail|pending")
    if declared == "pending":
        return {
            "gate": gate,
            "status": "pending",
            "contract_id": REGISTERED_GATES[gate],
            "job_fingerprint": None,
            "result_fingerprint": None,
            "evidence_refs": _string_list(raw.get("evidence_refs", []), f"{gate}.evidence_refs"),
            "blocking_findings": [],
        }

    binding = raw.get("semantic_binding")
    if not isinstance(binding, dict):
        raise ValueError(f"{gate}.semantic_binding required for pass/fail")
    job = binding.get("job")
    result = binding.get("result")
    if not isinstance(job, dict) or not isinstance(result, dict):
        raise ValueError(f"{gate}.semantic_binding requires job and result")

    validate_registered_job, validate_result = _load_semantic_runtime()
    job_errors = validate_registered_job(job)
    if job_errors:
        raise ValueError(f"{gate} registered job invalid: " + "; ".join(job_errors))
    result_errors = validate_result(job, result)
    if result_errors:
        raise ValueError(f"{gate} semantic result invalid: " + "; ".join(result_errors))
    if result.get("status") != "completed":
        raise ValueError(f"{gate} semantic result must be completed")

    input_obj = job.get("input")
    payload = input_obj.get("payload") if isinstance(input_obj, dict) else None
    if not isinstance(payload, dict):
        raise ValueError(f"{gate} semantic payload required")
    expected = REGISTERED_GATES[gate]
    if input_obj.get("model_contract_id") != expected:
        raise ValueError(f"{gate} requires {expected}")
    if payload.get("candidate_fingerprint") != candidate:
        raise ValueError(f"{gate} candidate fingerprint mismatch")
    if job.get("subject_id") != subject_id:
        raise ValueError(f"{gate} subject_id mismatch")

    provenance = job.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("source") != "model_contract_pack":
        raise ValueError(f"{gate} must come from model_contract_pack")
    if provenance.get("independent_gate") is not False:
        raise ValueError(f"{gate} must remain non-independent")

    judgment = result.get("judgment")
    if not isinstance(judgment, dict):
        raise ValueError(f"{gate} judgment required")
    semantic_result = judgment.get("result")
    if semantic_result == "insufficient_evidence":
        derived = "pending"
    elif semantic_result in {"pass", "fail"}:
        derived = semantic_result
    else:
        raise ValueError(f"{gate} judgment.result invalid")
    if declared != derived:
        raise ValueError(f"{gate}.status contradicts semantic result")

    blockers: list[dict[str, Any]] = []
    if gate == "self_audit":
        findings = judgment.get("findings", [])
        if not isinstance(findings, list):
            raise ValueError("self_audit findings must be array")
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                raise ValueError("self_audit finding must be object")
            if finding.get("blocking") is True:
                blockers.append({
                    "finding_id": _nonempty(finding.get("finding_id"), f"self_audit.findings[{index}].finding_id"),
                    "mechanism_id": _nonempty(finding.get("mechanism_id"), f"self_audit.findings[{index}].mechanism_id"),
                    "scope": _nonempty(finding.get("scope"), f"self_audit.findings[{index}].scope"),
                    "repair_owner": _nonempty(finding.get("repair_owner"), f"self_audit.findings[{index}].repair_owner"),
                    "evidence_refs": _string_list(finding.get("evidence_refs", []), f"self_audit.findings[{index}].evidence_refs"),
                })
        if derived == "pass" and blockers:
            raise ValueError("self_audit pass cannot contain blocking findings")
        if derived == "fail" and not blockers:
            raise ValueError("self_audit fail requires at least one blocking finding")

    return {
        "gate": gate,
        "status": derived,
        "contract_id": expected,
        "job_fingerprint": job.get("input_fingerprint"),
        "result_fingerprint": _result_fingerprint(result),
        "evidence_refs": _string_list(judgment.get("evidence_refs", raw.get("evidence_refs", [])), f"{gate}.evidence_refs"),
        "blocking_findings": blockers,
    }


def _continuity_gate(raw: Any, *, candidate: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("continuity gate object required")
    status = raw.get("status")
    if status not in GATE_STATUSES:
        raise ValueError("continuity.status must be pass|fail|pending")
    receipt_fp = raw.get("receipt_fingerprint")
    if status != "pending":
        receipt_fp = _sha(receipt_fp, "continuity.receipt_fingerprint")
    elif receipt_fp is not None:
        receipt_fp = _sha(receipt_fp, "continuity.receipt_fingerprint")
    gate_candidate = raw.get("candidate_fingerprint")
    if gate_candidate is not None and _sha(gate_candidate, "continuity.candidate_fingerprint") != candidate:
        raise ValueError("continuity candidate fingerprint mismatch")
    return {
        "gate": "continuity",
        "status": status,
        "receipt_fingerprint": receipt_fp,
        "evidence_refs": _string_list(raw.get("evidence_refs", []), "continuity.evidence_refs"),
    }


def _receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in receipt.items() if k != "receipt_fingerprint"}


def evaluate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("qualification payload must be object")
    candidate = _sha(payload.get("candidate_fingerprint"), "candidate_fingerprint")
    subject_id = _nonempty(payload.get("subject_id"), "subject_id")
    repair_cycle = payload.get("repair_cycle", 0)
    if isinstance(repair_cycle, bool) or not isinstance(repair_cycle, int) or repair_cycle < 0:
        raise ValueError("repair_cycle must be non-negative integer")

    self_audit = _semantic_gate(payload.get("self_audit"), gate="self_audit", candidate=candidate, subject_id=subject_id)
    reader = _semantic_gate(payload.get("reader_engagement"), gate="reader_engagement", candidate=candidate, subject_id=subject_id)
    continuity = _continuity_gate(payload.get("continuity"), candidate=candidate)

    gates = [self_audit, reader, continuity]
    pending = [g["gate"] for g in gates if g["status"] == "pending"]
    failed = [g["gate"] for g in gates if g["status"] == "fail"]
    blockers = list(self_audit.get("blocking_findings", []))

    if pending:
        status = "awaiting_semantic"
    elif failed or blockers:
        status = "repair_required"
    else:
        status = "qualified_for_independent"

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "candidate_fingerprint": candidate,
        "repair_cycle": repair_cycle,
        "qualification_status": status,
        "gates": gates,
        "pending_gates": pending,
        "failed_gates": failed,
        "blocking_findings": blockers,
        "qualified_for_independent": status == "qualified_for_independent",
        "independent": False,
        "semantic_content_reinterpreted_by_runtime": False,
        "provenance": {
            "source": "candidate_qualification_runtime",
            "exact_candidate_binding": True,
            "registered_semantic_results_required": True,
        },
        "authority": False,
        "permissions": {
            "canon_write": False,
            "framework_write": False,
            "durable_user_taste_write": False,
        },
        "model_execution": False,
    }
    receipt["receipt_fingerprint"] = _fp(_receipt_payload(receipt))
    return receipt


def validate_qualification_receipt(
    receipt: Any,
    *,
    candidate_fingerprint: str | None = None,
    subject_id: str | None = None,
    require_qualified: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return ["qualification receipt must be object"]
    if receipt.get("schema") != SCHEMA:
        errors.append("qualification schema mismatch")
    candidate = receipt.get("candidate_fingerprint")
    try:
        _sha(candidate, "candidate_fingerprint")
    except ValueError as exc:
        errors.append(str(exc))
    if candidate_fingerprint is not None and candidate != candidate_fingerprint:
        errors.append("qualification candidate fingerprint mismatch")
    if subject_id is not None and receipt.get("subject_id") != subject_id:
        errors.append("qualification subject_id mismatch")
    status = receipt.get("qualification_status")
    if status not in STATUSES:
        errors.append("qualification status invalid")
    blockers = receipt.get("blocking_findings")
    if not isinstance(blockers, list):
        errors.append("qualification blocking_findings must be array")
        blockers = []
    pending = receipt.get("pending_gates")
    failed = receipt.get("failed_gates")
    if not isinstance(pending, list) or not isinstance(failed, list):
        errors.append("qualification pending_gates/failed_gates must be arrays")
        pending = pending if isinstance(pending, list) else []
        failed = failed if isinstance(failed, list) else []
    if receipt.get("independent") is not False:
        errors.append("qualification must be independent=false")
    if receipt.get("authority") is not False:
        errors.append("qualification must be non-authoritative")
    permissions = receipt.get("permissions")
    if not isinstance(permissions, dict) or any(
        permissions.get(k) is not False for k in ("canon_write", "framework_write", "durable_user_taste_write")
    ):
        errors.append("qualification write permissions must be false")
    expected_fp = _fp(_receipt_payload(receipt))
    if receipt.get("receipt_fingerprint") != expected_fp:
        errors.append("qualification receipt_fingerprint mismatch")
    if status == "qualified_for_independent":
        if blockers:
            errors.append("qualified receipt cannot contain blocking findings")
        if pending:
            errors.append("qualified receipt cannot contain pending gates")
        if failed:
            errors.append("qualified receipt cannot contain failed gates")
        if receipt.get("qualified_for_independent") is not True:
            errors.append("qualified flag mismatch")
    elif receipt.get("qualified_for_independent") is not False:
        errors.append("unqualified receipt must set qualified_for_independent=false")
    if require_qualified and status != "qualified_for_independent":
        errors.append("candidate is not qualified_for_independent")
    return errors


def _semantic_binding(contract_id: str, subject_id: str, fp: str, judgment: dict[str, Any]) -> dict[str, Any]:
    if str(SEM) not in sys.path:
        sys.path.insert(0, str(SEM))
    from semantic_worker_router import make_contract_job  # type: ignore

    payload: dict[str, Any] = {"candidate_fingerprint": fp, "candidate_text": "Bounded candidate."}
    if contract_id == "quality.candidate_self_audit":
        payload.update({
            "rule_material": [{"id": "HF-SELF", "authority": "framework", "statement": "Keep realization functionally owned and natural."}],
            "profile_constraints": [],
        })
    elif contract_id == "reader.engagement_audit":
        payload["reader_grip"] = "very_high"
    job = make_contract_job(contract_id, subject_id, payload, source_session_id="SES-MANAGER")
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "self_test", "model_or_reviewer": "manager-semantic-fixture"},
        "judgment": judgment,
        "proposals": [],
        "errors": [],
    }
    return {"job": job, "result": result}


def self_test() -> dict[str, Any]:
    fp = "sha256:" + "a" * 64
    subject = "CH-SELF"
    pass_audit = _semantic_binding("quality.candidate_self_audit", subject, fp, {
        "confidence": 0.9,
        "result": "pass",
        "report": "No material blocking realization defect remains.",
        "findings": [],
        "evidence_refs": ["candidate:whole"],
    })
    fail_audit = _semantic_binding("quality.candidate_self_audit", subject, fp, {
        "confidence": 0.9,
        "result": "fail",
        "report": "A clustered over-authored dialogue rhythm remains.",
        "findings": [{
            "finding_id": "SELF-F-1",
            "mechanism_id": "HF-29",
            "severity": "cluster",
            "scope": "block",
            "repair_owner": "character",
            "blocking": True,
            "report": "Purpose is valid but realization is punchline-first and stacked.",
            "evidence_refs": ["candidate:block-1"],
        }],
        "evidence_refs": ["candidate:block-1"],
    })
    reader = _semantic_binding("reader.engagement_audit", subject, fp, {
        "confidence": 0.9,
        "result": "pass",
        "report": "The candidate sustains reader interest.",
        "strongest_positive": "Active social pressure.",
        "strongest_problem": None,
        "evidence_refs": ["candidate:whole"],
    })
    continuity = {
        "status": "pass",
        "candidate_fingerprint": fp,
        "receipt_fingerprint": "sha256:" + "c" * 64,
        "evidence_refs": ["continuity:self"],
    }

    qualified = evaluate({
        "candidate_fingerprint": fp,
        "subject_id": subject,
        "repair_cycle": 1,
        "self_audit": {"status": "pass", "semantic_binding": pass_audit},
        "reader_engagement": {"status": "pass", "semantic_binding": reader},
        "continuity": continuity,
    })
    failed = evaluate({
        "candidate_fingerprint": fp,
        "subject_id": subject,
        "repair_cycle": 0,
        "self_audit": {"status": "fail", "semantic_binding": fail_audit},
        "reader_engagement": {"status": "pass", "semantic_binding": reader},
        "continuity": continuity,
    })
    pending = evaluate({
        "candidate_fingerprint": fp,
        "subject_id": subject,
        "repair_cycle": 0,
        "self_audit": {"status": "pending", "evidence_refs": ["queue:self-audit"]},
        "reader_engagement": {"status": "pass", "semantic_binding": reader},
        "continuity": continuity,
    })
    stale_errors = validate_qualification_receipt(
        qualified,
        candidate_fingerprint="sha256:" + "b" * 64,
        subject_id=subject,
    )
    tampered = json.loads(json.dumps(qualified))
    tampered["repair_cycle"] = 99
    tamper_errors = validate_qualification_receipt(tampered, candidate_fingerprint=fp, subject_id=subject)

    checks = {
        "qualified_exact_candidate": not validate_qualification_receipt(qualified, candidate_fingerprint=fp, subject_id=subject),
        "blocking_self_audit_requires_repair": failed["qualification_status"] == "repair_required" and bool(failed["blocking_findings"]),
        "pending_semantic_is_not_qualified": pending["qualification_status"] == "awaiting_semantic" and not pending["qualified_for_independent"],
        "material_candidate_change_stales_receipt": any("candidate fingerprint mismatch" in x for x in stale_errors),
        "receipt_tamper_detected": any("receipt_fingerprint mismatch" in x for x in tamper_errors),
        "qualification_is_non_independent": qualified["independent"] is False,
        "runtime_does_not_reinterpret_semantics": qualified["semantic_content_reinterpreted_by_runtime"] is False,
        "no_write_authority": not any(qualified["permissions"].values()),
        "model_execution": qualified["model_execution"] is False,
    }
    return {
        "schema": SCHEMA,
        "candidate_qualification_contract": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="NovelForge pre-independent candidate qualification")
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--input", required=True)
    ev.add_argument("--output")
    vr = sub.add_parser("validate")
    vr.add_argument("--input", required=True)
    vr.add_argument("--candidate-fingerprint")
    vr.add_argument("--subject-id")
    vr.add_argument("--allow-unqualified", action="store_true")
    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "self-test":
        out = self_test()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["candidate_qualification_contract"] == "PASS" else 1

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.command == "evaluate":
        out = evaluate(raw)
        text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0

    errors = validate_qualification_receipt(
        raw,
        candidate_fingerprint=args.candidate_fingerprint,
        subject_id=args.subject_id,
        require_qualified=not args.allow_unqualified,
    )
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
