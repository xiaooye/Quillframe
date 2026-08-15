#!/usr/bin/env python3
"""Fail-closed binding checks for jobs that claim a registered model contract.

`semantic_worker_router.validate_job` intentionally accepts generic ad-hoc jobs
for blind evaluation and diagnostics. Production consumers need a stronger
question: if a job claims `input.model_contract_id`, is it *exactly* the job
shape defined by that registered contract rather than a manager-authored rubric
wearing a registered contract name?

This module answers only that deterministic binding question. It performs no
literary judgment and grants no authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from semantic_worker_router import (
    HERE,
    load_contract_registry,
    resolve_contract_registry,
    validate_contract_input,
    validate_job,
)

SCHEMA = "novelforge_registered_contract_binding_v1"


def validate_registered_job(job: dict[str, Any]) -> list[str]:
    errors = validate_job(job)
    if errors:
        return list(errors)

    input_obj = job.get("input")
    if not isinstance(input_obj, dict):
        return ["registered contract job input must be object"]
    contract_id = input_obj.get("model_contract_id")
    if not isinstance(contract_id, str) or not contract_id:
        return ["registered contract job requires input.model_contract_id"]

    try:
        registry_path, pack_id = resolve_contract_registry(contract_id)
        registry = load_contract_registry(registry_path)
    except ValueError as exc:
        return [f"registered contract resolution failed: {exc}"]
    contract = registry["contracts"].get(contract_id)
    if not isinstance(contract, dict):
        return [f"registered contract unavailable: {contract_id}"]

    payload = input_obj.get("payload")
    if not isinstance(payload, dict):
        errors.append("registered contract payload must be object")
    else:
        errors += validate_contract_input(contract_id, contract, payload)

    expected_input_keys = {"model_contract_id", "model_contract_version", "purpose", "payload"}
    if isinstance(contract.get("default_personas"), dict):
        expected_input_keys.add("default_personas")
    extra_input = sorted(set(input_obj) - expected_input_keys)
    missing_input = sorted(expected_input_keys - set(input_obj))
    if extra_input:
        errors.append("registered contract input has unexpected fields: " + ", ".join(extra_input))
    if missing_input:
        errors.append("registered contract input missing fields: " + ", ".join(missing_input))

    if job.get("kind") != contract.get("kind"):
        errors.append("registered contract kind mismatch")
    if input_obj.get("model_contract_version") != registry.get("version"):
        errors.append("registered contract version mismatch")
    if input_obj.get("purpose") != contract.get("purpose"):
        errors.append("registered contract purpose mismatch")
    if isinstance(contract.get("default_personas"), dict):
        if input_obj.get("default_personas") != contract.get("default_personas"):
            errors.append("registered contract default_personas mismatch")
    elif "default_personas" in input_obj:
        errors.append("registered contract unexpected default_personas")
    if job.get("rubric") != contract.get("rubric"):
        errors.append("registered contract rubric mismatch")
    if job.get("output_contract") != contract.get("output_contract"):
        errors.append("registered contract output_contract mismatch")
    if job.get("permissions") != contract.get("permissions"):
        errors.append("registered contract permissions mismatch")

    provenance = job.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("registered contract provenance must be object")
        return errors
    expected_registry_path = str(registry_path.relative_to(HERE)) if registry_path.is_relative_to(HERE) else str(registry_path)
    expected_provenance = {
        "source": "model_contract_pack",
        "registry_schema": registry.get("schema"),
        "registry_version": registry.get("version"),
        "registry_path": expected_registry_path,
        "pack_id": pack_id,
        "model_contract_id": contract_id,
        "input_contract_validated": bool(contract.get("input_contract")),
        "independent_gate": bool(contract.get("independent_gate", False)),
    }
    for key, expected in expected_provenance.items():
        if provenance.get(key) != expected:
            errors.append(f"registered contract provenance mismatch: {key}")
    return errors


def self_test() -> dict[str, Any]:
    from semantic_worker_router import make_contract_job

    fp = "sha256:" + "a" * 64
    good = make_contract_job(
        "quality.production_review",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "fixture", "reader_grip": "very_high"},
        source_session_id="SES-MANAGER",
    )
    project_bound = json.loads(json.dumps(good))
    project_bound["provenance"].update({
        "project_id": "PROJECT-SELF",
        "project_repo": "owner/project",
        "framework_repo": "owner/framework",
        "framework_commit": "f" * 40,
    })
    forged_rubric = json.loads(json.dumps(project_bound))
    forged_rubric["rubric"] = ["manager-authored easy rubric"]
    from semantic_worker_router import fingerprint_for
    forged_rubric["input_fingerprint"] = fingerprint_for(forged_rubric)

    forged_output = json.loads(json.dumps(project_bound))
    forged_output["output_contract"] = {"type": "object", "required": ["confidence", "result"], "properties": {"confidence": {"type": "number"}, "result": {"enum": ["pass", "fail"]}}}
    forged_output["input_fingerprint"] = fingerprint_for(forged_output)

    forged_permissions = json.loads(json.dumps(project_bound))
    forged_permissions["permissions"]["allowed_result_scope"] = "observation"
    forged_permissions["input_fingerprint"] = fingerprint_for(forged_permissions)

    forged_purpose = json.loads(json.dumps(project_bound))
    forged_purpose["input"]["purpose"] = "manager-authored substitute purpose"
    forged_purpose["input_fingerprint"] = fingerprint_for(forged_purpose)

    checks = {
        "canonical_job_passes": not validate_registered_job(good),
        "project_provenance_extensions_allowed": not validate_registered_job(project_bound),
        "forged_rubric_rejected": any("rubric mismatch" in x for x in validate_registered_job(forged_rubric)),
        "forged_output_contract_rejected": any("output_contract mismatch" in x for x in validate_registered_job(forged_output)),
        "forged_permissions_rejected": any("permissions mismatch" in x for x in validate_registered_job(forged_permissions)),
        "forged_purpose_rejected": any("purpose mismatch" in x for x in validate_registered_job(forged_purpose)),
    }
    return {
        "registered_contract_binding_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a NovelForge registered semantic contract job binding")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    val = sub.add_parser("validate-job")
    val.add_argument("--job", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["registered_contract_binding_contract"] == "PASS" else 1
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    errors = validate_registered_job(job)
    print(json.dumps({"valid": not errors, "errors": errors, "authority": False, "model_execution": False}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
