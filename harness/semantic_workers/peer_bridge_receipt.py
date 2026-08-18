#!/usr/bin/env python3
"""Machine receipt for Project-owned peer semantic validation.

The peer-chat relay proves job/result/nonce binding. The Project-hosted bridge
adds consuming-Project and exact-Framework provenance plus an auditable GitHub
runtime trace. This receipt is deterministic evidence bound to the exact result;
it is not a cryptographic signature, literary judgment, or Canon authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from peer_chat_relay import validate_peer_result
from registered_contract_binding import validate_registered_job

SCHEMA = "quillframe_project_peer_validation_receipt_v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def scalar_fingerprint(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be positive integer")
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty string")
    return value.strip()


def _sha(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value.lower()):
        raise ValueError(f"{name} must be 40-character git sha")
    return value.lower()


def _fingerprint(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    if len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{name} must be sha256:<64 hex>") from exc
    return value


def _repo_slug(value: Any, name: str) -> str:
    value = _nonempty(value, name).lower()
    parts = value.split("/")
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ValueError(f"{name} must be owner/repo")
    return value


def _runtime_trace(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("runtime_trace must be object")
    source = value.get("source", "project_owned_github_actions_bridge")
    if source != "project_owned_github_actions_bridge":
        raise ValueError("runtime_trace source must be project_owned_github_actions_bridge")
    return {
        "source": source,
        "github_run_id": _positive_int(value.get("github_run_id"), "runtime_trace.github_run_id"),
        "github_run_attempt": _positive_int(value.get("github_run_attempt"), "runtime_trace.github_run_attempt"),
        "github_event_name": _nonempty(value.get("github_event_name"), "runtime_trace.github_event_name"),
        "result_comment_id": _positive_int(value.get("result_comment_id"), "runtime_trace.result_comment_id"),
        "workflow_name": _nonempty(value.get("workflow_name"), "runtime_trace.workflow_name"),
        "framework_action_ref": _sha(value.get("framework_action_ref"), "runtime_trace.framework_action_ref"),
        "cryptographic_signature": False,
    }


def build_receipt(
    packet: dict[str, Any],
    result: dict[str, Any],
    *,
    project_id: str,
    project_repo: str,
    framework_repo: str,
    framework_commit: str,
    issue_number: int,
    runtime_trace: dict[str, Any],
) -> dict[str, Any]:
    from peer_chat_relay import validate_peer_result

    job = packet.get("job")
    if not isinstance(job, dict):
        raise ValueError("peer packet job required")
    peer_errors = validate_peer_result(packet, result)
    if peer_errors:
        raise ValueError("peer result invalid: " + "; ".join(peer_errors))
    contract_errors = validate_registered_job(job)
    if contract_errors:
        raise ValueError("registered contract invalid: " + "; ".join(contract_errors))

    provenance = job.get("provenance") or {}
    project_id = _nonempty(project_id, "project_id")
    project_repo = _repo_slug(project_repo, "project_repo")
    framework_repo = _repo_slug(framework_repo, "framework_repo")
    framework_commit = _sha(framework_commit, "framework_commit")
    issue_number = _positive_int(issue_number, "issue_number")
    trace = _runtime_trace(runtime_trace)
    if trace["framework_action_ref"] != framework_commit:
        raise ValueError("runtime_trace.framework_action_ref must equal framework_commit")

    expected_provenance = {
        "project_id": project_id,
        "project_repo": project_repo,
        "framework_repo": framework_repo,
        "framework_commit": framework_commit,
    }
    for key, expected in expected_provenance.items():
        actual = provenance.get(key)
        if key.endswith("_repo") and isinstance(actual, str):
            actual = actual.lower()
        if actual != expected:
            raise ValueError(f"job provenance mismatch for {key}: {actual!r} != {expected!r}")

    return {
        "schema": SCHEMA,
        "project_id": project_id,
        "project_repo": project_repo,
        "framework_repo": framework_repo,
        "framework_commit": framework_commit,
        "issue_number": issue_number,
        "job_id": job["job_id"],
        "subject_id": job["subject_id"],
        "model_contract_id": job["input"]["model_contract_id"],
        "input_fingerprint": _fingerprint(job["input_fingerprint"], "input_fingerprint"),
        "result_fingerprint": fingerprint(result),
        "relay_nonce_fingerprint": scalar_fingerprint(str(packet.get("relay_nonce") or "")),
        "worker_provider": _nonempty((result.get("worker") or {}).get("provider"), "worker.provider"),
        "registered_contract_validated": True,
        "peer_relay_validated": True,
        "runtime_trace": trace,
        "authority": False,
        "permissions": {
            "canon_write": False,
            "framework_write": False,
            "durable_user_taste_write": False,
        },
        "model_execution": True,
    }


def validate_receipt(receipt: Any, packet: dict[str, Any], result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return ["peer validation receipt must be object"]
    if receipt.get("schema") != SCHEMA:
        errors.append("peer validation receipt schema mismatch")
    if receipt.get("authority") is not False:
        errors.append("peer validation receipt must be non-authoritative")
    if receipt.get("permissions") != {
        "canon_write": False,
        "framework_write": False,
        "durable_user_taste_write": False,
    }:
        errors.append("peer validation receipt permissions invalid")
    if receipt.get("registered_contract_validated") is not True:
        errors.append("registered contract validation proof missing")
    if receipt.get("peer_relay_validated") is not True:
        errors.append("peer relay validation proof missing")
    if receipt.get("model_execution") is not True:
        errors.append("peer validation receipt must describe real model execution")

    job = packet.get("job")
    if not isinstance(job, dict):
        errors.append("peer packet job required")
        return errors
    errors += ["peer relay: " + item for item in validate_peer_result(packet, result)]
    errors += ["registered contract: " + item for item in validate_registered_job(job)]

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
    try:
        _positive_int(receipt.get("issue_number"), "issue_number")
        trace = _runtime_trace(receipt.get("runtime_trace"))
        if trace["framework_action_ref"] != receipt.get("framework_commit"):
            errors.append("peer validation receipt runtime framework ref mismatch")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def self_test() -> dict[str, Any]:
    from peer_chat_relay import build as build_packet
    from semantic_worker_router import make_contract_job

    repo_root = Path(__file__).resolve().parents[2]
    evals_root = repo_root / "evals"
    if str(evals_root) not in sys.path:
        sys.path.insert(0, str(evals_root))
    from qualification_test_fixtures import make_qualified_receipt

    fp = "sha256:" + "a" * 64
    qualification = make_qualified_receipt(fp, "CH-SELF")
    job = make_contract_job(
        "quality.production_review",
        "CH-SELF",
        {"candidate_fingerprint": fp, "candidate_text": "fixture", "reader_grip": "very_high"},
        source_session_id="SES-MANAGER",
        qualification_receipt=qualification,
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
        "judgment": {"confidence": 0.9, "result": "pass", "report": "fixture", "evidence_refs": ["fixture"]},
        "proposals": [],
        "errors": [],
    }
    trace = {
        "github_run_id": 123,
        "github_run_attempt": 1,
        "github_event_name": "issue_comment",
        "result_comment_id": 456,
        "workflow_name": "Project peer bridge",
        "framework_action_ref": "f" * 40,
    }
    receipt = build_receipt(
        packet,
        result,
        project_id="PROJECT-SELF",
        project_repo="owner/project",
        framework_repo="owner/framework",
        framework_commit="f" * 40,
        issue_number=7,
        runtime_trace=trace,
    )
    tampered = json.loads(json.dumps(receipt))
    tampered["result_fingerprint"] = "sha256:" + "0" * 64
    fake_ref = json.loads(json.dumps(receipt))
    fake_ref["runtime_trace"]["framework_action_ref"] = "e" * 40
    checks = {
        "valid_receipt_passes": not validate_receipt(receipt, packet, result),
        "result_tamper_rejected": any("result_fingerprint" in x for x in validate_receipt(tampered, packet, result)),
        "runtime_ref_tamper_rejected": any("framework ref mismatch" in x for x in validate_receipt(fake_ref, packet, result)),
        "registered_contract_proof_present": receipt["registered_contract_validated"] is True,
        "peer_relay_proof_present": receipt["peer_relay_validated"] is True,
        "project_framework_bound": receipt["project_id"] == "PROJECT-SELF" and receipt["framework_commit"] == "f" * 40,
        "runtime_trace_auditable": receipt["runtime_trace"]["source"] == "project_owned_github_actions_bridge" and receipt["runtime_trace"]["cryptographic_signature"] is False,
        "qualification_proof_not_exposed_to_peer": "dispatch_proof" not in packet["job"],
        "no_write_authority": not any(receipt["permissions"].values()),
    }
    return {
        "peer_bridge_receipt_contract": "PASS" if all(checks.values()) else "FAIL",
        "schema": SCHEMA,
        "checks": checks,
        "authority": False,
        "model_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["self-test"])
    args = parser.parse_args()
    if args.command == "self-test":
        value = self_test()
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0 if value["peer_bridge_receipt_contract"] == "PASS" else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
