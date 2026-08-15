#!/usr/bin/env python3
"""Machine receipt for Project-owned peer semantic validation.

The peer-chat relay proves job/result/nonce binding. The Project-hosted bridge
adds consuming-Project and exact-Framework provenance. This receipt combines
those already-validated facts into one deterministic object that a production
release consumer can bind to the exact semantic result.

It is evidence, not literary judgment or Canon authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from peer_chat_relay import validate_peer_result
from registered_contract_binding import validate_registered_job

SCHEMA = "novelforge_project_peer_validation_receipt_v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def scalar_fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_receipt(
    packet: dict[str, Any],
    result: dict[str, Any],
    *,
    project_id: str,
    project_repo: str,
    framework_repo: str,
    framework_commit: str,
    issue_number: int,
) -> dict[str, Any]:
    relay_errors = validate_peer_result(packet, result)
    if relay_errors:
        raise ValueError("peer relay validation failed: " + "; ".join(relay_errors))
    job = packet.get("job")
    if not isinstance(job, dict):
        raise ValueError("peer packet job required")
    contract_errors = validate_registered_job(job)
    if contract_errors:
        raise ValueError("registered contract binding failed: " + "; ".join(contract_errors))
    provenance = job.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("job provenance required")
    expected = {
        "project_id": project_id,
        "project_repo": project_repo.lower(),
        "framework_repo": framework_repo.lower(),
        "framework_commit": framework_commit,
    }
    for key, value in expected.items():
        actual = provenance.get(key)
        if key.endswith("_repo") and isinstance(actual, str):
            actual = actual.lower()
        if actual != value:
            raise ValueError(f"job/bridge provenance mismatch: {key}")
    if not isinstance(issue_number, int) or isinstance(issue_number, bool) or issue_number <= 0:
        raise ValueError("issue_number must be positive integer")
    nonce = packet.get("relay_nonce")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("relay nonce required")
    return {
        "schema": SCHEMA,
        "mode": "validate-result",
        "project_id": project_id,
        "project_repo": project_repo.lower(),
        "framework_repo": framework_repo.lower(),
        "framework_commit": framework_commit,
        "issue_number": issue_number,
        "job_id": job.get("job_id"),
        "subject_id": job.get("subject_id"),
        "model_contract_id": (job.get("input") or {}).get("model_contract_id"),
        "input_fingerprint": job.get("input_fingerprint"),
        "result_fingerprint": fingerprint(result),
        "relay_nonce_fingerprint": scalar_fingerprint(nonce),
        "worker_provider": (result.get("worker") or {}).get("provider"),
        "registered_contract_validated": True,
        "peer_relay_validated": True,
        "project_hosted": True,
        "authority": False,
        "model_execution": False,
    }


def validate_receipt(
    receipt: dict[str, Any],
    packet: dict[str, Any],
    result: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA:
        return ["invalid peer validation receipt schema"]
    if receipt.get("mode") != "validate-result":
        errors.append("peer validation receipt mode mismatch")
    if receipt.get("project_hosted") is not True:
        errors.append("peer validation receipt must be project_hosted")
    if receipt.get("registered_contract_validated") is not True:
        errors.append("peer validation receipt missing registered contract proof")
    if receipt.get("peer_relay_validated") is not True:
        errors.append("peer validation receipt missing relay proof")
    if receipt.get("authority") is not False:
        errors.append("peer validation receipt authority must be false")

    job = packet.get("job") if isinstance(packet, dict) else None
    if not isinstance(job, dict):
        errors.append("peer packet job required")
        return errors
    relay_errors = validate_peer_result(packet, result)
    errors += ["peer relay: " + item for item in relay_errors]
    contract_errors = validate_registered_job(job)
    errors += ["registered contract: " + item for item in contract_errors]

    expected = {
        "job_id": job.get("job_id"),
        "subject_id": job.get("subject_id"),
        "model_contract_id": (job.get("input") or {}).get("model_contract_id"),
        "input_fingerprint": job.get("input_fingerprint"),
        "result_fingerprint": fingerprint(result),
        "relay_nonce_fingerprint": scalar_fingerprint(str(packet.get("relay_nonce") or "")),
        "worker_provider": (result.get("worker") or {}).get("provider"),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"peer validation receipt mismatch: {key}")

    provenance = job.get("provenance") or {}
    provenance_expected = {
        "project_id": receipt.get("project_id"),
        "project_repo": receipt.get("project_repo"),
        "framework_repo": receipt.get("framework_repo"),
        "framework_commit": receipt.get("framework_commit"),
    }
    for key, value in provenance_expected.items():
        actual = provenance.get(key)
        if key.endswith("_repo") and isinstance(actual, str):
            actual = actual.lower()
        if actual != value:
            errors.append(f"peer validation receipt provenance mismatch: {key}")
    issue_number = receipt.get("issue_number")
    if not isinstance(issue_number, int) or isinstance(issue_number, bool) or issue_number <= 0:
        errors.append("peer validation receipt issue_number invalid")
    return errors


def self_test() -> dict[str, Any]:
    from peer_chat_relay import build as build_packet
    from semantic_worker_router import make_contract_job

    fp = "sha256:" + "a" * 64
    job = make_contract_job(
        "quality.production_review",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "fixture", "reader_grip": "very_high"},
        source_session_id="SES-MANAGER",
    )
    job["provenance"].update({
        "project_id": "PROJECT-SELF",
        "project_repo": "owner/project",
        "framework_repo": "owner/framework",
        "framework_commit": "f" * 40,
    })
    packet = build_packet(job)
    result = {
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "kind": job["kind"],
        "input_fingerprint": job["input_fingerprint"],
        "status": "completed",
        "worker": {"provider": "chatgpt_peer_chat", "model_or_reviewer": "fixture", "run_reference": packet["relay_nonce"]},
        "judgment": {"confidence": 0.9, "result": "pass", "codes": [], "evidence": ["fixture"], "summary": "fixture", "flatness_risk": "low"},
        "proposals": [],
        "errors": [],
    }
    receipt = build_receipt(
        packet,
        result,
        project_id="PROJECT-SELF",
        project_repo="owner/project",
        framework_repo="owner/framework",
        framework_commit="f" * 40,
        issue_number=7,
    )
    tampered = json.loads(json.dumps(receipt))
    tampered["result_fingerprint"] = "sha256:" + "0" * 64
    checks = {
        "valid_receipt_passes": not validate_receipt(receipt, packet, result),
        "result_tamper_rejected": any("result_fingerprint" in x for x in validate_receipt(tampered, packet, result)),
        "registered_contract_proof_present": receipt["registered_contract_validated"] is True,
        "peer_relay_proof_present": receipt["peer_relay_validated"] is True,
        "project_framework_bound": receipt["project_id"] == "PROJECT-SELF" and receipt["framework_commit"] == "f" * 40,
    }
    return {
        "peer_bridge_receipt_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/validate a Project-owned peer semantic validation receipt")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    build = sub.add_parser("build")
    build.add_argument("--packet", required=True)
    build.add_argument("--result", required=True)
    build.add_argument("--project-id", required=True)
    build.add_argument("--project-repo", required=True)
    build.add_argument("--framework-repo", required=True)
    build.add_argument("--framework-commit", required=True)
    build.add_argument("--issue-number", required=True, type=int)
    build.add_argument("--output")
    args = parser.parse_args()
    if args.command == "self-test":
        value = self_test()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0 if value["peer_bridge_receipt_contract"] == "PASS" else 1
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    receipt = build_receipt(
        packet,
        result,
        project_id=args.project_id,
        project_repo=args.project_repo,
        framework_repo=args.framework_repo,
        framework_commit=args.framework_commit,
        issue_number=args.issue_number,
    )
    text = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
