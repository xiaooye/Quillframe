#!/usr/bin/env python3
"""Deterministic pre-independent qualification for Quillframe production candidates.

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

SCHEMA = "quillframe_candidate_qualification_v1"
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
    dimensions: dict[str, str] | None = None
    if gate == "self_audit":
        raw_dimensions = judgment.get("dimensions")
        if not isinstance(raw_dimensions, dict):
            raise ValueError("self_audit dimensions must be object")
        dimension_keys = {"surface", "regression", "character_or_ownership", "natural_realization", "cluster"}
        if set(raw_dimensions) != dimension_keys:
            raise ValueError("self_audit dimensions must cover exact required dimension set")
        allowed_dimension_statuses = {"pass", "fail", "insufficient_evidence", "not_applicable"}
        if any(value not in allowed_dimension_statuses for value in raw_dimensions.values()):
            raise ValueError("self_audit dimension status invalid")
        dimensions = {key: str(raw_dimensions[key]) for key in sorted(raw_dimensions)}
        failed_dimensions = [key for key, value in dimensions.items() if value == "fail"]
        insufficient_dimensions = [key for key, value in dimensions.items() if value == "insufficient_evidence"]
        if derived == "pass" and (failed_dimensions or insufficient_dimensions):
            raise ValueError("self_audit pass contradicts failed/insufficient dimension")
        if derived == "fail" and not failed_dimensions:
            raise ValueError("self_audit fail requires at least one failed dimension")
        if derived == "pending" and not insufficient_dimensions:
            raise ValueError("self_audit insufficient_evidence requires at least one insufficient dimension")
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
        "dimensions": dimensions,
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


def _repair_preservation_gate(raw: Any, *, candidate: str, subject_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("repair_preservation gate object required for repair_cycle > 0")
    declared = raw.get("status")
    if declared not in GATE_STATUSES:
        raise ValueError("repair_preservation.status must be pass|fail|pending")
    if declared == "pending":
        return {"gate":"repair_preservation","status":"pending","contract_id":"quality.compare","job_fingerprint":None,"result_fingerprint":None,"objective_envelope_fingerprint":None,"target_outcome":"insufficient_evidence","objective_preservation":"insufficient_evidence","reader_value":"insufficient_evidence","character_relationship_energy":"insufficient_evidence","outcome_class":"inconclusive","evidence_refs":[]}
    binding=raw.get("semantic_binding")
    if not isinstance(binding,dict) or not isinstance(binding.get("job"),dict) or not isinstance(binding.get("result"),dict):
        raise ValueError("repair_preservation semantic_binding requires job and result")
    job=binding["job"]; result=binding["result"]
    validate_registered_job, validate_result = _load_semantic_runtime()
    job_errors=validate_registered_job(job)
    if job_errors: raise ValueError("repair_preservation registered job invalid: "+"; ".join(job_errors))
    result_errors=validate_result(job,result)
    if result_errors: raise ValueError("repair_preservation semantic result invalid: "+"; ".join(result_errors))
    if result.get("status")!="completed": raise ValueError("repair_preservation semantic result must be completed")
    input_obj=job.get("input",{}); payload=input_obj.get("payload",{}) if isinstance(input_obj,dict) else {}
    if input_obj.get("model_contract_id")!="quality.compare": raise ValueError("repair_preservation requires quality.compare")
    if payload.get("evolution_subject_id")!=subject_id: raise ValueError("repair_preservation subject mismatch")
    challenger=payload.get("challenger",{}); repair_context=payload.get("repair_context",{})
    if not isinstance(challenger,dict) or challenger.get("content_fingerprint")!=candidate: raise ValueError("repair_preservation challenger fingerprint mismatch")
    envelope=repair_context.get("objective_envelope",{}) if isinstance(repair_context,dict) else {}
    envelope_fp=envelope.get("fingerprint") if isinstance(envelope,dict) else None
    _sha(envelope_fp,"repair_preservation objective_envelope_fingerprint")
    judgment=result.get("judgment",{})
    target=judgment.get("target_outcome"); preservation=judgment.get("objective_preservation"); reader=judgment.get("reader_value"); energy=judgment.get("character_relationship_energy"); outcome=judgment.get("outcome_class")
    if "insufficient_evidence" in {target,preservation,reader,energy} or outcome=="inconclusive": derived="pending"
    elif outcome=="successful_repair" and target=="improved" and preservation=="preserved" and reader in {"improved","unchanged"} and energy in {"preserved","not_applicable"}: derived="pass"
    else: derived="fail"
    if declared!=derived: raise ValueError("repair_preservation.status contradicts semantic comparison")
    return {"gate":"repair_preservation","status":derived,"contract_id":"quality.compare","job_fingerprint":job.get("input_fingerprint"),"result_fingerprint":_result_fingerprint(result),"objective_envelope_fingerprint":envelope_fp,"target_outcome":target,"objective_preservation":preservation,"reader_value":reader,"character_relationship_energy":energy,"outcome_class":outcome,"evidence_refs":_string_list(judgment.get("evidence",[]),"repair_preservation.evidence_refs")}


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
    preservation = _repair_preservation_gate(payload.get("repair_preservation"), candidate=candidate, subject_id=subject_id) if repair_cycle > 0 else {"gate":"repair_preservation","status":"not_applicable","contract_id":"quality.compare","job_fingerprint":None,"result_fingerprint":None,"objective_envelope_fingerprint":None,"target_outcome":"not_applicable","objective_preservation":"not_applicable","reader_value":"not_applicable","character_relationship_energy":"not_applicable","outcome_class":"not_applicable","evidence_refs":[]}

    gates = [self_audit, reader, continuity, preservation]
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
        "surface_audit_status": (self_audit.get("dimensions") or {}).get("surface", self_audit["status"]),
        "regression_audit_status": (self_audit.get("dimensions") or {}).get("regression", self_audit["status"]),
        "character_or_ownership_status": (self_audit.get("dimensions") or {}).get("character_or_ownership", self_audit["status"]),
        "natural_realization_status": (self_audit.get("dimensions") or {}).get("natural_realization", self_audit["status"]),
        "cluster_audit_status": (self_audit.get("dimensions") or {}).get("cluster", self_audit["status"]),
        "reader_engagement_status": reader["status"],
        "continuity_status": continuity["status"],
        "repair_preservation_status": preservation["status"],
        "repair_target_status": preservation["target_outcome"],
        "objective_preservation_status": preservation["objective_preservation"],
        "repair_reader_value": preservation["reader_value"],
        "repair_character_relationship_energy": preservation["character_relationship_energy"],
        "repair_outcome_class": preservation["outcome_class"],
        "objective_envelope_fingerprint": preservation["objective_envelope_fingerprint"],
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
    for field in ("surface_audit_status", "regression_audit_status", "character_or_ownership_status", "natural_realization_status", "cluster_audit_status", "reader_engagement_status", "continuity_status", "repair_preservation_status"):
        if receipt.get(field) not in {"pass", "fail", "pending", "insufficient_evidence", "not_applicable"}:
            errors.append(f"qualification {field} invalid")
    if receipt.get("repair_target_status") not in {"improved","unchanged","worse","insufficient_evidence","not_applicable"}: errors.append("qualification repair_target_status invalid")
    if receipt.get("objective_preservation_status") not in {"preserved","degraded","materially_degraded","insufficient_evidence","not_applicable"}: errors.append("qualification objective_preservation_status invalid")
    if receipt.get("repair_reader_value") not in {"improved","unchanged","degraded","insufficient_evidence","not_applicable"}: errors.append("qualification repair_reader_value invalid")
    if receipt.get("repair_character_relationship_energy") not in {"preserved","degraded","not_applicable","insufficient_evidence"}: errors.append("qualification repair_character_relationship_energy invalid")
    if receipt.get("repair_outcome_class") not in {"target_not_fixed","objective_regression","successful_repair","inconclusive","not_applicable"}: errors.append("qualification repair_outcome_class invalid")
    cycle=receipt.get("repair_cycle")
    if isinstance(cycle,int) and not isinstance(cycle,bool) and cycle>0:
        if receipt.get("repair_preservation_status")!="pass": errors.append("repaired candidate requires passing repair_preservation")
        try: _sha(receipt.get("objective_envelope_fingerprint"),"objective_envelope_fingerprint")
        except ValueError as exc: errors.append(str(exc))
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
        "dimensions": {"surface":"pass","regression":"pass","character_or_ownership":"pass","natural_realization":"pass","cluster":"pass"},
        "findings": [],
        "evidence_refs": ["candidate:whole"],
    })
    fail_audit = _semantic_binding("quality.candidate_self_audit", subject, fp, {
        "confidence": 0.9,
        "result": "fail",
        "report": "A clustered over-authored dialogue rhythm remains.",
        "dimensions": {"surface":"fail","regression":"fail","character_or_ownership":"fail","natural_realization":"fail","cluster":"fail"},
        "findings": [{
            "finding_id": "SELF-F-1",
            "mechanism_id": "HF-29",
            "severity": "cluster",
            "scope": "block",
            "repair_owner": "character",
            "blocking": True,
            "report": "Purpose is valid but realization is punchline-first and stacked.",
            "function_assessment": "pass",
            "ownership_assessment": "fail",
            "natural_realization_assessment": "fail",
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
        "repair_cycle": 0,
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
    inconsistent_audits = [
        ("pass_with_failed_dimension_rejected", pass_audit, "pass",
         {"dimensions": {**pass_audit["result"]["judgment"]["dimensions"], "surface": "fail"}},
         "pass contradicts failed/insufficient dimension"),
        ("pass_with_insufficient_dimension_rejected", pass_audit, "pass",
         {"dimensions": {**pass_audit["result"]["judgment"]["dimensions"], "surface": "insufficient_evidence"}},
         "pass contradicts failed/insufficient dimension"),
        ("pass_with_blocking_finding_rejected", pass_audit, "pass",
         {"findings": fail_audit["result"]["judgment"]["findings"]},
         "pass cannot contain blocking findings"),
        ("fail_without_failed_dimension_rejected", fail_audit, "fail",
         {"dimensions": pass_audit["result"]["judgment"]["dimensions"]},
         "fail requires at least one failed dimension"),
        ("fail_without_blocking_finding_rejected", fail_audit, "fail", {"findings": []},
         "fail requires at least one blocking finding"),
        ("insufficient_audit_cannot_be_declared_pass", pass_audit, "pass",
         {"result": "insufficient_evidence"},
         "status contradicts semantic result"),
    ]
    consistency_checks: dict[str, bool] = {}
    for name, seed, declared, changes, expected_error in inconsistent_audits:
        binding = json.loads(json.dumps(seed))
        binding["result"]["judgment"].update(changes)
        try:
            evaluate({
                "candidate_fingerprint": fp, "subject_id": subject, "repair_cycle": 0,
                "self_audit": {"status": declared, "semantic_binding": binding},
                "reader_engagement": {"status": "pass", "semantic_binding": reader},
                "continuity": continuity,
            })
        except ValueError as exc:
            consistency_checks[name] = expected_error in str(exc)
        else:
            consistency_checks[name] = False
    uncertain_audit = json.loads(json.dumps(pass_audit))
    uncertain_audit["result"]["judgment"].update({
        "result": "insufficient_evidence",
        "dimensions": {**pass_audit["result"]["judgment"]["dimensions"], "regression": "insufficient_evidence"},
    })
    uncertain = evaluate({
        "candidate_fingerprint": fp, "subject_id": subject, "repair_cycle": 0,
        "self_audit": {"status": "pending", "semantic_binding": uncertain_audit},
        "reader_engagement": {"status": "pass", "semantic_binding": reader},
        "continuity": continuity,
    })
    consistency_checks["consistent_insufficient_audit_remains_pending"] = uncertain["qualification_status"] == "awaiting_semantic"
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

    from objective_envelope import build as build_objective_envelope
    from semantic_worker_router import make_contract_job
    envelope=build_objective_envelope({"subject_id":subject,"run_id":"RUN-SELF","authority_cutoff":"synthetic","objective_items":[{"id":"OBJ-SELF","category":"reader","statement":"Preserve active pressure.","source_refs":["plan:self"]}],"must_preserve":["active pressure"],"derived_from_rejected_realization":False})
    compare_payload={"evolution_run_id":"RUN-SELF","evolution_subject_id":subject,"comparison_id":"CMP-SELF","incumbent":{"candidate_id":"C0","content_fingerprint":"sha256:"+"0"*64},"challenger":{"candidate_id":"C1","content_fingerprint":fp,"repair_owner":"surface"},"repair_context":{"repair_target":"remove synthetic realization","objective_envelope":envelope}}
    compare_job=make_contract_job("quality.compare","CMP-SELF",compare_payload,source_session_id="SES-MANAGER")
    def compare_result(outcome:str)->dict[str,Any]:
        if outcome=="successful_repair": judgment={"confidence":.9,"winner":"challenger","reason":"target fixed; objective preserved","target_outcome":"improved","objective_preservation":"preserved","reader_value":"unchanged","character_relationship_energy":"preserved","outcome_class":"successful_repair","repaired_findings":["HF-SELF"],"introduced_regressions":[],"regressed_dimensions":[],"preserved_strengths":["active pressure"],"evidence":["candidate:compare"]}
        else: judgment={"confidence":.9,"winner":"incumbent","reason":"target fixed but pressure collapsed","target_outcome":"improved","objective_preservation":"materially_degraded","reader_value":"degraded","character_relationship_energy":"preserved","outcome_class":"objective_regression","repaired_findings":["HF-SELF"],"introduced_regressions":["reader_pressure"],"regressed_dimensions":["reader_pressure"],"preserved_strengths":[],"evidence":["candidate:compare"]}
        return {"job_id":compare_job["job_id"],"subject_id":compare_job["subject_id"],"kind":compare_job["kind"],"input_fingerprint":compare_job["input_fingerprint"],"status":"completed","worker":{"provider":"self_test","model_or_reviewer":"comparison-fixture"},"judgment":judgment,"proposals":[],"errors":[]}
    repaired_ok=evaluate({"candidate_fingerprint":fp,"subject_id":subject,"repair_cycle":1,"self_audit":{"status":"pass","semantic_binding":pass_audit},"reader_engagement":{"status":"pass","semantic_binding":reader},"continuity":continuity,"repair_preservation":{"status":"pass","semantic_binding":{"job":compare_job,"result":compare_result("successful_repair")}}})
    repaired_regression=evaluate({"candidate_fingerprint":fp,"subject_id":subject,"repair_cycle":1,"self_audit":{"status":"pass","semantic_binding":pass_audit},"reader_engagement":{"status":"pass","semantic_binding":reader},"continuity":continuity,"repair_preservation":{"status":"fail","semantic_binding":{"job":compare_job,"result":compare_result("objective_regression")}}})
    missing_preservation_guard=False
    try: evaluate({"candidate_fingerprint":fp,"subject_id":subject,"repair_cycle":1,"self_audit":{"status":"pass","semantic_binding":pass_audit},"reader_engagement":{"status":"pass","semantic_binding":reader},"continuity":continuity})
    except ValueError: missing_preservation_guard=True

    checks = {
        **consistency_checks,
        "qualified_exact_candidate": not validate_qualification_receipt(qualified, candidate_fingerprint=fp, subject_id=subject),
        "blocking_self_audit_requires_repair": failed["qualification_status"] == "repair_required" and bool(failed["blocking_findings"]),
        "pending_semantic_is_not_qualified": pending["qualification_status"] == "awaiting_semantic" and not pending["qualified_for_independent"],
        "material_candidate_change_stales_receipt": any("candidate fingerprint mismatch" in x for x in stale_errors),
        "receipt_tamper_detected": any("receipt_fingerprint mismatch" in x for x in tamper_errors),
        "qualification_is_non_independent": qualified["independent"] is False,
        "runtime_does_not_reinterpret_semantics": qualified["semantic_content_reinterpreted_by_runtime"] is False,
        "repair_success_can_qualify": repaired_ok["qualification_status"]=="qualified_for_independent" and repaired_ok["objective_preservation_status"]=="preserved",
        "repair_objective_regression_blocks": repaired_regression["qualification_status"]=="repair_required" and repaired_regression["repair_outcome_class"]=="objective_regression",
        "material_repair_missing_preservation_blocks": missing_preservation_guard,
        "baseline_preservation_not_applicable": qualified["repair_preservation_status"]=="not_applicable",
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
    parser = argparse.ArgumentParser(description="Quillframe pre-independent candidate qualification")
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
