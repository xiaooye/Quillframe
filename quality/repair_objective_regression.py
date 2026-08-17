#!/usr/bin/env python3
"""QA observability for repair-induced objective regression.

This module consumes an already-made semantic quality.compare judgment and
records whether a repair fixed its target while materially degrading a required
higher-order objective. It never decides literary quality itself.
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
if str(SEM) not in sys.path:
    sys.path.insert(0, str(SEM))

SCHEMA = "novelforge_repair_induced_objective_regression_v1"
TARGET = {"improved", "unchanged", "worse", "insufficient_evidence"}
PRESERVATION = {"preserved", "degraded", "materially_degraded", "insufficient_evidence"}
STATUS = {"observed", "not_observed", "inconclusive"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fp(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try: int(value[7:], 16)
    except ValueError as exc: raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name} required")
    return value.strip()


def _strings(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{name} must be string array")
    if not allow_empty and not value: raise ValueError(f"{name} must be non-empty")
    return [x.strip() for x in value]


def _payload(receipt: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in receipt.items() if k != "receipt_fingerprint"}


def record(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict): raise ValueError("repair objective regression payload must be object")
    target = payload.get("target_outcome")
    preservation = payload.get("objective_preservation")
    if target not in TARGET: raise ValueError("target_outcome invalid")
    if preservation not in PRESERVATION: raise ValueError("objective_preservation invalid")
    regressed = _strings(payload.get("regressed_dimensions", []), "regressed_dimensions")
    evidence = _strings(payload.get("semantic_evidence_refs", []), "semantic_evidence_refs", allow_empty=False)
    cycle = payload.get("repair_cycle")
    if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 1: raise ValueError("repair_cycle must be integer >= 1")

    if "insufficient_evidence" in {target, preservation}:
        status = "inconclusive"
    elif target == "improved" and preservation in {"degraded", "materially_degraded"}:
        status = "observed"
    else:
        status = "not_observed"
    if status == "observed" and not regressed:
        raise ValueError("observed objective regression requires regressed_dimensions")

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "subject_id": _nonempty(payload.get("subject_id"), "subject_id"),
        "incumbent_fingerprint": _sha(payload.get("incumbent_fingerprint"), "incumbent_fingerprint"),
        "challenger_fingerprint": _sha(payload.get("challenger_fingerprint"), "challenger_fingerprint"),
        "comparison_job_fingerprint": _sha(payload.get("comparison_job_fingerprint"), "comparison_job_fingerprint"),
        "comparison_result_fingerprint": _sha(payload.get("comparison_result_fingerprint"), "comparison_result_fingerprint"),
        "objective_envelope_fingerprint": _sha(payload.get("objective_envelope_fingerprint"), "objective_envelope_fingerprint"),
        "repair_target": _nonempty(payload.get("repair_target"), "repair_target"),
        "target_outcome": target,
        "objective_preservation": preservation,
        "regressed_dimensions": regressed,
        "semantic_evidence_refs": evidence,
        "repair_cycle": cycle,
        "detected_stage": _nonempty(payload.get("detected_stage"), "detected_stage"),
        "status": status,
        "repair_induced_objective_regression": status == "observed",
        "literary_judgment_performed_by_runtime": False,
        "authority": False,
        "permissions": {"canon_write": False, "framework_write": False, "durable_user_taste_write": False},
        "model_execution": False,
    }
    receipt["receipt_fingerprint"] = _fp(_payload(receipt))
    return receipt


def from_comparison(job: dict[str, Any], result: dict[str, Any], *, repair_cycle: int, detected_stage: str) -> dict[str, Any]:
    from semantic_worker_router import validate_result
    errors = validate_result(job, result)
    if errors: raise ValueError("invalid quality.compare evidence: " + "; ".join(errors))
    if result.get("status") != "completed": raise ValueError("quality.compare must be completed")
    input_obj = job.get("input", {})
    if input_obj.get("model_contract_id") != "quality.compare": raise ValueError("repair objective evidence requires quality.compare")
    payload = input_obj.get("payload", {})
    repair_context = payload.get("repair_context", {})
    envelope = repair_context.get("objective_envelope", {}) if isinstance(repair_context, dict) else {}
    incumbent = payload.get("incumbent", {})
    challenger = payload.get("challenger", {})
    judgment = result.get("judgment", {})
    return record({
        "subject_id": payload.get("evolution_subject_id"),
        "incumbent_fingerprint": incumbent.get("content_fingerprint"),
        "challenger_fingerprint": challenger.get("content_fingerprint"),
        "comparison_job_fingerprint": job.get("input_fingerprint"),
        "comparison_result_fingerprint": _fp(result),
        "objective_envelope_fingerprint": envelope.get("fingerprint"),
        "repair_target": repair_context.get("repair_target"),
        "target_outcome": judgment.get("target_outcome"),
        "objective_preservation": judgment.get("objective_preservation"),
        "regressed_dimensions": judgment.get("regressed_dimensions", []),
        "semantic_evidence_refs": judgment.get("evidence", []),
        "repair_cycle": repair_cycle,
        "detected_stage": detected_stage,
    })


def validate(receipt: Any) -> list[str]:
    if not isinstance(receipt, dict): return ["repair objective regression receipt must be object"]
    errors: list[str] = []
    if receipt.get("schema") != SCHEMA: errors.append("schema mismatch")
    try:
        rebuilt = record({
            "subject_id": receipt.get("subject_id"),
            "incumbent_fingerprint": receipt.get("incumbent_fingerprint"),
            "challenger_fingerprint": receipt.get("challenger_fingerprint"),
            "comparison_job_fingerprint": receipt.get("comparison_job_fingerprint"),
            "comparison_result_fingerprint": receipt.get("comparison_result_fingerprint"),
            "objective_envelope_fingerprint": receipt.get("objective_envelope_fingerprint"),
            "repair_target": receipt.get("repair_target"),
            "target_outcome": receipt.get("target_outcome"),
            "objective_preservation": receipt.get("objective_preservation"),
            "regressed_dimensions": receipt.get("regressed_dimensions"),
            "semantic_evidence_refs": receipt.get("semantic_evidence_refs"),
            "repair_cycle": receipt.get("repair_cycle"),
            "detected_stage": receipt.get("detected_stage"),
        })
    except ValueError as exc:
        return errors + [str(exc)]
    if receipt.get("status") not in STATUS: errors.append("status invalid")
    if receipt.get("receipt_fingerprint") != rebuilt["receipt_fingerprint"]: errors.append("receipt_fingerprint mismatch")
    if receipt.get("literary_judgment_performed_by_runtime") is not False: errors.append("runtime literary judgment must be false")
    return errors


def self_test() -> dict[str, Any]:
    base = {
        "subject_id":"CH-SYN", "incumbent_fingerprint":"sha256:"+"a"*64, "challenger_fingerprint":"sha256:"+"b"*64,
        "comparison_job_fingerprint":"sha256:"+"c"*64, "comparison_result_fingerprint":"sha256:"+"d"*64,
        "objective_envelope_fingerprint":"sha256:"+"e"*64, "repair_target":"remove synthetic banter", "repair_cycle":2,
        "detected_stage":"repair_comparison", "semantic_evidence_refs":["compare:e1"],
    }
    observed = record({**base,"target_outcome":"improved","objective_preservation":"materially_degraded","regressed_dimensions":["reader_question","character_energy"]})
    type_a = record({**base,"target_outcome":"unchanged","objective_preservation":"preserved","regressed_dimensions":[]})
    success = record({**base,"target_outcome":"improved","objective_preservation":"preserved","regressed_dimensions":[]})
    inconclusive = record({**base,"target_outcome":"insufficient_evidence","objective_preservation":"insufficient_evidence","regressed_dimensions":[]})
    checks = {
        "type_b_objective_regression_observed": observed["repair_induced_objective_regression"] is True,
        "type_a_target_not_fixed_not_mislabeled": type_a["repair_induced_objective_regression"] is False,
        "successful_repair_not_mislabeled": success["status"] == "not_observed",
        "insufficient_evidence_truthful": inconclusive["status"] == "inconclusive",
        "receipt_valid": not validate(observed),
        "runtime_does_not_judge_literature": observed["literary_judgment_performed_by_runtime"] is False,
        "model_execution": observed["model_execution"] is False,
    }
    return {"schema":SCHEMA,"repair_induced_objective_regression_contract":"PASS" if all(checks.values()) else "FAIL","checks":checks,"authority":False,"model_execution":False}


def main() -> int:
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="command",required=True); s.add_parser("self-test")
    r=s.add_parser("record"); r.add_argument("--input",required=True); r.add_argument("--output")
    a=p.parse_args()
    if a.command=="self-test":
        out=self_test(); print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out["repair_induced_objective_regression_contract"]=="PASS" else 1
    out=record(json.loads(Path(a.input).read_text(encoding="utf-8"))); text=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if a.output: Path(a.output).write_text(text,encoding="utf-8")
    else: print(text,end="")
    return 0


if __name__=="__main__": raise SystemExit(main())
